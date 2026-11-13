# Original international webOS app reference

Eleven original app icons are included. Ten icon resources and selected non-personal metadata were captured on 2026-10-30 from an OLED55C3RLA, firmware 43.21.71 / SDK 11.2.0.

YouTube, Netflix, Apple TV, Twitch, Emby, Plex, Jellyfin, Apple Music, LG Channels and Web Browser. PlxNative uses the original icon and package metadata from its upstream repository, pinned in `metadata.json`. No Russian streaming services are included. This is a practical international reference set available on this device, not a measured global popularity ranking.

`metadata.json` records exact native IDs/versions, package type (including stubs), resource field/name, pixel dimensions, byte lengths and SHA-256. `icons/` contains the unchanged original files. `inventory.json` embeds those same bytes for the browser renderer. Both main-project and toolkit copies must stay byte-identical; regenerate the inventory if intentionally replacing an original reference asset.

These are static rendering fixtures. Launches and network status remain browser simulations. The inventory includes
two generic simulated HDMI inputs (Console and Media player) for exploring the
Inputs menu; these labels were not read from a personal TV. `preview/bridge.js`
simulates live input status separately: the captured inputs report as connected
"PlayStation 5" and "Apple TV", and spare ports up to HDMI 4 as not connected. One-device resource provenance does not establish playback or universal TV compatibility. Device addresses, serial numbers, account/pairing keys, app data and full device inventories are excluded. Original app artwork keeps its publisher rights; see NOTICE.txt.

The initial Home order starts with PlxNative, Netflix, YouTube, Apple TV and
Apple Music. This is a preview default; saved user rearrangements take precedence.
The browser theme selector uses captures of this inventory in `preview/theme-cards/`.
