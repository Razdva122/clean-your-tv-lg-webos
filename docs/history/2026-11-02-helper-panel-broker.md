# Helper panel broker follow-up (#196)

## Cause and transport boundaries

The Home web app runs as `com.gathin.tvhome`, including the panel opened by
Helper. Its PalmServiceBridge call to `com.local.nativehome.service/status` is
cross-package LS2. Developer Mode SSH `luna-send-pub` success uses a different
caller identity and does not establish UI ACL permission. SSAP pairing and launch
acknowledgements likewise do not establish controller status or foreground routing.

The panel previously returned immediately on a refused status call. It therefore
never tried its existing same-package `com.gathin.tvhome.renewal/homeStatus`
method, even when the live controller could answer it. The service authorizes the
Home app identity, writes a nonce-correlated expiring request in its provisioned
channel and waits for the native controller response. Auto-renewal need not be
enabled. This is an existing supported path, not a new ACL or SSH workaround.

After an explicit service refusal only, the panel now checks that independent
broker. A successful response with boolean `enabled` enables settings; otherwise
the existing unknown-status warning and confirmed manual Start remain. Explicit
stopped/blocked status, malformed replies and missing cross-package responses
retain their existing handling. No automatic launch, emergency-state clearing,
permission change, new endpoint or persistent state is introduced.

## Scope and unresolved reports

- #196: fixes the reproduced UI gate; the reported SSH success does not prove
  that the device broker will answer. Physical confirmation remains outstanding.
- #106: same warning with working Home, but exact caller refusal/broker result
  remains unconfirmed. Existing diagnostic request remains applicable.
- #59: confirmed cross-package denial; the separate stopped-controller request-file
  failure is not fixed here. Confirmed Start was already released in #60.
- #12: C5 Home already works; Android and source-install fixes already shipped.
  Its underlying Home broker failure is separate and remains unconfirmed.
- #21: installation, startup and package versions remain separate questions;
  this change does not establish a fix for the original package refusal.
- #207: 720p and delivery changes already shipped in v1.6.0. Relay still selects
  exactly M-RCU input [0], output [1], and Home code 773. Standard IR source/code
  was not captured. The existing passive diagnostic procedure is the next bounded
  evidence step, only in a separately agreed session. No speculative input mapping
  is added. A C3 Magic pass does not establish LJ550T standard IR support.

## Verification and packaging

A regression using real panel code failed before the change when LS2 returned
false and the broker returned a boolean choice. Both choices pass afterward.
Panel tests retain stopped/blocked, invalid replies, failed broker, timeout,
stale callbacks, diagnostics privacy and explicit-start consent coverage.
Same-package bridge and service-jail fixtures pass without any TV access.
Browser geometry, disclosure navigation and privacy checks pass at 720p/1080p
in all 13 locales (Chrome required execution outside the filesystem sandbox).

Only launcher source changes: published Helper 0.6.21 bytes and production native
sources are unchanged. No Helper bump/build/transition acceptance is required by
this patch. A later production IR/native change would require a coordinated
freeze-time Helper bump, build and transition acceptance; never rebuild different
bytes under 0.6.21. Legacy UI/recovery boundaries (#152) are unchanged.

No device was contacted. Model, firmware, remote, installer platform and physical
Home/standby/cold-boot/OTA/rollback results for this patch are untested. Existing
user guides and translations retain the same actions and strings; no setup or
control instruction changes. Final candidate packaging and device acceptance are
owned by the release coordinator.
