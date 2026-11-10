# Bundled HEIC decoder

Unmodified `libheif-wasm/libheif-bundle.js` from npm `libheif-js@1.23.5`,
stored as `.txt` so the TV JavaScript compiler preserves the browser code.
It contains its WebAssembly payload and needs no CDN or separate WASM request.
The TV serves it only to the temporary wallpaper phone page, in a worker.

License: LGPL-3.0; upstream combined license texts are in `LICENSE.txt`.
This decoder is a separate, replaceable worker asset; CYTV's code does not
modify it. Source and build scripts:
- https://github.com/catdad-experiments/libheif-js/tree/d8ec4bc3bc5bf8055975577bccbbc7e1d7313c2d
- https://github.com/catdad-experiments/libheif-emscripten/tree/v1.23.5

The Emscripten revision pins the underlying libraries and build instructions.

Reproduce the vendored bytes:
```
npm pack libheif-js@1.23.5 --ignore-scripts
tar -xzf libheif-js-1.23.5.tgz
cp package/libheif-wasm/libheif-bundle.js libheif-bundle.txt
cp package/libheif-wasm/LICENSE LICENSE.txt
```

SHA-256 of `libheif-bundle.txt`: `074b2b55ef3de477ba9f794ca381f3f0324c1cba8c91b4af07395f39c22d54cc`.
