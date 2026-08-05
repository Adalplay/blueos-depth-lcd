import unittest
from types import SimpleNamespace

from depth_lcd.depth import depth_from_message


class Message(SimpleNamespace):
    def get_type(self):
        return self.message_type


class DepthConversionTests(unittest.TestCase):
    def test_global_position_depth(self):
        msg = Message(message_type="GLOBAL_POSITION_INT", relative_alt=-1234)
        sample = depth_from_message(msg)
        self.assertAlmostEqual(sample.depth_m, 1.234)

    def test_local_position_depth(self):
        msg = Message(message_type="LOCAL_POSITION_NED", z=2.5)
        sample = depth_from_message(msg)
        self.assertAlmostEqual(sample.depth_m, 2.5)

    def test_vfr_hud_depth(self):
        msg = Message(message_type="VFR_HUD", alt=-3.75)
        sample = depth_from_message(msg)
        self.assertAlmostEqual(sample.depth_m, 3.75)

    def test_preferred_source_filters_messages(self):
        msg = Message(message_type="VFR_HUD", alt=-1)
        self.assertIsNone(depth_from_message(msg, "GLOBAL_POSITION_INT"))


if __name__ == "__main__":
    unittest.main()

