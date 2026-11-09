# Root Node 0.12.2 compatibility prototype

<a id="unreleased-installer-beta"></a>

## Release 1.12.0 installer Beta

The separate `--legacy-node-beta` build mode enables exact Node 0.12.2 admission
in generated device code. The original `--legacy-node-prototype` mode below
remains host-only with Node 8+ admission. Neither is a hardware support claim.

The common installer also includes a Node 0.12.2 build of the existing mount-free
KeyFilters Home backend. Its source and selection are shared with ordinary Root;
only the Node compatibility build/runtime policy differ. Selection still requires
explicitly absent System Profile and supported firmware/device capabilities.
Admission uses verified capabilities rather than an SDK
number. It still requires a stock native Home executable; in-compositor Home
ribbons are unsupported. SDK 3.9.0 fixture success is not target-TV acceptance. See
[shared Home backend and recovery limits](C1-NATIVE-GATE.md#shared-root-runtime-variants-unpublished-beta-packaging).

The common installer stages Beta under `legacy-root-beta/`, containing both
graphics variants, the complete Root Updater/coordinator and System Updater.
All source transformations occur before bundle, IPK and outer payload hashes.
Beta marks `release.json` with `runtime_variant: node012-beta`; normal deployment
drivers reject that bundle. Generated Root and System setup accept only exact
0.12.2, and both updater Python entrypoints refuse `check` and new `install`
before network/transaction work. Status, restoration and original recovery remain
available. The normal shipping Root graph retains its Node 8+ gate.

Node 0.12.2 rejects Node's `--require` option. Its Beta recovery runner retains
the unchanged firmware bootstrap as the main script and initializes diagnostics
when entering project service code. Failures before project entry are therefore
not covered by that diagnostic file. Passive original-operation reads use
legacy Buffer APIs and never execute retained code.

Before any install submission, the shared CLI offers a default-cancel choice
after an identified ordinary Root Node refusal. Beta needs an additional
default-no confirmation; `--yes` cannot choose it. Other old Node versions offer
No-root only, subject to Helper requirements. Both editions' local pending work
and retained Root device state prevent a switch. All frontends reuse these
choices and persist the transport/variant for later maintenance.

No-root over root SSH uses the existing root authentication and pinned host key,
the private Luna sender, a distinct root-owned observer namespace and protected
IPK staging under `/var/lib/clean-your-tv-installer`. Its configuration uploads
inherit the verified Helper state directory's owner/group before publication.
The original Developer Mode observer program remains byte-identical so its
existing authenticated capsules remain usable. Product edition remains No-root;
root SSH does not grant permission to remove an unrelated Root installation.

Useful source commands (no TV connection):

```sh
npm ci
.venv-cytv/bin/python scripts/build-cytv.py --payload-only
NODE012=/absolute/path/to/node-v0.12.2/bin/node .venv-cytv/bin/python tests/root-node-compat.py --beta
NODE012=/absolute/path/to/node-v0.12.2/bin/node .venv-cytv/bin/python -m unittest tests.cytv.test_legacy_beta_build tests.cytv.test_root_runtime tests.cytv.test_root_passive
```

CLI maintenance can explicitly select `--edition no-root --connection root-ssh`
or `--edition root --root-variant node012-beta`; normal saved-profile selection
retains these fields. Beta feedback uses the existing local report and manual
[feedback guide](../FEEDBACK.md), including model, firmware/webOS, remote,
installer platform, exact versions, expected/actual tests and attempted recovery.
Untested fields remain untested. No automatic uploads or issue comments occur.

Physical acceptance and signed public delivery are still outstanding. This work
does not change an active frozen release's scope or select a release build.

## Original host prototype

This is an **opt-in host prototype for issue #160**, not a supported installation
path. Root still requires system Node 8+ in the computer installer, on-device
setup, deployment and Homebrew bootstrap. No TV was accessed to develop it.
It does not establish firmware routing, native LS2 module ABI, Home controls,
sound, standby, cold boot, OTA, rollback or compatibility on any TV. Candidate
scope, versions, build selection and acceptance are managed separately.

## Build and check locally

Run `npm ci` first. Each builder exposes an explicit flag; ordinary payload and
release builds do not select it:

```sh
python3 root-edition/build.py --output build/root-node-prototype --version 0.0.1 --legacy-node-prototype
python3 root-edition/build_updater.py --output build/root-updater-node-prototype --legacy-node-prototype
python3 system-updater/build.py --output build/system-node-prototype --legacy-node-prototype
```

The output directory must not exist. These artifacts retain component metadata;
keep them local and identify them by source revision, prototype flag and hashes.
Do not install, sign, publish or substitute them for a frozen candidate. Gate 8+
still rejects a TV with Node 0.12.2. System Node/Python, firmware and root are
never replaced. There is no new private Node runtime or provisioning endpoint.

Run the generated-artifact regression, preferably on Linux with the pinned
Node 0.12.2 already prepared by CI. `NODE8` optionally adds exact Node 8 coverage:

```sh
NODE012=/absolute/path/to/node-v0.12.2/bin/node \
NODE8=/absolute/path/to/node-v8.12.0/bin/node \
python3 tests/root-node-compat.py
```

Current Node always runs. Without `NODE012`, the script explicitly reports that
legacy execution was not performed. The TV test group runs this regression;
Linux CI supplies its existing SHA-256-pinned official Node 0.12.2. The baseline
option `--baseline` omits prototype compilation to reproduce the original syntax
failure on Node 0.12.2. Neither option contacts a TV. HTTPS tests open a temporary
loopback listener only.

## Build closure and trust boundaries

`scripts/root_node_build.py` and `compile-root-node.cjs` reuse Helper's existing
Babel/core-js/safe-buffer build dependencies. Every Node JS file receives ES5
syntax, an inline compatibility initializer and retained license text. Core-js's
WHATWG URL implementation supplies Node 0.12's missing `url.URL`; the native
`constants` module supplies the absent `fs.constants`. Safe Buffer methods are
added to the original Buffer constructor. Compatibility initializes once per
process, including independent nested fetch/policy CLIs and `python_boot.js`.
There are no added package/runtime paths; the initializer uses a process-local
`__cytvRootNodePrototypeCompat` flag, not a persisted TV state file.

Root IPK recovery service compilation happens after theme receiver injection;
Root support, Root updater and System supervisor bundles are compiled before
hashing. Root infrastructure is assembled from those actual generated bundles
and the Root IPK, including every private support copy. Existing bundle hashes,
IPK file hashes and supervisor infrastructure path inventories remain
self-consistent. **Hashes change:** these are not equivalent release artifacts
or permission to reuse old source/code pins or acceptance. No historical
supervisor migration, retained recovery driver or removal validator is relaxed.

The System download client also uses one explicit HTTPS options object, as the
Root client already does, so the configured CA, strict verification, headers and
callback reach the legacy API. This correction applies to the source client as
well as prototype compilation. URL allowlists, signature verification, redirect,
size and deadline limits remain enforced.

## Actual regression scope

The harness builds default and prototype Root IPKs, Root updater and System
supervisor bundles, verifies bundle hashes, extracts actual IPK services, and
checks the complete generated infrastructure inventory. Default builders still
copy Node sources without compatibility compilation. Prototype inventories have
the same paths. Each generated Node script is parsed in the selected exact
runtime; Chromium frontend assets remain under their separate web-engine tests.

Functional checks execute actual generated code for signed Root/System manifests
and standalone verification CLIs (including rejection under the packaged key),
valid and adversarial URLs, recovery status/activity boot, inventory, receiver
caller authorization, Root/System updater dispatch and the audio transaction
lock. Firmware `webos-service`, root UID, Luna calls and Python transaction
execution are bounded test substitutes: no firmware service is actually run.

Local HTTPS exercises the real Node TLS stack with a synthetic CA and verifies
success, relative redirects, foreign redirect refusal, redirect count, size,
HTTP/aborted transfer, hostname mismatch, untrusted certificates and deadlines.
Only the destination and fixture CA are replaced in the test process. The
original strict TLS options and real stream handling are retained. No public
network download or public feed availability is asserted.

The actual generated diagnostic preload writes its starting/exited records using
native file descriptors and preserves an explicit child exit status. Only TV root
ownership/directory-mode metadata is substituted in that fixture.

Five generated Python binding copies reject modified code, receipts, symlinks,
hard links, ownership/mode changes and unsafe driver paths before child launch.
A real local Python child verifies the generated binding's status propagation.
Synthetic signing keys/certificates live only in an automatically removed test
directory. The real release key rejects those fixture signatures; successful
CLI fixture verification uses a separate disposable copy, never a changed
packaged or published release key. The actual deployment gate executes with the
selected Node binaries and still rejects Node 0.12.2.

## Work required before any supported legacy installation

Keep #160 open. This is preparatory code, not a fix of its installation failure.
Do not infer support for #164 or use Helper #181 as Root acceptance. Before a
future gate change, independently review the generated closure, authenticate
and test the target vendor runtime/native module ABI, establish the firmware's
supported Home routing/recovery contract, and verify exact-build recovery,
installation/removal, controls/emergency state, audio, standby, cold boot and
signed update/rollback with an owner-authorized device session. Unknown target
userland ABI remains unknown; `uname -m` alone is insufficient. Existing older
routing work such as #107 is separate. No new device request is made here.


## Next prerequisite: vendor bootstrap and firmware contract

[2026-11-02 source/host investigation](../history/2026-11-02-legacy-root-prerequisites.md)
rechecked the generated closure after v1.6.0. The next missing evidence is the
**target firmware's bootstrap/module closure and Home interface readback**.
More transpilation or lowering Doctor's version requirement cannot supply it.
The record separates executable host evidence from target ABI, routing and
owner-supervised acceptance; it does not introduce an installation procedure.

The [2026-11-04 offline vendor follow-up](../history/2026-11-04-legacy-root-offline-vendor.md)
identifies an official B9 05.50.00 firmware input and the concrete next host-only
extraction/review task. It records bootstrap/native identity dependencies and
why current public OSE modules cannot substitute for the target firmware.
No TV connection or supported installation path is introduced.
