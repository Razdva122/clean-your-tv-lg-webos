# Passive Root diagnostic preparation — 2026-10-31

[PR #213](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/213) merged into
`release/next` as `5a44870fbd8bf1664b1b96c4fa09e3338b5972c1`. Its tree matches
reviewed/tested source `377ff94ce79f372eff5bab59c8d76b1c9d5fcf1b`.

The original [#161](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/161)
report still lacks the first worker failure. Working third-party Home routing
does not satisfy LG Home cancellation admission. No installer/runtime defect or
safe cancellation for that operation has been established from the available
report; the existing admission, routing, original-evidence and removal gates stay intact.

The new [maintainer procedure](../development/ROOT-PASSIVE-DIAGNOSTICS.md) supplies
a passive first diagnostic before staged admission: bounded system-Node reads of
saved files with fixed categories/allowlisted worker frames. It stages nothing,
imports no retained code, calls no Luna service and makes no product/recovery
content or permission changes. Filesystem access timestamps may change. The
separate saved recovery failure is not bound to the selected worker here; this
output is not an admission proof, quiescence check or recovery authorization.

Local macOS checks passed: 193 setup tests, 11 host admission tests and 24
cancellation tests. Four documented-command fixture cases also passed on actual
Node 8.12.0; the block parses as ES5. Fixtures cover privacy canaries, ambiguous
operations, unsafe ownership/modes, links, oversized/missing data and unchanged
file bytes/modes. Independent source review found no actionable findings.
[Selected PR CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41204114465)
passed required Linux/macOS summaries and Integration policy. Unaffected
browser/build/ARM Python/full-release jobs were skipped, not claimed as new passes.

No TV was connected, inspected or modified by this task. Root preservation,
actual cancellation/removal, Home controls, sound, standby, cold boot, OTA and
rollback remain unverified for #161. The next step is the owner's bounded
diagnostic response, followed by review of whether separately authorized,
exact-source admission is appropriate. No restore, reinstall, root/firmware
change, third-party routing change or evidence deletion is requested.

This change adds internal source documentation and tests, not a new installer
command or product package. It needs no additional component bump/rebuild beyond
the candidate's existing #212 scope. Ordinary setup/controls and all twelve
localized user-guide boundaries were reviewed and remain unchanged. Candidate
#210 stays unfrozen with no selected version, full build, artifact pin or TV acceptance.
