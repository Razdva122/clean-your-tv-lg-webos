# v1.5.2 — Automatic release assembly authentication

This maintenance release completes the automatic publication repair tracked in
[issue #172](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/172).
The final assembly step now receives the existing GitHub job token, allowing the
assembler to recheck the exact successful candidate run before consuming its
artifacts. A regression checks effective credentials and Actions permissions for
every assembler invocation. Source, run/attempt, full-suite, inventory, package,
signature and protected-publication checks remain required.

The caller/callee Actions permission correction and the faster development tools
were delivered in [1.5.1](RELEASE-1.5.1.md). Its first automatic run started but
exposed this separate missing-token step; the unchanged release was recovered
through pinned main tools and the existing protected signer. The one-off recovery
wrapper is excluded from this release.

There are no TV application, service, updater or installer behavior changes.
All component versions remain those in 1.5.1. Existing Appearance and standby
limitations retain their [1.5.0 evidence](RELEASE-1.5.0.md). No TV was connected
or modified and no new physical compatibility result is claimed.

The [release PR](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/178)
records normal publication; the [validation record](history/2026-10-30-release-1.5.2-validation.md) contains exact candidate and direct-delivery artifact evidence.
