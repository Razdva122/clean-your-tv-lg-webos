"""Graphics selection trusts the explicit UHD capability, never display geometry."""
import unittest


class GraphicsTests(unittest.TestCase):
    def test_exact_capability_values_choose_package_resolution(self):
        from cytv import graphics
        for value, expected in [(True, '1920x1080'), ('true', '1920x1080'),
                                (False, '1280x720'), ('false', '1280x720')]:
            with self.subTest(value=value):
                self.assertEqual(graphics.resolution({'returnValue': True, 'UHD': value}), expected)

    def test_missing_rejected_and_ambiguous_capability_fail_closed(self):
        from cytv import graphics
        for info in [None, [], {}, {'UHD': True}, {'returnValue': False, 'UHD': True},
                     {'returnValue': 1, 'UHD': True},
                     *[{'returnValue': True, 'UHD': value} for value in [None, 0, 1, 'TRUE', 'False', [], {}]],
                     {'returnValue': True, 'modelName': 'OLED C3', 'width': 1920, 'height': 1080}]:
            with self.subTest(info=info), self.assertRaises(ValueError):
                graphics.resolution(info)


if __name__ == '__main__': unittest.main()
