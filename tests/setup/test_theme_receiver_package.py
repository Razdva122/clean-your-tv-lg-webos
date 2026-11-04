import unittest
from scripts.theme_receiver import inject


class ThemeReceiverPackageTest(unittest.TestCase):
    def test_canonical_modules_are_owned_by_each_service_package(self):
        for files in ({'service.js': b'root'}, {'service.js': b'no-root'}):
            result = inject(files)
            self.assertEqual(result['service.js'], files['service.js'])
            self.assertIn(b'./theme-receiver/register', result['theme-receiver.js'])
            self.assertIn(b'exports', result['theme-receiver/core.js'])
            self.assertIn(b'themeReceiverStart', result['theme-receiver/register.js'])
            self.assertIn(b'CYTV_SESSION_EXPIRES', result['theme-receiver/wallpaper-phone.js'])
            self.assertNotIn('theme-receiver.js', files)

    def test_standalone_root_receiver_preserves_the_private_inventory(self):
        source = {'service.js': b"module.exports = require('./theme-receiver');"}
        result = inject(source, standalone=True)
        self.assertEqual(set(result), set(source))
        self.assertIn(b'themeReceiverStart', result['service.js'])
        self.assertNotIn(b"require('./theme-receiver')", result['service.js'])
        self.assertIn(b'CYTV_SESSION_EXPIRES', result['service.js'])
        self.assertNotIn(b"require('./wallpaper-phone')", result['service.js'])
        with self.assertRaises(ValueError):
            inject({'service.js': b'no receiver registration'}, standalone=True)


if __name__ == '__main__':
    unittest.main()
