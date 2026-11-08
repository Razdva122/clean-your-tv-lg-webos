<a id="separate-installer-outcomes-unreleased"></a>

# Separate installer outcomes

The shared host installer keeps package verification, launch submission/acceptance,
startup evidence and owner-reported Home behavior separate. `SetupOutcome` in
`cytv/outcomes.py` holds only invocation-local fixed fields in `tv_info`; it is
not persisted as a new TV/host control file or accepted as recovery authority.

| Field | Evidence / values |
| --- | --- |
| `packages` | `not-verified`; `verified` after existing No-root version verification or existing Root package/updater proofs |
| `launch_request` | `not-requested`; `submitted-unconfirmed` before the request; `accepted` only after its existing positive transport acknowledgement |
| `startup` | `not-checked`; `process-observed` from an existing Helper probe; `root-state-verified` from existing Root guardian/routes; `not-observed`; `unverified` |
| `home_button` | `not-tested`; `confirmed-by-user`; `not-working` from this invocation's explicit owner observation |

No-root adds one existing read-only Helper process probe after successful setup,
with a five-second reply/command timeout and normal SSH connection deadlines. It
can find a recognized controller or relay; this is not complete process-health,
service registration, key delivery or Home interception evidence. Failure is
best-effort/unverified and cannot turn completed installation into failed package
work. No retry, permission change, extra Luna endpoint, control injection,
emergency-state clearing or automatic repair is introduced.

Root reuses the current terminal package/updater proof and existing post-activation
guardian/route readback. Lost launch acknowledgement retains the existing pending
receipt and an unconfirmed launch result; no relaunch is submitted. Existing
activation/recovery failures remain failures. Root continuation initializes a
fresh outcome after the user's separate recovery confirmation and revalidates
all existing proofs. No Root runtime or retained-worker bytes change.

After successful setup, the owner is asked to open another app and press physical
Home once briefly. Choices are CYTV Home, LG Home/no expected response, or skip;
default is skip. `--yes` never supplies an answer, noninteractive execution and
EOF/Ctrl+C here leave the check untested. This is local observation, not automatic
hardware acceptance or publication consent. Failed/skipped Home does not uninstall,
retry setup, change routing, clear emergency stop or reclassify verified packages
as absent. All other controls/audio/power/update scenarios remain untested.

Console, Qt and Android share check events and fixed report fields. Android uses
semantic numeric choices, focuses skip, and consumes them once; it does not infer
an observation from Continue or translated prose. Desktop and Android distinguish
incomplete checks from completed device acceptance and prioritize local report
export. Failed backend operations retain their error result and known partial
facts. New runs clear UI/check data; later Status/Doctor do not import an old
owner observation. Export revalidates field types/enums and drops unknown keys;
no device IDs, app inventories, raw logs or free-form owner text are added.

All twelve installer guides and CLI instructions describe the candidate behavior.
The Czech guide remains TV-only. Embedding desktop/Android payloads need normal
candidate rebuild/version review. No release version, frozen artifact, physical
acceptance or publication is selected by this implementation.
