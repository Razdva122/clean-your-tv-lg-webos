"""Build the standalone screensaver popup for development testing."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cytv.package import ipk
from scripts.tv_web_build import compile_web

APP_ID = "com.cleanyourtv.screensaver"
WEB_FILES = ("appinfo.json", "index.html", "renderer.js", "settings.js", "style.css")
BACKGROUNDS = {
    "alpine-photo.jpg": "alpine/assets/bachsee.jpg",
    "ribbon-photo.jpg": "ribbon/assets/wallpaper.jpg",
    "alpine-video.mp4": "alpine/assets/wallpaper-4k.mp4",
    "ribbon-video.mp4": "ribbon/assets/wallpaper-4k.mp4",
    "alpine-video-1080p.mp4": "alpine/assets/wallpaper-1080p.mp4",
    "ribbon-video-1080p.mp4": "ribbon/assets/wallpaper-1080p.mp4",
}
RUNTIME_FILES = ("controller.js", "policy.js", "transport.js", "media.js", "settings.js")


def runtime_files(prefix="screensaver/"):
    return {prefix + name: (ROOT / "screensaver" / name).read_bytes() for name in RUNTIME_FILES}


def settings_script():
    return (ROOT / "screensaver/settings.js").read_bytes()


def root_bundle(source):
    """Inline the fixed Root JS closure without new private-service files."""
    needle = b"require('./screensaver-register')"
    if source.count(needle) != 1:
        raise ValueError("Expected a single Root screensaver registration")
    parts = runtime_files("./screensaver-runtime/")
    for name, path in {
        "screensaver": "root-edition/service/screensaver.js",
        "screensaver-register": "root-edition/service/screensaver-register.js",
        "screensaver-lg": "native/app/screensaver-lg.js",
    }.items():
        parts["./" + name + ".js"] = (ROOT / path).read_bytes()
    factories = b",\n".join(
        json.dumps(name[:-3]).encode() + b":function(require,module,exports){\n" + data + b"\n}"
        for name, data in sorted(parts.items())
    )
    inline = (b"(function(nativeRequire){var modules={" + factories + b"};var cache={};"
              b"function load(id){if(!Object.prototype.hasOwnProperty.call(modules,id)) throw Error('Missing screensaver module');"
              b"if(cache[id])return cache[id].exports;var unit={exports:{}};cache[id]=unit;"
              b"modules[id](function(name){return name.slice(0,2)==='./'?load(id.slice(0,id.lastIndexOf('/')+1)+name.slice(2)):nativeRequire(name);},unit,unit.exports);"
              b"return unit.exports;}return load;})(require)")
    for name in parts:
        module = name[:-3].encode()
        source = source.replace(b"require('" + module + b"')", b"loadScreensaver('" + module + b"')")
    strict = b"'use strict';\n"
    if not source.startswith(strict):
        raise ValueError("Unexpected Root service preamble")
    return strict + b"var loadScreensaver=" + inline + b";\n" + source[len(strict):]


def popup_files():
    files = {name: (ROOT / "screensaver" / name).read_bytes() for name in WEB_FILES}
    files["icon.png"] = (ROOT / "launcher/brand-v2-icon.png").read_bytes()
    files.update({"backgrounds/" + name: (ROOT / "themes" / source).read_bytes()
                  for name, source in BACKGROUNDS.items()})
    for theme in ("alpine", "ribbon"):
        for name in ("LICENSE.txt", "CREDITS.txt"):
            files["backgrounds/" + theme + "-" + name] = (ROOT / "themes" / theme / name).read_bytes()
    info = json.loads(files["appinfo.json"])
    if (info["id"] != APP_ID or info.get("defaultWindowType") != "popup"
            or info.get("requiredACG") or info.get("privilegedJail")):
        raise ValueError("Unexpected screensaver popup permissions or identity")
    return info, compile_web(files)


def add_root_resources(payload, prefix):
    info, popup = popup_files()
    # The Root package already contains several bit-identical theme assets.
    # The manifest and any missing resources belong to Root's verified DATA.
    index = {}
    for path, data in sorted(payload.items()):
        if path.startswith(prefix):
            index.setdefault(hashlib.sha256(data).digest(), path)
    sources = {}
    for name, data in sorted(popup.items()):
        source = index.get(hashlib.sha256(data).digest())
        if source is None or payload[source] != data:
            source = prefix + "screensaver-companion/files/" + name
            payload[source] = data
        sources[name] = source
    payload[prefix + "screensaver-companion/manifest.json"] = json.dumps({
        "schema": 1, "version": info["version"], "files": sources,
    }, sort_keys=True).encode()


def build():
    info, files = popup_files()
    prefix = "usr/palm/applications/" + APP_ID + "/"
    payload = {prefix + name: data for name, data in files.items()}
    payload["usr/palm/packages/" + APP_ID + "/packageinfo.json"] = json.dumps({
        "id": APP_ID, "version": info["version"], "app": APP_ID, "services": []
    }).encode()
    return ipk(APP_ID, info["version"], payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_bytes(build())
