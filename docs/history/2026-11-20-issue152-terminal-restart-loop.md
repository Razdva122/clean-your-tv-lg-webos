# Issue 152: repeated restart after terminal service removal — 2026-11-20

Base: `0abfa71aba733f6e28a6ccab8b6fb7182a7cada2` (`release/next`).
Report: [issue 152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152#issuecomment-7036782911).
No TV contacted, new reporter operation requested, or release selected.

## Evidence and reproduction

The posted Windows AMD64/cytv 0.23.0 report records terminal Helper and Home
removals, `restart-required`, `process-idle-unverified`, and no completed removal.
The owner reports another restart prompt after power cycling EF950V 04.26.35.
The report does not expose current process/target inventory or kernel proof, so
it cannot alone establish whether the installer observed that kernel change.

The local fixture reproduces that loop even with a positively observed new boot:
retain an empty protected Helper tree and a protected empty Home renewal service,
record both package terminals, and include an unrelated opaque Node invocation.
The original code returns `restart_required` after the changed boot instead of
finishing cleanup. The recognized restart is not the problem in this replay.

The existing post-restart exception was restricted to `targets <= {Helper}`;
service retention now also nominates Home as a target, disabling that exception.
It also compared all catalog targets, including unrelated apps, and final opaque
process acceptance/durable completion required a retained Helper application tree.
Service-only residue therefore could not finish either.

## Correction

Use the existing scoped post-kernel-change rule when **all remaining project
targets** have their own terminal removal. Unrelated catalog entries do not
participate. Apply final opaque-process handling and durable retry to retained
Helper and/or service directory trees. Keep the existing receipt field for
compatibility; no new persistent state, endpoint, permission, message or TV
JavaScript change is introduced.

Same-boot retries, outstanding requests, observed project/installer processes,
missing process enumeration, surviving app registrations and files/links do not
become success. The current inventory, SAM, process and controls readbacks still
run. The exception remains scoped to the original process-idle restart and its
observed kernel change; it is not an unconditional process-check bypass.

## Local validation and limits

- Regression was RED on the original code: after one simulated changed kernel it
  returned `{removed: false, verified_clean: false, restart_required: true}`.
- New cases cover Helper+Home services, service-only residue, an unreadable PID
  command line, an unrelated catalog app, same-boot retry, visible Home service
  process, missing `/proc`, and interrupted host completion followed by retry.
- The Linux ownership fixture also executes two install/remove cycles with
  Developer Mode UID 5755/GID 5000/groups 44/505/509/777, root-owned 0775 package
  containers, Helper state 5999:5000/0775 and service slots 0:0/0775 then
  5999:5000/0775. After the vendor terminal, an opaque unrelated process forces a
  restart; each simulated new boot permits verified completion. Vendor mutations
  and the intermediate install receipt are modeled by the existing fixture;
  actual production cleanup and boot-proof programs execute.
- Both Linux ownership cases passed in a network-disabled container with native
  Node 22. Changed boot IDs/volatile markers are simulated, not a booted TV image.
  Reuse the prior EF950V firmware investigation and its stock ARM/QEMU descriptor
  guard limitation; no new stock firmware runtime result is claimed. Only host
  Python decision logic changes here. Independent read-only review found no
  outstanding actionable defect. Final suite totals are recorded in the PR.

This establishes a reproducible cause and correction for the same reported
restart-loop class, not proof of the owner's undisclosed target/process state or
physical installation, Home-after-reboot, sound, standby, OTA or rollback acceptance.
