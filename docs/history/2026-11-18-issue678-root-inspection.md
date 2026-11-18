# Issue 678 retained Root inspection diagnostics

## Reported behavior

The public report concerns Root on OLED55B16LA, webOS/SDK 6.5.3,
Node 8.12.0, using the Windows AMD64 installer. The remote model and installed
Root/runtime component versions are unknown.

- CYTV 0.21.0, firmware 03.53.45, stopped at installation inspection. Basic
  requirements and capability-based compositor admission passed. Existing
  device markers were found, but fresh installation was not admitted.
- Intermediate attempts stopped at SSH connection. The reporter described the
  original attempt as their first installation and initially reported no Restore
  or Uninstall.
- CYTV 0.21.2, firmware 03.53.60, completed SSH and basic Root requirements.
  The requested separate doctor operation then stopped with
  root-operation-unconfirmed at operations.preflight.
- The reporter subsequently reported failed removal and supplied a screen
  showing unverified final cleanup. A removal diagnostic was not supplied.
  The reporter said they were ending further attempts.

Sources are [the original issue](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/678)
and [the later diagnostic and removal observation](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/678#issuecomment-6981608090).

## Confirmed host defects and change

Preflight reads the installed native runtime's status and rejects a result that
does not satisfy the existing active or inactive proof. Before this change, the
observed result was discarded before the diagnostic report was produced.
The report could therefore retain only the generic refusal.

The host now retains a bounded projection before that refusal. Native backend,
effective backend, routing, state, fixed stop reason, strict boolean flags and
guardian presence survive export. Existing recovery-integrity and Home-enabled
fields are retained too. Each new read clears previous runtime observations
before selecting Python or making the SSH request. A failed read cannot present
the preceding observation as current.

Product inspection's installation classification and fixed reason are also
retained. Final Node cleanup already returns a specific cleanup_error, but
the host's product projection discarded it. The projection now preserves its
fixed refusal codes and revalidates them on subsequent history exports.
Tokens, addresses, paths, arbitrary messages and raw runtime output are excluded
from the new diagnostic context.

The existing active/inactive predicates and cleanup admission remain in effect.
These changes repair evidence loss. They do not establish which runtime
predicate or cleanup check failed on the reporting TV.

## Offline investigation and limits

The host replay uses a modeled stopped compositor with a retained CYTV filter
and unverified stock Home. This is one state that reproduces the reported
preflight boundary, not an assertion of the TV's exact state. Control cases
exercise verified active and verified inactive native Home. The new tests fail
on the previous code because observations and cleanup refusal codes are absent.

An official LG support search for the exact B1 03.53.60 image did not locate a
download. LG's B1 support page previously listed 03.53.45. No image was downloaded,
extracted or run under QEMU for this change. Factory contents cannot reconstruct
this TV's retained CYTV runtime, live filter state or later removal result.
The host projection defect is reproducible independently of factory firmware.
No additional reporter run was requested.

Actual installation, Home input, sound, standby, cold boot, OTA, removal and
rollback on this B1 remain unverified. No TV was contacted during this change.

## Verification

Regression coverage checks refused and admitted native states, repeated status
reads and SSH failure, fixed cleanup codes, strict field validation, private-data
exclusion and repeated projection. Focused host suites also cover product
operations, reinstallation, activation recovery and the CLI.

The first combined run encountered existing version-text assertions after the
host's Russian auto-language selection. The same suites are run with
LC_ALL=en_US.UTF-8 to match those assertions.

Final focused run passed 326 tests across inspection diagnostics, capabilities,
diagnostic history, operations, reinstallation, action failures, auto recovery,
CLI, native gate parsing/operations/activation and retained activation
diagnostics. Python 3.9 grammar and Git whitespace checks passed.
Independent source review found and resolved stale-observation retention;
the final review found no remaining actionable issue.
