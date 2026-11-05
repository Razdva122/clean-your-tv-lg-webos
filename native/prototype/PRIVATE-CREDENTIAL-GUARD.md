# Private credential reader foundation

`native/app/private-credential.js` is check-only and deliberately unwired. It
reads only `/cytv-helper-state/ssap-key.json`, a UTF-8 JSON object with a nonempty
string `key`. The record has a 64 KiB byte bound; no additional key format or
length restriction is imposed. It never creates, repairs, pairs, imports shared
SDK state, calls a service or falls back to a legacy credential path.

The internal result is `{ok:true,key}` or `{ok:false,reason}` with reason
`missing`, `unsafe`, `unavailable` or `invalid-key`. A success object contains a
credential and must stay inside the native consumer, never a log or RPC reply.
There are no callers in this increment. The test factory injects filesystem and
kernel-process dependencies, with no path or command parameter.

Each call derives nonzero UID and GID from the process, pins an owned0755 root
FD/path, requires a same-owner/group0700 private directory and regular single-link
0600 file, and reads that checked FD in bounded chunks. File identity, mode,
owner/group, link count, size and available timestamps must match the path before
and after reading. Directory/root bindings are rechecked before and after key
bytes are read. All FDs close on success and failure. These endpoint checks are
not atomic openat confinement, specific app identity, executable integrity, or
proof of reboot persistence.

Focused host evidence: `node native/prototype/test-private-credential.cjs` passes
41 cases on current Node and exact0.10.15/0.10.25/0.12.2. Tests use real temporary
FDs, content and path replacements, with explicit native-root UID/GID metadata
fixtures. Old macOS Node0.10 does not export O_NONBLOCK; the fixture supplies its
host flag for these regular-file tests. The production reader requires exported
NOFOLLOW/NONBLOCK flags and returns unavailable when unsupported. No real key,
credential path or device was read. The source parses as ES5. Existing permission
and owner regression tests pass unchanged. The existing native test glob already
includes the focused test; no extra test group is added.

This is not a working Helper fix or a standalone shipping change. Provisioning,
authentication, all credential consumers, control/Stop migration, packaging and
final boot/device acceptance remain required before integration is usable.
