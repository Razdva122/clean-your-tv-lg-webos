'use strict';
/* Independent, read-only Linux ARM32 input observation. No Helper imports. */
var fs = require('fs');
var os = require('os');
var constants = require('constants');
var roles = {
    'LGE RCU': 'ir',
    'LGE M-RCU - Builtin [0]': 'magic_builtin',
    'LGE Simple Premium': 'simple_premium'
};

function allocate(length) { return Buffer.alloc ? Buffer.alloc(length) : new Buffer(length); }

function run(complete) {
    var devices = [], observations = [], selected = {}, timer = null;
    var finished = false, listening = false, start, previous, reads = 0, ticks = 0;
    var unavailable = false, scanning = true;

    function close(fd) {
        try { fs.closeSync(fd); } catch (ignored) { unavailable = true; }
    }
    function finish(reason) {
        var i;
        if (finished) { return; }
        finished = true;
        if (timer !== null) { clearTimeout(timer); timer = null; }
        for (i = 0; i < devices.length; i += 1) {
            if (devices[i].fd !== null) { close(devices[i].fd); devices[i].fd = null; }
        }
        if (listening) {
            process.removeListener('SIGINT', cancel);
            process.removeListener('SIGTERM', cancel);
            listening = false;
        }
        complete({
            schema_version: 1,
            status: observations.length ? 'observed_candidate' : 'no_observation',
            reason: reason,
            home_mapping_verified: false,
            observations: observations
        });
    }
    function cancel() { finish('cancelled'); }
    function clock() {
        var t = process.hrtime();
        var n = t[0] * 1000 + t[1] / 1000000;
        if (!isFinite(n) || n < previous) { throw new Error('clock'); }
        previous = n;
        return n;
    }
    function sourceRole(index) {
        var fd = null, b = allocate(256), n, name;
        try {
            fd = fs.openSync('/sys/class/input/event' + index + '/device/name', constants.O_RDONLY);
            n = fs.readSync(fd, b, 0, b.length, null);
            /* Reject truncation, NUL, CR and extra lines rather than trim unknown names. */
            if (n <= 0 || n >= b.length) { return null; }
            name = b.toString('utf8', 0, n);
            /* Confirm EOF so a short read cannot hide a non-allowlisted suffix. */
            if (fs.readSync(fd, b, 0, 1, null) !== 0) { return null; }
            if (name.charAt(name.length - 1) === '\n') { name = name.slice(0, -1); }
            return Object.prototype.hasOwnProperty.call(roles, name) ? roles[name] : null;
        } catch (ignored) { return null; }
        finally { if (fd !== null) { close(fd); } }
    }
    function scan() {
        var i, role, fd, stat;
        for (i = 0; i < 32 && !finished; i += 1) {
            if (clock() - start >= 10000) { finish('window_complete'); return; }
            role = sourceRole(i);
            if (!role || selected[role]) { continue; }
            fd = null;
            try {
                fd = fs.openSync('/dev/input/event' + i,
                    constants.O_RDONLY | constants.O_NONBLOCK | constants.O_NOFOLLOW);
                stat = fs.fstatSync(fd);
                /* Linux input major 13, evdev minor 64 + event index (0..31).
                 * These values fit the low dev_t encoding on ARM32. */
                if (!stat.isCharacterDevice() || stat.rdev !== 0x0d40 + i) {
                    unavailable = true;
                    close(fd); fd = null;
                    continue;
                }
                devices.push({fd: fd, role: role, pending: {}, dropped: false, tail: allocate(0), done: false});
                selected[role] = true;
                fd = null;
            } catch (ignored) { unavailable = true; }
            finally { if (fd !== null) { close(fd); } }
        }
    }
    function consume(device, data) {
        var bytes = Buffer.concat([device.tail, data]), offset, type, code, value;
        for (offset = 0; offset + 16 <= bytes.length; offset += 16) {
            /* Linux ARM32 little-endian timeval: two 32-bit longs; ignored. */
            type = bytes.readUInt16LE(offset + 8);
            code = bytes.readUInt16LE(offset + 10);
            value = bytes.readInt32LE(offset + 12);
            /* SYN_DROPPED invalidates an incomplete pair. */
            if (type === 0 && code === 3) { device.pending = {}; device.dropped = true; }
            if (type === 0 && code === 0) { device.dropped = false; }
            if (device.dropped) { continue; }
            if (type !== 1 || code > 2047) { continue; }
            if (value === 1) { device.pending[code] = true; }
            if (value === 0 && device.pending[code] === true) {
                observations.push({role: device.role, candidate_code: code, completed_pair: true});
                device.done = true; device.pending = {}; device.tail = allocate(0);
                close(device.fd); device.fd = null;
                return;
            }
        }
        /* Copy at most 15 bytes: never retain an entire consumed input buffer. */
        device.tail = allocate(bytes.length - offset);
        bytes.copy(device.tail, 0, offset);
    }
    function poll() {
        var i, device, buffer, n, active = false;
        if (finished) { return; }
        timer = null;
        try {
            if (clock() - start >= 10000) { finish('window_complete'); return; }
            if (ticks >= 500) { finish('clock_failure'); return; }
            ticks += 1;
            for (i = 0; i < devices.length; i += 1) {
                device = devices[i];
                if (device.done) { continue; }
                active = true;
                if (reads >= 128) { finish('read_budget_exhausted'); return; }
                buffer = allocate(512);
                try {
                    n = fs.readSync(device.fd, buffer, 0, buffer.length, null);
                    if (n > 0 && n <= buffer.length) { reads += 1; consume(device, buffer.slice(0, n)); }
                    else { unavailable = true; device.done = true; close(device.fd); device.fd = null; }
                } catch (error) {
                    if (error.code !== 'EAGAIN' && error.code !== 'EWOULDBLOCK' && error.code !== 'EINTR') {
                        unavailable = true; device.done = true; close(device.fd); device.fd = null;
                    }
                }
            }
            if (!active || devices.every(function (item) { return item.done; })) {
                finish(unavailable ? 'input_unavailable' : observations.length ? 'window_complete' : 'no_allowed_source');
                return;
            }
            timer = setTimeout(poll, 20);
        } catch (ignored) { finish('clock_failure'); }
    }

    if (process.platform !== 'linux' || process.arch !== 'arm' || os.endianness() !== 'LE' ||
            typeof process.hrtime !== 'function' || constants.O_RDONLY !== 0 ||
            typeof constants.O_NONBLOCK !== 'number' || constants.O_NONBLOCK === 0 ||
            typeof constants.O_NOFOLLOW !== 'number' || constants.O_NOFOLLOW === 0) {
        finish('unsupported_runtime'); return;
    }
    listening = true;
    process.on('SIGINT', cancel);
    process.on('SIGTERM', cancel);
    try {
        start = clock();
        scan();
        scanning = false;
        if (!finished) { poll(); }
    } catch (ignored) { finish(scanning ? 'input_unavailable' : 'clock_failure'); }
}

module.exports = {run: run};
if (require.main === module) {
    if (process.argv.length !== 2) {
        process.stdout.write(JSON.stringify({schema_version: 1, status: 'no_observation',
            reason: 'unsupported_arguments', home_mapping_verified: false, observations: []}) + '\n');
    } else {
        run(function (report) { process.stdout.write(JSON.stringify(report) + '\n'); });
    }
}
