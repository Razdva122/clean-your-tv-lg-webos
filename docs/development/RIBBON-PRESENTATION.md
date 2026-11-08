# Ribbon presentation in the single Home application

This is the published single-Home contract from v1.8.2. Historical prototype and device
observations retain their original scope in dated acceptance records.

## Native host

Both editions use their existing application identity and an ordinary persistent
CARD window, as in v1.7.1. Ribbon changes layout and the Home wallpaper, not native
window type. There is no companion application, extra component, cross-app
profile transport or new installer protocol.

The former global OVERLAY metadata and transient presentation ownership are
removed from the canonical Home path. CSS full/overlay state cannot substitute
for the native window contract. A normal launch/relaunch must not toggle or
forcibly close Home. Launching another application uses platform app switching;
Home does not request its own close merely because foreground changes.

Normal menus, settings and card-editing keep their existing navigation priority.
Explicit Helper Stop/emergency, independent watchdog cleanup and Root recovery
retain their own bounded control and key-release behavior. They are not theme
presentation actions.

## Appearance and media

Theme and personal-wallpaper restoration run concurrently. Presentation,
activation where required and updater health still wait for both validated
appearance barriers. Optional video preparation does not delay the first Home
appearance. Theme recovery and saved-personal-wallpaper ownership remain intact.

Ribbon always uses Home's own background. It does not expose an external player
or HDMI surface. The Home decoder path therefore follows the ordinary foreground
CARD lifecycle, not an underlay snapshot or a synthetic content:false response.
Visibility and focus suspension still detach media and release its resources.

The known built-in Black Hole 4K stream can use the existing independently
hash-verified packaged MSE route before an unrelated native cache acquisition.
Other media retain normal validated transport. Unsupported or failed playback
uses the existing supported fallback or a static poster; never an unchecked URL
or an undefined media handle. Package/video hashes, decoded dimensions,
first-frame handoff, cancellation and stale-callback fences remain required.

## Verification and acceptance

Compare native manifests and launch/lifecycle behavior with v1.7.1. Exercise the
actual compiled Root and No-root interfaces as CARD hosts. A browser clock does
not verify the TV compositor's lifetime; device persistence and responsiveness
must be observed on the exact versioned candidate. Cover settings/editing,
Home/app transitions, retained profile, wallpaper/input ownership, Stop/emergency,
standby and update/rollback. Host-only results never establish TV acceptance.

The discarded two-host/four-component proposal requires no package, permission,
provisioning or Supervisor change in this candidate.
