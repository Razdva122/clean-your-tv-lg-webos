"""Advisory installer update check; never downloads or executes an installer."""
from http.client import HTTPException
import json
import re
import ssl
import sys
from urllib.request import Request, urlopen
import webbrowser

from . import __version__, prompts
from .errors import UserError

REPOSITORY = 'https://github.com/Razdva122/clean-your-tv-lg-webos'
RELEASES = REPOSITORY + '/releases/latest'
API = 'https://api.github.com/repos/Razdva122/clean-your-tv-lg-webos/releases/latest'
DOWNLOAD = 'Open GitHub and download the latest version'
CONTINUE = 'No, install this version'
PROMPT = 'Installer version choice: '


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})', value):
        raise ValueError('Invalid installer version')
    return tuple(map(int, value.split('.')))


def latest(current=__version__):
    context = ssl.create_default_context()
    if sys.platform == 'darwin':
        # Frozen Python's build-host CA paths may not exist on the user's Mac.
        context.load_verify_locations(cafile='/etc/ssl/cert.pem')

    def read(url):
        request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'CleanYourTV-installer'})
        with urlopen(request, timeout=3, context=context) as response:
            data = response.read(262145)
        if len(data) > 262144:
            raise ValueError('Release metadata too large')
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError('Invalid release metadata')
        return value

    release = read(API)
    tag = release.get('tag_name')
    if (release.get('draft') is not False or release.get('prerelease') is not False
            or not isinstance(tag, str) or not tag.startswith('v')):
        raise ValueError('Not a stable release')
    version(tag[1:])
    # Pin metadata to the selected tag; /latest could change between requests.
    build = read(REPOSITORY + '/releases/download/' + tag + '/BUILD-INFO.json')
    versions = build.get('versions')
    if build.get('tag') != tag or not isinstance(versions, dict):
        raise ValueError('Release metadata mismatch')
    candidate = versions.get('cytv')
    return candidate if version(candidate) > version(current) else None


def offer(ask, write, non_interactive=False, use_bundled=False):
    write('Checking for installer updates…')
    try:
        candidate = latest()
    except (OSError, ValueError, HTTPException, RecursionError):
        write('Could not check for installer updates.')
        write('You can continue with this installer.')
        return True
    if candidate is None:
        return True
    write.heading('A newer installer is available')
    write(f'You are using installer {__version__}. GitHub has installer {candidate}.')
    write(RELEASES)
    if non_interactive:
        if use_bundled:
            return True
        raise UserError('Download the latest installer from GitHub, or explicitly use --use-bundled-version.')
    write.option(1, DOWNLOAD)
    write.option(2, CONTINUE)
    choice = prompts.number(ask, write, PROMPT, 1, 2)
    if choice == 2:
        return True
    if getattr(write, 'frontend', 'console') != 'desktop':
        try:
            webbrowser.open(RELEASES)
        except (OSError, webbrowser.Error):
            pass  # The fixed URL above remains usable without a browser.
    write('Download the latest installer from the GitHub page and run it. Installation has not started.')
    return False
