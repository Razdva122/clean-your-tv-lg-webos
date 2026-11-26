"""Explicit shared Home theme resources for packages and browser previews."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Keep this allowlist explicit: never copy arbitrary workspace files into packages.
WEATHER_FILES = ['weather-transport.js', 'weather-data.js', 'weather-icons.js', 'weather.js', 'weather-locales.js', 'weather.css'] + ['weather-icons/LICENSE-METEOCONS.txt', 'weather-icons/fill-clear-day.svg', 'weather-icons/fill-clear-night.svg', 'weather-icons/fill-drizzle.svg', 'weather-icons/fill-fog.svg', 'weather-icons/fill-overcast.svg', 'weather-icons/fill-partly-cloudy-day.svg', 'weather-icons/fill-partly-cloudy-night.svg', 'weather-icons/fill-rain.svg', 'weather-icons/fill-snow.svg', 'weather-icons/fill-thunderstorms.svg', 'weather-icons/monochrome-clear-day.svg', 'weather-icons/monochrome-clear-night.svg', 'weather-icons/monochrome-drizzle.svg', 'weather-icons/monochrome-fog.svg', 'weather-icons/monochrome-overcast.svg', 'weather-icons/monochrome-partly-cloudy-day.svg', 'weather-icons/monochrome-partly-cloudy-night.svg', 'weather-icons/monochrome-rain.svg', 'weather-icons/monochrome-snow.svg', 'weather-icons/monochrome-thunderstorms.svg']

THEME_FILES = WEATHER_FILES + [
    'install-settings.js', 'browser-profile.js',
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
    'wallpapers/alpine-preview.jpg',
    'wallpapers/ribbon-preview.jpg',
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

# Root Home's explicit source inventory doubles as the common portion of the
# launcher inventory when building a source export without a Git index.
ROOT_HOME_FILES = (
    'appinfo.json', 'home-presentation.js', 'viewport.js', 'release-notes.js',
    'system-updates.js', 'index.html', 'app.js', 'app-library.js', 'input-sources.js',
    'input-preview.js', 'i18n.js', 'catalogs.js', 'i18n.css', 'style.css',
    'theme-defaults.css', 'theme-policy.js', 'theme-runtime.js', 'home-layout.js',
    'layout-panel.js', 'settings-categories.js', 'layout-panel.css', 'settings-panel.css',
    'brand-v2-icon.png', 'brand-v2-largeIcon.png', 'splash.png',
    'fonts/outfit-300.ttf', 'fonts/outfit-400.ttf', 'fonts/outfit-500.ttf', 'fonts/outfit-700.ttf',
    'fonts/NotoSans.ttf', 'fonts/NotoSans-OFL.txt',
    'fonts/NotoSansDevanagari.ttf', 'fonts/NotoSansDevanagari-OFL.txt',
    'fonts/NotoSansKR.ttf', 'fonts/NotoSansKR-OFL.txt',
    'fonts/NotoSansSC.ttf', 'fonts/NotoSansSC-OFL.txt',
    'fonts/NotoSansTC.ttf', 'fonts/NotoSansTC-OFL.txt', 'fonts/OFL.txt',
    *THEME_FILES,
    'screensaver-idle.js', 'screensaver-personal.js', 'screensaver-settings.js',
    'screensaver-settings.css',
)
LAUNCHER_FILES = ROOT_HOME_FILES + (
    'config.js', 'fonts/outfit.ttf', 'helper-control.js', 'icon.png', 'largeIcon.png',
    'native-bootstrap.js', 'profile-bootstrap.js', 'renewal-panel.css', 'renewal-panel.js',
    'update-panel.js', 'user-data.js',
)
ROOT_UI_FILES = (
    'root-audio-locales.js', 'root-audio.js', 'root-locales.js', 'root-exit.js',
    'root-firmware-control.js', 'root-firmware.js', 'root-settings.js', 'root-settings.css',
    'tv-name.js', 'root-profile-data.js', 'root-profile.js', 'root-updates.js',
)
