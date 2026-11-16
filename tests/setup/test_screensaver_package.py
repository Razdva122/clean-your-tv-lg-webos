import json
import unittest

from cytv.package import data_files


class ScreensaverPackageTests(unittest.TestCase):
    def test_only_own_ordinary_popup_is_installed(self):
        from scripts.screensaver_package import build

        package = build()
        self.assertEqual(package, build())
        prefix = "usr/palm/applications/com.cleanyourtv.screensaver/"
        files = data_files(package)
        manifest = json.loads(files[prefix + "appinfo.json"])
        self.assertEqual(manifest["id"], "com.cleanyourtv.screensaver")
        self.assertEqual(manifest["defaultWindowType"], "popup")
        self.assertIs(manifest["visible"], False)
        self.assertFalse(manifest.get("requiredACG"))
        self.assertFalse(manifest.get("privilegedJail"))
        self.assertEqual(set(files), {
            prefix + name for name in
            ("appinfo.json", "index.html", "renderer.js", "settings.js", "style.css", "icon.png",
             "compat-polyfills.js", "compat-LICENSE.txt",
             "backgrounds/alpine-photo.jpg", "backgrounds/ribbon-photo.jpg",
             "backgrounds/alpine-video.mp4", "backgrounds/ribbon-video.mp4",
             "backgrounds/alpine-video-1080p.mp4", "backgrounds/ribbon-video-1080p.mp4",
             "backgrounds/alpine-LICENSE.txt", "backgrounds/ribbon-LICENSE.txt",
             "backgrounds/alpine-CREDITS.txt", "backgrounds/ribbon-CREDITS.txt")
        } | {"usr/palm/packages/com.cleanyourtv.screensaver/packageinfo.json"})

    def test_helper_embeds_canonical_runtime_in_app_jail_only(self):
        import runpy
        from pathlib import Path

        builder = runpy.run_path("scripts/build-cytv.py")
        app = builder["tracked_files"]("native/app")
        app["screensaver-controller.js"] = Path("native/app/screensaver-controller.js").read_bytes()
        svc = builder["tracked_files"]("native/service")
        files = data_files(builder["pack_app"](app, svc, architecture="arm", helper=True))
        prefix = "usr/palm/applications/com.local.nativehome/screensaver/"
        self.assertEqual({name.removeprefix(prefix) for name in files if name.startswith(prefix)}, {
            "controller.js", "policy.js", "transport.js", "media.js", "settings.js"
        })
        self.assertFalse(any("/services/com.local.nativehome.service/screensaver/" in name for name in files))

    def test_home_packages_share_settings_code_and_keep_their_identities(self):
        import runpy
        import sys

        from pathlib import Path
        from scripts.screensaver_package import settings_script

        builder = runpy.run_path("scripts/build-cytv.py")
        home = builder["tracked_files"]("launcher")
        renewal = builder["tracked_files"]("renewal-service")
        files = data_files(builder["pack_app"](home, renewal))
        prefix = "usr/palm/applications/com.gathin.tvhome/"
        app = json.loads(files[prefix + "appinfo.json"])
        self.assertEqual((app["id"], app["defaultWindowType"]), ("com.gathin.tvhome", "card"))
        self.assertIn(prefix + "screensaver-config.js", files)
        self.assertIn(prefix + "screensaver-settings.js", files)
        self.assertNotIn("usr/palm/applications/com.cleanyourtv.screensaver/appinfo.json", files)
        recipe = json.loads(files[prefix + "screensaver-companion/manifest.json"])
        from scripts.screensaver_package import popup_files
        popup_info, popup = popup_files()
        self.assertEqual(recipe['version'], popup_info['version'])
        self.assertEqual({name: files[source] for name, source in recipe['files'].items()}, popup)
        self.assertTrue(all(source.startswith(prefix) for source in recipe['files'].values()))
        root_dir = str(Path("root-edition").resolve())
        sys.path.insert(0, root_dir)
        try:
            root = runpy.run_path("root-edition/preview.py")["prepare"]()
        finally:
            sys.path.remove(root_dir)
        self.assertEqual(root["screensaver-config.js"], settings_script())
        self.assertIn("screensaver-settings.js", root)
        self.assertEqual(json.loads(root["appinfo.json"])["id"], "com.cleanyourtv.root.preview")
