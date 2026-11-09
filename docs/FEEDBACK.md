# Share an installation result

[Documentation](README.md) · [Recover first](RECOVERY.md)

Reports of successful installations help identify tested devices. Reports of
failures help reproduce problems. Both are useful; neither proves compatibility
with every TV using the same model name.

## What to include

- TV model, webOS/firmware version and remote type, if known. Do not include a serial number.
- No-root or Root; the published release and installed component versions, if available.
- Installer platform and version: Windows, macOS, Linux or Android.
- What you tried, what you expected and what actually happened.
- What you checked: installation only, app launch, Home/Back, emergency exit, standby/wake, true cold boot, updates or rollback. Mark anything not tested.
- Problems encountered, steps that resolved them, and any remaining problem. Distinguish observed results from a suspected cause.

A good title is **Installation result: TV model / firmware / edition**.
Use the [installation result form](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/new?template=installation-result.yml).
For an existing problem, add new evidence to its issue instead of opening a duplicate.

<a id="unreleased-installer-diagnostic-context"></a>

## Installer diagnostic context

Save the report from the original failed attempt before running another check.
Current installers retain a recorded first error separately from later status
errors and include checklist results plus a filtered Doctor/status summary.
Successful setup, status and restore also offer a report. Older failures cannot
be reconstructed retroactively; missing primary evidence is explicitly marked.
Known TV and CYTV versions are included when readable; supply missing details
from TV settings without posting a serial number. A successful Doctor check is
not confirmation that installation or physical Home works. Older releases such as v1.5.4 lack this diagnostic context. [Fields and limits](development/INSTALLER-DIAGNOSTICS.md).

## Keep private data private

The installer's standard **Save diagnostic report** export is already redacted.
When requesting it, ask the reporter to save and attach the report without adding
a privacy warning or manual redaction checklist.

Agents must still review evidence before publishing it. For raw logs, manually
assembled summaries and other nonstandard attachments, review a draft before
posting. Prefer a few relevant, redacted lines over a full log. Remove SSH/SSAP keys, passphrases,
pairing tokens, IP/MAC addresses, SSIDs, serial numbers, app inventories, private
paths, screenshots with personal content and recovery backups. A filename saying
“diagnostic” does not guarantee that its contents are safe to share.

If a log reveals credentials or a security weakness, do not publish it in a public
issue. Keep it private and ask the maintainer for a private reporting channel.

## If an AI agent helped

For your installation as an end user, the agent should offer a short, redacted
draft after the attempt, whether it succeeded, failed or succeeded after recovery.
It must ask your permission to publish that draft to the named issue or repository.
You may edit it, decline or keep it locally. Permission to install or debug is not
permission to publish. No response is not consent.

For an authorized maintainer release/QA session on a maintainer-owned or
project-owned test TV, the agent may record redacted technical acceptance results
in the related issue, release PR and repository without asking separately for each
update. The maintainer/test-device context must already be established from the
human's instructions. This exception does not cover remote help on another user's
device or that user's private information. A request to keep a run private still
applies, and the redaction rules above always apply.

The agent must not run extra TV tests, retry a failed installation or change
settings just to fill in a report. See [the agent instructions](../AGENTS.md#installation-results-and-user-consent).
