# Legacy Root prerequisites after v1.6.0

Source reviewed: `da748e26b015564d98aa2deba8b3cfb9c8b19f4d` (`release/next`).
Scope: #160, the legacy runtime part of #164, and the already delivered parser
part of #68. This is a source/host investigation. No TV was contacted or changed;
no installation, device result or supported legacy path is claimed.

## Reproduced host behavior

`npm ci` completed. The first generated-artifact run stopped because this host
Python lacked fontTools. A temporary host venv with
`scripts/build-requirements.txt` resolved that build dependency; it is not a TV
Python repair. The complete command then passed:

```sh
NODE012=/absolute/path/to/node-v0.12.2-darwin-x64/bin/node \
/absolute/path/to/host-venv/bin/python tests/root-node-compat.py
```

Host: macOS ARM64; official Darwin x64 Node **v0.12.2**, plus current Node
**v23.11.0**. The Node archive SHA-256 was
`7d382f8988ea441e2918d9d935003177affd13d4d160020df6b3d8ee7d65ec2d`,
matching the official v0.12.2 `SHASUMS256.txt`. Exact Node 8 and Node 0.10.25 were
not run in this investigation. Root's prototype targets 0.12.2; Helper's separate
0.10.25 fixtures are not Root compatibility evidence.

On both selected runtimes the harness passed generated diagnostic native-fd
writes/exit status, the 25-script closure/signature/dispatch tests, real loopback
HTTPS/TLS tests and all five generated Python-binding copies. This covers strict
CA and hostname verification, relative/foreign/looping redirects, response-size
limits, HTTP/abort/deadline errors, and binding rejection before child spawn.
It also asserts the ordinary builder paths and Node 8+ deployment gate. No new
host defect was reproduced, so no speculative compiler/runtime change was made.
Loopback uses a synthetic CA and destination; public GitHub TLS, vendor trust
store and vendor OpenSSL behavior on the TV remain untested.

Existing contract suites also passed: `test_root_capabilities.py` (9),
`test_private_service.py` (7), `test_root_provision.py` (17) and
`test_root_runtime_profile_plan.py` (9), **42 tests total**. Root suites use
`PYTHONPATH=root-edition`; an initial private-service invocation without that
path failed import before running tests, then passed with the required path.
`git diff --check` passed. Independent focused documentation/source review found
no actionable issues. No new test was added because no product behavior changed.

## Exact boundary the host harness cannot establish

The service fixture replaces `webos-service`, root UID, child dispatch and Luna
responses. The binding fixture exercises the generated **Python launcher trust
validator**, not a native Node/LS2 binding. Its five passing copies must not be
reported as proof of a vendor native module ABI.

The actual production launch chain is defined by:

- `root-edition/provision.py`: checked system Node and both
  `/usr/palm/services/jsservicelauncher/bootstrap-node.js` and `bootstrap.js`;
  the private recovery runner executes system Node with the diagnostic preload,
  `bootstrap-node.js -- PIDFILE /var/palm/ls2-dev PRIVATE_SERVICE`.
- `root-edition/updater/bootstrap.py` and `system-updater/setup.py`: the same
  vendor bootstrap argument shape for their private service closures.
- All three runners supply
  `NODE_PATH=/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules`.
  Their actual services require the firmware's `webos-service`.

Those firmware files and the resolved module/native dependency closure are not
contained in the prototype bundles or the reporter's version outputs. The exact
module filenames, architecture, loader dependencies and ABI therefore remain
unknown. A host x64 runtime cannot authenticate an ARM vendor closure, and the
B9's `uname -m` does not identify its Node executable's userland ABI.

## Minimum evidence needed for the next decision

This is a handoff for a separately authorized bounded investigation, **not a
request to run commands, install a prototype or repeat Doctor now**.

| Boundary | Missing input or result | Decision it enables |
| --- | --- | --- |
| Vendor runtime | Target model/firmware, Node `process.versions`/architecture, authenticated system Node and vendor bootstrap/module identities, native ELF class/machine/interpreter/dependencies | Select an ABI-compatible vendor execution path; do not assume a replacement Node can load vendor bindings |
| Vendor bootstrap | Review the target bootstrap sources and resolved `webos-service` native closure, then an authorized isolated bootstrap/register/respond/exit result with the intended UID and LS2 permissions | Establish the real invocation and service contract; a mocked constructor or simple `require` is insufficient |
| Home reads | Successful Settings `general.defaultApps` and System Profile `defaultApps`/`idleApp` replies under the existing validators | Establish whether this firmware has the required routing interface at all |
| Recovery | Independent write/rescan/readback and recovery proof for all three Home routes on that firmware | Determine whether a bounded activation trial is justified |
| Delivery | Exact signed prototype/candidate identity and owner-approved installation/removal, controls/emergency, audio, standby, cold boot, OTA/rollback scope | Establish only the tested device/scenario acceptance before any admission change |

Keep collected system binaries, module sources and raw replies private for review;
only concise redacted conclusions belong in issue updates. Do not collect app
inventories, credentials or unrelated Settings. Do not start or register a service
merely to fill this record. Device operations require the separately agreed scope.

The existing read schemas are in `cytv/root_capabilities.py` and
`root-edition/provision.py`: explicit successful replies, Settings `defaultApps`
an object (an absent `home` override is allowed), nonempty trimmed profile route
strings and Boolean `idleApp.support`. `false` is a valid read result; it does not
prove activation/recovery support. Missing System Profile is an independent
blocker; neither Node compatibility nor a Settings-only bypass resolves it.

## Issue disposition

- [#160](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160): the
  [B9 runtime reply](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/160#issuecomment-6529192934)
  identifies Node 0.12.2. The admitted Root installation remains unsupported;
  vendor ABI/bootstrap and firmware readbacks above are not supplied. Keep the
  supported-path work queued, rather than request the same versions again.
- [#164](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/164):
  [LJ622V outputs](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/164#issuecomment-6543601275)
  are for a separate TV. Original UJ630V runtime outputs remain outstanding;
  its existing information request still applies. Neither LJ622V nor B9 proves
  UJ630V compatibility. The reporter's willingness to test is not an agreed
  bounded device session.
- [#68](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/68): source CLI
  banner parsing and static fonts already shipped through #70/#72 in v1.3.0.
  Original visual confirmation and Helper-unavailable evidence remain requested.
  No new font or Helper fix follows from this Root investigation.

Normal Root still requires Node 8+ and the prototype remains opt-in/off by
default. No versions, release inventory, trust/rollback guards or SSH/bootstrap
implementation were changed. These prerequisites do not block unrelated fixes
in the next release, and this record does not resolve the original reports.
