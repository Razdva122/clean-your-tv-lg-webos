# Issue 364 experimental compositor implementation plan

**Goal:** admit Qt SDK 6–9 TVs by observed capabilities, without a model allowlist, using the existing mount-free Home routing protocol, with volatile configd state and independent recovery.

**Architecture:** retain the internal `c1-native-gate` / `compositor-keyfilter-v1` wire and package identifiers. Introduce marker schema 3 for capability-based admission; schemas 1 and 2 retain their original C1-only meaning. Reuse the native guardian, authenticated compositor broker, emergency reader and cancellable lifecycle controller. This is source/host preparation, not hardware acceptance.

**Spec:** the maintainer-approved design in this chat (2026-11-07), including no further reporter contact and experimental-only support.

## Constraints

- No TV connection, installation, reporter request, private-report publication or release/candidate changes.
- No Home executable/package mounts, CRIU changes, service restarts or input injection.
- No automatic emergency-stop clearing, same-boot retry, OTA or legacy C1 migration.
- Host admission is preliminary; recheck device admission before durable installation reservation and on activation.
- Refuse foreign Home takeover and unknown input ABI/configd state. Recovery does not require current admission to pass.

## Execution (inline)

- [x] Read CONTRIBUTING and current issue/timeline, create a feature branch from release/next, run npm ci and baseline capability/compositor checks.
- [x] Add failing host admission tests across models, denied/malformed responses, unsupported SDKs and a missing compositor payload. Run `python3 -m unittest tests.cytv.test_root_capabilities tests.cytv.test_root_gate`.
- [x] Add runtime tests for schema3 selection, legacy refusal, volatile effects/readback, conflict preservation, interrupted writes and boot restoration. Run `python3 -m unittest discover -s root-edition/tests -p test_c1_keyfilter_runtime.py`.
- [x] Implement capability-based host/device admission and schema3 broker validation. Keep the legacy schema validators C1-only; reuse all existing control barriers.
- [x] Exercise real transport negative-reply handling and broker schema3 admission with subprocess/VM fixtures. Run `python3 -m unittest discover -s root-edition/tests -p test_transport.py` and `node root-edition/service/test-c1-lease.cjs`.
- [x] Update candidate-only developer/user instructions and all localized guides. Explain the retained protocol names, volatile scope, fresh-install/conflict rules and untested hardware paths.
- [x] Run affected Root/installer/setup suites, JS lease/filter and native guardian checks. Review the complete diff, resolve findings, verify labels and retain experimental limitations in the final report.

## Acceptance boundaries

Host fixtures must cover valid capability-based identity across multiple models and refusal of invalid observations, unsupported SDKs/ELF, foreign takeover, unknown filter chains, lost/partial transactions, stock restoration, pair-preserving key handling and legacy schema protection. Physical Home, standby, cold boot, audio/HDMI and actual target-device recovery remain untested. The existing reporter's private Reddit messages are not a publication source or permission.

Verification outcomes and explicit limits: [dated source checks](../../history/2026-11-07-experimental-compositor-source-checks.md).
