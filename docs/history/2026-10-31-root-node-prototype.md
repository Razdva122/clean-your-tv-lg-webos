# Root Node prototype integration, 2026-10-31

PR [#194](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/194)
is preparatory host-only work for #160 and #164. The feature revision
`995e40310b6667bf4c1997bf81843d607051ec5e` incorporates current `release/next`.
No TV was accessed or changed; model, firmware/webOS and remote are not applicable
to these host checks. Physical installation, controls, sound, power, OTA and
rollback remain untested. Component metadata stays at the published baseline;
no version, candidate build or acceptance pin is selected.

## Verification

- `npm ci --ignore-scripts --no-audit --no-fund` passed on macOS ARM64.
- `NODE012=/path/to/node-v0.12.2/bin/node NODE8=/path/to/node-v8.12.0/bin/node python3 tests/root-node-compat.py`
  passed on exact 0.12.2, exact 8.12.0 and current 23.11.0. Actual generated
  bundles/IPKs/infrastructure, hashes, standalone signature CLIs, strict TLS,
  hostname checks, redirects/bounds/deadlines, native-fd diagnostics, five Python
  bindings and child status propagation were exercised. Synthetic host fixtures
  substitute firmware/LS2; this is not TV ABI acceptance.
- `scripts/test.sh tv setup` passed: 960 Root, 128 System, 193 setup Python cases,
  plus JS/native/compiler/theme checks. Its current-Node regression is separate
  from the three-runtime command above.
- `python3 scripts/tv_web_build.py --input launcher --output build/pr194-legacy-ui`
  followed by `BROWSER_CHANNEL=chromium TV_WEB_DIR=build/pr194-legacy-ui npm run test:legacy-ui`
  and `npm run test:geometry` with the same environment passed all four legacy
  modes and columns 1–8.
- Independent read-only source review found no actionable blockers.
- Fresh [implementation CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41209381886)
  and [Preview Pages build](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41209381571)
  passed on the refreshed feature revision, not a frozen combined candidate.

The original CI failed when an outdated UI fixture tried to click hidden
`#homeLanguage`; merging the latest integration base supplied its existing fix.
Initial local Chromium/loopback runs were blocked by sandbox permissions; the
same tests passed when run with those host capabilities allowed. No security
or release gate was weakened.

## Packaging and follow-up

Ordinary builds do not select the prototype compiler and Node 8+ admission
remains required. Prototype outputs must stay local: no signing, installation
or public artifact substitution is authorized by host results.

The HTTPS options correction changes normal System supervisor bytes. At freeze,
review System/infrastructure versions, generated inventories and retained-code
migration; rebuild affected bundles and embedding installers. Historical hashes
and device acceptance cannot authorize the changed bytes. Supported vendor Node
and native LS2 ABI, firmware Home/recovery contracts and exact signed-artifact
physical acceptance remain future work; #160 and #164 stay unresolved.

Reviewed `docs/TV-WEB-BUILD.md`, developer navigation and
`docs/development/ROOT-NODE-PROTOTYPE.md`. README/downloads and all twelve localized
setup/control guides need no prototype instruction because supported user paths
are unchanged. The final combined candidate still needs its documentation pass,
full build, versions and affected acceptance before publication.
