# Embedded UHD wallpaper authoring — 2026-11-03

Next-release development evidence, outside the frozen release inventory. This is
host/browser verification, not a device installation or release acceptance record.
TV model, firmware/webOS and remote: not exercised in this run.

Alpine 1.5.0 uses Friedrich-Karl Mohr’s real 6000×4000 Bachalpsee photograph under
CC BY-SA 3.0 Germany. A 6000×3375 crop is downsampled to UHD; the theme embeds a
two-second still H.264 loop (3840×2160, 1,095,094 bytes), FHD loop (331,865 bytes)
and static JPEG. Source hash and processing are in the theme’s preparation record
and credits. The published Alpine 1.4.4 distribution stays byte-identical.

Ribbon 1.1.0 uses the real 14575×8441 Webb Cosmic Cliffs image, credited to NASA,
ESA, CSA, and STScI under CC BY 4.0. A downsampled 4032×2268 master supplies a
small periodic camera orbit without upscaling. The 20-second, 24fps silent H.264
variants are 9,517,335 bytes (UHD) and 2,683,830 bytes (FHD). Motion is editorial,
not measured nebula movement. At 320×180 RGB sample resolution the mean absolute
first/last-frame difference is 1.25, compared with 20.41 at half the loop; this
bounds the seam against the intended movement, not perceived TV smoothness.

The shared compiler derives video hashes/dimensions and adds the explicit
capability. The paired toolkit carries bytes through source read, hashed build,
preview, outgoing PIN-authenticated send and submission. A clean runtime export
pins main-project commit 053f91cca27b7196582f3d4bd1d0b56cb353689e. Browser UHD was
selected explicitly because a desktop browser does not establish TV capability.

Verified locally on macOS with real Chrome, simulated TV services and the public
reference-app fixture:

- Toolkit: 64/64 tests, zero skips, including real H.264 decoding at 3840×2160 in
  both Root/No-root renderers, FHD/image fallback and decoder release.
- Compiler and immutable Alpine regression, complete theme tests, Showcase local
  byte/hash checks and mock remote transport, generated catalogue reproducibility.
- Packaged Ribbon: offline picker, persistence after reload, controls and Classic
  reset in both editions. Real video and personal HTTP/cache/Apply/reload browser
  integration also passed after the shared input-validation change.
- TV web compatibility checks and two real-encoder preparation guards passed:
  undersized images reject instead of upscaling; existing output is preserved.
- Independent code review reported no actionable findings. It additionally
  compared 87,381 Base64 cases against the previous syntax contract.

The real 9 MiB media regression initially exposed repeated-group Base64 regex
stack exhaustion. Input validation now checks quartet length, alphabet and padding
shape with bounded-stack expressions; file/hash/size validation is unchanged.
The failure was reproduced before the fix and the full media unpack/build/decode
checks pass afterward.

No TV was changed. Native webOS playback, decoder resource contention, standby,
cold boot, OTA and final release installation/rollback remain untested for these
new media artifacts. Local passing checks do not replace the frozen candidate
workflow or physical acceptance.
