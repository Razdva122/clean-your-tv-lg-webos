# Individual interrupted Root recovery handoffs

These are maintainer preparation decisions for #101, #133, #161, #216 and the
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

**Decision: existing automatic-auth inspection is not admitted when a password
is required.** `scripts/root-install-recovery.py` deliberately refuses secret
prompts and new host trust. Ordinary installer password fallback does not mean
that this internal tool supports it. Do not run ordinary status to establish
password access: status may stage code and execute retained binding helpers.
Do not install a key, reset known_hosts or edit the profile to get past this gate.

The concrete host-auth follow-up design is an explicit interactive **inspect
only** option, off by default: use a hidden local password/key-passphrase prompt
through the existing SSH strategy only after resolved authentication rejection;
keep the original host pin, deny missing/changed host keys, stop on EOF/timeout/
partial authentication, persist no secret or identity change, and stage nothing
until authentication succeeds. Password cancellation must leave original pending
and trust bytes unchanged. This option is not implemented by this PR; neither
a password in an argument/environment/file nor automatic reconnection is an
acceptable substitute. It requires separate review and the owner's agreement.

Once supported authentication is agreed, use the same locally pinned bundle and
`inspect`-only command as #133. Fresh Home/Back/control confirmation belongs to
any later removal decision; do not repeat historical control questions now.

## #133 — source preparation complete, inspection agreement outstanding

The [profile reply](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/133#issuecomment-6527765027)
and [maintainer acknowledgement](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/133#issuecomment-6531095375)
already settle local profile availability. Do not request another file check or
upload. **Decision: prepared for a separately agreed, one-shot inspection; no
connection is authorized yet.** Use the original Linux account and original
saved profile, not a replacement connection. Automatic authentication failure
stops the procedure, as for #101.

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

## #216 and #200 Windows follow-up — distinguish status from original failure

These are distinct original operations. Review [#216](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/216)
and the [Windows follow-up in #200](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/200#issuecomment-6536029007)
separately. **Decision: the original cause and cancellation eligibility are
undetermined; no retry/removal is admitted.** Exit 127 is a failed command's
status, not proof that Python is absent, that provisioning failed for a particular
Luna endpoint or that no Home effects occurred. `home_changed=false` is insufficient.

The host chain is `product_action → coordinator_code → _python →
_python_command → SSH.run`. Coordinator staging precedes interpreter selection
when no payload is supplied. `_python` may inspect/execute retained binding code;
normal status is not the passive diagnostic or isolated cancellation inspection.
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

The concrete next passive-inspection design, before an executable owner command,
is to match the local pending UUID to only that device request/submission and
bounded worker tail using the existing system-Node read-safety checks. Read the
retained binding/launcher and exact expected interpreter as **data**; classify
absent, unsafe, inconsistent or expected bytes separately. Inspect an old stage
only if its exact identity is retained in evidence; never choose the newest
`/tmp/cytv-*` directory. File presence/executable mode alone cannot prove the
interpreter, ELF loader or launcher executes. Do not run it to fill this gap.
A blocked request or absent worker is an explicit unavailable result, not reason
to patch records into `root-deploy` to satisfy the current reader.

Remaining prerequisite: owner agreement to that bounded read and an authenticated
operation/path selection. The current passive reader does not implement this
bootstrap/stage contract. Until reviewed, keep the operation unresolved. A later
launcher/interpreter execution or stage upload needs a separate reviewed scope;
never fall through from passive evidence to those actions. #200's macOS cache
failure stays with its separate investigation regardless of Windows progress.

## Code identity and records

Use the exact code commit and pin in the dated preparation record linked below.
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
