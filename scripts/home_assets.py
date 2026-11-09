"""Explicit shared Home theme resources for packages and browser previews."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keep this allowlist explicit: never copy arbitrary workspace files into packages.
WEATHER_FILES = ['weather-transport.js', 'weather-data.js', 'weather-icons.js', 'weather.js', 'weather-locales.js', 'weather.css'] + ['weather-icons/LICENSE-METEOCONS.txt', 'weather-icons/fill-clear-day.svg', 'weather-icons/fill-clear-night.svg', 'weather-icons/fill-drizzle.svg', 'weather-icons/fill-fog.svg', 'weather-icons/fill-overcast.svg', 'weather-icons/fill-partly-cloudy-day.svg', 'weather-icons/fill-partly-cloudy-night.svg', 'weather-icons/fill-rain.svg', 'weather-icons/fill-snow.svg', 'weather-icons/fill-thunderstorms.svg', 'weather-icons/monochrome-clear-day.svg', 'weather-icons/monochrome-clear-night.svg', 'weather-icons/monochrome-drizzle.svg', 'weather-icons/monochrome-fog.svg', 'weather-icons/monochrome-overcast.svg', 'weather-icons/monochrome-partly-cloudy-day.svg', 'weather-icons/monochrome-partly-cloudy-night.svg', 'weather-icons/monochrome-rain.svg', 'weather-icons/monochrome-snow.svg', 'weather-icons/monochrome-thunderstorms.svg']

THEME_FILES = WEATHER_FILES + ['tv-name.js', 'tv-name-config.js', 'tv-name-locales.js', 'tv-name.css'] + [
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
