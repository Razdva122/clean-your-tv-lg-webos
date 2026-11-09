(window.HomeI18n
  ? HomeI18n.ready
  : function (callback) {
      callback();
    })(function () {
  (function () {
    'use strict';
    var booted = false,
      profileError = false,
      systemRestore = null,
      restoreMarker = 'tvhome.rollback.restored.v1';
    function rpc(method, payload, cb, service) {
      var b,
        done = false;
      var timer = setTimeout(function () {
        finish(null);
      }, 2000);
      function finish(r, ok) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (b)
          try {
            b.cancel();
          } catch (_) {}
        cb(r, ok === true);
      }
      try {
        b = new PalmServiceBridge();
        b.onservicecallback = function (raw) {
          try {
            var r = JSON.parse(raw);
            finish(
              r.returnValue === true
                ? r.result === undefined
                  ? r.state
                  : r.result
                : null,
              r.returnValue === true
            );
          } catch (_) {
            finish(null);
          }
        };
        b.call(
          (service || 'luna://com.cleanyourtv.updater.service/') + method,
          JSON.stringify(payload || {})
        );
      } catch (_) {
        finish(null);
      }
    }
    function boot() {
      if (booted) return;
      booted = true;
      var s = document.createElement('script');
      s.src = 'app.js';
      s.onload = function () {
        function rendered() {
          // A rendered grid (including an intentionally empty Home) is a startup signal.
          if (
            !systemRestore &&
            !document.querySelector('#tiles .item[data-app-id]')
          ) {
            if (!window.AppLibrary || window.RootLauncherRendered !== true)
              return;
            var library = window.AppLibrary.create(
              localStorage,
              window.TV_APPS.apps,
              window.CONFIG
            );
            if (library.showAddApp() || library.visible().length) return;
          }
          var manifest = new XMLHttpRequest();
          manifest.open('GET', 'appinfo.json', true);
          manifest.timeout = 5000;
          manifest.onload = function () {
            try {
              if (manifest.status !== 0 && manifest.status !== 200) return;
              var info = JSON.parse(manifest.responseText);
              if (
                info.id === 'com.gathin.tvhome' &&
                typeof info.version === 'string' &&
                /^\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(info.version)
              ) {
                if (systemRestore) {
                  if (
                    info.version !== systemRestore.version ||
                    !window.AppLibrary ||
                    window.RootLauncherRendered !== true
                  )
                    return;
                  var expected = window.AppLibrary.create(
                    localStorage,
                    window.TV_APPS.apps,
                    window.CONFIG
                  )
                    .visible()
                    .map(function (a) {
                      return a.id;
                    })
                    .sort();
                  var actual = Array.prototype.map
                    .call(
                      document.querySelectorAll('#tiles .item[data-app-id]'),
                      function (el) {
                        return el.getAttribute('data-app-id');
                      }
                    )
                    .sort();
                  if (JSON.stringify(expected) !== JSON.stringify(actual))
                    return;
                  window.SystemUpdates.rpc('healthy', {
                    edition: 'no-root',
                    transaction: systemRestore.transaction,
                    version: info.version
                  }).catch(function () {});
                } else
                  rpc('healthy', { version: info.version }, function () {});
              }
            } catch (_) {}
          };
          manifest.onerror = manifest.ontimeout = function () {};
          manifest.send();
        }
        if (window.HomeUIReady)
          window.HomeUIReady.then(rendered, function (error) {
            if (window.SystemUpdates) systemError(error);
          });
        else rendered();
      };
      document.body.appendChild(s);
    }
    function use(s, restore, identity, system) {
      s = HomeData.validate(s);
      HomeData.save(localStorage, s);
      if (restore) {
        if (!system) {
          localStorage.removeItem('tvhome.columns.v1');
          localStorage.removeItem('tvhome.theme.choice.v1');
          localStorage.removeItem('tvhome.theme.trial.v1');
          localStorage.removeItem('tvhome.wallpaper.preferences.v1');
        }
        var previousLanguage = window.HomeI18n && HomeI18n.preference();
        ['tvhome.order', 'tvhome.layout', 'tvhome.language'].forEach(
          function (key) {
            if (s.settings[key] === undefined) localStorage.removeItem(key);
          }
        );
        HomeData.apply(localStorage, s);
        if (identity) localStorage.setItem(restoreMarker, identity);
        if (
          window.HomeI18n &&
          (HomeI18n.refresh(), HomeI18n.preference()) !== previousLanguage
        )
          window.location.reload();
      }
      window.TV_APPS = s.inventory;
      window.CONFIG = s.config;
      if (s.renewal)
        rpc(
          'restoreHistory',
          { state: s.renewal },
          function () {},
          'luna://com.gathin.tvhome.renewal/'
        );
    }
    function icon(url, cb) {
      if (/^data:image\/(png|jpeg|webp);base64,/.test(url)) {
        cb(null, url);
        return;
      }
      // Only packaged relative icon paths; never turn arbitrary remote content into a profile.
      if (
        typeof url !== 'string' ||
        url.indexOf('..') >= 0 ||
        /^([a-z]+:|\/)/i.test(url)
      ) {
        cb(Error('icon-path'));
        return;
      }
      var x = new XMLHttpRequest();
      x.open('GET', url, true);
      x.responseType = 'blob';
      x.timeout = 5000;
      x.onload = function () {
        if (
          (x.status !== 0 && x.status !== 200) ||
          !x.response ||
          x.response.size > 256 * 1024
        ) {
          cb(Error('icon'));
          return;
        }
        var f = new FileReader();
        f.onload = function () {
          cb(null, f.result);
        };
        f.onerror = function () {
          cb(Error('icon'));
        };
        f.readAsDataURL(x.response);
      };
      x.onerror = x.ontimeout = function () {
        cb(Error('icon'));
      };
      x.send();
    }
    window.HomeProfile = {
      capture: function (cb) {
        if (profileError) {
          cb(Error('stored-profile-unreadable'));
          return;
        }
        var inventory = JSON.parse(
          JSON.stringify(window.TV_APPS || { apps: [], inputs: [] })
        );
        var s = {
          schema: 1,
          inventory: inventory,
          config: JSON.parse(JSON.stringify(CONFIG)),
          settings: {}
        };
        try {
          [
            'tvhome.order',
            'tvhome.layout',
            'tvhome.language',
            'tvhome.name'
          ].forEach(function (key) {
            var value = localStorage.getItem(key);
            if (value !== null) s.settings[key] = value;
          });
        } catch (e) {
          cb(e);
          return;
        }
        var index = 0;
        function next(error, value) {
          if (error) {
            cb(error);
            return;
          }
          if (index > 0) inventory.apps[index - 1].icon = value;
          if (index < inventory.apps.length) {
            icon(inventory.apps[index++].icon, next);
            return;
          }
          rpc(
            'status',
            {},
            function (state) {
              if (!state || typeof state.enabled !== 'boolean') {
                cb(Error('renewal-state-unavailable'));
                return;
              }
              s.renewal = { enabled: false };
              ['last', 'lastRenewedAt', 'error'].forEach(function (k) {
                if (state[k] !== undefined) s.renewal[k] = state[k];
              });
              try {
                HomeData.save(localStorage, s);
                cb(null, s);
              } catch (e) {
                cb(e);
              }
            },
            'luna://com.gathin.tvhome.renewal/'
          );
        }
        next();
      }
    };
    function legacy() {
      var saved;
      try {
        saved = HomeData.load(localStorage);
      } catch (_) {
        profileError = true;
        boot();
        return;
      }
      // Personalized packages render immediately; generic upgrades may restore from
      // the independent updater's backup before constructing the tile grid.
      if (!saved && window.TV_APPS && TV_APPS.apps && TV_APPS.apps.length) {
        boot();
        return;
      }
      rpc('restore', { withTransaction: true }, function (value, ok) {
        var tx = value && value.transaction,
          snapshot =
            value && Object.prototype.hasOwnProperty.call(value, 'transaction')
              ? value.profile
              : value;
        function finish(restore, identity) {
          try {
            if (restore && snapshot) use(snapshot, true, identity);
            else if (saved) use(saved);
          } catch (_) {
            profileError = true;
          }
          boot();
        }
        if (!ok && !saved) profileError = true;
        if (
          tx &&
          ['rolling-back', 'rolled-back'].indexOf(tx.status) >= 0 &&
          tx.prior &&
          snapshot
        ) {
          var identity = tx.id + ':' + tx.prior.home;
          if (localStorage.getItem(restoreMarker) !== identity) {
            var manifest = new XMLHttpRequest();
            manifest.open('GET', 'appinfo.json', true);
            manifest.timeout = 5000;
            manifest.onload = function () {
              try {
                var info = JSON.parse(manifest.responseText);
                finish(
                  (manifest.status === 0 || manifest.status === 200) &&
                    info.id === 'com.gathin.tvhome' &&
                    info.version === tx.prior.home,
                  identity
                );
              } catch (_) {
                finish(false);
              }
            };
            manifest.onerror = manifest.ontimeout = function () {
              finish(false);
            };
            manifest.send();
            return;
          }
        }
        finish(!saved);
      });
    }
    function systemError(error) {
      profileError = true;
      window.SystemUpdates.open({
        edition: 'no-root',
        recovery: true,
        error: error.message
      });
    }
    if (window.SystemUpdates) {
      window.SystemUpdates.rpc('restoreProfile', { edition: 'no-root' })
        .then(function (restored) {
          if (!restored) {
            legacy();
            return;
          }
          if (!restored.transaction || !restored.version || !restored.profile)
            throw Error('Invalid system update backup');
          var manifest = new XMLHttpRequest();
          manifest.open('GET', 'appinfo.json', true);
          manifest.timeout = 5000;
          manifest.onload = function () {
            try {
              var info = JSON.parse(manifest.responseText);
              if (
                (manifest.status !== 0 && manifest.status !== 200) ||
                info.id !== 'com.gathin.tvhome' ||
                info.version !== restored.version
              )
                throw Error('Backup version does not match installed Home');
              var identity =
                'system:' +
                restored.transaction +
                ':' +
                restored.version +
                ':' +
                (['verifying-rollback', 'rolled-back'].indexOf(
                  restored.phase
                ) >= 0
                  ? 'rollback'
                  : 'install');
              var saved = null;
              try {
                saved = HomeData.load(localStorage);
              } catch (_) {}
              var already =
                saved && localStorage.getItem(restoreMarker) === identity;
              use(already ? saved : restored.profile, !already, identity, true);
              systemRestore = restored;
              window.RootLauncherRendered = false;
              boot();
            } catch (error) {
              systemError(error);
            }
          };
          manifest.onerror = manifest.ontimeout = function () {
            systemError(Error('Installed Home version unavailable'));
          };
          manifest.send();
        })
        .catch(function (error) {
          if (error.unavailable === true) legacy();
          else systemError(error);
        });
    } else legacy();
  })();
});
