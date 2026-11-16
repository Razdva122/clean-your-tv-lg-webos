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
      mediaKind: current && current.envelope.mediaKind,
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
    var hasKind =
      envelope && Object.prototype.hasOwnProperty.call(envelope, 'mediaKind');
    keys(
      envelope,
      'schemaVersion kind source image variants' + (hasKind ? ' mediaKind' : '')
    );
    if (
      envelope.schemaVersion !== 1 ||
      envelope.kind !== 'wallpaper' ||
      (hasKind && ['photo', 'video'].indexOf(envelope.mediaKind) < 0) ||
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
          failure,
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
          var cause =
            failure ||
            tx.error ||
            (event && event.target && event.target.error);
          reject(
            cause && cause.name === 'QuotaExceededError'
              ? cause
              : Error('Could not save wallpaper. Check available app storage.')
          );
        };
        try {
          action(
            tx.objectStore('wallpaper'),
            function (value) {
              result = value;
            },
            function (error) {
              failure = error;
              try {
                tx.abort();
              } catch (_) {
                cleanup();
                reject(error);
              }
            }
          );
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
    if (current && current.mediaRef)
      return { mediaRef: current.mediaRef, source: next };
    return { envelope: current ? current.envelope : null, source: next };
  }
  function checkMode(mode) {
    if (mode !== 'photo' && mode !== 'video') throw Error('Unknown media type');
  }
  function read(store, key, done) {
    var request = store.get(key);
    request.onsuccess = function () {
      done(request.result);
    };
  }
  function readActive(store, done) {
    read(store, 'slot', function (saved) {
      if (!saved || !saved.mediaRef) return done(saved);
      read(store, saved.mediaRef, function (envelope) {
        done({
          envelope: envelope,
          source: saved.source,
          mediaRef: saved.mediaRef
        });
      });
    });
  }
  function reap(store, ref) {
    if (
      typeof ref !== 'string' ||
      !/^media:[a-f0-9]{64}:(?:(?:4k|1080p):[a-f0-9]{64}(?::|$)){0,2}$/.test(
        ref
      )
    )
      return;
    read(store, 'slot', function (active) {
      if (active && active.mediaRef === ref) return;
      read(store, 'library:photo', function (photo) {
        if (photo === ref) return;
        read(store, 'library:video', function (video) {
          if (video !== ref) store.delete(ref);
        });
      });
    });
  }
  function mediaRef(envelope) {
    return (
      'media:' +
      envelope.image.sha256 +
      ':' +
      envelope.variants
        .map(function (variant) {
          return variant.quality + ':' + variant.sha256;
        })
        .sort()
        .join(':')
    );
  }
  function saveMedia(store, mode, envelope, apply, done, failWrite, cancelled) {
    var ref = mediaRef(envelope);
    read(store, 'library:' + mode, function (previous) {
      try {
        if (cancelled && cancelled()) throw Error('Cancelled');
        store.put(envelope, ref);
        store.put(ref, 'library:' + mode);
        if (apply) store.put({ mediaRef: ref, source: 'personal' }, 'slot');
        else reap(store, previous);
        done({ mediaRef: ref, previous: previous });
      } catch (error) {
        failWrite(error);
      }
    });
  }
  function libraryEnvelope(mode) {
    checkMode(mode);
    return transaction('readonly', function (store, set) {
      read(store, 'library:' + mode, function (ref) {
        if (ref) {
          read(store, ref, function (envelope) {
            set({ mediaRef: ref, envelope: envelope });
          });
        } else {
          // Open an already uploaded wallpaper without copying the old save.
          readActive(store, function (saved) {
            if (
              saved &&
              saved.envelope &&
              (mode === 'photo' ||
                (Array.isArray(saved.envelope.variants) &&
                  saved.envelope.variants.length))
            )
              set({
                mediaRef: saved.mediaRef,
                envelope: saved.envelope,
                legacy: true
              });
          });
        }
      });
    });
  }
  function importMedia(mode, envelope, cancelled) {
    return serialized(function () {
      checkMode(mode);
      var pack = validate(envelope);
      if (envelope.mediaKind && envelope.mediaKind !== mode)
        throw Error('Choose the matching file type');
      if (mode === 'video' && !pack.manifest.wallpaperVideo)
        throw Error('Choose a prepared video');
      if (cancelled && cancelled()) throw Error('Cancelled');
      var needed = JSON.stringify(envelope).length * 2 + 1048576;
      return root.StorageBudget.check(needed)
        .then(function () {
          return transaction('readwrite', function (store, set, failWrite) {
            if (cancelled && cancelled()) throw Error('Cancelled');
            saveMedia(store, mode, envelope, false, set, failWrite, cancelled);
          });
        })
        .then(function () {
          emit();
          return { mode: mode };
        })
        .catch(function (error) {
          return root.StorageBudget.quotaFailure(error, needed);
        });
    });
  }
  function readMedia(mode) {
    return libraryEnvelope(mode).then(function (item) {
      if (!item || !item.envelope) throw Error('No saved media');
      var pack = validate(item.envelope);
      // Older wallpaper records do not distinguish still clips from motion.
      // A photo selected from this old record uses its image poster.
      if (mode === 'photo' && item.legacy) delete pack.manifest.wallpaperVideo;
      return pack;
    });
  }
  function previewMedia(mode) {
    return libraryEnvelope(mode).then(function (item) {
      if (!item || !item.envelope) return null;
      var image = item.envelope.image;
      var poster = bytes(image, 2 * 1024 * 1024);
      return {
        url: root.URL.createObjectURL(
          new root.Blob([poster], { type: image.mediaType })
        ),
        width: image.width,
        height: image.height,
        qualities:
          item.legacy && mode === 'photo'
            ? []
            : item.envelope.variants.map(function (variant) {
                return variant.quality;
              })
      };
    });
  }
  function listMedia() {
    return transaction('readonly', function (store, set) {
      read(store, 'library:photo', function (photo) {
        read(store, 'library:video', function (video) {
          var legacy = current && current.envelope;
          set({
            photo: !!(photo || legacy),
            video: !!(video || (legacy && legacy.variants.length))
          });
        });
      });
    });
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
      token = generation,
      mode =
        item.envelope.mediaKind ||
        (item.envelope.variants.length ? 'video' : 'photo');
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
            function (store, set, failWrite) {
              saveMedia(
                store,
                mode,
                item.envelope,
                true,
                set,
                failWrite,
                function () {
                  return token !== generation;
                }
              );
            },
            token
          );
        })
        .then(function (saved) {
          if (token !== generation) {
            return transaction('readwrite', function (store) {
              store.put(record(source), 'slot');
              if (saved.previous) store.put(saved.previous, 'library:' + mode);
              else store.delete('library:' + mode);
              reap(store, saved.mediaRef);
            }).then(function () {
              throw Error('Cancelled');
            });
          }
          var old = current,
            oldBuiltin = builtin;
          builtin = null;
          item.mediaRef = saved.mediaRef;
          current = item;
          pending = null;
          source = 'personal';
          restoreError = '';
          render();
          emit();
          return Promise.all([
            dispose(old),
            dispose(oldBuiltin),
            transaction('readwrite', function (store) {
              reap(store, saved.previous);
              reap(store, old && old.mediaRef);
            }).catch(function () {})
          ]);
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
  function selectMedia(mode) {
    var restoring = start();
    return serialized(function () {
      return restoring
        .catch(function () {})
        .then(function () {
          return libraryEnvelope(mode);
        })
        .then(function (saved) {
          if (!saved || !saved.envelope) throw Error('No saved media');
          return prepare(saved.envelope, function () {
            return false;
          }).then(function (item) {
            var old = current,
              oldBuiltin = builtin;
            item.mediaRef = saved.mediaRef || mediaRef(item.envelope);
            return transaction('readwrite', function (store) {
              if (!saved.mediaRef) store.put(item.envelope, item.mediaRef);
              store.put(
                { mediaRef: item.mediaRef, source: 'personal' },
                'slot'
              );
              reap(store, old && old.mediaRef);
            }).then(
              function () {
                current = item;
                builtin = null;
                source = 'personal';
                restoreError = '';
                render();
                emit();
                return Promise.all([dispose(old), dispose(oldBuiltin)]);
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
        reap(store, current && current.mediaRef);
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
        readActive(store, set);
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
              if (current) current.mediaRef = saved.mediaRef;
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
    state: state,
    importMedia: importMedia,
    listMedia: listMedia,
    readMedia: readMedia,
    previewMedia: previewMedia,
    selectMedia: selectMedia
  };
})(this);
