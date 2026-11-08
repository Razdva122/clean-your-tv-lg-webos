"""Fixed Root catalog reads over SSH, without TV Node child processes."""
import shlex

from .errors import UserError, TVCommandError, connection_interrupted
from .transport import JsonReplies


READS = {
    'applications': ('luna://com.webos.applicationManager/listApps', 1024 * 1024),
    'inputs': ('luna://com.webos.service.eim/getAllInputStatus', 256 * 1024),
}


def read(remote, kind):
    uri, limit = READS[kind]
    channel = None
    try:
        channel = remote.channel(shlex.join(['/usr/bin/luna-send', '-n', '1', '-w', '8000', uri, '{}']))
        parser, size, reply = JsonReplies(), 0, None
        # Keep stdin open until the reply: EOF makes some TV luna-send builds
        # exit successfully without returning anything.
        for chunk in remote.chunks(channel, 8):
            size += len(chunk)
            if size > limit:
                return None, {'reason': 'oversized-reply'}
            replies = parser.feed(chunk)
            if replies:
                if reply is not None or len(replies) != 1:
                    return None, {'reason': 'malformed-reply'}
                reply = replies[0]
        # Drain through the SSH command's successful exit, not just a JSON
        # prefix. Also reject a truncated UTF-8 suffix held by the decoder.
        parser.utf8.decode(b'', final=True)
        if reply is None or parser.text.strip():
            return None, {'reason': 'malformed-reply'}
        return reply, None
    except TVCommandError as error:
        return None, {'reason': 'client-start-failed' if error.exit_status in (126, 127) else 'client-error'}
    except UserError as error:
        if connection_interrupted(error):
            raise
        return None, {'reason': 'timeout' if error.reason_code == 'operation-timeout' else 'client-error'}
    except ValueError:
        return None, {'reason': 'malformed-reply'}
    finally:
        if channel is not None:
            channel.close()


def capture(remote):
    replies, failures = [], {}
    for kind in READS:
        reply, failure = read(remote, kind)
        replies.append(reply)
        if failure:
            failures[kind] = failure
    return replies, failures
