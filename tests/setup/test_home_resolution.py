"""Explicit HD graphics packaging preserves the default FHD source manifests."""
import inspect
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from scripts.tv_web_build import stage

ROOT = Path(__file__).resolve().parents[2]


class HomeResolution(unittest.TestCase):
    def test_explicit_hd_staging_and_unchanged_source(self):
        self.assertIn('resolution', inspect.signature(stage).parameters, 'HD staging must be an explicit validated build option')
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp)/'source', Path(tmp)/'output'
            source.mkdir()
            original = json.dumps({'id':'test.app','resolution':'1920x1080'})
            (source/'appinfo.json').write_text(original)
            stage(source, output, compiler=lambda files: files, resolution='1280x720')
            self.assertEqual(json.loads((output/'appinfo.json').read_text())['resolution'], '1280x720')
            self.assertEqual((source/'appinfo.json').read_text(), original)
            stage(source, output, compiler=lambda files: files)
            self.assertEqual((output/'appinfo.json').read_text(), original)
            for invalid in ('3840x2160', '../appinfo.json', '', None):
                if invalid is None:
                    continue  # None retains the source manifest.
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    stage(source, output, compiler=lambda files: files, resolution=invalid)
                self.assertEqual((output/'appinfo.json').read_text(), original)

    def test_root_staging_uses_the_same_explicit_resolution(self):
        prepare = runpy.run_path(str(ROOT/'root-edition/preview.py'))['prepare']
        self.assertIn('resolution', inspect.signature(prepare).parameters)
        self.assertEqual(json.loads(prepare(resolution='1280x720')['appinfo.json'])['resolution'], '1280x720')
        self.assertEqual(json.loads(prepare()['appinfo.json'])['resolution'], '1920x1080')
        with self.assertRaises(ValueError):
            prepare(resolution='3840x2160')
