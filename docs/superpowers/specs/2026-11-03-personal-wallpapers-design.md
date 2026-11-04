# Personal wallpapers: CYTV UHD and phone image upload

Approved by the owner in chat: implement both CYTV photo-to-video upload and phone QR upload capped at 1080p, with explicit quality warnings. This builds on PR #264 and remains outside frozen release #246.

## User experience

CYTV has an Wallpapers entry on its initial screen, independent of installation. Choose JPG/PNG, preview/crop at 16:9, choose TV private IPv4 and its six-digit receiving PIN, prepare locally in a cancellable background worker, then send. Package FFmpeg in frozen desktop builds for each supported platform; no runtime download or Node dependency. Show original resolution and never label an upscaled low-resolution source as true 4K. Only generate UHD when the cropped source has at least 3840x2160 pixels. Generate FHD when at least 1920x1080; otherwise retain a bounded image only. Use silent H.264 MP4, still frame loop, plus a verified image fallback. Progress distinguishes preparation, transfer, and waiting for the TV's explicit Apply.

TV Settings > Wallpapers offers Theme / My wallpaper, Receive from CYTV, Upload from phone, preview and explicit Apply/Cancel for received data, and Remove personal wallpaper. Personal media persists independently of theme changes/reloads in one bounded IndexedDB slot; replacement is transactional and a rejected/cancelled upload preserves the last wallpaper. The existing video renderer owns playback; ThemeRuntime keeps theme layout, colours and other settings.

Phone: open a QR (or manually enter the same address and PIN) on the same private network, choose JPG/PNG, crop in a mobile page, explicitly acknowledge the warning, upload a bounded JPEG. No video conversion or computer/cloud service. Warning before sending and persistent TV label: phone upload is an ordinary image up to 1080p; actual sharpness is limited by TV UI resolution; use CYTV for the native 4K video layer. Reject video and HEIC in this first version. QR, image preparation and phone page work offline with no third-party requests.

## Wire contract (all fields untrusted)

`{schemaVersion:1,kind:"wallpaper",source:"cytv"|"phone",image:{mediaType:"image/jpeg"|"image/png",width:W,height:H,size:N,sha256:HEX,data:BASE64},variants:[{quality:"4k"|"1080p",mediaType:"video/mp4",width:W,height:H,size:N,sha256:HEX,data:BASE64}]}`

No arbitrary file paths or URLs. SHA-256, strict canonical base64, declared/actual byte lengths, image headers/native decode and MP4/SPS dimensions are checked before storage/application. Image <=2 MiB; CYTV image <=3840x2160, phone <=1920x1080 and no variants; UHD video <=12 MiB, FHD <=4 MiB, combined video <=16 MiB; envelope <=33 MiB. Reuse ThemeData imageInfo/hash/videoInfo and WallpaperMediaCache for preparation. Internal prepared input shape matches HomeWallpaper.configure, with stable id `personal:wallpaper` and internally assigned asset/video paths only. Never apply this as a theme or add it to theme catalogue.

## Receiver contract

Reuse the four existing owner-authenticated Luna receiver methods and TCP 8879. `themeReceiverStart` accepts optional `{kind:"wallpaper"}` (default theme remains unchanged). Its response adds `kind:"wallpaper",wallpaperProtocol:1` for this mode. `ThemeReceiver.start(signal, kind)` passes this opt-in; status/read/stop are unchanged. A session accepts one verified-structure JSON POST `/v1/wallpaper` with `X-CYTV-PIN`; 202 means received, not applied. Authenticated GET `/v1/wallpaper-capabilities` returns `{wallpaperProtocol:1}` for CYTV preflight. GET `/wallpaper` serves the bundled phone page only during wallpaper sessions. PIN can be conveyed in QR URL fragment (`#pin=...`), never exposed in unrelated routes/logs. Keep existing private-peer/exact Host, expiry, wrong-PIN, request/socket limits and single session ownership. Same-origin browser POST is allowed only on wallpaper route, with exact http Origin matching local Host and source phone; foreign Origins and browser posts to the theme route remain forbidden. No permissive CORS. Closing/hiding/changing settings stops an unreceived session; confirming/cancelling cleans the session. Downloaded personal media uses no author code.

## Public JS interfaces

`PersonalWallpaper.start():Promise` restores a saved wallpaper without changing theme selection. `receive(envelope, cancelled?):Promise<summary>` validates and prepares a pending candidate, does not persist/apply. `apply():Promise` atomically replaces the stored candidate and activates it; `cancel():void` disposes only pending work. `select('theme'|'personal'):Promise`, `remove():Promise`, `state():{source:'theme'|'personal',installed:boolean,pending:summary|null,origin:'cytv'|'phone'|null}`. Emit `home-wallpaper-change` after changes. Provide `HomeWallpaper.setPersonal(prepared|null, enabled)` to keep a personal input separate from the latest theme input; setting/resetting themes must not discard the personal choice. Renderer state adds `source`/`origin` as needed. Personal byte handles are disposed only after the renderer detaches.

## Verification boundaries

Test phone conversion/warning/headers with real browser file selection; decode QR; validate strict receiver boundaries and cancellation/expiry. Test personal store restore, quota failure, malformed/spoofed metadata, replacement races, theme changes and release-before-revoke in browser. Desktop tests exercise real FFmpeg output through existing JS videoInfo, UI crop and cancellation, outgoing HTTP preflight/POST boundaries and frozen binary inclusion. Both editions, supported locales and packaging allowlists must include the additions. A physical install is not final release, audio/control, standby, cold boot, OTA or rollback acceptance. No private owner-device observations are published without consent.
