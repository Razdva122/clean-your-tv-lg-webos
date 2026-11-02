# Root recovery preparation, 2026-11-01

This is a host/source verification record for the
[individual handoffs](../development/ROOT-RECOVERY-HANDOFFS.md), not another
owner's installation/recovery report. No TV was connected, staged, inspected,
restored or removed. No release, component version, candidate scope/build or
acceptance was selected.

## Exact source and retained code

Code source: [`2e425efed159967c47a3114372b913abdedd3926`](https://github.com/Razdva122/clean-your-tv-lg-webos/commit/2e425efed159967c47a3114372b913abdedd3926).
Base: `510cb35bd00e044fbabd45f3202e2244942e5df2` from `origin/release/next`.
Use this exact source commit for the host script, updated passive reader and
bundle rebuild. Later documentation commits do not replace this source pin.

Built with `python3 root-edition/build_updater.py --output
build/root-recovery-code`; obtained the pin using `python3
scripts/root-install-recovery.py digest --code-bundle build/root-recovery-code`.

| Identity | SHA-256 |
| --- | --- |
| Recovery code (bundle + both cancellation modules) | `7ba641c570b8e0a17654b43962b8bc6144b383fe50f764010cef51f2bf36d7f1` |
| Host `scripts/root-install-recovery.py` | `116752d438a30ee8b2cdabc1de3a20610fe147cdfca3eef14f21784cce1c9d6a` |
| Retained preparation archive | `82fbae58c0d2fad34c0bb0700820e691683b04184a6e2b9849f51bfb3ba74339` |

The generated code, separately pinned cancellation modules, host script and
identity record were preserved outside the temporary worktree in the maintained
checkout's ignored `build/recovery-handoffs/2026-11-01-2e425efe/` directory and
its adjacent `.tar.gz`. These are local preparation artifacts, not signed release
downloads or an instruction to upload them. Source and digest can be reviewed
without connecting. Neither this record nor an issue comment authorizes TV use.

## Changes and verification

A numeric SSH status alone could not distinguish failure while staging the
coordinator, selecting Python or invoking the driver. `product_action` now
annotates only those three fixed boundaries and the validated action on a
`TVCommandError`; diagnostics rechecks both allowlists before export. It adds
no commands/retries and does not capture command text, paths, UUIDs or stderr.
This does not identify the historical exit-127 cause.

The passive Node reader now recognizes one complete fixed provisioning-child
terminal in its selected worker's bounded tail. Other/repeated/truncated
exceptions remain unknown. It explicitly reports an unverified recovery-record
binding, never evaluates log text and does not authorize cancellation. Existing
read-safety checks and the cancellation contract remain unchanged.

Red/green: the host boundary regression failed at all three missing metadata
fields before implementation and passed afterward. The passive-child regression
failed on the absent child category before implementation and passed afterward.
Focused verification with the repository's Python dependencies: 56 recovery,
shared-operation, diagnostics, transport and passive-reader tests passed; seven
trust/real-loopback SSH cases passed. Cases cover exact private-Python command
arguments, saved pending unchanged after status failure, rejected export values,
password-required inspection refusing without new trust or staging, unsafe file
reads, ambiguous operations and privacy canaries. An initial test invocation
without `paramiko` failed for missing local dependencies; installing the unchanged
`cytv/requirements.txt` in an isolated venv resolved that environment failure.

Independent read-only review found no code/privacy/admission-regression issue;
its missing source-record finding is addressed by this dated record and link.
The actual generated digest matched the handoff pin during review.

Affected verification: `scripts/test.sh installer tv setup` passed its TV/Root
(960 Root + 128 System Python tests, plus JS/native/TV compatibility) and setup
(194 Python tests) groups. Its initial installer group lacked local SSH/SSAP/TLS
dependencies and failed with 16 import errors and two offline runtime-probe
failures. Repeating `scripts/test.sh installer` with the unchanged requirements
installed in the isolated venv passed: 542 cytv tests (31 expected optional
GUI/platform skips), plus 8 payload, 4 installer, 5 continuation and Homebrew JS
checks. No product workaround was applied. Both clean local rebuilds produced
the same recovery digest; preserved manifest files, archive SHA and local document
link targets were independently verified. `git diff --check` and ES5 parsing of
the documented block passed.

Exact Node 0.10.25/0.12.2/8.12.0 and physical-TV acceptance are not claimed by this host run.
The documented Node block is checked with existing filesystem/readonly fixtures;
legacy-runtime execution remains a separate check.

## Documentation and unresolved work

Updated internal admission, passive-diagnostic and cancellation references,
individual decisions and developer navigation. Reviewed all twelve localized
user-guide boundaries: ordinary setup, controls and public downloads do not
change; this source-only maintainer preparation adds no user setup step.

#101 still needs a separately reviewed interactive authentication path if its
original connection requires a password. #133 is prepared for a separately
agreed exact-source inspection, not admitted removal. #161 needs operation-bound
evidence and retains the third-party-Home refusal. #216 and the Windows pending
operation in #200 need a reviewed passive bootstrap/path-selection contract;
their original failure and cancellation eligibility remain unknown. No blind
restore/uninstall/retry or state deletion is supplied. #200 host-cache and #201
No-root work remain separate. Keep all original reports open; no status is
`released` on the basis of these preparations.
