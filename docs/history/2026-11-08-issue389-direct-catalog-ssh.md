# Root installer catalog reads over SSH — 2026-11-08

Source follow-up for [issue #389](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/389),
based on `release/next` commit `217c3a8988b2cb16d147cef71fa2e6e87cf436c5`.
This record contains synthetic host checks, not a new installation or acceptance
report from the reporting TV. No TV was accessed during this implementation.

## Change and boundaries

The Root installer previously asked TV Node to launch both Luna commands through
`child_process.execFile`. Read the same fixed application and input endpoints
directly over the existing authenticated SSH connection instead. This is the
normal Root setup path, not an automatic retry following a failed subprocess.

Each sequential query has an eight-second host deadline and Luna exit timeout;
both timeouts can therefore take about 16 seconds plus SSH channel setup. Keep
stdin open while awaiting the reply, enforce the existing 1 MiB / 256 KiB bounds,
and drain through successful command exit. Reject additional JSON objects,
trailing non-JSON, incomplete UTF-8 and oversized responses independently of SSH
chunk boundaries. Transport loss remains fatal, including during the optional
input query. Do not retry commands or reinterpret failed reads as empty success.

Pass captured JSON data into the shipped reader through its existing I/O-provider
argument. TV Node still validates metadata and reads bounded, allowed local icon
files; it no longer loads `child_process` for installer catalog reads. Preserve
application validation, icon budgets/formats/path checks, input normalization,
independent diagnostic causes and the partial-input warning/checklist behavior.

No new endpoint, permission, pairing, dependency or persistent device state.
Desktop/Android installers need rebuilding; no component version is selected in
this implementation PR. TV service/package sources and the installed service's
separate runtime readers remain unchanged. No-root inventory is unchanged.

## Verification

- Dependency setup: `npm ci` passed.
- Baseline inventory/transport checks: 30 cases passed before the change.
- The actual generated Node program runs with loading of `child_process`
  forbidden. It failed on the original query path and passes with captured SSH
  replies. This guards the transport choice; it does not emulate libuv internals.
- Fourteen focused inventory/CLI cases passed, including valid apps/inputs,
  independent read failures, malformed/empty app rejection, connection loss,
  script-like Unicode titles, original icon preservation and channel closure.
- Independent review found a valid-prefix/trailing-stream gap. Five subcases
  reproduced it before correction and pass after draining through command exit:
  separate junk, second JSON reply, truncated UTF-8, oversized tail and late
  command failure. Repeat review found no remaining actionable issue.
- The final combined inventory, diagnostic-context and SSH-transport run passed
  71 cases, including the trailing-stream and shell-exit-126 regressions.
- Shared icon budget/quality, inventory diagnostics, input status and inventory
  JS checks passed. The shared TV reader sources are unchanged.
- `scripts/test.sh installer android setup` passed: 1,165 installer cases
  (six expected optional/platform skips), 280 setup cases and 44 Android cases,
  plus Homebrew runtime/browser checks and 8 payload / 6 installer / 6
  continuation cases. No full frozen release candidate was dispatched.
- Final formatting, whitespace and Python 3.9 grammar checks passed.

## Documentation and remaining acceptance

Updated the installer diagnostics reference and recovery matrix. Reviewed the
CLI and localized setup guidance: controls, warnings and recovery instructions
do not change, so no user-string or translated-guide edit is needed.

Full package installation on the reporting device remains unverified. The
installed Root service's runtime catalog/input path, physical Home/remote,
sound, standby, cold boot, OTA and rollback were not tested here. Host checks do
not establish compatibility or justify closing the original issue.
