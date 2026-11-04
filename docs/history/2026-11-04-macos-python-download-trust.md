# macOS private Python download trust — 2026-11-04

Related: [#200](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/200).
Host-only reproduction on macOS 15.6.1 ARM64. No TV was discovered, contacted or
changed. TV model, firmware/webOS and remote are not applicable to these checks.
No existing user profile or recovery operation was used.

## Reproduction and cause

Downloaded official ARM64 CLI executables and checked their complete bytes against
each release's published `SHA256SUMS` before execution:

| Release / cytv | Executable SHA-256 |
| --- | --- |
| v1.5.0 / 0.6.0 | `07c39ff29e69b55aa64c201bf5f9da3d6dab7d7db447fd03953cf0b72be33681` |
| v1.7.1 / 0.8.1 | `c19f9ca80359796fa3e64840b360a30a780ae8427e7940cda95f635d315bf869` |

Both unchanged executables failed `--prepare-python-runtime --language en
--data-dir <fresh-private-directory> --non-interactive` with the reported generic
download error. The 0.8.1 report preserved `python_cache.reason: tls`; 0.6.0 predates
that reason field. Neither command initiated any TV operation.

As a single-variable diagnostic control, pointing only that process's
`SSL_CERT_FILE` to `/etc/ssl/cert.pem` made both unchanged executables download and
verify all 26,256,859 bytes. The archive matched the existing pinned SHA-256
`4a71641c8d5536175e404a961624e8656eba30e97b5026f6bd7dc31e4bbeaaea`.
No verification was disabled and no system environment or certificate file changed.

The official 1.7.1 desktop ZIP also passed its release checksum:
`01fa9a5ec9c7759a96a5ae5110a7ab74643c11311672ea987dc7e3df65f7fba4`.
Its bundled OpenSSL library contains the Python build-host CA directory under
`/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl`, including
`cert.pem` and `certs`. That Python framework is absent on this test Mac; the
macOS system CA file exists. Source execution under Homebrew Python 3.11.12
downloaded the same pinned archive successfully before the correction.

This establishes a reproducible frozen macOS packaging/trust defect, including
the release/version named in the original report. The reporter's historical CA
configuration was not collected, so it does not prove that every original failure
had this cause. The later Windows pending Root installation remains separate.

## Correction and checks

The shared downloader now creates a verified default HTTPS context and additionally
loads the fixed macOS system CA file on Darwin. It passes that context to its own
HTTPS handler. Other platforms retain their default trust source. This adds no
dependency, endpoint, profile field, TV permission or persistent device state.
Certificate/hostname checks, disabled proxies, redirect policy, size/deadline/hash
validation, cache ownership checks and atomic publication remain intact.

- `npm ci --no-audit --no-fund` completed in an isolated worktree.
- The regression forced both default CA paths to missing/empty locations. Before
  correction the effective download context had zero CA certificates and the test
  failed; afterward it loaded system roots with `CERT_REQUIRED`, hostname checks
  and the default TLS floor intact.
- A real self-signed loopback HTTPS server was rejected as `tls`; no temporary or
  final cache archive remained. This is host TLS, not a simulated TV installation.
- All 52 `test_python*.py` cases passed (two existing platform/runtime skips).
- Independent read-only review found no actionable issue and separately passed
  both new TLS tests.
- A local ARM64 PyInstaller 6.22.3 one-file CLI probe, built with Python 3.11.12
  from the corrected source, downloaded and verified the pinned archive with both
  default CA environment paths deliberately missing. A second invocation reused
  the verified cache. Probe SHA-256:
  `eee52ed74940e4611728c28efa92d2c5d947a75ddb9a101edf2a7542502b0096`.
  This is an unpublished host probe without the TV payload, not a final installer
  or a rebuild of the official Python 3.12.10 GUI.

- `PATH=<isolated-venv>/bin:$PATH bash scripts/test.sh installer setup android`
  exited 0: 232 setup tests, 705 installer tests (two existing platform skips),
  35 Android tests, 17 Homebrew Python tests and the selected Homebrew JS checks.
  The same isolated environment included pinned installer requirements; no user
  TV address or profile was used by these device-boundary fixtures.
- `git diff --check` passed.

## Delivery and documentation limits

Rebuild embedding installers through the release coordinator. No component
version, candidate inventory, build pin, release feed or published bytes changed.
Final frozen CLI/GUI artifacts still require normal candidate verification.
No install, Home routing, controls/audio, standby, cold boot, OTA or rollback was
tested. The issue stays open for the unresolved original device/recovery scope.

Updated the optional-Python reference and history index. Existing setup actions,
offline preparation command, recovery instructions and translated strings are
unchanged; the twelve maintained localized setup/control guides need no new user
action for this internal trust-source correction. The process-local environment
override above is reproduction evidence, not a request to retry the reporter's
pending installation or change certificate settings.
