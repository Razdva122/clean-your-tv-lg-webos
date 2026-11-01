# Issue 207: 720p and passive diagnostics — 2026-11-01

Implementation [PR #225](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/225), merged as
`c17f5d5a0746b4ab58d68239e09a6d2e99729a45`, reviewed source `ac5c756f86e05750ba90360d853f75f55fae442a`,
adds source-level HD graphics support and diagnostic preparation. The merged
implementation tree exactly matches the reviewed source tree. No TV was
connected or modified. TV model, firmware/webOS, remote and physical behavior
remain untested for these new bytes; no installation report is republished here.

## Result and limits

- Home uses one logical 1920×1080 scene fitted to the actual graphics viewport;
  Inputs and upward shortcut selection use logical rectangles. Trusted Settings,
  confirmation and recovery panels stay in physical viewport coordinates.
- Explicit HD staging/manual No-root/isolated Root build options validate only
  1280×720 or 1920×1080 and leave source manifests intact. Default normal
  desktop/Android payloads and signed-feed artifact selection remain FHD. This
  does not add automatic model detection or normal-channel HD delivery. Final
  HD artifacts and their update/rollback path still require selection/acceptance.
- Home Helper's Show/Hide diagnostics reuses all thirteen existing translations.
  It reports only the panel's existing caller-side replies with fixed outcomes,
  bounded numeric codes and typed booleans. Viewing performs no extra request,
  retry, start or state write. Malformed envelopes are not reported as success;
  stale generation replies cannot replace current evidence.
- The independent passive probe is Linux ARM32 little-endian/ES5 Node, fixed to
  ten seconds with bounded discovery/reads/output. It observes at most one
  completed pair per allowlisted remote role; no grab, injection, command spawn,
  network, permission change, state write, raw history or mapping activation.
  Future device execution requires a separately agreed owner-supervised window,
  reviewed exact source and sanitized Node environment. An observed candidate is
  not proof of Home mapping. No such device session occurred in this task.
- Native Helper/relay/controller sources, package pins, key-up, emergency and
  watchdog behavior are unchanged. IR Home routing and actual panel service
  refusal remain unresolved; no guessed input mapping or permission bypass ships.

## Verification

- Red/green: actual 1280×720 browser reproduced clipped first card; viewport
  module/HD staging were absent before implementation. Geometry, package-source
  immutability, invalid-resolution refusal and diagnostics regressions pass now.
- Real Chrome, both editions at HD/FHD: five presets × columns1–8, card visibility,
  native pointer hit-testing, focus-frame alignment, visually nearest shortcut,
  Inputs placement and standard Settings passed. Category navigation additionally
  passed 52 localized edition/resolution combinations.
- Helper disclosure real-browser fixtures passed thirteen locales at both sizes,
  including bounded scrolling, Back/focus return and zero extra status calls.
  Caller/service boundaries are simulated; this is not TV bus acceptance.
- Current Node and exact `/tmp/node-v0.12.2-darwin-x64/bin/node` passed passive
  probe fixtures (ARM32 packet parser/VM) and unsupported-host CLI refusal. This
  verifies legacy JS execution, not real ARM32 device access. Privacy/read-only,
  partial/interleaved pairs, repeats, SYN_DROPPED, unsafe names/leaves, flooding,
  monotonic clock and cleanup cases passed. No arbitrary key history is exported.
- Published Helper0.6.17 response compatibility, malformed/denied/timeout/current
  generation panel tests, and retained explicit Start confirmation passed.
- `scripts/test.sh tv setup`: **967 Root, 128 System, 198 setup** cases passed,
  plus selected JS/native/compatibility/theme checks. Real multi-UID checks are
  skipped on local macOS and covered by CI. General generated Root exact legacy
  runtimes were not configured locally; the separate exact0.12 probe result above
  does not imply those suites ran on0.12 locally.
- Compiled Home passed modern, no-inset, no-inset/no-ES2015 and prefixed-WebKit
  legacy browser modes. Offline HD Home/Root IPKs were inspected for the HD
  manifest and packaged viewport dependency; the source FHD manifest stayed
  unchanged. Root's output-symlink guard correctly refused an initial macOS temp
  alias; the real `/private/tmp` output rerun passed without weakening the guard.
- Focused passive-probe review and independent full feature review approved;
  no blocking finding remained. [Selected implementation CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41281184796)
  attempt 2 passed before merge. Attempt 1 stopped producing output after the
  new geometry/diagnostics checks passed; after more than fifteen minutes without
  progress it was cancelled (force-cancel was required) and unfinished checks
  rerun on the same source. The exact Helper browser fixture and following
  update-badge/Root Settings tests also passed locally during investigation. No
  check was bypassed or weakened. These are implementation checks, not a frozen
  full candidate build or physical acceptance.

After collection, release-flow metadata tests (16) and README release tests (3)
passed; no version, build pin or acceptance was added.

Offline development-package SHA-256 values (not release pins or installed bytes):

- Home HD1.6.1: `a1bf490a94fb0e254ceddb0be5717ff9df11f061097b57452c62d3dc12f3b5dd`
- Isolated Root HD0.0.1: `4accfe3144d90b613f0938ea87c804fa0e3dc8ca5c17b5049e73e3805e1c10b0`

Reviewed source fingerprints:

- Passive probe: `c8b4352130865344b601253d70c32899fd411a90e256223b8bea365b6aee3099`
- Home viewport: `499ba6d321bdc19b45a914986c4c69c89122c89ead76fa44471d970352adbe7b`
- Helper panel: `21c98b7c08fdb375a608db20273fa141a8cc5153ea5974b932d5986590acf51d`

## Documentation, packaging and remaining acceptance

Reviewed/updated: developer graphics/probe procedures, manual build boundary,
Helper diagnostics, developer navigation and all twelve existing localized guides
plus the Czech candidate guide. Current user instructions distinguish candidate
controls from published downloads. Existing labels are reused; no dependency,
permission, endpoint or persistent schema is added.

Rebuild affected Home/Root and embedding desktop/Android payloads at freeze;
retain exact unchanged Helper pins. HD package/update artifact selection remains
explicit work, not an inferred effect of the new runtime scale. No version,
complete build or acceptance pin was chosen here. `acceptance-report` still
selects controls, startup, ui-controls and update-recovery; source/browser results
cannot replace final artifact/model/state evidence. Original #207 remains open
for maintainer follow-up and an agreed device observation, not marked released.
