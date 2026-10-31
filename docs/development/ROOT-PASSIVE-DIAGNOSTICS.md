# Read an interrupted Root worker failure without recovery actions

Use this initial diagnostic for a `root-deploy` / `recovery_required` report
such as [#161](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/161),
when the original worker error is missing. It is separate from
[cancellation admission](ROOT-READONLY-ADMISSION.md). Working Home+ or another
launcher is not confirmation of LG Home and does not satisfy cancellation gates.

## One bounded read through the owner's existing Root SSH shell

Ask the owner to use their already working Root SSH session. This command uses
the system Node runtime (Root requires Node 8+) and built-in read APIs only.
It creates no TV files, stages no code, calls no Luna service and executes no
retained installer/recovery module. It does not launch/change Home, alter root,
reboot, install, remove, resume or reconcile anything. Filesystem reads may
update access timestamps; product/recovery contents and permissions are not changed.

Paste the complete block inside that existing TV shell, including the final
`CYTV_DIAGNOSTIC` line. Do not change permissions or paths if it refuses.

```sh
env -u NODE_OPTIONS -u NODE_PATH /usr/bin/node <<'CYTV_DIAGNOSTIC'
(function () {
  'use strict';
  var fs = require('fs'), c = require('constants');
  var base = '/var/lib/clean-your-tv-installation', out = {schema: 1};
  function directory(p) {
    var s = fs.lstatSync(p);
    if (!s.isDirectory() || s.uid !== 0 || (s.mode & 18)) throw Error('unsafe');
  }
  function read(p, limit, tail) {
    for (var parent = p.slice(0, p.lastIndexOf('/')); parent; parent = parent.slice(0, parent.lastIndexOf('/'))) directory(parent);
    directory('/');
    var fd = fs.openSync(p, c.O_RDONLY | c.O_NOFOLLOW | c.O_NONBLOCK);
    try {
      var s = fs.fstatSync(fd);
      if (!s.isFile() || s.uid !== 0 || s.nlink !== 1 || (s.mode & 63) || s.size > limit) throw Error('unsafe');
      var size = tail ? Math.min(tail, s.size) : s.size;
      var b = Buffer.alloc(size), offset = 0;
      while (offset < size) {
        var n = fs.readSync(fd, b, offset, size - offset, s.size - size + offset);
        if (n <= 0) throw Error('short-read');
        offset += n;
      }
      var after = fs.fstatSync(fd), current = fs.lstatSync(p);
      if (!current.isFile() || current.dev !== s.dev || current.ino !== s.ino ||
          after.size !== s.size || after.mtime.getTime() !== s.mtime.getTime()) throw Error('changed');
      return b.toString('utf8');
    } finally { fs.closeSync(fd); }
  }
  try {
    if (process.getuid() !== 0) throw Error('root-required');
    var failure;
    try { failure = JSON.parse(read('/var/lib/clean-your-tv-root/recovery-failure.json', 4096)); }
    catch (e) { if (e.code !== 'ENOENT') throw e; failure = null; }
    out.recovery = failure === null ? 'missing' : {};
    var allowed = {
      phase: ['manifest','stock-home','status','register','startup-hook','publish'],
      reason: ['failed','negative-reply','invalid-reply','oversized-reply','oversized-client-output','client-exited','client-start-failed','timeout'],
      luna_reason: ['permission-denied','service-missing','method-missing']
    };
    if (failure) Object.keys(allowed).forEach(function (k) {
      if (allowed[k].indexOf(failure[k]) >= 0) out.recovery[k] = failure[k];
    });
    directory(base);
    var names = fs.readdirSync(base), matches = [];
    if (names.length > 512) throw Error('too-many-records');
    names.forEach(function (name) {
      var m = /^request-([a-f0-9]{32})[.]json$/.exec(name);
      if (!m) return;
      var r = JSON.parse(read(base + '/' + name, 65536));
      if (r.operation !== m[1]) throw Error('mismatched-record');
      if (r.action === 'install' && r.stage === 'root-deploy' && r.state === 'recovery_required') matches.push(m[1]);
    });
    out.operation = matches.length === 1 ? 'one-root-deploy-failure' : matches.length ? 'ambiguous' : 'not-found';
    if (matches.length === 1) {
      var text = read(base + '/request-' + matches[0] + '/worker.log', 16777216, 8192);
      out.worker = {exception: 'unknown', frames: []};
      text.split('\n').forEach(function (line) {
        var e = /^(?:(?:subprocess|builtins)[.])?(ValueError|RuntimeError|CalledProcessError|OSError|PermissionError|FileNotFoundError|TypeError|KeyError):/.exec(line);
        if (e) out.worker.exception = e[1];
        var f = /^\s*File "[^"\r\n]*\/(install_driver[.]py|install_device[.]py|deploy[.]py|provision[.]py)", line [0-9]+, in (_run|perform|deploy|install|command|finalize|main|run)$/.exec(line);
        if (f) { out.worker.frames.push(f[1] + ':' + f[2]); out.worker.frames = out.worker.frames.slice(-8); }
      });
    }
    out.status = 'read';
  } catch (_) { out = {schema: 1, status: 'unavailable-or-unsafe'}; }
  console.log(JSON.stringify(out));
}());
CYTV_DIAGNOSTIC
```

The output contains fixed categories and allowlisted traceback frame names. It
omits addresses, keys, passwords, commands, original UUIDs, paths, raw exception
messages and full logs. Ask for only this small JSON response, after owner review.
Do not ask for private profiles, snapshots or the entire worker log. If it says
`unavailable-or-unsafe`, stop and review privately; do not chmod, delete evidence,
guess another operation, run a retained helper or bypass the check.

## Interpretation and next step

`recovery` reads a separate saved failure file. It is not cryptographically bound
to the selected worker here and may describe an older attempt. `ambiguous` never
selects the newest operation; `not-found`, unknown fields and missing files are
not successful recovery. A live writer can make the bounded snapshot refuse.

This diagnostic does not authenticate original candidate/package/snapshot bytes,
confirm process quiescence or inspect routing/LS2/activities. It is **not an
admission proof**, a cancellation authorization, evidence of preserved root or
firmware support. Even a `stock-home/service-missing` result only identifies a
possible next investigation; it does not admit the #133/#143 cancellation path.

After reviewing the result, prepare the exact reviewed-source admission procedure
for that operation with the owner. If third-party Home routing is active, retain
the existing refusal and investigate it separately; do not disable Home+ or write
Settings merely to satisfy admission. No Restore, Uninstall, reinstall, firmware
update, re-root or journal editing is requested by this diagnostic.

The procedure is source documentation, not a new installer command or package.
No TV has been contacted or recovered by its local fixture tests. Any later
installation/recovery report still requires the owner's approved text/destination.
