# Root cold-start identity and initial screen

Historical result (2026-10-27): [corrected C3 acceptance and manual physical rollback](../RELEASE-1.4.0-ACCEPTANCE.md) passed in the recorded scope. The maintainer accepted #90 and requested closure. Pending statements below describe earlier investigation checkpoints; other hardware remains unverified.

This records source work for issue #104, delivered in earlier releases. It is separate from issue #90's
intermittent standby input-readiness failure and PR #103's diagnostic reader.

## Observed existing-source behavior

The maintainer supervised two C3 AC-off tests on 2026-10-27. Existing Root 0.4.0
was active and recovery/guardian readback passed before each test. In the first,
Live TV's unconfigured-channels screen appeared, Root became disabled with stock
routing, and short Home opened LG Home. The kernel UUID was reused, while btime
later differed from the prior active intent. An earlier fault had already
revoked intent before the last recorded boot callback. The available records do
not uniquely identify dispatch versus independent guardian as the first writer.

After explicit user re-enable, the second test waited ten seconds after remote
off, disconnected AC for thirty seconds, reconnected and switched on. Live TV
again appeared first, but Root intent, guardian, routing and recovery were healthy;
short Home opened Clean. The user confirmed LG's Power On Screen was already Home;
read-only queries reported `general.homeAutoLaunch=on`,
`general.powerOnScreen=todays`, `option.quickStartMode=off`. An inert private `/tmp`
probe created before this cycle was absent afterward. The probe did not change
routing or runtime code. Device diagnostics and connection details remain private.

These are two separate outcomes: loss of Home control, and missing initial Clean
presentation despite working Home. Successful standby tests do not validate either
cold-start path. These observations are on the existing runtime, not acceptance
of the new source. Historical first-screen failures remain valid evidence.

## Source correction

`intent_runtime.boot_identity` centrally replaces UUID:btime with UUID plus a
random session nonce. A private `session.json` and `session.lock` share the
existing `/tmp/clean-your-tv-root-boot` directory with the normal-start marker.
The JSON schema is version 1 with `kernel` and a 32-character hexadecimal `token`.
The directory is created mode 0700 and records/lock mode 0600. Root ownership,
regular file/link checks, bounded lock acquisition, exact schema and atomic
publication protect concurrent consumers. Existing malformed records are retained
and rejected. Nothing writes this nonce to flash; existing durable intent stores
the resulting session identifier in its existing `boot` field. No new permissions
or network destinations are introduced.

All existing health, shutdown, update/audio and boot-gate callers share this
identity. Clock correction within a session cannot revoke it. A new kernel UUID
or a cleared volatile store creates a new identity. Old normal-start markers,
health and shutdown evidence cannot authorize that identity. Legacy UUID:btime
intent remains schema-valid and takes the existing restore-before-gate path;
only previously confirmed enabled intent can request rearm. Explicit/emergency
off, input faults and failsafe never become enabled through the new identity.

The nonce-store lifetime was checked on one C3 snapshot/AC-off path. A firmware
that restores this private volatile store can replay the nonce; verify that
path before claiming compatibility. Do not infer a new session solely from an
absent guardian, and never clear session state while Root is running.

Earlier releases added one guarded foreground launch after protected startup.
Published v1.7.0 removed those boot/wake launch paths entirely.
It prepares the existing owned native input before the next startup according to
[the selected source policy](ROOT-NATIVE-INPUT.md). Missing/unsupported native
selection leaves normal manual Home routing; it never starts a late launch loop.
Identity, restore-before-rearm, input-loss, shutdown and failsafe gates above
remain authoritative. Historical launch behavior and outcomes in linked records
are retained as evidence, not current candidate instructions.

## Exact 9194 candidate failure and shutdown ordering

The exact `9194c16a1a38e136823624fd5c9bce1b373fc92c` test artifacts
(build 40489987476) installed Root 0.5.0 on the maintainer's C3 after the
supported #111 transition. Before testing, all runtime hashes, active intent,
independent guardian and recovery integrity were checked. The owner confirmed
Clean, Emby launch/playback with retained login, short Home returning Clean,
arrows/hold/OK/Back/volume. These are basic-control passes only.

The first new-runtime AC test failed: remote off ten seconds, AC off thirty
seconds, reconnect/on and one minute without Home left Live TV/unconfigured
channels visible. Input ENODEV led to intent revocation and stock recovery;
a subsequent Home opened LG Home with working controls. The original log has
no event timestamps/session binding, so it cannot distinguish power-off teardown
from a restored observer after restart. No successful new-runtime AC boot,
standby, emergency/off persistence or physical rollback is established.

A separate passive diagnostic cycle kept Root disabled and did not grab/inject
input or import product runtime. Firmware reported Active Standby about fourteen
seconds before input ENODEV and repeated it about 1.4 seconds before input loss.
Systemd reported stopping about 0.4 seconds after input loss; the firmware marker
was not the recognized `remoteKey` value. This proves ordinary shutdown can
remove input before the old detector recognizes shutdown. It supports this
mechanism for #104 without supplying missing timing for the first failure or
resolving #90. The separately owned diagnostic observer and its TV directory
were removed. Root remains disabled with stock LG routing.

## Shutdown evidence policy under preparation

The guardian observes the existing local tvpower `power/getPowerState` endpoint
through one owned interactive `luna-send` subscription. A valid subscribed ON
snapshot (`Active` or `Screen Saver`) must precede `Active Standby` or `Power Off`.
An initial OFF snapshot never authorizes retention. Each actual OFF push records
fresh evidence; silence does not refresh it. The existing five-second expiry is
unchanged. Active, Screen Saver, unknown/malformed replies, EOF or subscriber
failure remove that subscription's evidence. No reconnect loop or input-error
exception grants permission. If the subscription is unavailable, existing
systemd/remoteKey checks remain and unclassified input faults still disable Root.

A transaction-specific `.power` record uses the existing root-owned volatile
health directory (0700, file0600), separately from `.shutdown` evidence. It is
removed when the stream/guardian ends. All monitor writers carry their captured
startup session; an old monitor cannot stamp evidence with a new session.
Monitor startup also checks the existing transaction/generation/token/session
binding. Normal stop joins owned observer threads and terminates/reaps the child.
No durable schema, permissions, user controls or external network destination
is added. No runtime module is added to the versioned closure.

A restored old observer can report failure before boot dispatch increments the
intent generation. When its bound enabled active/stopping intent belongs to a
different startup session, it leaves recovery to boot dispatch, including the
existing restore-before-gate and fresh input/guardian requirements. Same-session
faults still revoke intent. Escape, failsafe and package loss override this deferral;
previously fault-disabled intent is never re-enabled. This race is regression
coverage, not a proven timestamped cause of the first AC failure.

## Delivery and acceptance

Deliver the coherent retained runtime through supported checked setup/update.
An app-only update or new host installer does not replace it. Do not edit installed
runtime code or integrity receipts by hand. Keep original recovery/updater archives
and user data before a fresh setup; ordinary reinstallation can reset Root
preferences. Candidate builds and source tests do not establish device acceptance.

Remaining supervised tests on the actual corrected runtime:

- Remote-off/standby and AC-off cold boot separately: first screen without Home,
  then Emby to short Home, active intent, guardian and verified recovery.
- Repeated AC-off cycles, including early clock correction; verify the new
  session differs while its identity stays stable during the same startup.
- Open Emby early and retain it through startup readiness; no late relaunch.
- Triple-Home and explicit off, then cold boot: stay off and retain LG routing.
- Failures/unknown optional APIs, duplicate callbacks and in-flight explicit off.

New-code physical acceptance remains pending until recorded here with exact
installed source/bundle identities. No new firmware compatibility is claimed.
