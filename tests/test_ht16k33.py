import unittest
from unittest.mock import MagicMock

from depth_lcd.ht16k33 import DepthHT16K33, format_depth_digits


class HT16K33FormatTests(unittest.TestCase):
    def test_formats_two_digits_before_and_after_decimal(self):
        self.assertEqual(format_depth_digits(2.35), "0235")
        self.assertEqual(format_depth_digits(12.34), "1234")
        self.assertEqual(format_depth_digits(99.99), "9999")

    def test_rejects_values_outside_display_range(self):
        self.assertEqual(format_depth_digits(-0.01), "----")
        self.assertEqual(format_depth_digits(100.0), "----")

    def test_places_decimal_point_after_second_digit(self):
        bus = MagicMock()
        display = DepthHT16K33(6, 0x70, 8, bus_device=bus)
        display.show_depth(2.35)

        buffer = bus.write_i2c_block_data.call_args.args[2]
        self.assertEqual(buffer[0], 0x3F)
        self.assertEqual(buffer[2], 0x5B | 0x80)
        self.assertEqual(buffer[6], 0x4F)
        self.assertEqual(buffer[8], 0x6D)


if __name__ == "__main__":
    unittest.main()
