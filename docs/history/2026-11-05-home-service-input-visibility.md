# C3 Home service input visibility diagnosis — 2026-11-05

This maintainer-owned test-device observation addresses whether the ordinary
Home service can replace the native Helper by spawning the existing input relay.
It does not establish a working Helper or an accepted release candidate.

## Environment and scope

- TV: LG OLED55C3RLA, firmware43.21.71, SDK11.2.0. Marketing webOS version unknown.
- Remote: Magic Remote with pointer; exact remote model unknown.
- Edition: ordinary No-root Home service, inspected on a rooted maintainer C3.
  This is not acceptance on a clean unrooted TV.
- Installer/observer host: macOS ARM. Existing installed Home/Helper component
  versions were not reverified by this observation; final candidate bytes were
  not installed. The temporary SDK query fixture was version0.0.1.

Expected: a normal service can spawn a bounded native child; if the Home service
can see the relay's input devices, direct inherited pipes might remove the
separate Helper application and file mailbox. Short Home, normal Start/Stop and
an independent emergency exit remain required.

## Observed results

The temporary ordinary SDK service spawned its bundled query-only native child,
completed a pipe PING/PONG and observed actual child close with exit0. Both
expected built-in remote devices were not observed by that child. Its temporary
package and staging files were removed through normal terminal cleanup.

A separate read-only system observation found both exact built-in remote device
names and their character-device nodes. A harmless builtin `info` call activated
the installed Home renewal service. A unique exact service process title and
matching own-jail/kernel process-root device/inode, stable across two snapshots,
provided a diagnostic binding. Inside that root, `/dev/input` and all32 scanned
input event paths were absent. PID start time was not captured; this is not an
origin, lifecycle or authorization proof.

The simple current-Home-service-to-relay design therefore cannot access its
required input paths on this C3. Spawning a child alone does not establish device
access. No supported No-root packaging change that resolves this limitation has
been demonstrated; retaining the existing native boundary is still necessary
for the current candidate. Renaming or hiding a native component does not prove
that Helper was eliminated.

## Safety and acceptance limits

No input event node was opened during the system/Home metadata observations;
there was no ioctl, event read/write, grab, namespace entry or permission/config
change. The earlier SDK child queried device names only and did not read events,
grab devices or write input. No pairing, credential operation or real Helper
start occurred. Before and after each device phase, Root and its guardian were
off, recovery verified, stock SAM/profile/idle Home retained and Helper stopped.
The installer was idle and every coordinator window was returned.

No physical Home routing, emergency exit, audio/button behavior, update, rollback,
standby or full kernel boot was tested by these observations. Existing physical
results apply only to their original packages. This diagnosis does not justify
removing Helper, weakening protection or declaring the release ready.
