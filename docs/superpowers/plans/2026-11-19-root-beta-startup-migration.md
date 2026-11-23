# Root Beta startup migration implementation plan

Goal: migrate the retained native Root Beta runtime without removing its app or preferences, and enable capability-admitted startup in the offline B9 lab.

The user authorized the in-place design established by the B9 investigation and delegated model gating to a separate chat. Runtime/native migration and firmware lifecycle compatibility are separate implementation units.

- [x] Native shutdown adapter. Add guarded static capability reporting and a bounded Upstart shutdown observation alongside the systemd contract. Test faults, emergency stops, malformed replies and normal shutdown.
- [x] Capability admission. Separate chat removes the model tuple, audits related executable gates and supplies capability-based eligibility plus authenticated boot-policy callback integration.
- [x] Native startup policy. Preserve startup-policy settings and expose source choices through the retained service to the native backend. Launch only after a new verified session, with intent/health revalidation and receipt-before-effect.
- [x] Transactional migration. Authenticate the retained package and recovery proof, require quiescent stock routing, preserve emergency latches and settings, back up the exact old private runtime/support and proofs, publish candidate bytes/proofs with a resumable journal, verify runtime status, and keep an inverse. Never invoke package installation/removal.
- [x] Normal entry point. Add a dedicated migration command, explicit confirmation and original connection binding. Refuse unresolved installation/removal authority unless an unstarted removal is proven and explicitly abandoned for preserving the app. Keep a full host receipt archive.
- [x] Verification. Regression tests cover tampering, interruption/resume, rollback, old input data and consent. QEMU exact B9 firmware validates retained service/Node/LS2 and current ARM guard. Model board-only lifecycle effects explicitly and preserve all installed file hashes.
- [x] Review, documentation and focused draft PR. Keep current RC scope and selected build unchanged. Record unavailable hardware cases and remove temporary worktree after push and PR.

Ruling: the migration installs capability and preserves explicit Off. It does not automatically enable a previously disabled Home controller. The offline startup test first explicitly enables the modeled controller and then verifies a new normal boot. The reporter TV is outside this task's execution scope.
