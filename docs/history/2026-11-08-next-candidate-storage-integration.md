# Developer Mode storage fix integrated into the next candidate

The maintainer explicitly requested including PR #435 in the existing v1.13.0
candidate. It merged into `release/next` at `1fc7a9b331d21ee96ce7b24fc3436d2ac2fc4eeb`
on 2026-11-08. This adds a fourteenth implementation PR; selected component
versions remain unchanged. No final candidate build, acceptance or publication
is selected by this integration.

The reviewed head is `f06957b75126520640dbdb3abd93854bfb3caad6` over `33679143`.
Its [Tests run](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/42467863429)
passed all eight Linux/macOS runtime shards, both aggregate jobs and optional
Python. Release PR policy passed. Browser and full-release jobs were unselected;
this is focused implementation evidence. An independent source review found no
actionable blocker. Comments/reviews were rechecked immediately before merging.

The change addresses #409's observed private-storage mkdir/EACCES boundary by
selecting a safe owned Developer Mode jail leaf before pending/submission and
binding it to the original plan/capsule. It preserves existing observer source
bytes, Root SSH behavior, unsafe-root refusals, capacity checks and restart proof.
The linked issue is open with `bug` and exactly `status:awaiting-release`, verified
after integration. Public delivery and device confirmation remain outstanding.

No TV was contacted or changed for this integration. No model/firmware/remote,
physical controls, sound, standby/cold boot, OTA or rollback acceptance is claimed.
Shared desktop/console/Android installers and Root Updater's embedded cleaner must
be rebuilt from the resulting final candidate; earlier preliminary packages are
not evidence for these changed bytes.
