# Update storage retention (unreleased)

Update caches retain every SHA-256 reference in both updater stores, including
immutable baselines, installed packages, bootstrap/infrastructure records and the
latest current/candidate/prior rollback sets. After terminal update and Home
completion, unreferenced content-verified package blobs can be removed. Product
maintenance also sweeps after its exact final readback and matching terminal
ownership lease. Unknown records, pending journals, ambiguous installer outcomes,
unsafe ownership/links or changed references disable the sweep. This is not an
age-based policy or a fixed byte quota; protected recovery sets may still fill
storage. Duplicate blobs referenced in both stores remain available in both.

New product submissions seal their staging inventory in the existing submission
receipt. Only verified completion under that request's terminal product lease
retires those exact payload files. Logs, operational journals, profiles, private
Python and backups remain. Completed resume requests return historical receipts;
current installation still requires the separate current-state validation.
Historical requests without a sealed inventory and cancelled/unfinished/unknown
requests remain available for inspection and recovery.

The version-gated System replacement retains its bundle, baseline and archive:
the historical replacement verifier still requires those bytes. Its fixed old
owner transitions and same-ID retries do not create an unbounded update history.
Do not remove this evidence to make space or infer deletion permission from age.
No TV compatibility or physical acceptance is established by filesystem tests.
