# Home Helper diagnostics

## User workflow

In the desktop installer, open Maintenance and select **Home button diagnostics**.
In the Android installer, open Tools and select **Home button diagnostics**.
Choose the TV and No-root connection using the existing connection flow.

1. Open an app on the TV and continue when ready to record.
2. When prompted, press physical Home once, then leave the remote untouched.
   Keep the installer open for one minute.
3. Select **Save report** (desktop: **Save diagnostic report…**) and attach the
   resulting single JSON file to the issue. Say which app stayed visible.

No terminal commands, manual log collection or separate C5 Helper are required.

## Release handoff

[v1.1.0 stable](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.1.0) contains Helper 0.6.19 and cytv 0.3.0 with this diagnostic workflow. Download the stable installer for new feedback. Helper 0.6.19 still needs physical-TV acceptance; diagnostic capture alone does not establish that C5 or another model is fixed. The earlier v1.0.3 diagnostic baseline was Helper 0.6.18 / cytv 0.2.16.

Send the reply below only after a normal release candidate contains both the
updated Helper and installer. Published Helper 0.6.17 does not contain this mode.
The normal release process selects a new Helper version and builds it from source;
the build deliberately reuses the immutable published IPK for pinned 0.6.17.
Do not overwrite or relabel that baseline. Check the actual RC export on a TV
before sending the reply and link that RC in the comment.

## Implementation and report meaning

The ordinary Helper has an opt-in 60-second observation window. It adds no
launches, retries, input grabs or second foreground watcher. The existing control
channel handles `diagnostics-start` and `diagnostics-stop`; the installer handles
these automatically. A random session ID separates each capture from old logs.

Records include recognized Home presses, correlated launch requests and replies,
foreground observations, periodic samples, monitor status, and routing state.
The controller start record advertises `diagnosticsSchema: 1`.

Foreground samples use the existing subscription cache and carry its age; they
are not new queries. A blank app ID is a transition, while null means unknown.
A successful launch reply is only an acknowledgement. Unavailable monitoring is
reported explicitly. Neither an old observation nor a successful launch reply
proves which app became visible after Home.

The installer waits for confirmation that recording started, stops on cancellation,
and requests a stop after collection. Helper also expires the window independently.
It exports only allowlisted fields from the matching session into one private
JSON file. No credentials, addresses, full app inventory, raw logs or arbitrary
error text are copied. The report does include the observed application IDs and
timing. `complete` means the window expired, not that Home worked; check for an
actual Home event and usable foreground observations before drawing conclusions.
A missing start acknowledgement tells the user to update/start Helper.

## Draft reply for #12 — send only after the RC is available

Thanks for the logs. They show Home events reaching the Helper and successful
launch acknowledgements. We need to see which app actually becomes visible next.

The linked release or release candidate includes a simple diagnostic tool in the normal
installer. Please update both the installer and TV components using the RC linked
in this reply, then:

1. Open **Tools → Home button diagnostics** in the Android app (on a computer:
   **Maintenance → Home button diagnostics**), connect to your TV, and follow the
   prompts to start recording.
2. When prompted, press **Home once**, then leave the remote untouched and keep
   the installer open for one minute. Note what stays on screen.
3. Tap **Save report** and attach that single JSON file here. Tell us whether you
   saw Clean Your TV, LG Home, the original app, or a black screen.

No terminal commands or manual log collection are needed. The report contains
app IDs and timing, but no pairing keys or private connection details.

<a id="watchdog-recovery-unpublished-candidate-155"></a>

## Watchdog recovery (Helper 0.6.20, #155)

No-root Helper 0.6.20 distinguishes transient watchdog timeouts from an
emergency stop. Relay timeout 20 writes `state/watchdog`; the controller writes
the same latch before killing an unresponsive relay. Either this latch or
`state/blocked` prevents a new automatic controller/boot launch. A dead controller
therefore cannot cause an unattended restart loop. Explicit **Start Helper**
clears both latches, as the deliberate recovery action.

A surviving controller can recover timeout 20 or its own confirmed watchdog
SIGKILL. Recovery waits for the old process and its stdio to close, runs the
exclusive relay cleanup with a 2.5-second deadline, then waits 1.5 seconds before
starting a new relay. At most five attempts are allowed in a rolling ten-minute
window, measured with the controller's monotonic clock. The watchdog latch stays
until the replacement reports READY. Cleanup failure/timeout, exhausted attempts,
Stop, triple Home and other relay failures persistently stop recovery. No
automatic path deletes `blocked`. Stop is checked during cleanup, before retry,
and before accepting READY. Routing preferences are re-applied to the new relay;
late events from the previous relay cannot launch Home or affect its replacement.

Private controller events `worker-watchdog`, `worker-restart` (with attempt),
`worker-restart-limit`, `worker-start`, `cleanup` and relay READY/EXIT distinguish
these stages. They are not new exported diagnostic-schema fields. Review/redact
logs before sharing them. The only new persistent state is the watchdog latch;
there are no new permissions or network endpoints. Component versions are selected
at release freeze; a reporter's locally labelled Helper 0.6.20 is not a published
or accepted build of this change. Rebuild both the native relay and Helper JS;
ship matching app/service bytes and rebuild embedded installer payloads.

Host regressions run the actual source and compiled controller with a virtual
clock and synthetic TV/Luna boundaries. The C regression executes the actual
relay against synthetic evdev and checks that watchdog, Stop and triple Home
release held keys before ungrabbing. These checks do not establish physical-TV
compatibility. Candidate acceptance is still required on the reported NANO80T:
separate standby/wake from cold boot, check Home and arrows/OK/Back/volume/pointer,
confirm triple Home and manual resume, and record exact build hashes/versions.
No new TV install or standby, cold boot, audio, OTA or rollback result is claimed.
The different arrow-key symptom in #96 remains unresolved.

## Candidate panel caller diagnostics (#207)

The candidate Home Helper panel offers **Show diagnostics / Hide diagnostics**.
It displays a bounded snapshot of its actual existing Helper-status and, when
already eligible, Home-status requests. Viewing the snapshot issues no RPC and
starts no controller. Error text, identities, addresses and raw replies are not
exported. Unknown/malformed/timeout states remain distinct; success does not prove
physical Home interception. Share the small JSON only when requested, after
reviewing it; a full screenshot or raw log is unnecessary.

This is separate from the opt-in Home event recording that requires a running
Helper. [Caller outcomes and 720p boundaries](development/HOME-GRAPHICS-RESOLUTION.md),
[passive IR preparation](development/PASSIVE-REMOTE-DIAGNOSTICS.md). No new physical
acceptance is claimed, and no extra owner-device operation is authorized here.
