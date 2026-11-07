/* Trusted built-in media references reuse verified bundled bytes, without applying theme layout or CSS. */
(function (root) {
  'use strict';
  var catalog = [
    {
      'id': 'builtin:black-hole',
      'title': 'Black Hole',
      'author': 'Xecutioner',
      'license': 'Non-commercial use',
      'themeId': 'builtin:ribbon',
      'videoSha256':
        '37a30030526f89a939ad09c852736a9d0b01722630e2aca01869da2a70f256fb',
      'stream': {
        'url': 'wallpapers/black-hole-stream.mp4',
        'size': 11205167,
        'sha256':
          '8cc5673395c3cc84f0ab3280e69fe55df0f62e57423c248490e7c200c3ae251c',
        'mime': 'video/mp4; codecs="avc1.640033"',
        'seconds': 12
      }
    }
  ];
  function find(id) {
    return catalog.filter(function (item) {
      return item.id === id;
    })[0];
  }
  function list() {
    return catalog.map(function (item) {
      return {
        id: item.id,
        title: item.title,
        author: item.author,
        license: item.license
      };
    });
  }
  function prepare(id, cancelled, appearanceOnly) {
    var item = find(id),
      data = root.ThemeData;
    if (!item) return Promise.reject(Error('Unknown built-in wallpaper'));
    return Promise.all([
      data.request('appinfo.json', 65536, true),
      data.request('builtin-themes.json', 65536, true)
    ])
      .then(function (values) {
        if (cancelled && cancelled()) throw Error('Cancelled');
        var info = JSON.parse(data.decode(values[0])),
          registry = JSON.parse(data.decode(values[1])),
          version = info.themeEngineVersion || info.version;
        var entry = registry.themes.filter(function (record) {
          return record.id === item.themeId;
        })[0];
        if (
          !entry ||
          entry.url !== 'themes/' + item.themeId.slice(8) + '/cytv-theme.json'
        )
          throw Error('Built-in wallpaper files are missing');
        return data
          .load(entry, version, null, null, true, appearanceOnly)
          .then(function (pack) {
            return data.prepare(pack, version, cancelled, appearanceOnly);
          });
      })
      .then(function (prepared) {
        var variant =
          prepared.manifest.wallpaperVideo &&
          prepared.manifest.wallpaperVideo.variants.filter(function (v) {
            return v.quality === '4k';
          })[0];
        if (!variant || variant.sha256 !== item.videoSha256) {
          data.dispose(
            prepared.assetHandles,
            prepared.videoHandles,
            prepared.videoLease
          );
          throw Error('Built-in wallpaper identity mismatch');
        }
        prepared.manifest = Object.assign({}, prepared.manifest, {
          id: item.id,
          title: item.title
        });
        prepared.origin = 'builtin';
        prepared.wallpaperAuthor = item.author;
        prepared.wallpaperLicense = item.license;
        return { prepared: prepared };
      });
  }
  function creditFor(manifest) {
    var variants =
      (manifest &&
        manifest.wallpaperVideo &&
        manifest.wallpaperVideo.variants) ||
      [];
    return (
      catalog.filter(function (item) {
        return variants.some(function (v) {
          return v.sha256 === item.videoSha256;
        });
      })[0] || null
    );
  }
  function streamFor(variant) {
    var item = catalog.filter(function (item) {
      return (
        variant &&
        variant.quality === '4k' &&
        variant.sha256 === item.videoSha256
      );
    })[0];
    return item ? item.stream : null;
  }
  root.WallpaperLibrary = {
    list: list,
    has: function (id) {
      return !!find(id);
    },
    prepare: prepare,
    streamFor: streamFor,
    creditFor: creditFor
  };
})(window);
