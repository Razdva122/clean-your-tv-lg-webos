# Installer journal/cache integration — 2026-11-01

## Integrated scope

Both reviewed implementation PRs are integrated in `release/next` and included in
the unfrozen [candidate #210](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/210).
This records source integration, not publication, a selected build or device acceptance.

| PR | Feature revision | Merge commit | Delivered source behavior / remaining limit |
| --- | --- | --- | --- |
| [#218](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/218) | `2a2480b94044daf7015aaa7ef6796386641f28ec` | `336804b7f2615e75ac08acfd14cc044404a0ae58` | No-root status retains uncertain install/removal journals instead of inferring completion from versions/hashes or app absence; #201 recovery remains unresolved. |
| [#220](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/220) | `1e3250843d7f07377f0e2696f31588ec8a56bb5b` | `069babce11e3d6da915ee074a4d17beb564ff23c` | Reports fixed host Python download/cache failure reasons without URLs, paths or exception text; original #200 macOS cause and subsequent Root recovery remain unresolved. |

Neither PR had a blocking review, unresolved review conversation or failed check
at integration. Normal merge commits were used without administrator bypass.
The review retained installer authority gates, TLS/redirect/size/deadline/SHA-256
validation and existing translated messages. No new endpoint, permission or
persistent product state was introduced.

## Validation

- [#218 implementation CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41272540700)
  and [integration policy](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41272540701)
  passed at the feature revision above.
- [#220 implementation CI](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41272968735)
  and [integration policy](https://github.com/Razdva122/clean-your-tv-lg-webos/actions/runs/41272968814)
  passed at its feature revision. Both PRs passed required Linux/macOS summaries,
  selected runtime and optional ARM Python checks. Browser, installer build,
  Preview deployment and full-release jobs were intentionally unselected.
- On the combined source `069babce11e3d6da915ee074a4d17beb564ff23c`,
  `npm ci` and an isolated Python environment with the unchanged
  `cytv/requirements.txt` preceded the focused host run:
  `PYTHONPATH=tests/cytv .venv/bin/python -m unittest test_operations test_transport test_python_runtime test_python_cache_cli test_diagnostics`.
  All 126 cases passed, with two expected isolated-Linux-root skips, on macOS
  ARM64/Python 3.14.2. The models cover both pending actions, exact app-list
  endpoints, uncertain idle/terminal responses, unchanged journals and safe
  cache-reason propagation. This was not a frozen full-candidate run.
- Release-flow and README metadata checks passed (16 + 3 cases). The committed
  inventory includes both PRs and their original issues; no version/build/pin or
  physical result was selected. Local Markdown targets and `git diff --check`
  were verified for this integration record.

## Documentation and packaging

Reviewed/updated with #218: `docs/CLI.md`, `docs/RECOVERY.md`,
`docs/development/NO-ROOT-PACKAGE-AUTHORITY.md`, developer navigation and all twelve
`docs/i18n/` guides. They explicitly separate the source correction from a
supported recovery result. #220 updates `docs/CLI.md` and
`docs/OPTIONAL-PYTHON.md`; its optional diagnostic field does not change setup,
controls or translated error messages, so it adds no further guide translation.
README/downloads retain the published v1.5.4 baseline. Existing unrelated candidate
documentation review is retained; final version/artifact reconciliation is pending.

Rebuild cytv desktop/console installers and the Android embedded installer payload
at freeze. Review their component versions and Android versionCode then; this
integration selects none. These PRs change no TV package/Helper source bytes by
themselves, while the candidate's existing TV rebuild scope still applies.
No complete candidate build is pinned and earlier device evidence is not extended.

## Original reports and acceptance

#201 remains open at `status:needs-info`: the existing exact `/dev/listApps`
request still awaits a response, and authoritative transaction termination and
service-registration readback remain a maintainer prerequisite. Matching files,
app absence or LG Home availability do not admit reconciliation.

#200 remains open for maintainer follow-up (`status:planned`): neither host
categories nor success on a different host establishes its original Mac cause.
The separate Root recovery source preparation in #221 is still under review;
it is not included by this integration and supplies no completed device recovery.
No new unanswered reporter request is manufactured to justify `needs-info`.
Neither issue is marked awaiting release/released merely for partial diagnostics
or preservation work, and neither is closed.

No TV was contacted or changed. Frozen macOS CLI/GUI, installed service registration,
actual recovery, Home/Back/key release/emergency controls, sound, standby, cold
boot, OTA and rollback remain untested for these exact combined candidate bytes.
No installation result from another user is republished. Final full-candidate
validation and affected signed-artifact/device acceptance remain release gates.
