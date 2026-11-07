# Release checks

- Select a short case list from the actual release diff using
  [risk-based case selection](RELEASE-FLOW.md#select-cases-by-the-failure-they-could-detect).
  Give every case a changed-path/dependency reason and use the least expensive
  faithful check. The component matrices are case libraries, not an automatic
  full physical pass. Record exclusions and explicit deferrals; do not relabel
  untested new artifacts as passed.

- Complete the [planned case pass and failure inventory](RELEASE-FLOW.md#complete-planned-cases-before-batch-fixes)
  before the fix batch; verify affected and newly reachable cases before its merge.

- Complete the [candidate documentation pass](RELEASE-FLOW.md#update-documentation-for-every-candidate)
  before marking the release PR ready; repeat after scope or version changes.
- Update affected usage, installation, update/removal, troubleshooting and
  recovery guides, including translations, commands, links and versions.
- Record reviewed/updated files, checks and remaining documentation limitations
  in the release PR. Release notes alone do not complete this check.
- Verify README stable downloads/component sections against `release-versions.json`
  with `python3 -m unittest discover -s tests/setup -p test_readme_release.py`.
- Verify the complete candidate CI suite and platform builds once; retain the run,
  attempt and artifact hashes. Use the pinned result across evidence-only edits.
- Run affected tests while implementing. Run the full suite and final package
  checks on the explicitly frozen candidate; preserve results for unchanged
  inputs rather than repeating every local/CI check for an evidence edit.
- Hold new features after freeze. Record an explicit decision for every new
  blocker or accepted limitation; never infer acceptance from silence.
- Record matching `acceptance_build` (run:attempt); selecting a different build
  invalidates prior acceptance. Review `acceptance-report` and carry unchanged
  scenarios only with identical artifact hashes and device/state preconditions.
- Build from a clean inventory; inspect package contents for credentials and state.
- Preserve licenses and upstream attribution.
- Mark hardware-tested and untested paths explicitly.
- Keep a rollback package locally.
- Publish checksums with artifacts.
- Never upload firmware, SSH/SSAP keys, live device backups or raw personal logs.

## Root Edition gate

- Keep development-only tools out of production IPKs.
- Source integration as Root Preview does not certify a stable binary release.
- Do not publish a stable Root Edition installer until the selected affected hardware gates in
  [Root Edition testing](../root-edition/TESTING.md) pass and remaining limitations
  are explicitly recorded. Existing release-blocking failures remain gates.
- Select exact metadata/registration-cache, profile and SAM rollback cases when
  their code, package boundary or state transition is affected; preserve independent
  recovery readiness before device changes.
- Document native-button emergency behavior separately from No-root controls.
- Never present a diagnostic-app result as a production-launcher result.
