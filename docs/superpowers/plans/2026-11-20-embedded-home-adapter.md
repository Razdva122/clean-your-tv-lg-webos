# Embedded Home adapter implementation plan

The approved scope reuses the C1 native guardian, lifecycle health pipes,
emergency input reader and recovery operations for embedded compositor Home.
Admission follows observed capabilities, without model or firmware allowlists.

1. Establish the stock compositor launch and rollback contract from factory
   Upstart and QML files. Record the independent recovery mechanism before
   changing admission.
2. Add an embedded target mode to the existing native guardian. Preserve
   ordinary C1 behavior and all token, stop, boot and lease barriers.
3. Implement a bounded QML adapter using the existing C1 filter and lease
   broker. Keep complete key pairs, previous policies, emergency stop and
   expired-lease fallback.
4. Add an owned launch transaction with write-ahead recovery, installation,
   removal and boot reconciliation. Detect concurrent or foreign launch edits.
5. Wire the adapter through backend selection, bundle manifests, CLI, installer,
   repair and removal. Preserve retained C1 schemas and ordinary Root behavior.
6. Verify affected tests and factory replay, including interrupted writes,
   controller/guardian/service failures, lease expiry, boot and full removal.
7. Review the complete change, prepare the PR against release/next and report
   device-only acceptance gaps.

The firmware and its extracted vendor files stay outside Git. The frozen
release candidate continues under its existing coordinator.
