# Crăciun la Brașov 1.2.0

Maintained UHD packaging of Rares's theme, imported from
`spatariurares/clean-your-tv-themes` source commit
`695122b2c16d05bbe7c6b6a8f754784dbbfa3963` and reviewed distribution 1.1.0
(`34557f284aa2ef4f4d990543d675edb34ed9cebe6226087de4ba51a8ab11e27e`).
The original CSS, composition, JPEG wallpaper and preview remain unchanged.

Version 1.2.0 adds silent two-second H.264 still loops at 3840×2160 and
1920×1080, plus the original JPEG fallback. The preparation record describes
the already upscaled input JPEG: the original AI-generated image was 1672×941,
enlarged with Real-ESRGAN by the author. UHD video output adds neither animation
nor native source detail. The catalogue therefore shows 4K without a motion icon.

Rares's styling is MIT; the wallpaper and derived video are CC BY 4.0.
Full original notices and the packaging attribution are in LICENSE/CREDITS.
The maintained identity is `github:razdva122/clean-your-tv-lg-webos:craciun`.
Existing author-version installations retain their identity and selection;
there is no automatic substitution of a cached theme.

Build committed source with the ordinary author toolkit and a current runtime:

```sh
python3 scripts/export-theme-runtime.py --out build/craciun-runtime
node ../clean-your-tv-lg-theme/bin/theme.cjs build themes/craciun \
  --runtime build/craciun-runtime --out distributions/craciun/1.2.0 \
  --repository https://github.com/razdva122/clean-your-tv-lg-webos \
  --commit "$(git rev-parse HEAD)"
```

Package generation and browser checks are not physical-TV acceptance. Publish
the reviewed package through the normal release/next workflow and retain the
old immutable author distribution as historical evidence.
