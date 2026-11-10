# Synthetic HEIC fixture

`photo.heic` is a generated 320 × 180 teal image. `iphone-24mp.heic` is
a generated 5712 × 4284 teal image, matching a typical iPhone 24 MP photo.
Neither is a personal photo.
It was encoded from a solid-color PNG with macOS ImageIO using:

```
sips -s format heic source.png --out photo.heic
```

It contains no personal EXIF or location data. It is distributed under the
repository's license and exercises actual HEIC decoding in the WebKit phone-page test.
