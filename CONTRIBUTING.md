# Contributing

Use the maintained project checkout for normal development. Temporary Git
worktrees are allowed for parallel tasks so each task has its own working
directory and branch. This applies to No-root, Root and the desktop/console
installer. Run Git, build and verification commands from the root of the checkout
you are working in. `release/next` is the integration branch; `main` accepts
finalized release PRs only.

Remove every temporary worktree you create when its work is finished. First save
all needed changes and commits in Git and, where applicable, push the branch or
create/update its PR. Preserve any required artifacts outside the temporary
worktree. Prefer the managed worktree archive/remove tool when available; otherwise
use `git worktree remove`. Delete its temporary build outputs and dependencies
with it. Do not leave unused worktree folders behind or remove another task's
active checkout.

The former `release-desktop/` checkout is archived under
`archives/2026-10-24-release-desktop/`. The former `stable/` checkout was moved
to the project root on 2026-10-25, preserving its Git history and local changes.
The previous workspace README and legacy Root symlink are preserved in
`archives/2026-10-25-workspace-flattening/`. Archives and the
legacy Root checkout are for reference/recovery only; do not develop or publish
from them. Coordinate concurrent edits and commit or stash incomplete changes
before switching branches. Contributors with their own clone can use its normal
checkout path. Temporary worktrees follow the same contribution and release rules
as the maintained checkout.

Write technical and developer documentation in English. Maintain the twelve localized
user guides under `docs/i18n/` when changing user-facing setup or controls.
For every release candidate, complete the affected parts of the [documentation pass](docs/RELEASE-FLOW.md#update-documentation-for-every-candidate),
record reviewed guides and verification in the release PR, and keep candidate
instructions separate from published downloads and historical hardware evidence.

Run `npm ci` first. TV web packages use Babel/core-js and PostCSS, with a strict
compatibility check after conversion; see [TV web build](docs/TV-WEB-BUILD.md).
Helper app/service JS uses a separate Babel/core-js/safe-buffer build for TV
Node 0.10.25+. Set `NODE010` and `NODE012` to run its regression against exact
Node 0.10.25 and 0.12.2 runtimes alongside current Node.
Keep changes small and reproducible. During implementation run the tests for the
changed behavior and its dependencies; `scripts/test.sh ui`, `tv`, `installer`, `setup`,
`android` and `preview` select existing groups. Follow the affected PR checks and
run a broader group for shared or unknown dependencies. The complete
`scripts/test.sh` and browser suites remain required on the frozen release
candidate; do not repeat an unchanged full local run merely to copy its result
into another record. New code, failures or changed test preconditions justify a
new affected run. Describe the test model, firmware, expected behavior and actual
behavior. Separate standby tests from cold
boots. Never claim compatibility from a successful package installation alone.

Input changes must preserve triple-Home emergency release (long Home in legacy
Helper versions through 0.6.13), watchdog behavior, key-up delivery
and unrelated buttons. Do not automatically clear emergency-stop state. Explain
any new persistent state, permission or network endpoint in the pull request.

Share only redacted logs. Exclude SSH/SSAP credentials, addresses, SSIDs, app
inventories and personal screenshots. Report security issues privately to the
repository maintainer once a reporting channel is configured; do not publish credentials.


Target feature, fix and maintenance PRs at `release/next`. No release version is
needed during preparation. Link related issues in the PR. At candidate freeze,
collect the inventory, select the version and complete the release PR checks;
see [Release integration flow](docs/RELEASE-FLOW.md). Shipping notices are posted
automatically only after verified publication.

## Contribute a theme

Use the [theme contribution walkthrough](docs/development/CONTRIBUTING-THEMES.md) to create, preview, test, package and submit an independently hosted theme. The [Showcase reference](showcase/README.md) defines registry and review requirements. Theme submission PRs also target `release/next`; they do not publish a release by themselves.

## Documentation organization

Keep README a short user entry point. Put installation, use, recovery and
maintenance instructions behind the [documentation index](docs/README.md).
Keep source/maintainer procedures in [development references](docs/development/README.md)
and dated reports in [history](docs/history/README.md). Do not append a new
release story to every user guide. Update the current instruction in place;
link the original release evidence instead. Clearly separate unpublished paths.
Preserve inbound links/anchors when reorganizing and retain recovery details.

For another user's installation, an agent must show a redacted draft and destination
and obtain explicit user consent before publication. Authorized maintainer QA on
maintainer/project-owned test devices may publish redacted technical acceptance
records without per-report confirmation. Privacy and scope limits apply to both;
see [AGENTS.md](AGENTS.md#installation-results-and-user-consent).

## Reuse release evidence

Build a versioned candidate before physical acceptance, then use
`python3 scripts/release-flow.py pin-build --run-id RUN_ID` to select its successful
run/attempt. Commit observations with the matching `acceptance_build` token and
artifact hashes. Evidence/documentation edits preserve equivalent pinned builds;
product/build input changes require a new build and affected acceptance. Use
`acceptance-report` to review scenario scope and `sync-record` to regenerate the
candidate PR's machine-owned block. See the scoped acceptance and rollout rules
in [Release integration flow](docs/RELEASE-FLOW.md). Do not rerun unchanged manual
cases when their artifact hashes and device/state preconditions still match.

## Short development and release cycles

Use [TV development](docs/development/TV-DEVELOPMENT.md) for UI-only live feedback
and explicit signed Root package QA. These preliminary results cannot satisfy
the complete release gate. Themes use the existing computer-to-TV receiver.

One coordinator owns the candidate, inventory, build selection and release PR.
At freeze, finish versions and documentation together and explicitly dispatch
the complete candidate build. Hold new features in their working branches until
this release ships. Admit only changes needed to resolve a release blocker;
each such product change requires a new build and affected acceptance.

Loss of control/data/audio, broken update/recovery and regressions in emergency
behavior block delivery. Other findings need an explicit fix-now or documented
follow-up decision, with remaining failures and untested paths visible. No agent
may silently convert a failure to a pass or infer acceptance of a new risk.

Keep one current summary of build, tests and blockers in the release PR, linking
dated evidence. Update affected instructions with the feature, retain reviews of
unchanged guides, and let the existing generated block own inventory/version
facts. Group necessary physical observations into a bounded owner-supervised
session; automate repeatable UI checks where available.
