# C1 native gate implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement an explicit experimental C1 Home routing backend with independent native recovery, retaining the supported profile backend.
**Architecture:** A native fixed-path gate and guardian own volatile native-Home/checkpoint mounts. A Python developer adapter selects the experiment, verifies admission and retains separate state; ordinary Root defaults remain profile-based.
**Tech Stack:** C99/POSIX/Linux, static ARM musl via the existing Zig toolchain, Python 3.9+, existing Root app/service.
**Spec:** docs/superpowers/specs/2026-11-04-c1-native-gate.md

## Global Constraints

- Root application ID: com.cleanyourtv.root.preview. Experimental backend: c1-native-gate.
- No TV access or release publication; no automatic capability fallback.
- Independent native recovery, exact mount ownership, no fabricated profiles, stop latch persists.
- Preserve ordinary Root routing/installer/updater behavior; keep experimental operations explicitly selected.
- Experimental acceptance is source/host only until actual package-bound C1 tests.

## Task 1: Native gate and recovery process

Files: create root-edition/gate/ C sources, native README, and root-edition/tests/test_native_gate.py with its native fixture/harness as needed. Own no other files.
Interfaces: implement the exact fixed-path config and command protocol in the spec. Publish the output/status schema in root-edition/gate/README.md and message the coordinator before changing an interface.

- [ ] Write native compile/behavior tests first. Initially fail because the helper does not exist, then exercise actual parser and process behavior.
- [ ] Implement strict launch-envelope/config parsing, fixed absolute bounded Luna children, static ARM-compatible helper and selfcheck.
- [ ] Implement READY-before-mount guardian, independent input deadline, emergency, signal/failure release and retained stop/outcome.
- [ ] Check owned target/checkpoint mounts and propagation peers before effects and after inverse; refuse conflicts and incomplete reads.
- [ ] Test malformed/oversized inputs, preload, missing app/negative Luna, timeout, input death, emergency, ownership conflict and failed inverse. Build host fixture and static ARM binary; report exact limits.
- [ ] Self-review and commit only task-owned files.

## Task 2: Opt-in backend and lifecycle integration

Files: root-edition/gate_backend.py and dedicated experimental builder/installer/control entry point; root-edition/runtime/cli.py, UI exit validation and existing packaging/lifecycle guards only where required. Add focused Python/JS tests.
Interfaces: consume the native command/config/status schema from task 1. Maintain distinct gate intent/journal. Never pass synthetic profiles to existing validators.

- [ ] Add failing tests for explicit selection, C1 admission, unsupported-firmware/default rejection and missing/malformed native proof.
- [ ] Implement a concrete experimental bundle build and recovery-only setup path, including verified native hash and immutable runtime copy.
- [ ] Add explicit control/status/restore/boot dispatch for selected experimental installs, with triple-Home observer and native lease. Keep ordinary profile calls unchanged.
- [ ] Refuse standard OTA/bootstrap migration of experimental state before effects; verify stock before experimental removal. Add update/removal regression tests.
- [ ] Test actual control subprocesses, install/setup boundaries and profile path regression. Commit reviewed changes.

## Task 3: Verification, documentation and review

Files: docs/development/C1-NATIVE-GATE.md, docs/development/README.md, appropriate test runner and packaging tests; no compatibility or public release claims.

- [ ] Run npm ci, focused native/Python/JS tests, affected Root/installer suites and experimental package build/inspection.
- [ ] Document exact commands, experimental selection, state/permissions, recovery, lifecycle limits and untested device matrix.
- [ ] Review the complete branch independently, fix material findings, repeat affected checks only after changes.
- [ ] Re-read #298 before status reconciliation; source implementation is planned/pending review or in-progress as appropriate, never released.
- [ ] Save commits and a reviewable branch/draft PR as authorized; remove/archive the temporary worktree while retaining artifacts.
