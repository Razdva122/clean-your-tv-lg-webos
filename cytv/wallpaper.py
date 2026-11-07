"""Local photo/video preparation and the temporary, PIN-authenticated wallpaper receiver."""
import errno
import base64
import hashlib
import http.client
import ipaddress
import io
import json
import math
from pathlib import Path
import re
import socket
import select
import subprocess
import sys
import tempfile
import time

from .errors import COMPUTER_STORAGE_FULL, reports_storage_full
from . import storage

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRect, Qt
from PySide6.QtGui import QImageReader

IMAGE_LIMIT = 2 * 1024 * 1024
UHD_LIMIT = 12 * 1024 * 1024
FHD_LIMIT = 4 * 1024 * 1024
ENVELOPE_LIMIT = 33 * 1024 * 1024
VIDEO_INPUT_LIMIT = 512 * 1024 * 1024
VIDEO_FORMATS = {'.mp4':'mov', '.mov':'mov', '.mkv':'matroska', '.webm':'matroska'}


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


def run_ffmpeg(command, cancel=None, stderr=None):
    check_cancel(cancel)
    with tempfile.TemporaryFile() as diagnostic:
        return _run_ffmpeg(command, cancel, stderr if stderr is not None else diagnostic)


def _run_ffmpeg(command, cancel, stderr):
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr if stderr is not None else subprocess.DEVNULL, **options) as process:
        try:
            deadline = time.monotonic() + 120
            while process.poll() is None:
                check_cancel(cancel)
                if time.monotonic() >= deadline:
                    raise ValueError('Image preparation timed out.')
                time.sleep(.05)
            check_cancel(cancel)
            if process.returncode:
                stderr.seek(0, 2)
                stderr.seek(max(0, stderr.tell() - 65536))
                if reports_storage_full(stderr.read(65536)):
                    raise ValueError(COMPUTER_STORAGE_FULL)
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
    storage.local(width*height*4+2*(UHD_LIMIT+FHD_LIMIT)+1024*1024, progress)
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


def prepare_video(path, cancel=None, progress=lambda message: None):
    """Reuse the bounded personal-media wire format; never send source audio."""
    check_cancel(cancel)
    path = Path(path).resolve()
    demuxer = VIDEO_FORMATS.get(path.suffix.lower())
    if any(c in str(path) for c in ('\r','\n')) or not demuxer or not path.is_file() or not 0 < path.stat().st_size <= VIDEO_INPUT_LIMIT:
        raise ValueError('Choose MP4, MOV, MKV or WebM up to 512 MiB.')
    progress('Preparing video wallpaper…')
    # Force a container demuxer and local-file input: playlists and network URLs
    # cannot make FFmpeg fetch other resources from an untrusted source file.
    source = ['-protocol_whitelist','file','-f',demuxer,'-i',str(path)]
    executable = ffmpeg_executable()
    storage.local(3840*2160*4+2*(UHD_LIMIT+FHD_LIMIT)+1024*1024, progress)
    with tempfile.TemporaryDirectory(prefix='cytv-video-') as directory:
        directory = Path(directory)
        with (directory/'probe.txt').open('w+b') as diagnostic:
            try:
                run_ffmpeg([executable,'-nostdin','-hide_banner']+source+
                           ['-map','0:v:0','-c:v','copy','-an','-t','0','-f','null','-'],cancel,stderr=diagnostic)
            except ValueError as error:
                if str(error) == COMPUTER_STORAGE_FULL:
                    raise
                raise ValueError('Choose a readable video from 1 to 60 seconds, up to 3840×2160.') from None
            diagnostic.seek(0); info = diagnostic.read(65536).decode('utf-8',errors='replace')
        duration = re.search(r'^  Duration: (\d+):(\d{2}):(\d{2}(?:\.\d+)?)',info,re.MULTILINE)
        stream_info = re.search(r'^  Stream #0:\d+(?:\[[^\]\r\n]*\])?(?:\([^\)\r\n]*\))?: Video:[^\r\n]*',info,re.MULTILINE)
        dimensions = re.search(r' (\d+)x(\d+)(?:[ ,\[])',stream_info[0] if stream_info else '')
        sar = re.search(r'\[SAR (\d+):(\d+) DAR',stream_info[0] if stream_info else '')
        ratio = int(sar[1])/int(sar[2]) if sar and int(sar[2]) else 1
        seconds = int(duration[1])*3600+int(duration[2])*60+float(duration[3]) if duration else 0
        if not dimensions or not 1 <= seconds <= 60 or not 16 <= int(dimensions[1]) <= 3840 or not 9 <= int(dimensions[2]) <= 2160 or not 16 <= int(dimensions[1])*ratio <= 3840:
            raise ValueError('Choose a readable video from 1 to 60 seconds, up to 3840×2160.')
        poster = directory/'poster.jpg'
        run_ffmpeg([executable,'-nostdin','-y','-v','error']+source+
                   ['-map','0:v:0','-frames:v','1','-an','-vf','scale=trunc(iw*sar/2)*2:ih,setsar=1','-q:v','2',str(poster)],cancel)
        # The first decoded frame is the static fallback until video starts.
        image = load_image(poster)
        crop = crop_rect(image.width(),image.height())
        image = image.copy(QRect(*crop))
        for quality in (92,80,65,45,25):
            data = QByteArray(); stream = QBuffer(data); stream.open(QIODevice.OpenModeFlag.WriteOnly)
            if not image.save(stream,'JPEG',quality):
                raise ValueError('Video preparation failed. Choose another video.')
            stream.close()
            if data.size() <= IMAGE_LIMIT:
                break
        else:
            raise ValueError('Wallpaper exceeds the TV size limit.')
        result = dict(schemaVersion=1,kind='wallpaper',source='cytv',
                      image=asset(bytes(data),'image/jpeg',image.width(),image.height()),variants=[])
        for quality,width,height,limit,ceiling in [('4k',3840,2160,UHD_LIMIT,8_000_000),('1080p',1920,1080,FHD_LIMIT,2_000_000)]:
            if quality == '4k' and (crop[2] < width or crop[3] < height):
                continue
            progress('Preparing ' + quality + ' video…')
            output = directory/(quality+'.mp4')
            rate = str(min(ceiling,int(limit*8*.85/seconds)))
            run_ffmpeg([executable,'-nostdin','-y','-v','error']+source+
                       ['-map','0:v:0','-t',str(seconds),'-vf',f'scale=trunc(iw*sar/2)*2:ih,setsar=1,crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}:exact=1,scale={width}:{height},setsar=1',
                        '-r','25','-an','-sn','-dn','-map_metadata','-1','-c:v','libx264','-preset','veryfast','-crf','23',
                        '-maxrate',rate,'-bufsize',rate,'-pix_fmt','yuv420p','-profile:v','high','-level:v','5.1' if width==3840 else '4.1',
                        '-threads','2','-movflags','+faststart',str(output)],cancel)
            if not 0 < output.stat().st_size <= limit:
                raise ValueError('Wallpaper exceeds the TV size limit.')
            item = asset(output.read_bytes(),'video/mp4',width,height); item['quality'] = quality
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


def wait_socket(transport, deadline, cancel, writing=False):
    """Poll on the I/O thread; cross-thread shutdown cannot wake recv on all OSes."""
    while True:
        check_cancel(cancel)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('Transfer timed out.')
        readable, writable, _ = select.select([] if writing else [transport],
                                              [transport] if writing else [], [], min(.05, remaining))
        if readable or writable:
            check_cancel(cancel)
            if time.monotonic() >= deadline:
                raise ValueError('Transfer timed out.')
            return


class ReceiverReader(io.RawIOBase):
    def __init__(self, stream, transport, deadline, cancel):
        super().__init__()
        self.stream, self.transport, self.deadline, self.cancel = stream, transport, deadline, cancel

    def readable(self):
        return True

    def readinto(self, buffer):
        if not len(buffer):
            return 0
        while True:
            wait_socket(self.transport, self.deadline, self.cancel)
            result = self.stream.readinto(buffer)
            if result is not None:
                return result

    def close(self):
        try:
            self.stream.close()
        finally:
            super().close()


class ReceiverSocket:
    def __init__(self, transport, deadline, cancel):
        self.transport, self.deadline, self.cancel = transport, deadline, cancel
        transport.setblocking(False)

    def __getattr__(self, name):
        return getattr(self.transport, name)

    def makefile(self, mode):
        # Keep native SocketIO's reference so HTTPConnection.close cannot detach
        # the response's fd before its buffered reader finishes or is closed.
        stream = self.transport.makefile(mode, buffering=0)
        return io.BufferedReader(ReceiverReader(stream, self.transport, self.deadline, self.cancel))

    def sendall(self, data):
        remaining = memoryview(data)
        while remaining:
            wait_socket(self.transport, self.deadline, self.cancel, writing=True)
            try:
                count = self.transport.send(remaining)
            except BlockingIOError:
                continue
            if not count:
                raise OSError('Connection closed')
            remaining = remaining[count:]


def upload(host, pin, envelope, cancel=None, progress=lambda message: None):
    host = destination(host,pin)
    check_cancel(cancel)
    body = json.dumps(envelope,separators=(',',':')).encode('utf-8')
    if len(body) > ENVELOPE_LIMIT:
        raise ValueError('Wallpaper exceeds the TV size limit.')
    connection = http.client.HTTPConnection(host,8879,timeout=20)
    deadline = time.monotonic() + 20
    def create_transport(address, timeout, source_address):
        return ReceiverSocket(connect_ipv4(address, deadline, cancel), deadline, cancel)
    # The same bounded factory handles both initial connect and POST reconnect.
    connection._create_connection = create_transport
    def request(method,path,data=None):
        check_cancel(cancel)
        connection.request(method,path,body=data,headers={'X-CYTV-PIN':pin,'Content-Type':'application/json','Connection':'close'})
        response = connection.getresponse()
        try:
            reply = response.read(65537)
        finally:
            response.close()
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
        required = sum(item['size'] for item in envelope.get('variants', [])) + 1024*1024
        snapshot = capabilities.get('videoCacheStorage')
        available = snapshot.get('available') if isinstance(snapshot, dict) else None
        if type(available) is not int or not 0 <= available <= 2**53-1:
            available = None
        values = dict(location='Video cache', required=storage.mib(required))
        message = (storage.UNKNOWN.format(**values) if available is None else
                   storage.SUMMARY.format(**values, available=storage.mib(available, False),
                                          shortfall=storage.mib(max(0,required-available))))
        if envelope.get('variants'):
            progress(message)
            if available is not None and required > available:
                raise ValueError(message)
        progress(storage.UNKNOWN.format(location='TV app storage', required=storage.mib(len(body)*2+1024*1024)))
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
        connection.close()
