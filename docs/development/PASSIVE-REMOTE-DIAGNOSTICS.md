# Passive remote candidate diagnostic (preparation only)

`scripts/passive-remote-diagnostic.js` is an independent, read-only diagnostic
prepared for the investigation of issue #207. It does not use the Helper and does
not establish a Home mapping. No TV was accessed while preparing or testing it.
Desktop fixtures exercise the parser and safeguards, not physical TV acceptance.

<a id="delivery-over-the-existing-ssh-connection-unreleased"></a>

## Delivery over the existing SSH connection

The stdin entrypoint supports an agreed observation without putting a script file
on the TV. Before the session, download the reviewed script to the computer from
an immutable commit URL, verify the maintainer-provided SHA-256, and review this
procedure and the script. Do not pipe an unverified network download into SSH.

Keep the TV awake. Replace `YOUR_EXISTING_SSH_COMMAND` below with the existing
working Developer Mode SSH command, preserving its target, port, key and host
identity verification. It must run a remote command without a pseudo-terminal;
omit `-t`/`-tt`. Do not publish that private connection command. If no trusted
working Developer Mode connection exists, stop and tell the maintainer rather
than creating a replacement profile, enabling root or changing permissions.

```sh
YOUR_EXISTING_SSH_COMMAND \
  'unset NODE_OPTIONS NODE_PATH; exec /usr/bin/node' \
  < ./passive-remote-diagnostic.js
```

The approved ten-second window starts as soon as Node receives the script.
Press and release physical Home once on the agreed remote during that window,
with no other buttons. Share only the single bounded JSON result, including an
inconclusive fixed reason if applicable; do not share an SSH command, full logs,
app inventory or credentials. Do not repeat the capture or repair permissions
after a denied/inconclusive result without a new agreed window. Helper may remain
running: this observer neither stops it nor competes for an exclusive grab.
An existing exclusive reader can prevent observations on that source, so absence
is not proof that a button was not pressed or that the input does not exist.

Use bare `/usr/bin/node`, not `node -`: exact Node 0.12.2 rejects the `-` option.
Both file execution and stdin emit one report; requiring the module does not
start observation. The read-only parser, source allowlist, ten-second/read limits,
cancellation and redaction rules below are identical for both entrypoints.
This change enables evidence collection for #304/#207; it adds no IR mapping or
production relay/controller change. Device compatibility remains unverified.

## Observation contract

Use only in a future, explicitly agreed owner-supervised window, delivered through
an **already working Dev Mode SSH connection**. The owner must review the script
and this procedure first. Do not enable Root, change firmware, force-enable SSH,
change permissions, restart services or recover a connection to run this probe.
If Dev Mode access is unavailable, stop. This diagnostic supplies no workaround.

Before the agreed window, confirm the owner can use the normal remote and end the
SSH process. Keep the current installation and recovery state unchanged. Run the
reviewed file with the TV's existing Node executable, without script arguments.
Clear `NODE_OPTIONS` and `NODE_PATH` in that command's environment before Node
starts; do not source a profile or use preload flags. If the reviewed invocation
cannot enforce this, stop rather than invent a fallback. The
script has no prompt: its observation starts immediately. During this single
window, the owner must press and release **only one Home button once** on the
agreed remote, with no other key presses. Do not hold or repeat it. The maximum
monotonic window is ten seconds, including discovery. It may finish earlier after
all selected sources complete a pair, access failure, cancellation or a budget
limit. SIGINT or SIGTERM closes descriptors and emits a cancelled report.

The script reads bounded names under `/sys/class/input/event0..31/device/name`.
Only these exact names are eligible:

| Source name | Redacted report role |
| --- | --- |
| `LGE RCU` | `ir` |
| `LGE M-RCU - Builtin [0]` | `magic_builtin` |
| `LGE Simple Premium` | `simple_premium` |

The output side `LGE M-RCU - Builtin [1]` and all other names are excluded.
Only one readable source per role is selected. Event nodes are restricted to
`/dev/input/event0..31`, opened with `O_RDONLY | O_NONBLOCK | O_NOFOLLOW`.
`fstat` must confirm a character device with Linux input major 13 and the expected
evdev minor 64–95. Symlinks, regular files and mismatched device numbers fail
closed. Discovery is limited to 32 indices and each name to fewer than 256 bytes plus a one-byte EOF probe.

The only accepted input ABI is Linux ARM32 little-endian: 16-byte `input_event`,
with two 32-bit timeval fields followed by type, code and value. No host ABI is
guessed: x64, other operating systems, big-endian and unavailable safety flags
return `unsupported_runtime`. ES5 syntax and legacy Buffer APIs permit Node
0.12.2; exact-runtime fixture results must be recorded separately from hardware
acceptance. Kernel timestamps are ignored. Partial records are bounded to a
15-byte remainder. `SYN_DROPPED` clears pending keys and suppresses records until
`SYN_REPORT`. Repeats and non-key records do not produce observations.

At most the first complete key-down/key-up pair for each role is emitted, with
key code in 0–2047 (including LG code 773). Each role closes immediately after its
first pair; subsequent key history is not parsed, retained, or reported from that role. Processing is
limited to 128 successful reads of up to 512 bytes, at most 500 polling passes,
and three selected roles. Empty nonblocking reads do not consume the successful
read budget. Polling uses `process.hrtime`, not the wall clock; clock rollback or
stalled-clock exhaustion fails closed. All descriptors close on normal exit,
read failure and catchable cancellation. SIGKILL or power loss cannot run cleanup;
the operating system closes process descriptors.

Stdout contains one bounded JSON object. It includes a fixed status/reason,
`home_mapping_verified: false`, and at most three role/code/pair observations.
`observed_candidate` means an eligible source produced a pair during the window;
it cannot prove the owner's button identity, Home routing, a safe mapping or a
fix. Another application can continue reading the same events. The diagnostic
does not grab devices, issue ioctls, inject keys, write files, upload data, make
network calls, spawn commands, inspect installed apps or change Helper state.
It never reports names, device paths, serials, raw bytes, timestamps or exception
text. CLI arguments, including raw logging or duration options, are refused.

A missing source, denied read, unsupported runtime or incomplete pair is an
inconclusive result. Do not escalate privileges, alter input ownership or repeat
capture without a new agreed window. Preserve the observed fixed reason and
state unknown/untested fields. Any later report must follow `AGENTS.md` consent
and redaction rules; this preparation grants no publication consent for another
owner's device result. Home mapping remains unverified until separately reviewed
and accepted under the project release process.

Run `node tests/passive-remote-diagnostic.cjs` from the repository root for the
VM fixture suite and ES5 parse check. The suite substitutes only built-in I/O,
platform and clocks and opens no real input devices. Running the standalone CLI
on a non-ARM host should emit `unsupported_runtime` with no observations.
