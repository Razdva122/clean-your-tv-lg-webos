# Issue 207: passive IR Home and cancellation corrections

This unpublished source branch retains ferrets6's original contribution from
[PR 419](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/419), commit
`82229cfa599efdddd1f1e2be31cd0dc96e5fb1c2`, and adds corrections for its
[three review findings](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/419#pullrequestreview-5816874981).
It does not select a release version, change package pins or authorize TV work.

## Attribution and license

The original author commit and authorship are preserved in Git ancestry.
Credit: **ferrets6** for the contribution and fixtures; **Mr-Hubiverse** for the
published passive-IR/delayed-launch approach. Both explicitly permit MIT
adaptation with attribution:
[Mr-Hubiverse permission](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/207#issuecomment-6710825782),
[ferrets6 permission](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/207#issuecomment-6714351078).
The repository MIT license remains unchanged. The historical 0.6.21 existing-suite
result contains no IR-specific assertions and is not acceptance of this branch.

## Corrections and regression evidence

- The controller rejects delayed activation from an exited, watchdog-killed,
  non-ready, superseded or terminal relay. Exit/close, watchdog kill, Stop,
  explicit LG visits and Home-control changes cancel its queued IR timer.
  Launch-boundary checks retain the exit/watchdog fences while waiting for an
  existing Home close. Deferred callbacks retain their original worker identity,
  so recovery cannot transfer an old launch to a missing/replacement relay.
  M-RCU Home also consumes a pending IR timer rather than
  allowing that earlier activation to launch again.
- Off/On invalidates pending IR work rather than merely checking the latest
  preference at timer expiry. Native D/E commands reset the unfinished IR press,
  so a release after re-enabling requires a new down event.
- IR `SYN_DROPPED` clears unfinished Home and emergency tap history. Events through
  the next `SYN_REPORT` are ignored. A new complete press is required afterwards;
  three fresh qualifying taps still release with reason 27. This does not modify
  the existing grabbed M-RCU filter's overflow/emergency behavior.

Before changing production code, the new controller cases failed for exit before
close, watchdog kill before close and Off/On (one stale Home launch each). C cases
failed for Off/On across a press, overflow across a press and overflow across an
emergency series. After correction, all pass. The native recovery case explicitly
checks that two pre-overflow taps do not combine with one later tap, and that
three entirely new taps still trigger emergency release. The existing fixture
continues to cover short/held Home, Home Off, read-only/no-grab/no-re-emission,
IR device loss and normal triple Home.

Commands from the feature checkout:

```sh
npm ci
node tests/controller-ir-home.cjs
node tests/controller-home.cjs
node --test tests/controller-resume-home.cjs tests/controller-watchdog.cjs
cc -std=c99 -Wall -Wextra -Werror native/prototype/test_relay_ir.c native/prototype/filter.c -o build/tests/test-relay-ir
build/tests/test-relay-ir
for scenario in off-on overflow-taps overflow-press overflow-emergency; do
  build/tests/test-relay-ir "$scenario"
done
```

These focused checks pass, including 82 existing node:test cases. Independent review reproduced an additional stale deferred-close callback during
watchdog recovery; the held-callback regression failed before correction and
passes after binding the activation to its originating worker. The IR controller
script runs isolated exit/watchdog/Off-On/Stop/deferred-close regressions, and `scripts/test.sh`
registers every added native scenario in both `tv` and `tv-runtime` profiles.
Full affected runtime and final review results are recorded in the follow-up PR.

## Documentation and delivery boundaries

`docs/CONTROLS.md` and all thirteen existing localized guides identify this as
unpublished No-root IR behavior: approximately 700 ms delay, possible LG Home
flash, held Home left to webOS, triple-Home escape, unknown stock Developer Mode
access and no permission workaround. Published download instructions and Root
controls are unchanged. No persistent state, privilege grant, network endpoint,
dependency, system configuration change or automatic emergency-latch clearing
is introduced.

The sole release coordinator must decide integration and scope. Shipping requires
synchronized Helper versions/manifests/pins, a newly built source package and
embedding installers, authentic published-Home/new-Helper transition approval,
affected documentation review and artifact-bound controls/emergency/key-up
acceptance before a final candidate. Existing published 0.7.5 bytes are not
silently replaced. No release candidate, version or build is selected here.

## Physical scope

No TV was contacted or changed. TV model, firmware/webOS, physical remote and
installer platform for this branch are **unknown/not tested**. Edition under
source review: No-root. Component release version: not selected. Actual Home
routing on LJ550T, stock Developer Mode read access, long-press timing, source
duplication, key-up/unrelated physical buttons, sound, standby, AC cold boot,
OTA and rollback are **not tested on this branch**. Host fixtures do not verify
these behaviors. Rooted/manual-install contributor observations retain their
original source/device scope; no new installation report is being published.
