"""Owner-approved pairing from the trusted on-TV installer worker."""
from ipaddress import IPv4Address
import os
import socket
import struct

from cytv.errors import UserError
from cytv.tv import SSAP


class PairingError(RuntimeError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _local_ipv4():
    import fcntl

    get_flags, get_ipv4 = 0x8913, 0x8915  # Linux SIOCGIFFLAGS and SIOCGIFADDR.
    up, loopback, point_to_point = 0x1, 0x8, 0x10
    # Inspect kernel interfaces using an unbound socket. No discovery packets
    # or address arguments enter this worker.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as control:
        for _, interface in socket.if_nameindex():
            request = struct.pack('16s24x', os.fsencode(interface))  # Linux ifreq, including padding.
            try:
                flags = struct.unpack_from('H', fcntl.ioctl(control, get_flags, request), 16)[0]
                if not flags & up or flags & (loopback | point_to_point):
                    continue
                addr = IPv4Address(fcntl.ioctl(control, get_ipv4, request)[20:24])
            except OSError:
                continue
            if not (addr.is_loopback or addr.is_link_local or addr.is_unspecified
                    or addr.is_multicast or addr.is_reserved):
                return str(addr)
    raise OSError('No active TV network address')


def available():
    """Check client and local listener prerequisites without issuing a prompt."""
    try:
        import websockets
        from websockets.sync import client

        if getattr(websockets, '__version__', None) != '15.0.1' or not callable(client.connect):
            return False
        host = _local_ipv4()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(1)
            probe.bind((host, 0))
            probe.connect((host, 3001))
        return True
    except (ImportError, OSError, ValueError):
        return False


def collect(fallback, *, allow_missing_inputs=None):
    """Keep the key and normalized inventory in the caller's private worker."""
    code = 'pairing-unavailable'
    try:
        # The pinned synchronous WebSocket client makes one direct upgrade and
        # rejects redirects. A fresh registration never reads or writes a keyfile.
        with SSAP(_local_ipv4(), None, lambda _: None, first_pair=True) as tv:
            code = 'inventory-unavailable'
            return tv.inventory(fallback, allow_missing_inputs=allow_missing_inputs), tv.key
    except Exception as error:
        if (code == 'pairing-unavailable' and isinstance(error, UserError)
                and error.reason_code in ('pairing-rejected', 'pairing-timeout')):
            code = error.reason_code
        raise PairingError(code) from None
