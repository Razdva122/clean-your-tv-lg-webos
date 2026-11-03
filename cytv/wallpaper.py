"""Local photo preparation and the temporary, PIN-authenticated wallpaper receiver."""
import errno
import base64
import hashlib
import http.client
import ipaddress
import json
import math
from pathlib import Path
import re
import socket
import select
import subprocess
import sys
import tempfile
import threading
import time

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QImageReader

IMAGE_LIMIT = 2 * 1024 * 1024
UHD_LIMIT = 12 * 1024 * 1024
FHD_LIMIT = 4 * 1024 * 1024
ENVELOPE_LIMIT = 33 * 1024 * 1024


class Cancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def destination(host, pin):
    if not isinstance(host, str):
        raise ValueError('Enter a private IPv4 address.')
    if not isinstance(pin, str):
        raise ValueError('Enter the six-digit PIN shown on your TV.')
    try:
        address = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        raise ValueError('Enter a private IPv4 address.') from None
    if not any(address in ipaddress.IPv4Network(net) for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')):
        raise ValueError('Enter a private IPv4 address.')
    if not re.fullmatch(r'[0-9]{6}', pin):
        raise ValueError('Enter the six-digit PIN shown on your TV.')
    return str(address)


def ffmpeg_executable():
    # Frozen applications only use the explicitly bundled binary: no PATH or download.
    if getattr(sys, 'frozen', False):
        return str(Path(sys._MEIPASS) / 'ffmpeg' / ('ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'))
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_image(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Choose a JPG or PNG image up to 64 MiB.')
    reader = QImageReader(str(path))
    if bytes(reader.format()).lower() not in (b'jpeg', b'jpg', b'png'):
        raise ValueError('Choose a JPG or PNG image up to 64 MiB.')
    size = reader.size()
    if size.width() < 16 or size.height() < 9 or size.width() * size.height() > 80_000_000:
        raise ValueError('Choose a JPG or PNG image up to 64 MiB.')
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        raise ValueError('Image preparation failed.')
    return image


def crop_rect(width, height, zoom=1., horizontal=.5, vertical=.5):
    if not all(math.isfinite(v) for v in (zoom, horizontal, vertical)) or not 1 <= zoom <= 4 or not 0 <= horizontal <= 1 or not 0 <= vertical <= 1:
        raise ValueError('Invalid crop.')
    unit = max(1, int(min(width / 16, height / 9) / zoom))
    w, h = unit * 16, unit * 9
    return round((width - w) * horizontal), round((height - h) * vertical), w, h


def asset(data, media_type, width, height):
    return dict(mediaType=media_type, width=width, height=height, size=len(data),
                sha256=hashlib.sha256(data).hexdigest(), data=base64.b64encode(data).decode('ascii'))


def run_ffmpeg(command, cancel=None):
    check_cancel(cancel)
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options) as process:
        try:
            deadline = time.monotonic() + 120
            while process.poll() is None:
                check_cancel(cancel)
                if time.monotonic() >= deadline:
                    raise ValueError('Image preparation timed out.')
                time.sleep(.05)
            check_cancel(cancel)
            if process.returncode:
                raise ValueError('Image preparation failed.')
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def prepare(path, crop=None, cancel=None, progress=lambda message: None):
    check_cancel(cancel)
    progress('Preparing wallpaper…')
    image = load_image(path)
    crop = crop if crop is not None else crop_rect(image.width(), image.height())
    if len(crop) != 4 or any(type(v) is not int for v in crop):
        raise ValueError('Invalid crop.')
    x, y, width, height = crop
    if min(x,y) < 0 or width < 16 or height < 9 or width * 9 != height * 16 or x + width > image.width() or y + height > image.height():
        raise ValueError('Invalid crop.')
    image = image.copy(QRect(*crop))
    poster = image.scaled(3840,2160,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation) if width > 3840 else image
    for quality in (92,80,65,45,25):
        data = QByteArray(); stream = QBuffer(data); stream.open(QIODevice.OpenModeFlag.WriteOnly)
        if not poster.save(stream,'JPEG',quality):
            raise ValueError('Image preparation failed.')
        stream.close()
        if data.size() <= IMAGE_LIMIT:
            break
    else:
        raise ValueError('Wallpaper exceeds the TV size limit.')
    result = dict(schemaVersion=1, kind='wallpaper', source='cytv', image=asset(bytes(data),'image/jpeg',poster.width(),poster.height()),variants=[])
    with tempfile.TemporaryDirectory(prefix='cytv-wallpaper-') as directory:
        source = Path(directory) / 'crop.png'
        if width >= 1920:
            check_cancel(cancel)
            if not image.save(str(source),'PNG'):
                raise ValueError('Image preparation failed.')
        for quality,w,h,limit,rate in [('4k',3840,2160,UHD_LIMIT,'8M'),('1080p',1920,1080,FHD_LIMIT,'2M')]:
            if width < w or height < h:
                continue
            progress('Preparing ' + quality + ' video…')
            output = Path(directory) / (quality + '.mp4')
            run_ffmpeg([ffmpeg_executable(),'-nostdin','-y','-v','error','-loop','1','-i',str(source),'-vf',f'scale={w}:{h}',
                        '-t','2','-r','25','-an','-c:v','libx264','-preset','veryfast','-tune','stillimage','-crf','20',
                        '-maxrate',rate,'-bufsize',rate,'-pix_fmt','yuv420p','-profile:v','high','-level:v','5.1' if w==3840 else '4.1',
                        '-threads','2','-movflags','+faststart',str(output)],cancel)
            if output.stat().st_size > limit:
                raise ValueError('Wallpaper exceeds the TV size limit.')
            item = asset(output.read_bytes(),'video/mp4',w,h); item['quality'] = quality
            result['variants'].append(item)
    check_cancel(cancel)
    return result


def connect_ipv4(address, deadline, cancel=None):
    """Own the socket throughout connect; poll cancellation within 50 ms."""
    transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        check_cancel(cancel)
        if time.monotonic() >= deadline:
            raise ValueError('Transfer timed out.')
        transport.setblocking(False)
        error = transport.connect_ex(address)
        pending = (errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY, errno.EINTR,
                   getattr(errno, 'WSAEINPROGRESS', 10036), getattr(errno, 'WSAEWOULDBLOCK', 10035),
                   getattr(errno, 'WSAEALREADY', 10037), getattr(errno, 'WSAEINTR', 10004))
        if error not in (0,) + pending:
            raise OSError(error, 'Connection failed')
        while error:
            check_cancel(cancel)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('Transfer timed out.')
            _, writable, exceptional = select.select([], [transport], [transport], min(.05, remaining))
            if writable or exceptional:
                error = transport.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if error:
                    raise OSError(error, 'Connection failed')
        check_cancel(cancel)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('Transfer timed out.')
        transport.settimeout(remaining)
        return transport
    except BaseException:
        transport.close()
        raise


def upload(host, pin, envelope, cancel=None, progress=lambda message: None):
    host = destination(host,pin)
    check_cancel(cancel)
    body = json.dumps(envelope,separators=(',',':')).encode('utf-8')
    if len(body) > ENVELOPE_LIMIT:
        raise ValueError('Wallpaper exceeds the TV size limit.')
    connection = http.client.HTTPConnection(host,8879,timeout=20)
    done = threading.Event()
    deadline = time.monotonic() + 20
    # HTTPConnection calls this factory on both preflight and POST reconnect.
    connection._create_connection = lambda address, timeout, source_address: connect_ipv4(address, deadline, cancel)
    # HTTPResponse owns the makefile after Connection: close detaches conn.sock.
    transport_socket = [None]
    def watch():
        while not done.wait(.05):
            if (cancel is not None and cancel.is_set()) or time.monotonic() >= deadline:
                current_socket = connection.sock or transport_socket[0]
                if current_socket is not None:
                    try: current_socket.shutdown(socket.SHUT_RDWR)
                    except OSError: pass
                connection.close()
    monitor = threading.Thread(target=watch,daemon=True); monitor.start()
    def request(method,path,data=None):
        check_cancel(cancel)
        connection.request(method,path,body=data,headers={'X-CYTV-PIN':pin,'Content-Type':'application/json','Connection':'close'})
        transport_socket[0] = connection.sock
        response = connection.getresponse()
        reply = response.read(65537)
        check_cancel(cancel)
        if time.monotonic() >= deadline:
            raise ValueError('Transfer timed out.')
        if len(reply) > 65536:
            raise ValueError('Invalid TV response.')
        return response.status,reply
    try:
        progress('Checking TV wallpaper receiver…')
        status,reply = request('GET','/v1/wallpaper-capabilities')
        if status != 200:
            raise ValueError('Open Receive from CYTV on your TV and check the PIN.')
        try: capabilities = json.loads(reply)
        except (ValueError,UnicodeError): raise ValueError('Invalid TV response.') from None
        if not isinstance(capabilities,dict) or type(capabilities.get('wallpaperProtocol')) is not int or capabilities['wallpaperProtocol'] != 1:
            raise ValueError('Update Clean Your TV to receive personal wallpapers.')
        progress('Sending wallpaper…')
        status,_ = request('POST','/v1/wallpaper',body)
        if status != 202:
            raise ValueError('The TV did not accept the wallpaper. Open a new receiving session to retry.')
        return 'received'
    except (OSError,http.client.HTTPException):
        check_cancel(cancel)
        if time.monotonic() >= deadline:
            raise ValueError('Transfer timed out.') from None
        raise ValueError('Could not transfer wallpaper. Check the TV receiving screen and your home network.') from None
    finally:
        done.set(); connection.close(); monitor.join(timeout=1)
