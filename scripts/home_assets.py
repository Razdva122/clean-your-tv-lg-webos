"""Explicit shared Home theme resources for packages and browser previews."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keep this allowlist explicit: never copy arbitrary workspace files into packages.
THEME_FILES = [
    'wallpaper.js',
    'wallpaper.css',
    'wallpaper-panel.js',
    'wallpaper-panel.css',
    'wallpaper-locales.js',
    'wallpaper-media-cache.js',
    'personal-wallpaper.js',
    'wallpaper-library.js',
    'wallpaper-stream.js',
    'wallpapers/black-hole-stream.mp4',
    'wallpaper-qr.js',
    'theme-data.js',
    'theme-store.js',
    'theme-manager.js',
    'theme-receiver.js',
    'theme-panel.js',
    'theme-panel.css',
    'theme-locales.js',
    'builtin-theme-files.json',
] + json.loads((ROOT / 'launcher/builtin-theme-files.json').read_text())
