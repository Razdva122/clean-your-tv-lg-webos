# Unattended C3 UI and status checks — 2026-10-30

The maintainer authorized autonomous tests on the powered-on test TV. This is a
bounded observation of the installed package and a temporary in-memory proof for
[#176](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/176), not signed
candidate installation or complete release acceptance. Candidate
[#182](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/182) source was
`a978d1615163588ae259e9f83c2b55639569560e`, unfrozen and unversioned.

## Device and artifact scope

- Device: maintainer C3, LG OLED55C3RLA; firmware 43.21.71; webOS SDK 11.2.0.
- Edition: Root. Installed Root Home 0.6.1; Root Updater 0.3.3; System Updater
  1.1.2. Separate shared-UI version was not queried in this session. Physical
  remote model is unknown and no physical remote input was tested.
- Installed System receipt still names v1.5.0. Its Root IPK digest is
  `419de466e43095b426d9652c102fabd2c3ebd5a58c4dbb0f4928056b6d4b9f64`.
  This receipt identifies the installed baseline; it is not a new package hash
  obtained from a candidate installation during this run.
- Control/installer host: macOS ARM64. Used the saved trusted Root SSH connection
  and existing production-app inspector. No installer operation, package upload,
  package replacement, new pairing or trust reset was performed.
- Initial state: Root Home was already foreground, rendered and using Alpine,
  with By theme selected, no theme trial and settings closed. Persistent Home
  intent was enabled/active and the guardian active; this state was preserved.
  No unresolved local installer receipt was present. The retained update and
  Home-resume phases were complete, with three successful installer terminals.

## Actual checks

| Check | Expected | Observed result and limit |
| --- | --- | --- |
| Settings categories | Selecting a category retains focus and selects that category. | PASS: five categories, selected state and focus confirmed. No install, reset, audio-recovery or Home-toggle button was activated. |
| Installed Appearance reproduction | Reproduce the reported bottom-scroll clamp when Classic changes to fixed-layout Alpine after focusing the already selected By theme option. | REPRODUCED: the installed UI lane moved 110 px. This confirms the existing failure; it is not an unexpected new candidate regression. |
| Temporary candidate geometry proof | Retaining the hidden Columns footprint prevents the scroll clamp while preserving focus, DOM and control exclusion. | PASS for this experiment: 0 px lane displacement, zero bad frames among 42 samples, Apply focus/DOM preserved, hidden direct focus and pointer hit-testing excluded, parent aria-hidden true. |
| Installed renderer reload | First observed visible frames use the saved Alpine background; saved data survives and scripts do not fail. | PASS: 123 sampled frames, 51 visible; every visible sample was Alpine with a background image. Zero observed window script errors and unhandled rejections. Host-observed readiness was 4.032 seconds in this one run, including control latency; this is not a startup timing guarantee or compositor/video measurement. |
| Native app status | Real app-originated status calls work and retained transaction is complete. | PASS: System Updater status returned complete; Root status returned enabled/active intent with active guardian. A plain root-shell System status request was rejected; the actual production-app request succeeded. No guard or permission was changed. |
| Images and audio status | Visible icons are loaded; audio state remains readable and unchanged. | PASS: all eight visible tile images loaded. Audio API replied and final volume/mute state matched the initial capture. Audible sound, HDMI continuity and physical volume keys are untested. |
| Final restoration | Remove temporary instrumentation and retain exact original user/control state. | PASS: profile, theme choice, Columns, theme inventory, Home intent and effective routing matched. Settings closed and Root remained foreground. App manifests, current-root descriptor, transaction and product lease records matched their initial hashes; local installer receipt remained absent. Guardian stayed active. |

## Temporary proof method and cleanup

The geometry experiment used the two footprint CSS rules from #176 and the
corresponding DOM class/aria state handling, temporarily in the existing renderer.
An observer supplied the class/aria handling for this experiment; the candidate's
compiled layout module and IPK were **not** installed or accepted. This establishes
the footprint mechanism on this TV renderer, not full package equivalence,
installation acceptance or every accessibility interaction. The installed
baseline and experiment remained distinct observations.

Each theme transition used the real existing Appearance controls. Only built-in
Classic and Alpine were selected; no theme was installed or removed. The final
Alpine selection, raw saved choice, profile, Columns and theme inventory were
verified against the initial capture. Temporary style/observer state was removed.
A final ordinary uninstrumented renderer reload removed the measurement listener
closures, and all final restoration checks passed. Raw profiles, source records,
app inventory and debugger evidence remain private off-device; none is included
in this record.

## Remaining acceptance

No standby, wake, restart, AC-off cold boot, physical Home/Back/arrows, key-up,
triple-Home emergency, watchdog fault injection, audible sound, new OTA/update,
rollback, uninstall or recovery operation was performed. Existing guards, latches,
preferences, journals and service permissions were not patched or cleared.
Renderer reload does not accept any power-state path.

The original [#171 standby failure](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171)
remains unresolved: no controlled same-cycle power trace or new diagnostic runtime
was installed. #170 remains awaiting release and exact-artifact acceptance. No
new support for another reporter's firmware, Node 0.10 TV, Homebrew prerequisite
or retained recovery operation follows from these C3 observations.

The new combined candidate still requires version selection, a coherent signed
build, affected exact-artifact acceptance, rollback evidence and normal release
policy. This record does not populate release acceptance or authorize publication.
