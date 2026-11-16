/* Screensaver leases borrow the shared personal media library; no second store. */
(function (root) {
  'use strict';
  var known = { photo: false, video: false };
  function mode(value) {
    if (value !== 'photo' && value !== 'video')
      throw Error('Invalid media mode');
    return value;
  }
  function state() {
    return { photo: known.photo, video: known.video };
  }
  function start() {
    return Promise.resolve()
      .then(function () {
        return root.PersonalWallpaper.listMedia();
      })
      .then(function (value) {
        known = { photo: value.photo === true, video: value.video === true };
        return state();
      });
  }
  function receive(kind, envelope, cancelled) {
    return Promise.resolve()
      .then(function () {
        return root.PersonalWallpaper.importMedia(
          mode(kind),
          envelope,
          cancelled
        );
      })
      .then(function () {
        return start();
      })
      .then(function (value) {
        root.document.dispatchEvent(
          new root.CustomEvent('home-screensaver-media-change')
        );
        return value;
      });
  }
  function qualityFor(quality, variants, uhd) {
    if (quality === 'image') return 'image';
    if (
      variants.indexOf('4k') >= 0 &&
      ((quality === '4k' && uhd !== false) ||
        (quality === 'auto' && uhd === true))
    )
      return '4k';
    return variants.indexOf('1080p') >= 0 ? '1080p' : 'image';
  }
  function preview(kind) {
    return root.PersonalWallpaper.previewMedia(mode(kind));
  }
  function prepare(kind, cancelled, quality, uhd) {
    var rendition,
      lease = null,
      disposed = false,
      watcher = null;
    function check() {
      if (disposed || (cancelled && cancelled())) throw Error('Cancelled');
    }
    function dispose() {
      if (disposed) return Promise.resolve();
      disposed = true;
      root.clearInterval(watcher);
      return lease ? Promise.resolve(lease.dispose()) : Promise.resolve();
    }
    return Promise.resolve()
      .then(function () {
        check();
        return root.PersonalWallpaper.readMedia(mode(kind));
      })
      .then(function (pack) {
        check();
        if (!pack || !pack.manifest || !root.WallpaperMediaCache)
          throw Error('Media unavailable');
        var variants =
          pack.manifest.wallpaperVideo && pack.manifest.wallpaperVideo.variants;
        rendition = qualityFor(
          quality || '4k',
          (variants || []).map(function (v) {
            return v.quality;
          }),
          uhd
        );
        if (rendition !== 'image') {
          pack.manifest.wallpaperVideo.variants = variants.filter(function (v) {
            return v.quality === rendition;
          });
          return root.WallpaperMediaCache.prepare(
            pack.manifest,
            pack,
            cancelled
          );
        }
        var asset = pack.manifest.assets[0],
          bytes = pack.files[asset.path];
        return root.WallpaperMediaCache.prepareImage(
          {
            mediaType: asset.mediaType,
            width: asset.width,
            height: asset.height,
            size: bytes.byteLength,
            sha256: root.ThemeData.hash(bytes)
          },
          bytes
        );
      })
      .then(function (value) {
        lease = value;
        check();
        if (cancelled)
          watcher = root.setInterval(function () {
            if (cancelled()) dispose().catch(function () {});
          }, 250);
        return lease.acquire(cancelled);
      })
      .then(function (handles) {
        check();
        root.clearInterval(watcher);
        var url = rendition === 'image' ? handles.photo : handles[rendition];
        if (
          typeof url !== 'string' ||
          !/^http:\/\/127\.0\.0\.1:([0-9]{1,5})\/[a-f0-9]{32}\/(?:4k\.mp4|1080p\.mp4|photo\.jpg|photo\.png)$/.test(
            url
          )
        )
          throw Error('Invalid media cache handle');
        var port = +url.split(':')[2].split('/')[0];
        if (port < 1 || port > 65535) throw Error('Invalid media cache port');
        return {
          mediaUrl: url,
          mode: /\.mp4$/.test(url) ? 'video' : 'photo',
          dispose: dispose
        };
      })
      .catch(function (error) {
        return dispose().then(function () {
          throw error;
        });
      });
  }
  root.ScreensaverPersonal = {
    start: start,
    state: state,
    receive: receive,
    prepare: prepare,
    preview: preview
  };
})(this);
