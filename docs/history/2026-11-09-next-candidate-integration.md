# Next candidate integration, 2026-11-09

This is source integration and host verification for [candidate #458](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/458), after published v1.14.0. No TV was contacted, no installation report is republished, and no physical acceptance or public delivery is claimed. The candidate remains unfrozen: version selection, final build pin and acceptance are pending.

## Scope and conflict resolution

The batch integrates #457, #459, #461 and #462 into `release/next` using merge commits. #460 already reconciled the previous publication's current instructions. The committed release plan owns the complete inventory.

- #457 supplies legacy No-root stock-screen removal, retained schema-1 C1 recovery support, asynchronous cleanup and current matching-completion reconciliation. See [removal evidence](2026-11-09-installer-removal-four-issues.md).
- #459 requires explicit full reinstallation to deliver the selected runtime and bounds fresh activation failure explanations. See [runtime delivery evidence](2026-11-09-root-installer-runtime-delivery.md).
- #461 changes website/demo presentation and adds individual/intersected Video/4K filters. Its PR records website/browser verification; installed TV controls are unchanged.
- #462 supplies narrow immutable-system-image admission and a verified cleanup-to-new-native-request handoff. See [native admission evidence](2026-11-09-issue440-native-install-recovery.md).

Updating #462 after #457 exposed a cleanup-tail conflict. Retain the asynchronous child reader, fallback activity inventory, complete-removal reconciliation and confined scratch retirement from #457 together with #462's stock-compositor proof. Convert the added stock-proof call chain to async/await, including awaiting the configuration reply before reading `configs`. Existing stock-compositor tests now prohibit synchronous subprocesses and cover both final cleanup and read-only proof/refusal paths.

Updating #459 retains both dated history entries. Combining it with #462 preserves both rules: a self-consistent installed runtime requires explicit replacement, while verified clean removal with `can_install` admits a fresh request and selects the native handoff when appropriate. No `can_maintain` shortcut is restored.

## Verification

Combined product/test source: `225f34aae845c7b10ebae43fbda924827114934a`; #462 conflict-resolution source: `60eef4d50ae1984df0091ade1242bae91d811d83`.

- Cleanup-tail suite on current host Node: 55 tests, two platform skips.
- Cleanup-tail/child suites on exact Node 8.12.0: 58 tests, three platform skips.
- Root clean removal: 81 tests passed.
- Combined native/clean-reinstall/explicit-reinstall host group: 64 tests passed.
- `npm ci`, `npm run format:check`, README release metadata (three tests) and whitespace checks passed.

The first direct cleanup-suite command omitted `PYTHONPATH=root-edition`, causing five import errors. The async integration also initially accessed a Promise's `configs` property, causing two stock-proof failures. The corrected command and awaited reply passed the complete cleanup suites above; no failing result is counted as acceptance.

Refreshed selected PR CI passed on the exact conflict-resolution sources:

- #462: [Tests](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42594909549), source `60eef4d5`.
- #459: [Tests](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42595136621), [desktop runtime](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42595136616), [website/preview](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42595136620) and Integration policy, combined source `225f34aa`.
- All selected PR checks for #457/#461 also passed before integration. The merged `release/next` product tree at `f8d2eb8f7` is identical to checked combined source `225f34aa` (`git diff --exit-code 225f34aa f8d2eb8f7`).

The additional local affected run `scripts/test.sh installer setup android tv-runtime` passed Root (1,200 tests, three skips), System (136), setup (289), selected native/JS/legacy runtime and Homebrew support checks. After the matching combined-source CI passed the selected full PR matrix, the redundant local run was stopped deliberately during the installer suite (exit 143). The local installer suite and subsequent Android group are not claimed complete; their selected checks passed in that CI. These are distinct from a versioned frozen-candidate build.

## Documentation, packaging and remaining work

The release PR records the affected English recovery/maintenance and developer guides, all thirteen localized practical guides, website reference and unchanged published README metadata. Final candidate-wide documentation/link/translation review remains pending at freeze.

Root, installer, Android and affected updater support need version/manifests and rebuilt artifacts at freeze. Unchanged Helper source does not carry these installer fixes. No component version is selected by this integration. Full trusted candidate build, signed package equivalence, original-signer APK upgrade and affected update/rollback acceptance remain pending. Homebrew promotion remains disabled under its independent acceptance gate.

Issues #283/#438/#440 await public release and then device-specific confirmation. #240/#418 retain planned original-installation investigation; #355 retains planned original C2 activation follow-up. All stay open. Source improvements, host checks and package installation do not prove reporter recovery or compatibility. No new reporter test, recovery mutation or diagnostic repetition is requested in this integration.
