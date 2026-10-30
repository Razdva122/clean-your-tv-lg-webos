# Fast release cycle implementation plan

> Execute with subagent-driven-development; the user approved implementation and integration into main in the originating chat.

**Goal:** Shorten change-to-TV feedback without letting preliminary checks satisfy release admission.

**Architecture:** Use scoped PR checks, explicit full candidate builds, a direct TV payload artifact with protected signing, and a separate UI-only hosted development preview. Reuse existing package builders, admission, hashes, and release evidence.

**Tech stack:** Python standard library, Node, existing Babel/PostCSS and Playwright, GitHub Actions, webOS CLI.

**Spec:** The approved proposals in the originating chat: freeze scope; retain equivalent pinned builds; automate UI checks; parallelize runtime/browser validation; avoid duplicate tests and manual metadata; introduce quick UI and signed TV delivery; keep full verification before publication.

## Constraints

- Feature changes enter through release/next; main receives a finalized release PR. No protection bypass, arbitrary signing, or weakening production verification.
- Do not overwrite production Root under its misleading root.preview app ID. Dev UI has separate identity/storage and cannot invoke production services or change Home routing.
- Build/signer provenance includes exact source, workflow/run/attempt, artifact digest, package hashes and versions. Untrusted candidate code never executes with signing credentials.
- No new TV installation or physical acceptance is assumed from this implementation request. Device operations remain explicit commands with preflight and safe failure behavior.
- Keep exact Node 0.12 Helper and webOS web compilation checks where affected. Unknown/shared source changes conservatively broaden checks.
- Do not publish private device data. No new scheduled automation.

## Task 1 — CI profiles and explicit candidate freeze

Owned files: scripts/ci-scope.py, scripts/test.sh, scripts/release-flow.py, scripts/release-inputs.py; .github/workflows/tests.yml, cytv.yml, cytv-runtime.yml, preview-pages.yml; corresponding setup tests and focused browser smoke fixture if required.

- [x] Add failing scope tests: CSS selects UI/compatibility checks without installer/runtime/emulation; native/input/updater changes retain affected critical tests; unknown inputs select full relevant groups.
- [x] Implement short PR checks and full release checks with distinct verifiable evidence. Split full Linux browser work from runtime. Keep required PR status names honest and present.
- [x] Stop full candidate builds on ordinary pushes; explicit full candidate dispatch validates the frozen source. Preserve failed-job retries and input-equivalent pinned reuse; metadata pushes cannot cancel an in-flight selected build.
- [x] Deduplicate preview testing. Restrict desktop freeze checks to relevant dependency/entrypoint/packaging/platform changes.
- [x] Prove preliminary/quick jobs cannot satisfy release admission; update job evidence checks and regressions. Check actionlint and focused tests.

## Task 2 — Direct TV artifact and protected QA signing

Owned files: new scripts/build-tv-candidate.py, .github/workflows/tv-candidate.yml; scripts/root-candidate-feeds.py, scripts/sign-root-candidate.cjs, .github/workflows/publish-release.yml and associated tests. Do not edit shared CI/release-flow files; coordinate required interfaces.

- [x] Add failing tests for exact direct TV artifact admission and rejection of changed run attempts, digests, paths, versions and incomplete bundles.
- [x] Build the coherent Root/Home-runtime-updater package set directly with existing builders; no desktop executable or Android packaging prerequisite.
- [x] Add explicit lightweight TV QA workflow and protected signing from trusted release tools. Keep existing complete candidate path supported.
- [x] Verify archives without executing candidate source in signing jobs. Preserve versions, hashes, public-key pin and ordinary device recovery.
- [x] Run focused signing/packaging tests and export a small machine-readable artifact manifest for the delivery command.

## Task 3 — Local developer entrypoint and UI iteration

Owned files: new scripts/tv-dev.py, tests/setup/test_tv_dev.py, docs/development/TV-DEVELOPMENT.md; optionally preview-only files. Do not edit product UI/service sources, package.json, or shared workflows.

- [x] Add behavioral tests for UI staging with distinct identity/storage and disabled production service calls, rejecting unsafe paths and invalid inputs.
- [x] Provide a compiled UI-only hosted preview command with change watching and webOS CLI live reload, plus stage-only operation for unattended verification. Use existing preview sources and compatibility compilation.
- [x] Provide one explicit command to dispatch/wait/download/verify direct TV QA artifacts, with safe device preflight/install through the existing admission implementation where possible. Coordinate artifact contract with Task 2. Do not connect to a TV during implementation.
- [x] Preserve user profiles and never force equal-version updates. Clearly distinguish UI feedback, preliminary package QA and final release evidence.
- [x] Document existing theme-send reuse and commands, run focused tests and stage/compile smoke checks.

## Task 4 — Integration, process rules, release and review

Owned by coordinator: CONTRIBUTING.md, AGENTS.md, docs/RELEASE-FLOW.md and development index, .github/workflows/release.yml, release metadata/notes, review records.

- [x] Document one release coordinator, explicit freeze, blocker decisions, scoped manual cases, one current status block, targeted local tests and final full verification.
- [x] Resolve existing Automatic release startup failure without weakening required signing/job permissions.
- [x] Review each task and combined diff. Run complete repository tests once, browser checks, workflow lint and package equality verification as applicable.
- [ ] Open implementation PR to release/next, attach it, merge after checks, collect inventory, prepare maintenance release with unchanged TV component versions and truthful evidence.
- [ ] Run full trusted candidate, pin, verify unchanged TV package bytes against published baseline where reusable. Merge finalized release PR to main after required checks; verify publication and issue notifications/labels for its frozen inventory.
- [ ] Preserve outputs and remove only this task's temporary worktree after completion.
