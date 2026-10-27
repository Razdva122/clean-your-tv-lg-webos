# Homebrew catalog submission preparation

Date: 2026-10-27. Status: **not submitted; public promotion disabled**.

## Published product and Installer identity

Project [v1.4.0](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.4.0)
was published on 2026-10-27. It contains no CYTV Installer IPK or Homebrew manifest.
Publishing Root 0.5.0 does not publish or accept the separate TV installation path.

The trusted [candidate run 40512827076](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/40512827076)
at `9785fd6795ce145d5084d196ecfeb08194a11729` has a successful Homebrew job.
Its development Installer is `com.cleanyourtv.installer` **0.0.0**, with Root
0.5.0, Root Updater 0.3.1 and supervisor 1.1.0 in the offline payload.

| Candidate property | Value |
| --- | --- |
| IPK size | 61,328,554 bytes |
| IPK SHA256 | `fb1d38620ac1da731bff91dce23f9c154800b00794c025d47f9eeb2f509d81fd` |
| Serialized manifest SHA256 | `315118e2095cf5599c33b49015e08a4b60a7a0a4b9885a292e45c6713c847638` |
| Offline payload manifest SHA256 | `d25fc57561115f8e80b7e2233920db57f135f8aedf936d6004a3d4d6d1cdda0d` |

The candidate manifest's intended v1.4.0 IPK URL is not a published asset.
Version 0.0.0 cannot be promoted. Freeze a new originating release, independent
Installer version and exact rebuilt artifacts after acceptance; do not append
unaccepted Installer files to the already published release.

## Catalog preflight

The existing `cleanyourtv-installer.yml` and actual candidate manifest passed
the upstream PackageInfo and PackageManifest JSON schemas at apps-repo commit
`f3c64646459e9526832fcfc6e61d5c8d009decb4`. This is schema validation, not the
complete upstream linter or proof of public URL reachability. Screenshots are
recommended by upstream; the project's own acceptance requires representative
TV images. Do not publish the maintainer's private room photo or raw diagnostics.

The eventual upstream change belongs at
`webosbrew/apps-repo:packages/cleanyourtv-installer.yml`, category `utility`,
pool `main`. Keep the current YAML explicitly marked as a draft until the
remaining gates pass. The intended stable manifest endpoint remains
`https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/homebrew-manifest.json`.

## Physical session and prerequisite blocker

The maintainer's C3 accepted the original candidate package; all 161 regular
files matched the IPK. Fixed root-side Homebrew inspection recognized the
existing Root 0.4.0 / Root Updater 0.3.0 installation as maintainable with no
active operation. All 73 existing product package files remained unchanged.
The maintainer confirmed readable UI and directional focus, but supplied a
photo showing **Setup unavailable**, not a successful maintenance screen.

[Issue #116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116)
tracks this blocker. An app-attributed call was denied by LS2. Homebrew 0.7.3
exposes its elevated API to `public`, while webOS 11's generated application
permissions no longer include that group. The upstream
[Homebrew PR #233](https://github.com/webosbrew/webos-homebrew-channel/pull/233),
commit `50fa99e1f08959b665b2e34d0d85cb2222c4c2c9`, grants `lunabus.query` too.
It is merged upstream but absent from the latest published Homebrew release.

A tested appinfo-only permission declaration did not change the generated
client ACL on this TV. That unsuccessful change and its packaging assertion
were removed from project source. Its local test IPK was
`a501b2f2d1e9ae11a04a633638a042c5b024992b816cac8e0576cbb6cdb6b1a0`;
do not confuse it with the original CI artifact or approved release bytes.

The maintainer authorized a temporary exact upstream prerequisite patch and
its subsequent rollback. The two exact upstream changes plus a service rescan
alone did not change the already running service's effective API groups.
After the service's normal `quit`/lazy-restart cycle, it still ran as UID 0,
introspection included `lunabus.query`, and app-attributed fixed `inspect`
returned `installed`. This establishes a conditional backend result; the
actual UI confirmation and verified prerequisite rollback are recorded
separately below. It cannot establish stock-0.7.3 compatibility.
Raw evidence and original rollback bytes stay in ignored local diagnostics.

The maintainer then confirmed that pressing **Check status** displayed the
maintenance screen with Root Home 0.4.0 / Root Updater 0.3.0. No activation,
restore or product-removal action was confirmed. The temporary Homebrew API
file was removed, the original manifest SHA256 was restored exactly, and a
normal Homebrew service restart confirmed both UID 0 and the original
effective API groups without `lunabus.query`. The temporary prerequisite
change is no longer installed.

Installer-only removal then returned a matching terminal result, its application
and package directories were absent, and all 73 original product package-file
hashes still matched the baseline. The two test upload stages were removed.
No clean product setup, full-product removal, activation, update, rollback or
power-cycle acceptance is claimed from this session.

Local `npm ci --ignore-scripts --no-audit --no-fund` and the project's
`scripts/test.sh setup installer` checks passed using the existing cytv Python
environment outside the desktop sandbox (Chrome and PTY checks require it).
The final unchanged manifest suite passed 17 tests. The unsuccessful appinfo
experiment's assertion was intentionally removed with that experiment; it
would only have tested the ineffective declaration, not functional TV access.

## Remaining submission gates

- Resolve and document the supported Homebrew prerequisite on webOS 11.
- Complete the new installation-path matrix, including clean setup, both-client
  handoff, runtime preparation, interruptions, upgrades, rollback and removal.
  Published Root power-cycle evidence is scoped to that product and path.
- Obtain meaningful named human review; disclose AI assistance in the eventual
  catalog PR. Automated review alone does not satisfy upstream's policy.
- Freeze exact nondevelopment artifacts and add `homebrew/release.json` only
  after real acceptance. Use the protected release pipeline for publication.
- Verify public manifest, original immutable IPK, checksums, icon and screenshot
  URLs. Rerun current upstream validation before submission.
- Submit the catalog PR and address maintainer review; submission itself is
  not catalog acceptance.

No catalog PR or release approval is created by this preparation record.
