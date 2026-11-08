# Individual interrupted Root recovery handoffs

These are maintainer preparation decisions for #101, #133, #161, #216, #240 and the
pending Root operation in #200. They are not device results, owner consent,
installation instructions or compatibility evidence. No device connection is
part of preparing this document. Keep each owner's original host profile and
TV evidence separate; never copy another device's proof or use the newest
operation by date. Host-cache work in #200 and No-root #201 are separate.

## Review and execution boundary

Before sending an executable handoff, pin the exact source commit, generated
bundle and recovery modules using the code identity record below. Review the
host script as well: the recovery digest covers the bundle and two cancellation
modules, not every host file. A matching digest alone does not authorize a
connection. Agree the connection, temporary staging and limited cleanup with
that particular owner before execution. Do not ask again for answers already
present in the linked discussions.

[Local UUID lookup](ROOT-READONLY-ADMISSION.md#prepare-locally-without-a-tv-connection)
is local only, under the original PC account. No profile, key, host address,
UUID or snapshot needs public posting. Exactly one matching original pending
Root install is required. Preserve ambiguous, missing or changed evidence.

Only `inspect` may omit the candidate. The saved candidate is then verified
against that exact operation's submission and snapshot. A separate, later
mutation still requires the explicit original candidate, unchanged code pin,
reviewed proof and fresh LG Home/control confirmation. An admissible inspection
is not cancellation. The following decisions authorize no `remove`, `reconcile`,
Restore, Uninstall, resume, reinstall, firmware change or Home-setting write.

## #101 — authentication blocks the existing admission tool

Read the [latest owner reply](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/101#issuecomment-6547380654)
before preparing the private handoff. The saved-profile availability question
is answered. The original `install-observed` path is supported only if all
original-operation proof checks pass; the issue number is not a proof.

**Decision: use the explicit inspect-only authentication option only after a
separately agreed, exact-source handoff.** `scripts/root-install-recovery.py
inspect --interactive-auth` allows hidden local password/key-passphrase entry
through the existing SSH strategy. Without the flag it still refuses secret
prompts. Both inspect modes require the original local cytv host pin, refuse
new/changed trust, preserve the profile and known_hosts bytes, and never reconnect
after an interrupted agent login. Do not install a key, reset known_hosts or edit
the profile to get past a refusal.

The implemented host-auth option is explicit and off by default: use a hidden local password/key-passphrase prompt
through the existing SSH strategy only after resolved authentication rejection;
keep the original host pin, deny missing/changed host keys, stop on EOF/timeout/
partial authentication, persist no secret or identity change, and stage nothing
until authentication succeeds. Password cancellation must leave original pending
and trust bytes unchanged. The prompt refuses echoed-input fallback. A password in an argument,
environment or file is unsupported. Actual frozen Windows prompt behavior
remains untested; source/loopback tests are not device handoff acceptance.
The option requires source review and that particular owner's agreement.

Once supported authentication is agreed, use the same locally pinned bundle and
`inspect`-only command as #133. Fresh Home/Back/control confirmation belongs to
any later removal decision; do not repeat historical control questions now.

## #133 — source preparation complete, inspection agreement outstanding

The [profile reply](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/133#issuecomment-6527765027)
and [maintainer acknowledgement](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/133#issuecomment-6531095375)
already settle local profile availability. Do not request another file check or
upload. **Decision: prepared for a separately agreed, one-shot inspection; no
connection is authorized yet.** Use the original Linux account and original
saved profile, not a replacement connection. The original pinned automatic-auth procedure still stops on authentication
failure; adding interactive authentication is a changed handoff scope and needs
its own source review and owner agreement, as for #101.

After agreement, the exact-source handoff is:

```sh
python3 scripts/root-install-recovery.py inspect \
  --code-bundle build/root-recovery-code \
  --operation ORIGINAL_UUID \
  --code-sha256 7ba641c570b8e0a17654b43962b8bc6144b383fe50f764010cef51f2bf36d7f1
```

`ORIGINAL_UUID` is the one local lookup result, never a fabricated example. This
command is review material until the owner agrees to connection/staging. It
creates one private temporary code tree and removes only that tree after a
successful invocation. On refusal/unknown outcome, stop and retain the tree
until process quiescence is reviewed; do not blindly clean it up or retry.

The expected outcome is a small authenticated admission/refusal response, not a
working installation. Review original candidate, UUID, code and proof together
privately. The finalize proof authenticates original pending manifest and LS2
snapshot/registrations, absence of readiness/activity/activation, installed bytes,
SDK terminal and lease. It can refuse even when historical controls worked.
Missing System Profile remains a separate firmware-routing support blocker.

## #161 — completed passive request; additional operation-bound evidence needed

The [passive reply](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/161#issuecomment-6545721228)
answers the previous request. Do not ask for it again. **Decision: cancellation
is not admitted.** Home+ must remain in place; it does not establish the LG Home
admission conditions. Do not disable it to manufacture a passing precondition.

The smallest next passive inspection is the updated, pinned
[worker reader](ROOT-PASSIVE-DIAGNOSTICS.md): it classifies a single complete
allowlisted provisioning child from the selected worker tail and explicitly
marks the separate recovery record's binding as unverified. It executes no
retained code, stages nothing and calls no Luna service. Obtain agreement to this
additional read first; the old passive response is not consent for another run.
Unknown/ambiguous/missing/truncated results stop with evidence preserved.

Before treating the worker as the owner's pending operation, compare its UUID
with the local original pending UUID privately; the reader's unique-failure
selection alone does not establish that match. If they cannot be matched without
raw evidence, arrange private review rather than asking for a full log/profile.
Even a classified `provision/finalize` child does not bind `recovery-failure.json`
to that worker. The actual admission tool must verify submission, candidate,
snapshot, deploy/provision journals and the exact retained service state together.
A third-party route remains a refusal under the existing contract. A procedure
that preserves Home+ while recovering this state requires a separately reviewed
routing/recovery contract; this PR does not invent one.

## #240, #216 and #200 Windows follow-up — distinguish status from original failure

These are distinct original operations. Review [#216](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/216)
and the [Windows follow-up in #200](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/200#issuecomment-6536029007)
separately. **Decision: the original cause and cancellation eligibility are
undetermined; no retry/removal is admitted.** Exit 127 is a failed command's
status, not proof that Python is absent, that provisioning failed for a particular
Luna endpoint or that no Home effects occurred. `home_changed=false` is insufficient.

The historical host chain is `product_action → coordinator_code → _python →
_python_command → SSH.run`. Coordinator staging precedes interpreter selection
when no payload is supplied. `_python` may inspect/execute retained binding code;
historical normal status is not the passive diagnostic or isolated cancellation inspection.
Current source uses the operation-bound passive reader for Root install status
at `coordinator-submitted`, returning recovery-required with no resume/finish
authority. Other maintenance states retain their existing guarded behavior.
A previous successful private Python provisioning does not establish which
interpreter a later status selected. Do not upload replacement runtime/code,
rerun status, change PATH or remove pending just to diagnose 127.

New host reports record the fixed `root_action` and `root_boundary` categories:

| Boundary | What it establishes | What remains unknown |
| --- | --- | --- |
| `coordinator-stage` | SSH failure while preparing current coordinator code | Which shell/tool/path check failed; original worker failure |
| `python-select` | SSH failure while selecting/verifying Python | Binding/launcher/interpreter/tool cause; original worker failure |
| `driver` | SSH invocation of the selected interpreter/driver failed | Interpreter, environment launcher, script/import or nested child cause |

No additional TV command, command text, stderr, UUID or path is collected by
this annotation. Existing reports cannot be retroactively assigned a boundary.
Do not ask owners to rerun status solely to get these new fields.

The operation-bound reader is now implemented in `cytv/root_passive.py`, with
an internal `scripts/root-passive-inspection.py --operation ORIGINAL_UUID` entry.
See [the bounded procedure and categories](ROOT-PASSIVE-DIAGNOSTICS.md#original-operation-bootstrap-and-path-selection).
It uses only the original saved Root profile, requires its existing local host
pin, and reads the exact request/submission/snapshot. An optional
`--interactive-auth` permits hidden local entry without trust/profile changes.
No code bundle is uploaded and no retained Python/launcher is executed. Blocked
requests, absent worker and inconsistent evidence remain explicit refusals.

For #216 and #200, owner agreement to the bounded read remains outstanding.
For #240, the [latest owner reply](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/240#issuecomment-6612048529)
corrects the original installer platform to Android and agrees to an Android-supported
read-only inspection once the exact procedure is supplied. The owner updated the
app in place and retained the pending operation, but cannot confirm the original
profile/pin bytes. Do not repeat the macOS-account question or assume a desktop
profile belongs to that Android operation.

Published 1.8.2 (Android 0.8.2 / versionCode 22, #289) includes shared original-profile inspection from
**Review recovery options** for this exact pending stage. It requires one saved
matching Root profile and operation, the existing local host pin, explicit
(default-No) inspection confirmation and unchanged original records. It preserves
the original identity regardless of the current Android auth form. No coordinator,
retained Python, Luna call, trust update or worker replay is involved. The internal
PC script uses the same host selector; it is not an Android installation step.
The owner has already tested Android 0.8.2; do not ask them to wait for that baseline
or repeat the same failed recovery. Current installers include typed authentication and explicit original-operation recovery choices; delivery does not establish recovery on the reporting device. The [bounded phone procedure](../../android/README.md#interrupted-root-installation-inspection-unreleased)
describes the published inspection scope. Source checks do not establish physical
Android-to-TV acceptance or original recovery. Missing/ambiguous local records stop; do not copy replacement
profiles or ask the owner to repeat failed recovery attempts.

Do not rerun ordinary status just to collect new fields, substitute another profile,
or infer recovery from matching private Python bytes. #240's successful manual interpreter checks
do not prove which interpreter the failed driver selected. #200's macOS CA fix
(#297) shipped in 1.8.2; the reporter's historical CA environment is unconfirmed.
That host correction is separate from the later pending Windows Root operation.
Original causes and individual recovery remain unresolved.

## Code identity and records

The [2026-11-02 host source record](../history/2026-11-02-root-pinned-passive-inspection.md)
pins the new inspect-auth/passive implementation and its untested handoff limits.
Existing #133 cancellation source and bundle pins below remain historical and
must not be silently replaced with a newer host script.

Use the exact code commit and pin in the
[dated preparation record](../history/2026-11-01-root-recovery-handoffs.md#exact-source-and-retained-code).
Rebuild from that commit, then require the locally generated `digest` output to
match the pin in #133 before any separately agreed inspection. Retain the entire
generated bundle and both cancellation modules together outside a temporary
worktree. Do not substitute a package version, latest branch or older admitted
proof. The host command above does not download an artifact or contact a TV
until explicitly run with an existing original operation.

For each eventual private handoff record source/bundle/host-script hashes, UUID,
original candidate/proof, model, firmware/webOS, remote, edition/components,
installer platform, expected/actual check, problems and attempted resolutions.
Use `unknown` for missing fields and `untested` for controls, sound, standby,
cold boot, OTA and rollback unless actually observed. The preparation here has
no device result. After another owner's operation, offer a concrete redacted
result draft with its destination and obtain permission before posting it.
