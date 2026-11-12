## Release candidate

Base: `main`. Head: `release/next` in this repository.
Keep this PR in draft while collecting changes. Choose the version at freeze.

Maintain this description after every implementation merge, scope change,
version decision and validation run. The candidate workflow regenerates its marked block from committed
`release-plan.json`; maintain human observations and reasons outside that block. Follow [the release record requirements](../../docs/RELEASE-FLOW.md#maintain-the-release-candidate-pr-description).

## Scope

<!-- List every included implementation PR, related issues and resulting behavior.
Record exclusions/reversions or partial delivery; match release-plan.json. -->

## Component versions

<!-- Replace placeholders with actual values. Use TBD for unselected targets.
Distinguish proposed targets from bumps already committed. Retain all rows and
explain unchanged components. Include Android versionCode in its row. -->

| Component | Last published | Currently committed | Proposed/final target | Bump status and reason |
| --- | --- | --- | --- | --- |
| Overall release | TBD | TBD | TBD | Not selected |
| Home | TBD | TBD | TBD | TBD |
| Home Helper | TBD | TBD | TBD | TBD |
| cytv installer | TBD | TBD | TBD | TBD |
| Android installer / versionCode | TBD | TBD | TBD | TBD |
| Root edition | TBD | TBD | TBD | TBD |
| Independent updater | TBD | TBD | TBD | TBD |

## Packaging and delivery

<!-- Identify rebuilds, pinned baselines, manifest synchronization and rollback
requirements. An unchanged pinned Helper package does not ship new Helper source
fixes. State which version bumps and package checks remain before delivery. -->

## Documentation

<!-- Complete the documentation pass in docs/RELEASE-FLOW.md for this candidate.
List reviewed/updated guides and translations, command/link checks, reasons for
unchanged guides, and remaining work or deliberate limitations. Refresh after
scope/version changes. Release notes alone do not replace usage instructions. -->

## Validation and acceptance

<!-- Record actual test/build results with links or commands and checked commits.
Separate implementation-PR checks from combined/frozen-candidate checks. Include
TV model/firmware, tested and untested paths, limitations and rollback evidence.
Do not claim hardware acceptance from automated tests or package installation. -->

## Release timings

<!-- Follow docs/RELEASE-FLOW.md#record-release-candidate-timings.
Keep one table per candidate, preserving earlier attempts. Add a row for each
build, test pass, fix, wait for the user, rebuild and retest as it happens.
Use timestamps with a UTC offset and include failed and cancelled attempts. -->

- Release task handed to agent: <!-- Timestamp -->
- Candidate: <!-- RC number or commit -->

| Stage | Started | Ended | Elapsed | Outcome / evidence |
| --- | --- | --- | --- | --- |
| <!-- Stage --> | | | | |

- Outcome and timestamp: <!-- Accepted, superseded or withdrawn -->
- Total elapsed from handoff to outcome: <!-- Wall-clock time -->
- Time waiting for the user: <!-- Wall-clock time spent waiting -->
- Verified publication timestamp and total elapsed since handoff: <!-- For the candidate that ships -->

## Release gates

- [ ] `release-plan.json` lists every merged implementation PR and its issues.
- [ ] Reverted PRs are listed under `excluded` with a reason.
- [ ] This description matches the inventory and states proposed versus committed component versions.
- [ ] Final version matches `release-versions.json` and release notes.
- [ ] Changed component manifests and versions agree.
- [ ] README stable release links and component versions pass automated metadata validation.
- [ ] Candidate documentation pass is complete; affected guides/translations match the release and remaining limitations are recorded above.
- [ ] Rebuilt packages contain the intended changes; pinned baselines and delivery limitations are recorded.
- [ ] TV acceptance rows include artifact hashes, device/state preconditions and untested paths.
- [ ] Selected build run/attempt matches `acceptance_build`; changed bytes have affected acceptance.
- [ ] Complete platform builds and full tests pass for the selected build; candidate inputs are equivalent.
- [ ] Rollback baseline is verified.

A merge integrates the release. Shipping notices follow verified publication.
