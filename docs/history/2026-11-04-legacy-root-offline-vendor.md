# Legacy Root: next offline vendor investigation, 2026-11-04

Repository source: `4ceadb65f56cef9780a9f8e4111bc8ba95500597`
(`release/next`). Scope: #160 only. This is a host/source investigation,
not an installation procedure or an enabled legacy release. No TV was contacted.
No system Node/Python, firmware, Home route or recovery record was changed.

## Result and next work item

The candidate path is **compiled project JS on the existing firmware Node
0.12.2, using that firmware's own bootstrap and native modules**. It does not
require replacing system Node or shipping a second Node. It is not yet a
supported Root path: the target launch chain and Home/recovery contracts remain
unverified.

The next concrete work item is **establish the offline extraction prerequisite,
then extract and statically review the official B9 05.50.00 firmware on a computer**, producing a private, hash-bound vendor
dependency inventory before proposing a target bootstrap experiment. This can
start without contacting the reporter's TV or asking for repeated version output.
Do not substitute current OSE modules for the firmware modules.

This advances the [previous prerequisite record](2026-11-02-legacy-root-prerequisites.md)
with an official offline input, named dependencies, invocation/security checks
and an explicit completion criterion.

## Primary sources and new findings

[LG's JS service specification](https://webostv.developer.lge.com/develop/guides/js-service-basics)
lists Node 0.12.2 for webOS TV 3.x/4.x. This agrees with the reporter's existing
output; it is not an anomalous system runtime that installation should repair.
The same page distinguishes pure JS dependencies from C/C++ add-ons. Root's
privileged services are a separate project implementation; the public app
documentation is not approval of its Root permissions or private launch path.

The following **reference sources** were read at immutable public revisions.
They establish what must be checked, not the contents of the B9 firmware:

| Reference | Pinned revision | Relevant observation |
| --- | --- | --- |
| [LG OSE launcher](https://github.com/webosose/mojoservicelauncher/tree/1dc7681fc2b5995c219801efd33cda0cbfbd7879) | `1dc7681fc2b5995c219801efd33cda0cbfbd7879` | `bootstrap.js` requires `mojoloader`, consumes the post-`--` PID-file argument and reads service metadata from the working directory. `bootstrap-node.js` calls `palmbus.setAppId`, optionally pushes public/private roles and requires the service directory. |
| [LG OSE service library](https://github.com/webosose/nodejs-module-webos-service/tree/1dd2c9d6cd21eb5d84f7619432ed6d2784bb56f9) | `1dd2c9d6cd21eb5d84f7619432ed6d2784bb56f9` | JS wrappers require both `palmbus` and `pmloglib`; service construction creates native handles and activity tracking. A successful import alone is not a registration/dispatch test. |
| [LG OSE native bus binding](https://github.com/webosose/nodejs-module-webos-sysbus/tree/74dba8be8deae3dfe6a6c9f3e3e733c61ad3aa1c) | `74dba8be8deae3dfe6a6c9f3e3e733c61ad3aa1c` | `palmbus.js` loads `webos-sysbus.node`. The build links GLib and luna-service2. `SetAppId` checks caller-script identity against build-generated trusted paths in this revision. |

The native identity check is an additional reason **not to copy, patch or
transpile the firmware bootstrap into project-owned state** merely to make a
host test pass. The reference binding can reject that execution context even
when the JS parses. Whether the B9 binding implements the same check is unknown;
inspect its actual implementation/build or binary before drawing that conclusion.

Current public `webos-service` is also not a ready-made legacy dependency:
on exact Node 0.12.2 its `lib/service.js` fails parsing at
`function(...params)`. The initial public revision
[`bad46b2c28ecb53bfd8da37349b61c478473a65d`](https://github.com/webosose/nodejs-module-webos-service/tree/bad46b2c28ecb53bfd8da37349b61c478473a65d)
parses. Neither is authenticated as the B9 module. This comparison is a warning
against substituting a convenient upstream checkout, not evidence of a defect
in the reporter's firmware.

## Official offline firmware input

[LG's OLED65B9PLA support page](https://www.lg.com/ru/support/product/lg-OLED65B9PLA.ADRB)
lists version **05.50.00**, dated **2025-09-19**, and includes OLED65B9PLA in
the applicable models. Its public
[firmware ZIP](https://gscs-b2c.lge.com/downloadFile?fileId=yO2QC2KTmfkO6FAPqWYPOw)
is a candidate offline input. The reporter's full regional suffix is unknown;
do not claim this identifies the installed image byte for byte.

A bounded HTTP Range read of bytes 0–4095 returned HTTP 206,
`Content-Range: bytes 0-4095/1006244110`. The ZIP local header names:

```text
lib32-starfish-dvb-secured-m16p3-grampians-31-05.50.00_prodkey_usb_V3_SECURED.epk
```

Only the header was downloaded in this investigation. The complete ZIP/EPK
hash, CRC, signed-container verification, decryption and filesystem extraction
are **not performed**. The filename's `lib32` is a clue, not proof of the Node
ELF architecture or its installed loader. HTTPS source provenance does not
replace signed-container verification or establish correspondence with the
reporter's live filesystem.

## Extraction prerequisite found during review

The candidate extractor [epk2extract at
`a0ccd8a4b4f48d05675a4cddd233f8780ee36767`](https://github.com/openlgtv/epk2extract/blob/a0ccd8a4b4f48d05675a4cddd233f8780ee36767/README.md)
documents AES/RSA key inputs for EPK v2/v3. It does not make the encrypted
vendor filesystem available merely because the official ZIP can be downloaded.
No extraction key or matching extracted sysroot was supplied or used here; no
claim of successful verification/decryption follows from the archive header.

Therefore the **first bounded action** is to establish whether a trusted,
lawfully available offline key set or independently authenticated extracted
05.50.00 sysroot is already available for this image. Record its provenance
privately, without publishing keys. This investigation does not authorize or
request dumping keys from a TV. If no qualifying offline input is available,
stop at `encrypted-image / target-closure-unavailable`: the no-TV constraint
remains in force. Do not lower admission or replace the target closure with
OSE simply to unblock the research. The official image locator is useful
preparation, not a promise that its encrypted contents can already be inspected.

## Bounded offline extraction task

Use a separate disposable host directory, with no TV profile, SSH identity or
device transport. Keep firmware binaries and extracted vendor sources out of
this repository and public issue attachments.

1. After the offline extraction prerequisite is met, download the complete ZIP
   from the official input above. Record final URL,
   byte length, SHA-256, ZIP integrity and EPK identity. Record the extraction
   tool's exact source/version and the vendor-signature verification result
   separately from decompression success. If verification or extraction is
   unavailable, retain that specific blocker rather than accepting an arbitrary
   mirror, unrelated firmware or unsigned reconstruction.
2. Extract on the host without executing image scripts/binaries. Preserve the
   image paths and symbolic-link targets in the inventory; do not accidentally
   resolve a firmware link against the host's `/usr`. Resolve every dependency
   within the extracted image and record missing components.
3. Inventory the closure below with source-image identity, path, type/link target,
   size and SHA-256. Inspect ELF headers/dynamic metadata statically (for example
   `readelf -h -l -d -V`); do not use execution or `ldd` to infer dependencies.
   Record ELF class, machine, interpreter, needed libraries, RPATH/RUNPATH and
   symbol-version requirements. This establishes static compatibility constraints,
   not that a native module can actually load.
4. Trace bootstrap metadata/arguments, module lookup order, native identity
   restrictions and LS2 registration/permission format against all three project
   runners. Check the target service library's caller identity, method dispatch,
   activity lifetime and response APIs used by Root. Do not infer modern ACG
   compatibility from a readable package alone.

Required dependency inventory:

| Entry | Required review |
| --- | --- |
| `/usr/bin/node` and its loader/library closure | Actual userland ABI and runtime identity; kernel `uname` is insufficient. Vendor source/build correspondence or later runtime evidence remains needed for the native module ABI. |
| `/usr/palm/services/jsservicelauncher/bootstrap-node.js` and `bootstrap.js` | Exact argument parser, cwd assumptions, PID-file effects, service ID, trusted-script path and role handling. |
| `mojoloader`, `webos-service`, `palmbus`, `pmloglib` | Resolve under the project runners' `NODE_PATH=/usr/palm/frameworks:/usr/lib/nodejs:/usr/lib/node_modules`, including the actual Node lookup rules and recursive JS/native dependencies; do not guess filenames from OSE. |
| Resolved native `.node` files and their ELF dependencies | Node/V8 module ABI evidence, architecture, loader, GLib/LS2/logging dependencies and caller-script checks. No rebuild/replacement is implied. |
| Target LS2 launch/role/permission configuration relevant to these services | Whether the current private recovery/updater/supervisor launch and own caller identity can be represented without widening authority. |
| Relevant Settings/System Profile implementation/configuration | Static evidence about availability/schema; file presence alone cannot prove a successful live Home read, writes or recovery. |

The three project runners are `root-edition/provision.py:runner_bytes`,
`root-edition/updater/bootstrap.py` and `system-updater/setup.py`.
They currently retain system Node, the vendor bootstrap path, private cwd,
PID file, LS2 configuration root and fixed `NODE_PATH`. Root recovery also
uses its packaged diagnostic preload. Review that full invocation; replacing
the `webos-service` constructor in a fixture skips it.

**Done for this offline task:** a private image-bound closure inventory plus a
redacted report classifying each required boundary as statically compatible,
incompatible or unknown, with exact evidence and the next experiment it permits.
An unavailable image/verification/module is an explicit unknown, not a pass.
A mismatch should produce a focused proposal/test before any admission change.

If static review is compatible, the following implementation step is a separately
reviewed bootstrap/registration experiment using the **unchanged target** runtime,
bootstrap and native modules. A host fixture can exercise real vendor JS with a
substitute native boundary, but must label that substitution and cannot satisfy
native ABI, permissions or live Home acceptance. No such device experiment is
authorized or performed by this record.

## Checks actually run

Host: macOS ARM64, Python **3.14.2**, current Node **23.11.0**, official Darwin
x64 Node **0.12.2**. No TV model/remote applies to host tests. The Node archive
SHA-256 `7d382f8988ea441e2918d9d935003177affd13d4d160020df6b3d8ee7d65ec2d`
matched the [official Node checksums](https://nodejs.org/download/release/v0.12.2/SHASUMS256.txt).

- `npm ci --no-audit --no-fund` passed. An isolated host venv installed the
  existing `scripts/build-requirements.txt` pin, fontTools **4.60.1**.
- `NODE012=<verified-node>/bin/node .venv/bin/python tests/root-node-compat.py`
  passed on exact 0.12.2 and current Node: 25-script generated closure,
  signatures/dispatch, strict loopback TLS/redirect/bounds, diagnostic fd writes
  and all five generated Python-launcher binding copies. The fixture still
  substitutes `webos-service`; native LS2 and vendor TLS are not tested.
- Existing `test_root_capabilities.py` (9), `test_private_service.py` (7),
  `test_root_provision.py` (17) and `test_root_runtime_profile_plan.py` (9)
  passed: **42 cases**. The last three live under `root-edition/tests`, with
  `PYTHONPATH=root-edition`. An initial invocation used nonexistent
  `tests/root` and failed discovery; correcting the test directory passed.
- Parse-only `new Function(fs.readFileSync(file, 'utf8'))` on exact 0.12.2
  accepted the pinned OSE bootstrap files and initial service source, and rejected
  the current service source as described above. No vendor module was required,
  registered or run.

Parse input SHA-256:

| Input | SHA-256 |
| --- | --- |
| OSE `bootstrap-node.js` | `51261fff92729e3d5609f90b05954c188e4c8b681754721394e60dcfd3a97cd4` |
| OSE `bootstrap.js` | `0e7d01f9115f563b6f8a865b0640698b923eb0b86c44e4906ed96c1c0401f730` |
| Initial OSE `lib/service.js` | `31af3688a683d673b16e81087811c06ac4cddba8cd247a01534a53c5499921aa` |
| Current pinned OSE `lib/service.js` | `1c79c88c21d44f3169ce4c287ce09cad0e8c00d30b035383d6ad16f13f530bb7` |

## Remaining support boundaries

Normal Root admission remains Node 8+ in the computer installer, device deployment,
updater and supervisor bootstrap. The compiler remains opt-in. No shipped payload,
permission, endpoint, runtime gate, recovery authority, version or release plan
changes here. The twelve localized setup/control guides need no action change.

Successful target Settings/System Profile read/write/recovery contracts are still
required independently of JS/ABI. Exact signed installation/removal, Home and other
controls/emergency, audio, standby, cold boot, OTA and rollback remain untested.
The B9 remains unsupported by the normal Root path; #160 stays open with the
remaining maintainer work queued. No repeat Doctor/version output or new reporter
device action is requested.
