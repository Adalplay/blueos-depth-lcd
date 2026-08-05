from __future__ import annotations

import logging
import json
import os
import threading
import time
from urllib.request import urlopen

import uvicorn

from .depth import depth_from_mavlink2rest
from .lcd import DepthLCD
from .state import AppState
from .web import create_app

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAVLINK2REST_URL = os.getenv(
    "MAVLINK2REST_URL", "http://host.docker.internal:6040/v1/mavlink"
)
DEPTH_SOURCE = os.getenv("DEPTH_SOURCE", "GLOBAL_POSITION_INT").upper()
I2C_BUS = int(os.getenv("I2C_BUS", "6"), 0)
LCD_ADDRESS = int(os.getenv("LCD_ADDRESS", "0x27"), 0)
LCD_EXPANDER = os.getenv("LCD_EXPANDER", "PCF8574")
LCD_TITLE = os.getenv("LCD_TITLE", "Profundidade:")
UPDATE_INTERVAL = max(0.1, float(os.getenv("UPDATE_INTERVAL", "0.5")))
STALE_TIMEOUT = max(1.0, float(os.getenv("STALE_TIMEOUT", "5")))
LCD_RETRY_INTERVAL = max(2.0, float(os.getenv("LCD_RETRY_INTERVAL", "5")))

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("depth-lcd")


class DepthWorker:
    """Recebe MAVLink e atualiza o LCD sem bloquear o servidor web."""

    def __init__(self, state: AppState) -> None:
        self.state = state
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self.run, name="depth-worker", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)

    def run(self) -> None:
        LOGGER.info(
            "Iniciando: MAVLink2Rest=%s, fonte=%s, I2C=%d, LCD=0x%02X",
            MAVLINK2REST_URL,
            DEPTH_SOURCE,
            I2C_BUS,
            LCD_ADDRESS,
        )
        lcd: DepthLCD | None = None
        last_lcd_attempt = 0.0
        last_display = 0.0

        try:
            while not self.stop_event.is_set():
                now = time.monotonic()

                if lcd is None and now - last_lcd_attempt >= LCD_RETRY_INTERVAL:
                    last_lcd_attempt = now
                    try:
                        lcd = DepthLCD(I2C_BUS, LCD_ADDRESS, LCD_EXPANDER)
                        self.state.set_lcd_status(True)
                        LOGGER.info("LCD conectado em /dev/i2c-%d, endereço 0x%02X", I2C_BUS, LCD_ADDRESS)
                    except Exception as error:
                        self.state.set_lcd_status(False, str(error))
                        LOGGER.warning("LCD indisponível: %s", error)

                try:
                    depth_m, source = self.read_depth()
                    self.state.update_depth(depth_m, source)
                    if lcd is not None and now - last_display >= UPDATE_INTERVAL:
                        try:
                            lcd.show_depth(depth_m, self.state.snapshot()["title"])
                            last_display = now
                        except Exception as error:
                            LOGGER.warning("Falha ao escrever no LCD: %s", error)
                            self.state.set_lcd_status(False, str(error))
                            lcd.close()
                            lcd = None
                except Exception as error:
                    LOGGER.debug("MAVLink2Rest ainda sem dados: %s", error)

                snapshot = self.state.snapshot()
                if snapshot["age_seconds"] is not None and snapshot["age_seconds"] > STALE_TIMEOUT:
                    self.state.set_mavlink_disconnected()

                if lcd is not None and self.state.consume_test_request():
                    try:
                        lcd.show_lines("Teste do LCD", "Funcionando!")
                        last_display = now
                    except Exception as error:
                        self.state.set_lcd_status(False, str(error))
                        lcd.close()
                        lcd = None
                self.stop_event.wait(UPDATE_INTERVAL)
        finally:
            if lcd is not None:
                lcd.close()

    def read_depth(self) -> tuple[float, str]:
        """Lê a árvore do MAVLink2Rest e encontra a mensagem configurada."""
        with urlopen(MAVLINK2REST_URL, timeout=2) as response:
            payload = json.load(response)

        sample = depth_from_mavlink2rest(payload, DEPTH_SOURCE)
        return sample.depth_m, sample.source


def run() -> None:
    state = AppState(LCD_TITLE)
    worker = DepthWorker(state)
    app = create_app(state, worker)
    uvicorn.run(app, host="0.0.0.0", port=80, log_level=LOG_LEVEL.lower())


if __name__ == "__main__":
    run()
