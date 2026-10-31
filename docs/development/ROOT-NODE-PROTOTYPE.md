# Root Node 0.12.2 compatibility prototype

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
