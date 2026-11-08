<a id="update-storage-retention-unreleased"></a>

# Update storage retention

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


## Private retention diagnostics

Each attempted cache sweep or staging retirement emits a fixed summary, for
example `cytv-retention scope=cache reason=complete removed=0`. The allowlisted
scopes are `cache`, `cache-peer` (peer-store admission) and `staging`. Reasons are
`complete` (including a successful no-op), `admission-refused` (missing/unsafe or
unfinished proof), `missing-inventory` (no nonempty sealed staging inventory),
`proof-changed` (changed references, receipts or payload identity/content) and
`filesystem-error`. The summary contains no paths, filenames, operation IDs,
inventory, exception messages or device data. It is one summary per primitive,
not one message per file; an outer failure after retirement can emit another
summary with the staging count already removed.

The integer return and `removed` count describe successful unlinks, including
partial progress before a later failure. An unlink is counted before directory
fsync: `filesystem-error removed=1` can mean that one file disappeared but its
deletion durability was not confirmed. It does not authorize retry, establish a
strict byte quota or change the installation/update result. Logging is best
effort and cannot turn retention into an operation failure.

Summaries go independently to the standard-library platform syslog sink and
stderr. Product workers already capture stderr in the private request's
`worker.log`; inspect it locally and select only the fixed `cytv-retention`
lines when preparing diagnostics. The rest of that log may contain private
information and must not be published as-is. Both OTA workers discard stderr,
so their summaries depend on the device's platform logging configuration and
availability of Python syslog. Platform log storage, filtering and retrieval
are device-dependent and have not been physically verified here; no durable
observation is promised when both sinks are unavailable. No store JSON record,
new persistent log file, deletion authority or cleanup eligibility is added.

The shared store implementation is copied into the Root updater and rebuilt
System supervisor packages. Installed packages retain their pinned support code;
a Root UI update does not automatically replace a retained System supervisor or
add its newer cleanup/diagnostic hooks. Candidate packaging and acceptance must
identify the coherent packages actually delivered and tested. This change does
not migrate retained supervisors. Power loss during terminal staging retirement
can still leave partial historical payloads: the primitive tolerates missing
already-retired files on explicit valid re-entry, but automatic re-entry or
background garbage collection is not implemented.
