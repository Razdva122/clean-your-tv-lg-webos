"""Host-only HTTPS trust checks; no TV connection or existing profile."""
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from pathlib import Path
import ssl
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from cytv import python_runtime as runtime
from cytv.errors import PythonCacheError


class PythonDownloadTLSTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'darwin', 'Uses the macOS system CA file')
    def test_macos_download_trusts_system_roots_without_build_machine_ca_paths(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'SSL_CERT_FILE': str(Path(tmp) / 'missing-build-ca.pem'),
                'SSL_CERT_DIR': tmp}), patch.object(runtime.urllib.request, 'build_opener',
                                                  wraps=runtime.urllib.request.build_opener) as builder, \
                patch.object(runtime.urllib.request.OpenerDirector, 'open', side_effect=OSError('stop before network')):
            with self.assertRaises(PythonCacheError):
                runtime.prime_cache(Path(tmp).resolve() / 'cache', lambda _: None)
            opener = runtime.urllib.request.build_opener(*builder.call_args.args)
            https = next(h for h in opener.handlers if isinstance(h, runtime.urllib.request.HTTPSHandler))
            context = https._context or ssl.create_default_context()
            self.assertGreater(context.cert_store_stats()['x509_ca'], 0)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            self.assertGreaterEqual(context.minimum_version, ssl.TLSVersion.TLSv1_2)

    def test_download_rejects_untrusted_https_and_keeps_cache_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
            now = datetime.datetime.now(datetime.timezone.utc)
            cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                    .public_key(key.public_key()).serial_number(x509.random_serial_number())
                    .not_valid_before(now - datetime.timedelta(minutes=1))
                    .not_valid_after(now + datetime.timedelta(days=1))
                    .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
                    .sign(key, hashes.SHA256()))
            (root / 'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            (root / 'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                          serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(root / 'cert.pem', root / 'key.pem')
            with HTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler) as server:
                server.socket = context.wrap_socket(server.socket, server_side=True)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    with patch.object(runtime, 'URL', f'https://localhost:{server.server_port}/archive'):
                        with self.assertRaises(PythonCacheError) as caught:
                            runtime.prime_cache(root / 'cache', lambda _: None)
                    self.assertEqual(caught.exception.reason, 'tls')
                    self.assertEqual(list((root / 'cache').iterdir()), [])
                finally:
                    server.shutdown()
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())
