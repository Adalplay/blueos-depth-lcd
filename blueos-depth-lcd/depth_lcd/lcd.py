from __future__ import annotations

import logging

from RPLCD.i2c import CharLCD

LOGGER = logging.getLogger(__name__)


class DepthLCD:
    def __init__(self, bus: int, address: int, expander: str = "PCF8574") -> None:
        self._lcd = CharLCD(
            i2c_expander=expander,
            address=address,
            port=bus,
            cols=16,
            rows=2,
            charmap="A00",
            auto_linebreaks=False,
        )
        self.show_lines("Depth LCD", "Aguardando...")

    def show_depth(self, depth_m: float, _source: str) -> None:
        self.show_lines("Profundidade:", f"{depth_m:.2f} metros")

    def show_lines(self, first: str, second: str) -> None:
        for row, text in enumerate((first, second)):
            self._lcd.cursor_pos = (row, 0)
            self._lcd.write_string(text[:16].ljust(16))

    def close(self) -> None:
        try:
            self._lcd.clear()
            self._lcd.close(clear=False)
        except Exception:
            LOGGER.exception("Erro ao fechar o LCD")
