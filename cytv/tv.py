"""SSAP pairing and fresh inventory, with icons embedded as local data URLs."""
import base64
from io import BytesIO
import json
import re
from pathlib import Path
import ssl
import time
import urllib.parse
import urllib.request

from .state import private_write
from .transport import NoRedirect
from .errors import UserError, TVConnectionError, TVNotReady


MAX_EMBEDDED_ICON = 256 * 1024
MAX_ICON_DOWNLOAD = 8 * 1024 * 1024
ICON_DOWNLOAD_BUDGET = 24 * 1024 * 1024
RESIZED_ICON_BUDGET = 512 * 1024
MAX_ICON_DIMENSION = 2048
RESIZED_ICON_DIMENSION = 192


def connection_closed(error):
    frame = error.rcvd
    if frame and frame.code == 1008 and frame.reason == 'Try Again Later (EWS)':
        return TVNotReady()
    return TVConnectionError('TV remote-control connection closed. Keep the TV on and check its pairing request.',
                             close_code=frame.code if frame else None)


def tv_context(compatible=False):
    # Same LG self-signed local control endpoint used by the existing lgtv.py.
    context = ssl.create_default_context()
    context.check_hostname, context.verify_mode = False, ssl.CERT_NONE
    if compatible:
        # Older TVs offer static RSA with AES-GCM instead of ECDHE/DHE.
        # Keep the default suites first, TLS 1.2 minimum and security level.
        suites = ':'.join(cipher['name'] for cipher in context.get_ciphers())
        context.set_ciphers(suites + ':AES128-GCM-SHA256:AES256-GCM-SHA384')
    return context


def fetch_icon(url, limit):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                       urllib.request.HTTPSHandler(context=tv_context()))
    with opener.open(url, timeout=5) as response:
        return response.read(limit + 1)


def check_icon_dimensions(width, height):
    if not (0 < width <= MAX_ICON_DIMENSION and 0 < height <= MAX_ICON_DIMENSION):
        raise ValueError('Invalid icon dimensions')


def resize_android_icon(data):
    from java import jclass

    factory = jclass('android.graphics.BitmapFactory')
    options = jclass('android.graphics.BitmapFactory$Options')()
    options.inJustDecodeBounds = True
    factory.decodeByteArray(data, 0, len(data), options)
    width, height = options.outWidth, options.outHeight
    check_icon_dimensions(width, height)
    ratio = min(1, RESIZED_ICON_DIMENSION / max(width, height))
    bitmap = factory.decodeByteArray(data, 0, len(data))
    if bitmap is None:
        raise ValueError('Invalid icon image')
    try:
        scaled = jclass('android.graphics.Bitmap').createScaledBitmap(
            bitmap, max(1, round(width * ratio)), max(1, round(height * ratio)), True)
        try:
            output = jclass('java.io.ByteArrayOutputStream')()
            png = jclass('android.graphics.Bitmap$CompressFormat').PNG
            if not scaled.compress(png, 100, output):
                raise ValueError('Unable to resize icon')
            return bytes(output.toByteArray())
        finally:
            if scaled != bitmap:
                scaled.recycle()
    finally:
        bitmap.recycle()


def resize_icon(data):
    try:
        from PIL import Image
    except ImportError:
        return resize_android_icon(data)
    try:
        with Image.open(BytesIO(data), formats=('PNG', 'JPEG', 'WEBP')) as source:
            check_icon_dimensions(*source.size)
            image = source.convert('RGBA')
            image.thumbnail((RESIZED_ICON_DIMENSION, RESIZED_ICON_DIMENSION))
            output = BytesIO()
            image.save(output, 'PNG')
            return output.getvalue()
    except Image.DecompressionBombError as exc:
        raise ValueError('Invalid icon dimensions') from exc


def include_tuner(launchpoints, installed):
    """Supplement launch points only with the tuner the TV reports installed."""
    if not isinstance(launchpoints, list) or len(launchpoints) > 300 or not isinstance(installed, list) or len(installed) > 300:
        return launchpoints
    for app in installed:
        if (isinstance(app, dict) and app.get('id') == 'com.webos.app.livetv'
                and isinstance(app.get('title'), str) and 0 < len(app['title']) <= 256):
            return [dict(app, hidden=False)] + [a for a in launchpoints
                                               if not isinstance(a, dict) or a.get('id') != app['id']][:299]
    return launchpoints


class Inventory:
    def __init__(self, host, fallback, fetch=None):
        self.host, self.fallback, self.fetch = host, fallback, fetch
        self.download_remaining = ICON_DOWNLOAD_BUDGET
        self.resize_remaining = RESIZED_ICON_BUDGET
        self.icon_diagnostics = {'schema': 1, 'status': 'reading', **dict.fromkeys(
            ('apps', 'embedded', 'fallback', 'missing_uri', 'rejected_uri', 'fetch_failed', 'invalid_image'), 0)}

    def icon(self, app, alternatives=()):
        fields = ('extraLargeIcon', 'largeIcon', 'mediumLargeIcon', 'icon', 'miniicon', 'favicon')
        candidates = []
        for source in (app, *alternatives):
            for field in fields:
                candidate = source.get(field)
                if isinstance(candidate, str) and re.fullmatch(
                        r'/resources/[a-fA-F0-9]{16,128}/[A-Za-z0-9][A-Za-z0-9_.-]*', candidate):
                    urls = ('https://' + self.host + ':3001' + candidate,
                            'http://' + self.host + ':3000' + candidate)
                else:
                    urls = (candidate,)
                for url in urls:
                    if url not in candidates:
                        candidates.append(url)
        data, kind, has_uri = self.fallback, 'png', False
        counts = self.icon_diagnostics
        for candidate in candidates:
            if candidate is None or candidate == '':
                continue
            has_uri = True
            try:
                if not isinstance(candidate, str):
                    raise ValueError('Invalid icon URI')
                url = urllib.parse.urlsplit(candidate)
                if url.scheme not in ('http', 'https') or url.hostname != self.host or url.username or url.password:
                    raise ValueError('Invalid icon URI')
                if url.port not in (None, 80, 443, 3000, 3001):
                    raise ValueError('Invalid icon port')
            except ValueError:
                counts['rejected_uri'] += 1
                continue
            limit = min(self.download_remaining, MAX_ICON_DOWNLOAD)
            try:
                if limit <= 0:
                    raise ValueError('Icon download budget exceeded')
                fetched = self.fetch(url.geturl()) if self.fetch else fetch_icon(url.geturl(), limit)
                self.download_remaining -= min(len(fetched), limit)
                if not fetched or len(fetched) > limit:
                    raise ValueError('Invalid icon size')
            except (OSError, ValueError):
                counts['fetch_failed'] += 1
                continue
            if fetched.startswith(b'\xff\xd8'):
                format_name = 'jpeg'
            elif fetched[:4] == b'RIFF' and fetched[8:12] == b'WEBP':
                format_name = 'webp'
            elif fetched.startswith(b'\x89PNG\r\n\x1a\n'):
                format_name = 'png'
            else:
                counts['invalid_image'] += 1
                continue
            if len(fetched) > MAX_EMBEDDED_ICON:
                resize_limit = min(self.resize_remaining, MAX_EMBEDDED_ICON)
                if resize_limit <= 0:
                    continue
                try:
                    fetched = resize_icon(fetched)
                    if not fetched or len(fetched) > resize_limit:
                        raise ValueError('Invalid resized icon size')
                except Exception:
                    # An optional icon decoder can fail on malformed TV artwork.
                    counts['invalid_image'] += 1
                    continue
                format_name = 'png'
                self.resize_remaining -= len(fetched)
            data, kind = fetched, format_name
            counts['embedded'] += 1
            break
        else:
            counts['fallback'] += 1
            if not has_uri:
                counts['missing_uri'] += 1
        return 'data:image/' + kind + ';base64,' + base64.b64encode(data).decode()

    def build(self, launchpoints, inputs, installed=None):
        self.download_remaining = ICON_DOWNLOAD_BUDGET
        self.resize_remaining = RESIZED_ICON_BUDGET
        self.icon_diagnostics.update({key: 0 for key in self.icon_diagnostics if key not in ('schema', 'status')},
                                     status='reading')
        if not isinstance(launchpoints, list) or not isinstance(inputs, list) or len(launchpoints) > 300 or len(inputs) > 100:
            raise ValueError('Unexpected TV inventory')
        alternatives = {}
        if isinstance(installed, list) and len(installed) <= 300:
            for catalog in (launchpoints, installed):
                seen_sources = set()
                for source in catalog:
                    if not isinstance(source, dict):
                        continue
                    appid = source.get('id')
                    if isinstance(appid, str) and appid not in seen_sources:
                        seen_sources.add(appid)
                        alternatives.setdefault(appid, []).append(source)
            launchpoints = include_tuner(launchpoints, installed)
        apps, seen = [], set()
        for app in launchpoints:
            if not isinstance(app, dict) or app.get('hidden'):
                continue
            appid, title = app.get('id'), app.get('title')
            if not isinstance(appid, str) or not 0 < len(appid) <= 256 or not isinstance(title, str) or len(title) > 256:
                raise ValueError('Invalid TV application metadata')
            if appid in seen:
                continue
            seen.add(appid)
            self.icon_diagnostics['apps'] += 1
            apps.append({'id': appid, 'title': title, 'icon': self.icon(app, alternatives.get(appid, ())),
                         'iconColor': str(app.get('iconColor') or app.get('bgColor') or '')[:64]})
        devices = []
        for device in inputs:
            if not isinstance(device, dict) or not isinstance(device.get('appId'), str):
                continue
            label = device.get('label') or device.get('id') or device['appId']
            devices.append({'appId': device['appId'][:256], 'label': str(label)[:256]})
        self.icon_diagnostics['status'] = 'complete'
        result = {'apps': apps, 'inputs': devices}
        if self.resize_remaining < RESIZED_ICON_BUDGET:
            result['fallbackIcon'] = 'data:image/png;base64,' + base64.b64encode(self.fallback).decode()
        return result


class SSAP:
    def __init__(self, host, directory, progress=print, *, settings_write=False, reuse_only=False):
        self.settings_write = settings_write
        self.host, self.directory, self.progress = host, Path(directory), progress
        self.reuse_only = reuse_only
        self.counter, self.ws, self.key = 0, None, None

    def __enter__(self):
        from websockets.sync.client import connect
        from websockets.exceptions import ConnectionClosed
        from lgtv import PERMISSIONS
        keyfile = self.directory / ('ssap-settings.json' if self.settings_write else 'ssap.json')
        permissions = ['READ_SETTINGS', 'WRITE_SETTINGS'] if self.settings_write else PERMISSIONS
        saved = json.loads(keyfile.read_text()) if keyfile.exists() else {}
        key = saved.get('key') if isinstance(saved, dict) else None
        if self.reuse_only and not (isinstance(key, str) and 0 < len(key) <= 1024):
            raise UserError('No saved TV remote-control pairing is available.')
        payload = {'forcePairing': False,
                   'manifest': {'manifestVersion': 1, 'appVersion': '1.1', 'permissions': permissions}}
        if not self.reuse_only:
            payload['pairingType'] = 'PROMPT'
        if key:
            payload['client-key'] = key
        connect_timeout = 5 if self.reuse_only else 10
        try:
            self.ws = connect(f'wss://{self.host}:3001', ssl=tv_context(), open_timeout=connect_timeout,
                              max_size=8 * 1024 * 1024, proxy=None)
        except ssl.SSLError:
            # Retry only the TLS connection, before sending any pairing data.
            self.ws = connect(f'wss://{self.host}:3001', ssl=tv_context(compatible=True),
                              open_timeout=connect_timeout, max_size=8 * 1024 * 1024, proxy=None)
        try:
            self.progress('Checking TV remote-control access…' if key else 'Accept the remote-control pairing request on the TV if shown…')
            self.ws.send(json.dumps({'id': 'register_0', 'type': 'register', 'payload': payload}))
            deadline = time.monotonic() + (5 if self.reuse_only else 65)
            while time.monotonic() < deadline:
                reply = json.loads(self.ws.recv(timeout=max(0.1, deadline - time.monotonic())))
                if not isinstance(reply, dict) or not isinstance(reply.get('payload', {}), dict):
                    raise ValueError('Invalid TV pairing response')
                response = reply.get('payload', {})
                if reply.get('type') == 'error':
                    raise UserError('TV pairing was rejected. Check the on-screen request and local network access.',
                                    reason_code='pairing-rejected' if self.settings_write else 'user-error')
                if self.reuse_only and response.get('pairingType'):
                    raise UserError('The TV did not accept the saved remote-control pairing.')
                if reply.get('type') == 'registered':
                    registered = response.get('client-key')
                    if not isinstance(registered, str) or not 0 < len(registered) <= 1024:
                        raise ValueError('Invalid TV pairing response')
                    if self.reuse_only:
                        if reply.get('id') != 'register_0' or registered != key:
                            raise UserError('The TV did not accept the saved remote-control pairing.')
                    else:
                        private_write(keyfile, json.dumps({'key': registered}).encode())
                    self.key = registered
                    return self
            raise TVConnectionError('Timed out waiting for the TV pairing request. Keep the TV on and accept it with the remote.',
                                    reason_code='pairing-timeout')
        except ConnectionClosed as exc:
            self.ws.close()
            raise connection_closed(exc) from exc
        except TimeoutError as exc:
            self.ws.close()
            raise TVConnectionError('Timed out waiting for the TV pairing request. Keep the TV on and accept it with the remote.',
                                    reason_code='pairing-timeout') from exc
        except BaseException:
            self.ws.close()
            raise

    def __exit__(self, *args):
        self.ws.close()

    def call(self, uri, payload=None, *, timeout=20):
        from websockets.exceptions import ConnectionClosed
        self.counter += 1
        request = 'cytv_' + str(self.counter)
        try:
            self.ws.send(json.dumps({'id': request, 'type': 'request', 'uri': uri, 'payload': {} if payload is None else payload}))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                reply = json.loads(self.ws.recv(timeout=max(0.1, deadline - time.monotonic())))
                if not isinstance(reply, dict):
                    raise UserError('Invalid TV remote-control reply')
                if reply.get('id') != request:
                    continue
                payload = reply.get('payload', {})
                if reply.get('type') == 'error' or (isinstance(payload, dict) and payload.get('returnValue') is False):
                    raise UserError('TV permission was denied. Check pairing and run cytv doctor.',
                                    reason_code='ssap-request-rejected' if self.settings_write else 'user-error')
                if reply.get('type', 'response') != 'response' or not isinstance(payload, dict):
                    raise UserError('Invalid TV remote-control reply')
                return payload
            raise UserError('Reading TV applications timed out. Keep the TV on and check the connection.')
        except ConnectionClosed as exc:
            raise connection_closed(exc) from exc
        except TimeoutError as exc:
            raise UserError('Reading TV applications timed out. Keep the TV on and check the connection.') from exc

    def inventory(self, fallback):
        self.icon_diagnostics = {'schema': 1, 'status': 'unavailable'}
        points = self.call('ssap://com.webos.applicationManager/listLaunchPoints').get('launchPoints')
        inputs = self.call('ssap://tv/getExternalInputList').get('devices')
        # listLaunchPoints can omit the installed broadcast tuner entirely.
        # Unsupported optional discovery must not break the normal inventory.
        try:
            installed = self.call('ssap://com.webos.applicationManager/listApps')
        except (UserError, json.JSONDecodeError, AttributeError):
            # The wire parser assumes an object; optional malformed JSON or a
            # non-object reply must not discard the successful baseline reads.
            installed = None
        apps = installed.get('apps') if isinstance(installed, dict) and installed.get('returnValue') is not False else None
        inventory = Inventory(self.host, fallback)
        self.icon_diagnostics = inventory.icon_diagnostics
        return inventory.build(points, inputs, apps)
