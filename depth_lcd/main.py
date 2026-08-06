from __future__ import annotations

import json
import logging
import os
import threading
import time
from urllib.request import urlopen

import uvicorn

from .depth import depth_from_mavlink2rest
from .ht16k33 import DepthHT16K33
from .lcd import DepthLCD
from .state import AppState
from .web import create_app

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAVLINK2REST_URL = os.getenv(
    "MAVLINK2REST_URL", "http://host.docker.internal:6040/v1/mavlink"
)
DEPTH_SOURCE = os.getenv("DEPTH_SOURCE", "GLOBAL_POSITION_INT").upper()
DISPLAY_TYPE = os.getenv("DISPLAY_TYPE", "LCD").strip().upper()
I2C_BUS = int(os.getenv("I2C_BUS", "6"), 0)
LCD_ADDRESS = int(os.getenv("LCD_ADDRESS", "0x27"), 0)
LCD_EXPANDER = os.getenv("LCD_EXPANDER", "PCF8574")
LCD_TITLE = os.getenv("LCD_TITLE", "Profundidade:")
HT16K33_ADDRESS = int(os.getenv("HT16K33_ADDRESS", "0x70"), 0)
HT16K33_BRIGHTNESS = int(os.getenv("HT16K33_BRIGHTNESS", "8"), 0)
UPDATE_INTERVAL = max(0.1, float(os.getenv("UPDATE_INTERVAL", "0.5")))
STALE_TIMEOUT = max(1.0, float(os.getenv("STALE_TIMEOUT", "5")))
DISPLAY_RETRY_INTERVAL = max(2.0, float(os.getenv("DISPLAY_RETRY_INTERVAL", "5")))

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("depth-display")


def create_display():
    """Cria somente o driver selecionado nas configurações da extensão."""
    if DISPLAY_TYPE == "LCD":
        return DepthLCD(I2C_BUS, LCD_ADDRESS, LCD_EXPANDER)
    if DISPLAY_TYPE == "HT16K33":
        return DepthHT16K33(I2C_BUS, HT16K33_ADDRESS, HT16K33_BRIGHTNESS)
    raise ValueError("DISPLAY_TYPE deve ser LCD ou HT16K33")


class DepthWorker:
    """Recebe MAVLink e atualiza o display sem bloquear o servidor web."""

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
        display_address = LCD_ADDRESS if DISPLAY_TYPE == "LCD" else HT16K33_ADDRESS
        LOGGER.info(
            "Iniciando: MAVLink2Rest=%s, fonte=%s, display=%s, I2C=%d, endereco=0x%02X",
            MAVLINK2REST_URL,
            DEPTH_SOURCE,
            DISPLAY_TYPE,
            I2C_BUS,
            display_address,
        )
        display = None
        last_display_attempt = 0.0
        last_update = 0.0

        try:
            while not self.stop_event.is_set():
                now = time.monotonic()

                if display is None and now - last_display_attempt >= DISPLAY_RETRY_INTERVAL:
                    last_display_attempt = now
                    try:
                        display = create_display()
                        self.state.set_display_status(True)
                        LOGGER.info(
                            "Display %s conectado em /dev/i2c-%d, endereco 0x%02X",
                            DISPLAY_TYPE,
                            I2C_BUS,
                            display_address,
                        )
                    except Exception as error:
                        self.state.set_display_status(False, str(error))
                        LOGGER.warning("Display %s indisponivel: %s", DISPLAY_TYPE, error)

                try:
                    depth_m, source = self.read_depth()
                    self.state.update_depth(depth_m, source)
                    if display is not None and now - last_update >= UPDATE_INTERVAL:
                        try:
                            display.show_depth(depth_m, self.state.snapshot()["title"])
                            last_update = now
                        except Exception as error:
                            LOGGER.warning("Falha ao escrever no display: %s", error)
                            self.state.set_display_status(False, str(error))
                            display.close()
                            display = None
                except Exception as error:
                    LOGGER.debug("MAVLink2Rest ainda sem dados: %s", error)

                snapshot = self.state.snapshot()
                if snapshot["age_seconds"] is not None and snapshot["age_seconds"] > STALE_TIMEOUT:
                    self.state.set_mavlink_disconnected()

                if display is not None and self.state.consume_test_request():
                    try:
                        display.show_test()
                        last_update = now
                    except Exception as error:
                        self.state.set_display_status(False, str(error))
                        display.close()
                        display = None

                self.stop_event.wait(UPDATE_INTERVAL)
        finally:
            if display is not None:
                display.close()

    def read_depth(self) -> tuple[float, str]:
        """Lê a árvore do MAVLink2Rest e encontra a mensagem configurada."""
        with urlopen(MAVLINK2REST_URL, timeout=2) as response:
            payload = json.load(response)
        sample = depth_from_mavlink2rest(payload, DEPTH_SOURCE)
        return sample.depth_m, sample.source


def run() -> None:
    state = AppState(LCD_TITLE, DISPLAY_TYPE)
    worker = DepthWorker(state)
    app = create_app(state, worker)
    uvicorn.run(app, host="0.0.0.0", port=80, log_level=LOG_LEVEL.lower())


if __name__ == "__main__":
    run()
