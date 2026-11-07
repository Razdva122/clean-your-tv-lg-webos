/* One independent, transactional personal media slot. No theme code or URLs are imported. */
(function (root) {
  'use strict';
  var database,
    started,
    current = null,
    pending = null,
    builtin = null,
    source = 'theme',
    restoreError = '',
    generation = 0,
    restoreGeneration = 0,
    writing = null,
    applying = false,
    writeQueue = Promise.resolve();
  function emit() {
    root.document.dispatchEvent(new root.CustomEvent('home-wallpaper-change'));
  }
  function summary(item) {
    return item
      ? {
          origin: item.envelope.source,
          posterURL: item.prepared.assetHandles.poster,
          width: item.envelope.image.width,
          height: item.envelope.image.height,
          storageBudget: item.storageBudget,
          qualities: item.envelope.variants.map(function (v) {
            return v.quality;
          })
        }
      : null;
  }
  function state() {
    return {
      source: source.indexOf('builtin:') === 0 ? 'builtin' : source,
      builtinId: source.indexOf('builtin:') === 0 ? source : null,
      installed: !!current,
      pending: summary(pending),
      origin: current ? current.envelope.source : null,
      error: restoreError
    };
  }
  function fail() {
    throw Error('Invalid personal wallpaper');
  }
  function keys(value, names) {
    if (
      !value ||
      typeof value !== 'object' ||
      Array.isArray(value) ||
      Object.keys(value).sort().join(',') !== names.split(' ').sort().join(',')
    )
      fail();
  }
  function bytes(value, max) {
    keys(value, 'mediaType width height size sha256 data');
    if (
      !Number.isInteger(value.size) ||
      value.size < 1 ||
      value.size > max ||
      typeof value.data !== 'string' ||
      value.data.length !== 4 * Math.ceil(value.size / 3) ||
      value.data.length % 4 !== 0 ||
      /[^A-Za-z0-9+/=]/.test(value.data) ||
      /=[^=]|={3}/.test(value.data) ||
      !/^[a-f0-9]{64}$/.test(value.sha256)
    )
      fail();
    var raw = root.atob(value.data);
    if (raw.length !== value.size || root.btoa(raw) !== value.data) fail();
    var out = new Uint8Array(raw.length);
    for (var i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
    if (root.ThemeData.hash(out) !== value.sha256) fail();
    return out.buffer;
  }
  function validate(envelope) {
    keys(envelope, 'schemaVersion kind source image variants');
    if (
      envelope.schemaVersion !== 1 ||
      envelope.kind !== 'wallpaper' ||
      ['phone', 'cytv'].indexOf(envelope.source) < 0 ||
      !Array.isArray(envelope.variants) ||
      envelope.variants.length > 2 ||
      (envelope.source === 'phone' && envelope.variants.length)
    )
      fail();
    var image = envelope.image;
    if (!image || ['image/jpeg', 'image/png'].indexOf(image.mediaType) < 0)
      fail();
    var imageBytes = bytes(image, 2 * 1024 * 1024),
      info = root.ThemeData.imageInfo(imageBytes, image.mediaType, true);
    if (
      info.width !== image.width ||
      info.height !== image.height ||
      (envelope.source === 'phone' &&
        (image.width > 1920 || image.height > 1080))
    )
      fail();
    var manifest = {
        id: 'personal:wallpaper',
        title: 'My wallpaper',
        defaults: { wallpaperAssetId: 'poster', dim: 0 },
        assets: [
          {
            id: 'poster',
            path: 'personal/poster',
            mediaType: image.mediaType,
            width: image.width,
            height: image.height
          }
        ]
      },
      files = { 'personal/poster': imageBytes },
      qualities = {},
      total = 0;
    var variants = envelope.variants.map(function (v) {
      keys(v, 'quality mediaType width height size sha256 data');
      if (
        ['4k', '1080p'].indexOf(v.quality) < 0 ||
        qualities[v.quality] ||
        v.mediaType !== 'video/mp4'
      )
        fail();
      qualities[v.quality] = true;
      var copy = {
          mediaType: v.mediaType,
          width: v.width,
          height: v.height,
          size: v.size,
          sha256: v.sha256,
          data: v.data
        },
        data = bytes(copy, (v.quality === '4k' ? 12 : 4) * 1024 * 1024),
        parsed = root.ThemeData.videoInfo(data),
        w = v.quality === '4k' ? 3840 : 1920,
        h = v.quality === '4k' ? 2160 : 1080;
      if (
        v.width !== w ||
        v.height !== h ||
        parsed.width !== w ||
        parsed.height !== h
      )
        fail();
      total += data.byteLength;
      if (total > 16 * 1024 * 1024) fail();
      var path = 'personal/' + v.quality + '.mp4';
      files[path] = data;
      return {
        quality: v.quality,
        mediaType: v.mediaType,
        width: w,
        height: h,
        size: v.size,
        sha256: v.sha256,
        path: path
      };
    });
    if (variants.length) manifest.wallpaperVideo = { variants: variants };
    return { manifest: manifest, files: files };
  }
  function dispose(item) {
    if (!item) return Promise.resolve();
    var p = item.prepared;
    return Promise.resolve(p.wallpaperRelease)
      .then(function () {
        return p.videoLease && p.videoLease.dispose
          ? p.videoLease.dispose()
          : null;
      })
      .then(function () {
        root.ThemeData.dispose(
          p.assetHandles,
          p.videoLease ? {} : p.videoHandles
        );
      });
  }
  function prepare(envelope, cancelled) {
    var pack = validate(envelope),
      handles = {},
      videos = {},
      lease = null,
      url = root.URL.createObjectURL(
        new root.Blob([pack.files['personal/poster']], {
          type: envelope.image.mediaType
        })
      );
    handles.poster = url;
    return new Promise(function (resolve, reject) {
      var image = new root.Image(),
        done = false,
        timer = root.setTimeout(function () {
          finish(Error('Wallpaper image decode timed out'));
        }, 8000);
      function finish(error) {
        if (done) return;
        done = true;
        root.clearTimeout(timer);
        image.onload = image.onerror = null;
        if (error) reject(error);
        else resolve();
      }
      image.onload = function () {
        finish(
          cancelled()
            ? Error('Cancelled')
            : image.naturalWidth === envelope.image.width &&
                image.naturalHeight === envelope.image.height
              ? null
              : Error('Wallpaper dimensions mismatch')
        );
      };
      image.onerror = function () {
        finish(Error('Could not decode wallpaper'));
      };
      image.src = url;
    })
      .then(function () {
        if (cancelled()) throw Error('Cancelled');
        if (!pack.manifest.wallpaperVideo) return;
        if (root.WallpaperMediaCache)
          return root.WallpaperMediaCache.prepare(
            pack.manifest,
            pack,
            cancelled
          ).then(function (value) {
            lease = value;
          });
        pack.manifest.wallpaperVideo.variants.forEach(function (v) {
          videos[v.quality] = root.URL.createObjectURL(
            new root.Blob([pack.files[v.path]], { type: v.mediaType })
          );
        });
      })
      .then(function () {
        if (cancelled()) throw Error('Cancelled');
        return {
          envelope: envelope,
          prepared: {
            manifest: pack.manifest,
            assetHandles: handles,
            videoHandles: videos,
            videoLease: lease,
            origin: envelope.source
          }
        };
      })
      .catch(function (error) {
        return dispose({
          prepared: {
            assetHandles: handles,
            videoHandles: videos,
            videoLease: lease
          }
        }).then(function () {
          throw error;
        });
      });
  }
  function open() {
    if (database) return database;
    database = new Promise(function (resolve, reject) {
      if (!root.indexedDB) {
        reject(Error('Wallpaper storage unavailable'));
        return;
      }
      var request = root.indexedDB.open('ctv-personal-wallpaper-v1', 1),
        timer = root.setTimeout(function () {
          done = true;
          database = null;
          reject(Error('Wallpaper storage timed out'));
        }, 8000),
        done = false;
      request.onupgradeneeded = function () {
        request.result.createObjectStore('wallpaper');
      };
      request.onsuccess = function () {
        root.clearTimeout(timer);
        if (done) {
          request.result.close();
          return;
        }
        done = true;
        var db = request.result;
        db.onversionchange = function () {
          db.close();
          database = null;
        };
        resolve(db);
      };
      request.onerror = request.onblocked = function () {
        done = true;
        root.clearTimeout(timer);
        database = null;
        reject(Error('Wallpaper storage unavailable'));
      };
    });
    return database;
  }
  function transaction(mode, action, token) {
    return open().then(function (db) {
      return new Promise(function (resolve, reject) {
        if (token !== undefined && token !== generation) {
          reject(Error('Cancelled'));
          return;
        }
        var tx = db.transaction(['wallpaper'], mode),
          result,
          timer = root.setTimeout(function () {
            try {
              tx.abort();
            } catch (_) {}
          }, 8000);
        if (mode === 'readwrite' && token !== undefined) writing = tx;
        function cleanup() {
          root.clearTimeout(timer);
          if (writing === tx) writing = null;
        }
        tx.oncomplete = function () {
          cleanup();
          resolve(result);
        };
        tx.onabort = tx.onerror = function (event) {
          cleanup();
          var cause = tx.error || (event && event.target && event.target.error);
          reject(
            cause && cause.name === 'QuotaExceededError'
              ? cause
              : Error('Could not save wallpaper. Check available app storage.')
          );
        };
        try {
          action(tx.objectStore('wallpaper'), function (value) {
            result = value;
          });
        } catch (e) {
          try {
            tx.abort();
          } catch (_) {}
          cleanup();
          reject(e);
        }
      });
    });
  }
  function cancel() {
    generation++;
    if (writing)
      try {
        writing.abort();
      } catch (_) {}
    var old = pending;
    pending = null;
    dispose(old);
    emit();
  }
  function receive(envelope, cancelled) {
    cancel();
    var token = generation;
    return Promise.resolve()
      .then(function () {
        return prepare(envelope, function () {
          return token !== generation || (cancelled && cancelled());
        });
      })
      .then(function (item) {
        if (token !== generation || (cancelled && cancelled()))
          return dispose(item).then(function () {
            throw Error('Cancelled');
          });
        return root.StorageBudget.check(
          JSON.stringify({ envelope: item.envelope, source: 'personal' })
            .length *
            2 +
            1048576
        ).then(
          function (b) {
            if (token !== generation || (cancelled && cancelled()))
              return dispose(item).then(function () {
                throw Error('Cancelled');
              });
            item.storageBudget = b;
            pending = item;
            emit();
            return summary(item);
          },
          function (error) {
            return dispose(item).then(function () {
              throw error;
            });
          }
        );
      });
  }
  function record(next) {
    return { envelope: current ? current.envelope : null, source: next };
  }
  function render() {
    root.HomeWallpaper.setPersonal(
      source.indexOf('builtin:') === 0
        ? builtin && builtin.prepared
        : current && current.prepared,
      source !== 'theme'
    );
  }
  function serialized(action) {
    var result = writeQueue.then(action);
    writeQueue = result.catch(function () {});
    return result;
  }
  function apply() {
    if (!pending || applying)
      return Promise.reject(Error('No pending wallpaper'));
    var item = pending,
      token = generation;
    applying = true;
    return serialized(function () {
      return root.StorageBudget.check(
        JSON.stringify({ envelope: item.envelope, source: 'personal' }).length *
          2 +
          1048576
      )
        .then(function (b) {
          item.storageBudget = b;
          return transaction(
            'readwrite',
            function (store) {
              store.put(
                { envelope: item.envelope, source: 'personal' },
                'slot'
              );
            },
            token
          );
        })
        .then(function () {
          if (token !== generation) {
            return transaction('readwrite', function (store) {
              store.put(record(source), 'slot');
            }).then(function () {
              throw Error('Cancelled');
            });
          }
          var old = current,
            oldBuiltin = builtin;
          builtin = null;
          current = item;
          pending = null;
          source = 'personal';
          restoreError = '';
          render();
          emit();
          return Promise.all([dispose(old), dispose(oldBuiltin)]);
        });
    }).then(
      function (value) {
        applying = false;
        return value;
      },
      function (error) {
        applying = false;
        return root.StorageBudget.quotaFailure(
          error,
          JSON.stringify({ envelope: item.envelope, source: 'personal' })
            .length *
            2 +
            1048576
        );
      }
    );
  }
  function select(next) {
    var isBuiltin = root.WallpaperLibrary && root.WallpaperLibrary.has(next);
    if (['theme', 'personal'].indexOf(next) < 0 && !isBuiltin)
      return Promise.reject(Error('Invalid wallpaper source'));
    var restoring = start();
    return serialized(function () {
      return restoring
        .catch(function () {})
        .then(function () {
          if (next === 'personal' && !current)
            throw Error('No personal wallpaper');
          if (next === source) {
            render();
            return;
          }
          return (
            isBuiltin
              ? root.WallpaperLibrary.prepare(next)
              : Promise.resolve(null)
          ).then(function (item) {
            return transaction('readwrite', function (store) {
              store.put(record(next), 'slot');
            }).then(
              function () {
                var old = builtin;
                builtin = item;
                source = next;
                restoreError = '';
                render();
                emit();
                return dispose(old);
              },
              function (error) {
                return dispose(item).then(function () {
                  throw error;
                });
              }
            );
          });
        });
    });
  }
  function remove() {
    restoreGeneration++;
    cancel();
    return serialized(function () {
      return transaction('readwrite', function (store) {
        if (source.indexOf('builtin:') === 0)
          store.put({ envelope: null, source: source }, 'slot');
        else store.delete('slot');
      }).then(function () {
        var old = current;
        current = null;
        if (source.indexOf('builtin:') !== 0) source = 'theme';
        restoreError = '';
        render();
        emit();
        return dispose(old);
      });
    });
  }
  function start() {
    if (started) return started;
    var token = restoreGeneration;
    started = serialized(function () {
      return transaction('readonly', function (store, set) {
        var request = store.get('slot');
        request.onsuccess = function () {
          set(request.result);
        };
      })
        .then(function (saved) {
          if (!saved || token !== restoreGeneration) return;
          var cancelled = function () {
            return token !== restoreGeneration;
          };
          return (
            saved.envelope
              ? prepare(saved.envelope, cancelled)
              : Promise.resolve(null)
          )
            .then(function (item) {
              if (cancelled()) return dispose(item);
              current = item;
              source =
                saved.source === 'personal' && current ? 'personal' : 'theme';
              if (
                root.WallpaperLibrary &&
                root.WallpaperLibrary.has(saved.source)
              )
                return root.WallpaperLibrary.prepare(
                  saved.source,
                  cancelled,
                  true
                ).then(function (value) {
                  if (cancelled()) return dispose(value);
                  builtin = value;
                  source = saved.source;
                });
            })
            .then(function () {
              if (cancelled()) return;
              restoreError = '';
              render();
              emit();
            });
        })
        .catch(function (error) {
          if (token !== restoreGeneration) return;
          restoreError = 'Could not change wallpaper settings.';
          emit();
          throw error;
        });
    });
    return started;
  }
  root.PersonalWallpaper = {
    start: start,
    receive: receive,
    apply: apply,
    cancel: cancel,
    select: select,
    remove: remove,
    state: state
  };
})(this);
