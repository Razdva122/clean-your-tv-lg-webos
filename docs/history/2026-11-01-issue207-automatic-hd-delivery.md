# Issue 207: automatic HD delivery — 2026-11-01

Implementation PR #226, reviewed head `3cc772efb6595d45a4565bb4333f266292f324f5`,
merged as `84ce123f200fcfb0c10fcdd638400ca94e20392b`, with a tree identical to the reviewed source,
extends #225 source-level layout/build support into installer and OTA selection.
This is host/source verification, not a TV installation report. No TV was
connected or modified; model, firmware/webOS, remote and physical behavior for
these new bytes are untested. No private owner diagnostics are republished.

## Selection and trust

Desktop/console and Android share the same selector. A fixed read-only
`com.webos.service.tv.systemproperty/getSystemInfo` query asks only for `UHD`.
Successful boolean/exact lower-case string true selects 1920×1080; false selects
1280×720. Unknown, malformed or rejected capability stops before new pairing,
Python provisioning or install intent. No model-name or viewport heuristic.
Retained recovery/resume keeps its original artifacts without reselection.

Both Home IPKs and both complete Root bundles are embedded and hash-verified.
Selection validates fixed catalogue paths and actual ID/version/resolution before
personalization. Each platform/APK must contain both variants; a valid FHD-only
payload cannot opt out by omitting the catalogue. No new runtime dependency,
privilege, key, endpoint origin or persistent schema is added. Native Helper and
relay sources/pins remain unchanged.

New clients choose separate signed schema-1 HD feeds and strict
`_720p_all.ipk` launcher URLs. The selected channel does not grant trust: proofs
are verified unchanged, wrong-channel signed manifests are refused and actual
package resolution is checked. All equal-version, downgrade, profile, emergency,
Helper, rollback and baseline restrictions remain. New publication after the
immutable v1.5.4 historical boundary requires the complete graphics contract.
Historical FHD-only retries remain compatible within that boundary.

First HD publication requires newer Home and Root versions. Legacy Home HD OTA
waits for an actual compatible published HD rollback baseline. Once established,
Root-only/unchanged-Home releases carry the exact signed HD candidate/previous
history forward, with verified public origin, signatures, bytes and resolution;
publication requires its pinned feed pair. No fictitious prior HD baseline is
created. System OTA retains the authenticated actual installed baseline, even
when that rollback package is FHD.

Existing independently provisioned Root/System updaters require the supported
computer setup/replacement to acquire the selector. Ordinary component OTA does
not replace that independently pinned code. Old clients retain their existing
behavior until migration; no device migration occurred here.

## Review and verification

Independent AI-assisted installer/OTA and build/publication reviews approved.
Three pipeline findings were fixed and independently re-reviewed: optional
platform graphics verification, omission-based historical publication admission,
and loss of established HD Home feeds when Home does not change. Installer
review also moved No-root capability selection ahead of SSAP pairing.

Observed red/green regressions cover capability parsing/refusal/order, missing or
tampered payloads, signed-channel substitution, actual wrong-resolution bytes,
unchanged original rollback, strict all-platform verification, first-HD version
advance, prior-HD proof/hash validation and unchanged-Home feed retention.

- TV checks: 967 Root and 132 System cases passed, plus selected JS/native,
  compatibility, legacy protocol/signature/ownership and theme checks. Local
  exact generated Root Node0.12 suites were not configured; no claim they ran.
- Final affected rerun: 204 setup, 563 installer (two explicit platform-specific
  skips) and 23 Android tests passed. Homebrew payload/runtime/bridge/UI and
  installer/continuation fixtures passed. This is Android host/package testing,
  not final signed APK/emulator/physical upgrade acceptance.
- New installer errors have all twelve published installer translations. Initial
  Chinese packaged-font checks caught two missing characters; equivalent wording
  using existing glyphs corrected them. Both real packaged-font checks and all
  14 installer localization tests passed. Automatic font preparation is a
  separate subsequent change, not evidence claimed by this implementation.
- Final implementation CI: [run 41285141545](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41285141545) passed before merge, alongside Windows/Intel macOS/Integration policy checks. No required check may be bypassed.

## Actual local build

Rebuilt payload and Android staging at 2026-11-01T07:29:37Z from the final reviewed
working-tree bytes (before commit; evidence marks this explicitly, based on
`40d6e7e19161600733ba7b0cc176948a760e5cd5`). 520 source fingerprints aggregate
`7f64285d903c04e3ab708d074119403e4fc9a415f6af8628f391dbd0982199a5`.

209 payload files and all four ID/version/resolution combinations verified.
Both Root bundles contain 44 files and 105 package members; FHD/HD IPKs are
5,430,510/5,430,514 bytes and their largest member is 2,797,732 bytes, below the
unchanged package/member bounds. Four unsigned local system sets validate and
share the same infrastructure bytes. Android matches every payload file, its
manifest and all 32 Python modules, including selection, CLI and translations.

Payload manifest SHA-256:
`a825927a9fb2834580f448788ff1ee0034553e800bef3be120310bb7f305d3f3`.
Shared Root infrastructure SHA-256:
`c5c2354bd19038b86f0a8efefd256a18098a82f34332fc242c12956a354aae94`.
These are local development artifacts, not final release pins or installed bytes.

## Documentation and release limits

Updated manual/update/graphics references and all thirteen candidate TV guides.
README published downloads/versions remain unchanged. Freeze must bump affected
Home/Root/installer/updater/supervisor components coherently, rebuild all platforms,
select a successful complete candidate and perform affected exact-package
controls/startup/UI/update-recovery acceptance. Hardware graphics, sound, power,
OTA, rollback and original IR Home routing remain unverified. #207 stays open
for its unresolved original failure; no release or compatibility claim.
