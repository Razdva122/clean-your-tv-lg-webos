# Release integration flow

Features, fixes and maintenance integrate in `release/next`. Only a finalized
release PR from that branch may merge into `main`. This repository calls its
primary branch `main`, not `master`. The preparation branch has no version in
its name: choose the version when the candidate's scope is known.

## Collect changes without choosing a version

1. Create `release/next` from `main`, or fast-forward the existing branch to
   `main` after the previous release. Use merge commits for all PRs. Squash and
   rebase merging are disabled to preserve ancestry across release cycles.
2. Start the new cycle with `release-plan.json` containing `version: null`, empty
   `changes`/`excluded` lists and empty `acceptance`. Keep the last shipped
   `release-versions.json` value until freeze; it is not the next version.
3. Target implementation PRs at `release/next`. Record linked issues using
   GitHub's closing references or a plain `Related issues: #123, #456` line.
   Links and inventory numbers refer to this repository. Do not close a partially
   delivered issue merely because its PR merged.
4. Open a draft `release/next` → `main` PR using the release template. Its policy
   check remains unsuccessful until the version, scope and acceptance are final.
5. After merging implementation PRs, collect the inventory on `release/next`:

   ```sh
   git fetch origin main
   python3 scripts/release-flow.py collect
   ```

   This updates the plan with PR titles and linked issues without selecting a
   version. Review the summaries, add any extra related issues, and commit it.
   The collector includes only merged implementation PRs present in the commit
   range since `origin/main`; previous releases are not repeated.

An issue describes work; its implementation enters through a PR. Metadata-only
commits such as preparing the plan and selecting versions may be made directly
on the preparation branch. Product changes should enter through reviewed PRs.

## Maintain the release candidate PR description

Every `release/next` → `main` release candidate must maintain a current release
record in its PR description, starting when the draft is opened. Use the
[release PR template](../.github/PULL_REQUEST_TEMPLATE/release.md). The **Maintain next release candidate** workflow refreshes a marked generated
block from the committed plan, versions and selected build. It preserves human
sections. Use `python3 scripts/release-flow.py sync-record` to refresh explicitly.
Collect the inventory first; proposed bumps, packaging reasons, observations and
documentation review remain human-maintained.

The maintainer integrating an implementation PR must collect and commit the release
inventory; the candidate workflow refreshes its generated PR block. Update the
human decisions and observations when they change as part of that integration. Refresh
the description after scope changes, exclusions or reversions, version decisions,
new validation results and candidate freeze. Do not leave this until publication.

The description must contain:

- **Scope:** every included implementation PR and related issue, its resulting
  behavior, and any exclusions or partial delivery. Keep it consistent with
  `release-plan.json`.
- **Version table:** the overall release and every component (Home, Home Helper,
  cytv installer, Android installer, Root edition and independent updater). Show
  the last published version, the version currently committed in the candidate,
  the proposed/final target, the reason for changing or retaining it, and whether
  the bump is proposed or committed. Include Android `versionCode`. Before a
  target is selected, write `TBD`; never present a proposal as an applied bump.
- **Packaging impact:** identify packages/installers that need rebuilding and
  any pinned baseline that prevents source changes from shipping. In particular,
  Helper source fixes do not reach users while builders reuse the published
  package at the unchanged Helper version. Record the required version bump,
  manifest synchronization, new source-package validation and rollback checks.
- **Validation:** actual test/build results with links or reproducible commands
  and the checked commit or PR revision. Distinguish checks on an earlier PR
  from checks on the combined or frozen candidate; record pending and failed
  checks. A version bump or package rebuild needs validation of the new artifacts.
- **Acceptance and release gates:** physical-TV model/firmware and tested paths,
  known limitations, untested behavior, rollback evidence and remaining work.
  Keep the checklist current; automated checks are not hardware acceptance.

At freeze, replace tentative version targets with the final values, verify them
against release metadata and component manifests, link the release notes, and
record validation of the exact frozen candidate. Until then, explicitly state
that the PR is an unfrozen draft and which bumps have not been committed.

## Update documentation for every candidate

The maintainer preparing each candidate owns a documentation pass against its
actual release inventory. Start it while collecting changes, refresh affected
instructions when an implementation PR merges, and finish it before marking the
release PR ready. Release notes alone do not replace updated usage instructions.

- Review README, installation/update/removal guides, troubleshooting, supported
  devices and prerequisites, and affected component documentation. Update commands,
  download links, versions, screenshots and recovery/rollback instructions where
  behavior changed. Remove obsolete instructions.
- Review translated guides for the same changes. Update affected translations;
  record any remaining gaps explicitly in the release PR.
- Check documented commands and links against the candidate's actual CLI and
  artifacts. Distinguish candidate-only instructions from the published stable
  release, and retain honest hardware-tested and untested limitations.
- Add a **Documentation** section to the release PR listing the reviewed/updated
  files, verification performed and remaining work. If a guide needs no change,
  record why. Resolve stale instructions before marking the PR ready; document
  deliberate remaining limitations rather than checking an unfinished item.

Keep current user guides task-first and reachable from [the documentation index](README.md).
Keep README short; place commands/build internals in [developer references](development/README.md)
and dated evidence in [history](history/README.md). Update a current instruction
in place instead of appending another release story. Avoid copying the complete
component version table into every guide. Preserve old links/anchors when moving
material. Feedback from another user's installation requires explicit consent
before an agent publishes it. Authorized maintainer QA on maintainer/project-owned
test devices does not require per-report confirmation; privacy and task-scope
limits still apply. See [feedback](FEEDBACK.md).

The README's `release:downloads` and `release:components` sections must match
`release-versions.json`, including the release tag/notes links and Android
versionCode. Update these visible sections when selecting versions at freeze;
do not remove or duplicate their HTML boundary comments. Historical evidence
outside those sections keeps its original versions. Run:

```sh
python3 -m unittest discover -s tests/setup -p test_readme_release.py
```

Required Linux/macOS setup tests validate the actual README; README-only changes
now select these checks. The trusted release policy also reads and validates the
candidate README as data. Policy-source changes take effect when integrated into
`main`; required candidate tests enforce this check during the initial rollout.
This detects metadata drift, not whether all explanatory prose is accurate:
keep the manual documentation pass.

Repeat the affected parts of this pass after scope changes, reversions or version
changes. Unchanged guides retain their recorded review; do not redo a complete
documentation pass merely to append acceptance evidence. The release
template and [release checklist](RELEASE_CHECKLIST.md) make it a maintainer gate;
CI does not establish that documentation matches product behavior.

## Freeze and validate the candidate

One coordinator owns the frozen inventory, selected build and acceptance record.
Select versions and write candidate notes before physical acceptance. Finish
product changes before freeze; queue unrelated changes for the following cycle.
Then explicitly start the full candidate:

```sh
gh workflow run cytv.yml --ref release/next -f full_candidate=true
```

This runs the complete Linux/macOS suite, browser matrix, ARM Python checks,
Android and all four desktop builds. Browser validation runs alongside runtime
tests. Ordinary pushes do not start installer builds or cancel this run. The
release PR stays draft until actual acceptance is recorded. A new product input
requires a new full candidate; evidence-only edits can retain the verified pin.
`test_build=true` produces preliminary feedback artifacts and cannot satisfy the
full-release validation marker.

For preliminary device feedback before integration, the same explicit dispatch
can build a named branch in this repository other than `main`. Select that branch
and enable `test_build`; pushes to feature branches, tags, PR refs and dispatches
without this option do not produce installers. The branch still needs prepared
version metadata and matching release notes. All platform payload, compatibility,
packaging and signature checks remain enabled, alongside affected validation.
These are draft test artifacts tied to the dispatched source commit, never a
release candidate or release acceptance. Stable signing/publication and trusted release
policy still require their existing `release/next`/`main` provenance; branch test
builds cannot satisfy those gates or replace the final candidate build.

For the shortest Root feedback cycle, use the direct `tv-candidate.yml` workflow
or the [TV development command](development/TV-DEVELOPMENT.md). It compiles only
the coherent Root application, updater and infrastructure packages, without
desktop bundling or Android. The admitted build job first runs affected UI checks
or the TV runtime suite; behavioral and unknown/shared changes retain controls,
watchdog, emergency and recovery regressions before any signed device delivery.
The protected signer verifies the exact source,
workflow run/attempt, artifact digest, package inventory and pinned public key.
`direct_tv_qa=true` selects this input in **Sign and publish release** with
`publish=false` and `preliminary_root_qa=true`. This produces unpublished signed
QA artifacts; it cannot satisfy final build or hardware acceptance gates.

Existing Root installations require signed coherent System packages rather than
reinstallation. The older desktop-artifact path remains available: a maintainer may explicitly dispatch
**Sign and publish release** from protected `release/next` with `publish=false`,
`preliminary_root_qa=true`, the draft `candidate_build_run`, exact
`candidate_source_sha` and `candidate_branch`. The macOS ARM64 package job and
its digest-bound artifact must already have completed successfully; no known
failed/cancelled job is admitted. Other validation may still be running. Keep
that candidate branch at the selected SHA until signing/recheck finishes; a
missing/moved branch or same-name tag is rejected.

The preliminary path uses protected signing tools to inspect package data, never
executes candidate-source code, and preserves the existing signing environment
and release key. Provenance and signed notes explicitly identify preliminary QA.
This produces Root-only unpublished test artifacts; it is not final acceptance,
No-root approval or stable publication. Record actual package hashes, results and
outstanding tests. A later failed check invalidates readiness; diagnose and build
again. Final release gates still require the complete successful trusted build
and affected acceptance. Use ordinary supported rollback/update when changing
candidate artifacts; never force equal-version updates or edit device receipts.

Once the complete candidate run succeeds, pin it before testing:

```sh
python3 scripts/release-flow.py pin-build --run-id RUN_ID
```

The command verifies trusted origin, successful jobs and equivalent inputs. It
writes `build: {run_id, attempt, source}` in `release-plan.json`. Selecting a
different run or attempt clears the previous `acceptance` and `acceptance_build`.
Commit the pin and later acceptance evidence normally; they do not rebuild the
installers. Record `acceptance_build` as `"RUN_ID:ATTEMPT"` alongside the acceptance
text. The gate rejects evidence bound to another run/attempt, and a rerun after
acceptance invalidates the pin even if its source SHA is unchanged.

Policy and publication both require the build source to be an ancestor of the
candidate with every non-documentation Git blob/type/mode unchanged. The only
exempt regular files are `release-plan.json`, top-level `README.md` and Markdown
under `docs/`. Executable/symlink documents, packaged notices, embedded Android
guides, versions, dependencies, tests, workflows and unknown inputs require a
new build. Do not broaden this allowlist without inspecting actual package inputs.
Final bundles use current release documentation; embedded installer bytes remain
those tested. The final main merge must match its second parent's entire tree.

A stale pin cannot authorize new code. Remove it when changing product/build
inputs, build the new candidate, pin that successful run and record its affected
acceptance. Never change a published version's contents. Keep downloaded test
artifacts and their hashes: expired/deleted artifacts require a new build and
new evidence for the affected bytes.

Choose the final version based on the actual scope. Set it in `release-plan.json`
and `release-versions.json`, update changed component manifests/versions, and
write `docs/RELEASE-X.Y.Z.md`. Component versions are independent of the overall
release version. A final plan looks like:

```json
{
  "schema": 1,
  "version": "1.2.0",
  "changes": [
    {"pr": 123, "issues": [45, 67], "summary": "Fix focus after returning Home"}
  ],
  "excluded": [
    {"pr": 124, "reason": "Reverted in full before candidate freeze"}
  ],
  "build": {"run_id": 123456, "attempt": 1, "source": "0123456789abcdef0123456789abcdef01234567"},
  "acceptance_build": "123456:1",
  "acceptance": "TV model and firmware; artifact hashes; tested paths; untested paths; rollback evidence/link"
}
```

The required **Release policy** status is produced by a trusted
`pull_request_target` workflow executing policy from `main`. Feature PRs receive a separate **Integration policy** status, so their checks
cannot satisfy the release gate on another PR with the same SHA. Candidate commits
are fetched and read as data; their scripts are never executed by this workflow.
It rejects:

- A PR to `main` from any branch other than this repository's `release/next`.
- An unset, invalid, unchanged or regressing release version; mismatched metadata;
  missing release notes or empty hardware acceptance evidence.
- Missing, duplicate or unexpected implementation PRs in the release inventory.
  Every merged PR must be included or explicitly excluded with a reason. Partial
  delivery belongs in `changes` with an accurate summary; exclude only changes
  that will not ship.
- Omitted issues linked to included PRs. The gate checks closing references and
  `Related issues:` lines and verifies that listed issues are actual issues.
- An unsuccessful/incomplete trusted candidate build or full-suite result.
  Android, four desktop jobs, Linux/macOS tests, browser validation, the full-release
  marker and ARM Python checks must succeed.
  A selected build may come from a trusted push or explicit dispatch on
  `release/next`. Unpinned candidates retain exact-head validation.

The policy returns pending while a build is unavailable/running, releasing its
runner immediately. The candidate completion event refreshes it automatically,
including failed-job reruns. API/check failures leave the gate blocked. Policy
always executes trusted `main` code and reads candidate objects only as data.

`main` additionally requires up-to-date Linux/macOS tests, a PR and resolved
conversations. Administrators follow the same rules. Force pushes and branch
removal are disabled. No second maintainer approval is mandatory, allowing solo
maintenance; review the release diff before merging and keep repository write
access limited to trusted maintainers.

Apply the [release checklist](RELEASE_CHECKLIST.md) and Root Edition hardware
gates. CI cannot certify physical TV behavior: record actual acceptance and
untested paths honestly. A product/build-input change invalidates the selected build and its affected
acceptance. Documentation/evidence-only commits preserve a verified pin. Mark the PR ready only after all
checks and acceptance are complete.

## Scoped physical acceptance and retry recovery

Before testing, run:

```sh
python3 scripts/release-flow.py acceptance-report
```

This conservatively recommends scenarios from changes since `main`; it is not an
acceptance result or a replacement for reviewing dependencies. Only known visual
assets select `ui-controls` alone. Behavioral frontend JS and unknown/shared paths
select the full matrix. Service/input paths select controls, startup and recovery;
installer/updater paths select update-recovery, including post-transition controls
and audio. Add scenarios whenever the change affects their preconditions.

Record one row per scenario with build run/attempt, artifact SHA-256, model and
firmware, initial state/upgrade source, expected/observed result, evidence link,
and untested paths. `update-recovery` includes installation/update/retained rollback
and controls/audio after the transition; `startup` distinguishes standby and cold
boot; `controls` includes Home, Back, other controls and emergency off. Retain
independent recovery and owner-presence requirements for physical changes.

Carry an observation only when all artifacts used by that scenario have identical
hashes and its preconditions (firmware, prior state/version and upgrade path) match.
The candidate input comparison is enough to keep the same selected installer
bytes across evidence edits; source similarity across rebuilt packages alone is
not enough. Do not repeat unchanged cases merely because the overall release
number changed. Do not carry a different model's result or label an untested path
passed. An unresolved failure remains a failure until investigated.

For a failed CI job at unchanged source, use GitHub's **Re-run failed jobs** or
`gh run rerun RUN_ID --failed`; successful jobs and their artifacts remain
available. Uploads from a rerun job replace its own partial artifacts, avoiding
name conflicts after an interrupted upload. A new attempt invalidates any existing
acceptance pin. Fix deterministic failures before retrying. Pin only the final successful
attempt, then accept its bytes. Publication/notification recovery keeps its normal
separate retry paths; do not rebuild or republish merely to retry a comment.

### Policy rollout

Pinned build reuse is already available in trusted `main` policy. When changing
workflow gates, preserve the existing required job names for the first release
and also complete the new full-release/browser gates. After the release merges,
trusted policy requires those additional gates on subsequent candidates. Never
weaken branch protection or use a preliminary build as final acceptance.

## Merge, publish and notify

Merge the release PR using a merge commit. The existing publication pipeline
reuses the successful candidate installers after verifying that the exact second
parent and Git tree match the resulting `main` commit. It revalidates the complete candidate test/build record,
packages, signs and verifies the release without rerunning the full suite or
recompiling platform installers. Signing/package regression checks still run.
A merge means integrated;
shipping is confirmed only after publication and verification of the packages
and signed update feeds.

Ordinary PRs run only affected checks: UI, TV/webOS, installer, Android, preview or
packaging/release tools. Shared dependencies enable every affected group; unknown
paths conservatively enable all checks. Documentation-only changes skip application
checks and Pages builds while keeping the required Linux/macOS status names green.
Visual UI changes compile the affected web applications and run focused browser
smoke checks. TV behavior changes retain the critical runtime, controls, watchdog,
recovery and update checks. The complete theme browser matrix and frozen desktop
runtime matrix run at candidate freeze; native runtime changes also select their
PR checks. Required status summaries fail if any selected check fails or is
unexpectedly skipped.
Feature branches run affected tests on PR events. Successful runtime results may
be reused within the same PR/day when the checked-out merge tree (including base
changes), selected groups, OS/image, exact Python/Node and installed Python
dependencies match. Only a small run-ID marker is restored; no cached code executes. Its source run
and the latest prior Tests run on that branch must still be successful; newer
failed/running evidence or an API error forces fresh tests. Fork PRs do not use
these markers.
Current README/plan metadata always runs, and affected setup/packaging checks
remain fresh. Cache outages fall back to tests; explicit rerun attempts bypass
hits. Full candidate validation never uses these PR success markers.

Feature branches run affected tests on PR events. The prepared candidate build
runs the full suite once. Release PR checks retain the required Linux/macOS status
names and run metadata/setup checks; the trusted Release policy enforces the full
candidate suite. Standalone push suites and the full publication suite are removed.
Pinned-equivalent documentation/evidence changes do not rebuild installers. Preview
validation belongs to Tests and the full candidate suite; Preview Pages compiles
and deploys that source without duplicating the same preview tests in a second
PR workflow.

Packaging saves `RELEASE-INVENTORY.json` with the tag, exact source commit,
release PR, included implementation PRs, their issues and delivered summaries.
The asset is included in checksums. Notification scope comes from this frozen
inventory, not from later edits to PR descriptions.

After successful publication and final verification, automation comments on
every included implementation PR, every listed issue and the release PR. A
shared issue receives one comment listing all of its delivered changes.
Excluded PRs receive no shipping notice. Notices describe the delivered portion
and do not close issues automatically.

Retries verify the signed feeds again, bind the release tag and build metadata
to the inventory's source commit, verify its checksum and compare it with the
committed plan. A hidden `<!-- shipped:vX.Y.Z -->` marker identifies each
GitHub Actions bot comment. Existing matching comments are reused/updated;
human comments with the same marker are not touched. A failed target does not
prevent notices to other targets. The workflow reports the missing targets and
fails so the delivery can be retried.

If publication fails, no shipping notice is sent. If notices fail after
publication, the product is already released: do not republish it just to retry
comments. Run **Retry release notifications** on `main` with the published tag.
It shares the publication concurrency lock and only delivers missing/changed
notices. Releases predating this inventory format are verified and skipped.
Never reuse a published version for changed contents; use a new patch release.
Resolve a failed publication before integrating the next release.

After the release merges, fast-forward `release/next` to `main`, clear the plan
for the next cycle, and continue collecting features without a new version.

## Automatic next candidate and recovery

After signed publication passes its public verification, the publishing workflow
starts the next cycle automatically: it advances `release/next` to a commit based
on the published `main` tree, clears only `release-plan.json`, and opens a new
draft PR to `main`. Existing next-cycle work is preserved. A failed publication
does not reset the branch. Shipping notices still run if next-cycle setup fails.

The **Maintain next release candidate** workflow also checks pushes to
`release/next` and supports manual dispatch on that branch. It creates a draft
only when the branch has changes and no open candidate exists, then refreshes the
marked generated scope/version/build block. Human sections are preserved. Opening the draft does not freeze a version or
establish artifact/TV acceptance. Maintain its scope and validation record as
described above. Actions-created commits/PRs do not themselves trigger other
workflows; subsequent implementation pushes trigger the normal checks.

Repository Actions settings must enable **Allow GitHub Actions to create and
approve pull requests**. These workflows request PR write access and do not
approve or merge PRs. If automatic setup fails after publication, repair the
reported permissions/state and retry with:

```sh
python3 scripts/release-flow.py start-cycle --tag vX.Y.Z
```

For an already prepared next-cycle branch, run
`python3 scripts/release-flow.py ensure-candidate`. Both commands reuse an existing
candidate. The cycle reset verifies the published tag against current `main`,
checks the signed feeds, and uses a non-forced ref update so concurrent work
cannot be overwritten. Never reset or force-push an active preparation branch.

## Initial rollout and protection maintenance

The first installation is an infrastructure bootstrap: merge the workflow,
script, tests and documentation through an installation PR from `release/next`
to `main`, with product versions unchanged. Existing CI must pass. This one-time
step installs the trusted policy before its status becomes mandatory; the
already published product version is skipped by the publication planner.
It does not publish a product release or send shipping notices.

Then an administrator applies and reads back repository merge settings and the
complete branch protection policy:

```sh
python3 scripts/release-flow.py protect
```

This requires repository administration permission. Run it only for intentional
policy setup: it manages the exact required checks and merge methods described
above. Do not require the new status before the bootstrap merge, as its trusted
workflow does not exist on `main` yet. Product releases after bootstrap must
follow the final candidate gate; there is no permanent bootstrap exception.

Workflow changes themselves take effect only after integration into `main`.
Release-branch Android signing uses the persistent preview identity on trusted
pushes; PR workflows receive no signing secrets. Stable feed signing and
publication remain restricted to `main` and the `release-signing` environment.

Android candidate builds use `assembleRelease` and `lintRelease`. The published
package ID and pinned signing certificate remain unchanged so preview users can
update without losing private profiles, imported keys or recovery receipts. The
`CYTV_ANDROID_PREVIEW_KEYSTORE_B64` secret name and
`android/preview-certificate.sha256` filename are retained for identity continuity;
they do not imply a debuggable build. The trusted APK verifier rejects
`application-debuggable` and includes `debuggable: false` in the build report;
assembly rejects reports without that explicit boolean. No unsigned fallback is
allowed. Native fixtures are compiled in CI but need a separate emulator run.
See [Android acceptance and limits](../android/STABLE-READINESS.md) for the
maintainer-approved emulator scope used to remove preview at candidate freeze,
physical-device follow-up and the mandatory final signed-artifact upgrade checks.

## Homebrew Installer candidate and promotion gate

The new Root-only CYTV Installer remains **unreleased**. Its independent installer
version and embedded product versions must be recorded separately. Review
[Homebrew packaging and exact CLI](../homebrew/README.md) and the
[acceptance matrix and persistent-state inventory](development/HOMEBREW-INSTALL-ACCEPTANCE.md).
All physical rows and meaningful human review remain pending; current coding and
reviews were AI-assisted. No catalog submission or public availability follows
from passing CI. Do not copy historical C3 evidence onto this path.

`homebrew/release.json` is deliberately absent, so public promotion is disabled.
An unaccepted or stale-record Homebrew candidate CI job is optional. A later
accepted record selects its originating project release, independent nondevelopment
installer version, exact IPK and serialized manifest hashes, frozen original URLs,
and genuine hardware/human evidence. Selected promotion requires the successful
trusted workflow and Homebrew job. Signing/publication compare sourceApproval to
the immutable committed source record; BUILD-INFO alone cannot grant approval.

Unrelated later product releases carry the previously approved Installer bytes
and metadata unchanged, including its original immutable IPK URL and honest older
embedded versions. They do not rebuild or adopt orphan assets. Rebuild and record
exact frozen artifacts for a new acceptance; verify package/feed assets through
the normal protected release flow. Public HTTPS reachability, screenshots, named
human review, accurate AI disclosure and catalog-maintainer review remain separate
gates. A draft implementation PR targets `release/next`; whole-branch review,
push/PR attachment and managed-worktree preservation/cleanup follow the normal
contribution rules. No release version is selected during feature preparation.

## Root-only candidate signing for maintainer QA

The existing signing workflow has a separate manual Root QA mode. It does not
create a release, move a channel, upload release assets or approve a Helper
transition. Normal stable signing/publication still runs only from `main` with
its complete release/No-root compatibility gates.

After a complete successful `cytv.yml` build from this repository's `release/next`,
run the signing workflow on `release/next` with `publish=false`, the exact tag and
its build run ID:

```sh
gh workflow run publish-release.yml --ref release/next \
  -f tag=v1.5.0 -f publish=false -f candidate_build_run=40873451401
```

Replace the example tag/run with the candidate being tested. Admission requires
all mandatory platform/runtime jobs, a committed matching release plan/version,
an unpublished version above `main`, and one unexpired CLI artifact with a
GitHub SHA-256 digest. The preparer checks that digest before extracting the
payload and checks every embedded hash/version from a clean checkout of the exact
build commit. It prepares only the three Root components before the signing step
receives the existing release key. The signer independently checks the Root-only
inventory, package sizes/hashes, versions and provenance, then verifies its result
with the pinned public key. No No-root manifest is signed. A final API recheck
rejects changed run attempts/artifacts before delivery.

The output is an Actions artifact named `signed-root-candidate-RUN-ATTEMPT` with
`system-update-root.json`, the three exact packages, an unsigned manifest and
public `PROVENANCE.json`. It contains no TV profile, address, PIN or credential.
Keep the provenance and package hashes with private device observations. Use the
existing signed Root acceptance admission and supported updater; never replace
its key, private receipts or LS2 rules to make a candidate pass. Root-only QA is
not a stable release, acceptance of No-root/Helper, or proof that retained Root
permissions can migrate. The final combined release still requires its complete
build and affected acceptance after integration.
