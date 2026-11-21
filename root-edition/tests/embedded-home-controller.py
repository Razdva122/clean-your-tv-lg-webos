"""Offline adapter for the real CYTV lifecycle controller and its health pipe."""
import argparse
import http.server
import os
import select
import subprocess
import sys
from types import SimpleNamespace

TOKEN = 'a' * 32
PORT = 34917


def watch(control, ready):
    sys.path.insert(0, '/project/root-edition/runtime')
    import c1_keyfilter as controller

    # W17M has no installed C1 guardian or application manager in this lab.
    # Keep the actual controller loop, validation, and pipe protocol.
    def subscribe(*_args, **kwargs):
        script = 'import sys; print(\'{"returnValue":true,"subscribed":true}\'); sys.stdin.read()'
        return subprocess.Popen([sys.executable, '-u', '-c', script], **kwargs)

    controller.subprocess = SimpleNamespace(
        Popen=subscribe, PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL,
        TimeoutExpired=subprocess.TimeoutExpired,
    )
    controller.read_intent = lambda *_: {'token': TOKEN, 'phase': 'active'}
    controller.selection = lambda *_: {'schema': 4}
    controller.filter_present = lambda *_: True
    controller.native = lambda *_args, **_kwargs: dict(
        returnValue=True, backend=controller.BACKEND, routing=controller.ROUTING, profiles=None,
        state='armed', token=TOKEN, mounted=False, healthy=True,
        stock_verified=False, stopped=False, guardian_pid=2, reason='',
    )
    controller.watch(TOKEN, control, ready)


def supervise():
    control, writer = os.pipe()
    ready, notifier = os.pipe()
    child = subprocess.Popen(
        [sys.executable, __file__, '--watch', str(writer), str(notifier)],
        pass_fds=(writer, notifier),
    )
    os.close(writer)
    os.close(notifier)
    try:
        assert select.select([ready], [], [], 5)[0]
        assert os.read(ready, 128) == ('WATCH ' + TOKEN + '\n').encode()
        assert select.select([control], [], [], 5)[0]
        assert os.read(control, 128).startswith(b'READY\n')
        os.set_blocking(control, False)
        launched = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                import json
                from urllib.parse import urlparse, parse_qs
                request = urlparse(self.path)
                args = parse_qs(request.query)
                result = dict(returnValue=False)
                if request.path == '/lease':
                    assert args.get('adapter') == ['embedded-qml-v1']
                    if child.poll() is None:
                        assert select.select([control], [], [], 2)[0]
                        assert b'PING\n' in os.read(control, 65536)
                    result = dict(returnValue=True, subscribed=True,
                        backend='c1-native-gate', routing='compositor-keyfilter-v1',
                        token=TOKEN, healthy=child.poll() is None,
                        sequence=1 if child.poll() is None else 2)
                elif request.path == '/home' and child.poll() is None:
                    assert args.get('token') == [TOKEN]
                    launched.append(True)
                    result = dict(returnValue=True, backend='c1-native-gate',
                        routing='compositor-keyfilter-v1', token=TOKEN)
                elif request.path == '/kill' and len(launched) == 1:
                    child.kill()
                    assert child.wait(timeout=2) == -9
                    os.set_blocking(control, True)
                    while os.read(control, 65536):
                        pass
                    print('CYTV watch(): wait returned -9 and CONTROL pipe reached EOF', flush=True)
                    result = dict(returnValue=True)
                response = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        with http.server.HTTPServer(('127.0.0.1', PORT), Handler) as server:
            print('controller-ready', flush=True)
            server.serve_forever()
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=2)
        os.close(ready)
        os.close(control)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--watch', nargs=2, type=int)
    args = parser.parse_args()
    watch(*args.watch) if args.watch else supervise()
