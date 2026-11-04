/* Isolated UI staging only: bundled verified files need no native media service. */
(function (root) {
  'use strict';
  root.WallpaperMediaCache = {prepare: function (manifest, pack) {
    var handles = {}, blobs = [], local = /^themes\/[a-z0-9-]+\/cytv-theme\.json$/.test(pack.url || '');
    var base = local ? pack.url.slice(0, pack.url.lastIndexOf('/') + 1) : '';
    manifest.wallpaperVideo.variants.forEach(function (variant) {
      if (local) handles[variant.quality] = base + variant.path;
      else {
        var url = root.URL.createObjectURL(new root.Blob([pack.files[variant.path]], {type:variant.mediaType}));
        handles[variant.quality] = url; blobs.push(url);
      }
    });
    return Promise.resolve({handles:handles, acquire:function () { return Promise.resolve(handles); },
      release:function () { return Promise.resolve(); },
      dispose:function () { blobs.forEach(function (url) { root.URL.revokeObjectURL(url); }); blobs = []; }});
  }};
}(window));
