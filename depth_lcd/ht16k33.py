from __future__ import annotations

import logging
import math

LOGGER = logging.getLogger(__name__)


SEGMENTS = {
    "0": 0x3F,
    "1": 0x06,
    "2": 0x5B,
    "3": 0x4F,
    "4": 0x66,
    "5": 0x6D,
    "6": 0x7D,
    "7": 0x07,
    "8": 0x7F,
    "9": 0x6F,
    "-": 0x40,
    " ": 0x00,
}


def format_depth_digits(depth_m: float) -> str:
    """Converte 0 a 99,99 m em quatro dígitos; o ponto é controlado à parte."""
    if not math.isfinite(depth_m) or depth_m < 0:
        return "----"
    hundredths = round(depth_m * 100)
    if hundredths > 9999:
        return "----"
    return f"{hundredths:04d}"


class DepthHT16K33:
    """Controla um display HT16K33 de quatro dígitos pelo barramento I2C."""

    DIGIT_OFFSETS = (0, 2, 6, 8)

    def __init__(
        self,
        bus: int,
        address: int = 0x70,
        brightness: int = 8,
        bus_device=None,
    ) -> None:
        if bus_device is None:
            from smbus2 import SMBus

            bus_device = SMBus(bus)
        self._bus = bus_device
        self._address = address
        self._brightness = max(0, min(15, brightness))
        self._bus.write_byte(self._address, 0x21)
        self._bus.write_byte(self._address, 0x81)
        self._bus.write_byte(self._address, 0xE0 | self._brightness)
        self.show_waiting()

    def _write_digits(self, text: str, decimal_after_second: bool = False) -> None:
        buffer = [0x00] * 16
        for offset, character in zip(self.DIGIT_OFFSETS, text[:4].ljust(4)):
            buffer[offset] = SEGMENTS.get(character, 0x00)
        if decimal_after_second:
            buffer[self.DIGIT_OFFSETS[1]] |= 0x80
        self._bus.write_i2c_block_data(self._address, 0x00, buffer)

    def show_depth(self, depth_m: float, _title: str = "") -> None:
        digits = format_depth_digits(depth_m)
        self._write_digits(digits, decimal_after_second=digits != "----")

    def show_waiting(self) -> None:
        self._write_digits("----")

    def show_test(self) -> None:
        self._write_digits("8888", decimal_after_second=True)

    def close(self) -> None:
        try:
            self._write_digits("    ")
        except Exception:
            LOGGER.exception("Erro ao apagar o HT16K33")
        try:
            self._bus.close()
        except Exception:
            LOGGER.exception("Erro ao fechar o barramento do HT16K33")
