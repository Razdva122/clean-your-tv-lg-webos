(window.HomeI18n && window.HomeI18n.ready
  ? window.HomeI18n.ready
  : function (callback) {
      callback();
    })(function () {
  (function () {
    'use strict';
    function t(source, params) {
      if (window.HomeI18n) return window.HomeI18n.t(source, params);
      return String(source).replace(/\{(\w+)\}/g, function (_, key) {
        return params && params[key] !== undefined
          ? params[key]
          : '{' + key + '}';
      });
    }
    var data = window.RootProfileData,
      failed = false,
      booted = false,
      systemRestore = false;
    var marker = 'tvhome.root.restored.v1';
    function recovery(error) {
      failed = true;
      window.RootUpdates.open({
        recovery: true,
        error:
          t('Launcher profile could not be restored.') + ' ' + t(error.message)
      });
    }
    function save(profile) {
      profile = data.validate(profile);
      var raw = JSON.stringify(profile);
      localStorage.setItem(data.key, raw);
      if (localStorage.getItem(data.key) !== raw)
        throw Error('Local profile readback failed');
      return profile;
    }
    function icon(url) {
      if (
        typeof url === 'string' &&
        /^data:image\/(png|jpeg|webp);base64,/.test(url)
      )
        return Promise.resolve(url);
      return new Promise(function (resolve, reject) {
        if (
          typeof url !== 'string' ||
          !url ||
          url.indexOf('..') >= 0 ||
          /[?#\\]/.test(url) ||
          /^([a-z]+:|\/)/i.test(url)
        )
          return reject(Error('Only packaged icons can be preserved'));
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'blob';
        xhr.timeout = 5000;
        xhr.onload = function () {
          if (
            (xhr.status !== 0 && xhr.status !== 200) ||
            !xhr.response ||
            xhr.response.size > 256 * 1024
          )
            return reject(Error('Packaged icon is missing or too large'));
          var reader = new FileReader();
          reader.onload = function () {
            resolve(reader.result);
          };
          reader.onerror = function () {
            reject(Error('Could not read icon'));
          };
          reader.readAsDataURL(xhr.response);
        };
        xhr.onerror = xhr.ontimeout = function () {
          reject(Error('Could not read packaged icon'));
        };
        xhr.send();
      });
    }
    window.RootProfile = {
      capture: function (options) {
        if (failed)
          return Promise.reject(
            Error('Stored profile is unreadable. Open Recovery.')
          );
        return Promise.resolve().then(function () {
          var snapshot = {
            schema: 1,
            inventory: JSON.parse(JSON.stringify(window.TV_APPS)),
            config: JSON.parse(JSON.stringify(window.CONFIG)),
            settings: {}
          };
          (options && options.system
            ? [
                'tvhome.order',
                'tvhome.language',
                'tvhome.layout',
                'tvhome.name'
              ]
            : ['tvhome.order', 'tvhome.language']
          ).forEach(function (key) {
            var value = localStorage.getItem(key);
            if (value !== null) snapshot.settings[key] = value;
          });
          return Promise.all(
            snapshot.inventory.apps.map(function (app) {
              return icon(app.icon).then(function (embedded) {
                app.icon = embedded;
                // Discovery can supply empty/noncanonical cosmetic metadata;
                // omit it at capture, keeping stored-profile validation strict.
                if (
                  typeof app.iconColor !== 'string' ||
                  !/^#[0-9a-fA-F]{6}$/.test(app.iconColor)
                )
                  delete app.iconColor;
              });
            })
          ).then(function () {
            return save(snapshot);
          });
        });
      }
    };
    function boot(restored) {
      if (booted) return;
      booted = true;
      window.RootLauncherRendered = false;
      var script = document.createElement('script');
      script.src = 'app.js';
      script.onerror = function () {
        recovery(Error('Launcher could not start'));
      };
      script.onload = function () {
        function rendered() {
          if (
            !restored ||
            ['verifying', 'verifying-rollback'].indexOf(restored.phase) < 0
          )
            return;
          try {
            if (window.RootLauncherRendered !== true)
              throw Error('Launcher did not finish rendering');
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
              throw Error(
                'Restored launcher tiles do not match the saved profile'
              );
            var health = {
              transaction: restored.transaction,
              version: window.ROOT_VERSION
            };
            if (systemRestore) {
              window.SystemUpdates.rpc('healthy', {
                edition: 'root',
                transaction: health.transaction,
                version: health.version
              }).catch(recovery);
              return;
            }
            window.RootUpdates.rpc('ready', health)
              .then(function () {
                if (restored.phase === 'verifying')
                  return window.RootUpdates.rpc('confirm', health);
              })
              .catch(recovery);
          } catch (error) {
            recovery(error);
          }
        }
        if (window.HomeUIReady) window.HomeUIReady.then(rendered, recovery);
        else rendered();
      };
      document.body.appendChild(script);
    }
    var saved = null,
      localError = null;
    try {
      var raw = localStorage.getItem(data.key);
      if (raw !== null) saved = data.validate(JSON.parse(raw));
    } catch (error) {
      localError = error;
    }
    var pendingTransaction = null,
      pendingAttempts = 0,
      systemPermissionRefused = false;
    function waitForSystemProfile() {
      if (pendingAttempts++ >= 120)
        throw Error('System update profile readiness timed out');
      return new Promise(function (resolve) {
        setTimeout(resolve, 1000);
      }).then(systemProfile);
    }
    function systemProfile() {
      return window.SystemUpdates.rpc('restoreProfile', {
        edition: 'root'
      })
        .then(function (value) {
          if (value) {
            if (pendingTransaction && value.transaction !== pendingTransaction)
              throw Error('System update transaction changed during startup');
            return value;
          }
          // CARDs can start before the worker enters verification. Do not consume
          // startup with a generic/legacy profile while this System update owns it.
          return window.SystemUpdates.rpc('status', {}).then(function (state) {
            if (
              pendingTransaction &&
              (!state ||
                state.edition !== 'root' ||
                state.id !== pendingTransaction)
            )
              throw Error('System update transaction changed during startup');
            if (!state || state.edition !== 'root' || state.phase === 'aborted')
              return null;
            if (state.phase === 'recovery-required')
              throw Error('System update requires recovery');
            if (
              [
                'preparing',
                'downloading',
                'backed-up',
                'suspending',
                'installing',
                'verifying',
                'rolling-back',
                'verifying-rollback',
                'complete',
                'rolled-back'
              ].indexOf(state.phase) < 0
            )
              return null;
            pendingTransaction = state.id;
            return waitForSystemProfile();
          });
        })
        .catch(function (error) {
          // Package replacement can temporarily reset legacy registrations before
          // the worker repairs them. Wait for an ordinary validated read; never
          // accept a profile or send health through the permission refusal.
          if (
            error.message !==
            'Legacy updater permissions changed; computer recovery required'
          )
            throw error;
          systemPermissionRefused = true;
          return waitForSystemProfile();
        });
    }
    function restore() {
      if (!window.SystemUpdates)
        return window.RootUpdates.rpc('restoreProfile', {});
      return systemProfile().then(
        function (value) {
          if (value) {
            systemRestore = true;
            return value;
          }
          return window.RootUpdates.rpc('restoreProfile', {});
        },
        function (error) {
          if (
            !pendingTransaction &&
            !systemPermissionRefused &&
            error.unavailable === true
          )
            return window.RootUpdates.rpc('restoreProfile', {});
          throw error;
        }
      );
    }
    restore()
      .then(function (restored) {
        if (restored) {
          if (!restored.transaction || restored.version !== window.ROOT_VERSION)
            throw Error('Backup version does not match this Root package');
          var identity =
            (systemRestore ? 'system:' : '') +
            restored.transaction +
            ':' +
            restored.version +
            (systemRestore
              ? ':' +
                (['verifying-rollback', 'rolled-back'].indexOf(
                  restored.phase
                ) >= 0
                  ? 'rollback'
                  : 'install')
              : '');
          var profile = data.validate(restored.profile);
          var alreadyRestored =
            saved &&
            !localError &&
            (restored.phase === 'aborted' ||
              localStorage.getItem(marker) === identity);
          if (alreadyRestored) profile = saved;
          else {
            var previousLanguage = window.HomeI18n
              ? window.HomeI18n.preference()
              : null;
            save(profile);
            // System snapshots omit appearance; keep app-origin preferences for normal
            // startup validation. Legacy backup restores retain their Classic reset.
            if (!systemRestore) {
              localStorage.removeItem('tvhome.columns.v1');
              localStorage.removeItem('tvhome.theme.choice.v1');
              localStorage.removeItem('tvhome.theme.trial.v1');
              localStorage.removeItem('tvhome.wallpaper.preferences.v1');
            }
            if (profile.settings['tvhome.order'] === undefined)
              localStorage.removeItem('tvhome.order');
            else
              localStorage.setItem(
                'tvhome.order',
                profile.settings['tvhome.order']
              );
            if (systemRestore) {
              if (profile.settings['tvhome.layout'] === undefined)
                localStorage.removeItem('tvhome.layout');
              else
                localStorage.setItem(
                  'tvhome.layout',
                  profile.settings['tvhome.layout']
                );
            }
            if (profile.settings['tvhome.language'] === undefined)
              localStorage.removeItem('tvhome.language');
            else
              localStorage.setItem(
                'tvhome.language',
                profile.settings['tvhome.language']
              );
            if (profile.settings['tvhome.name'] !== undefined)
              localStorage.setItem(
                'tvhome.name',
                profile.settings['tvhome.name']
              );
            localStorage.setItem(marker, identity);
            if (window.HomeI18n) {
              if (
                previousLanguage !== window.HomeI18n.preference() &&
                window.location &&
                window.location.reload
              ) {
                window.location.reload();
                return;
              }
              window.HomeI18n.refresh();
            }
          }
          window.TV_APPS = profile.inventory;
          window.CONFIG = profile.config;
        } else {
          if (localError) throw localError;
          if (saved) {
            window.TV_APPS = saved.inventory;
            window.CONFIG = saved.config;
          }
        }
        boot(restored);
      })
      .catch(function (error) {
        // Existing personalized packages remain usable before one-time updater provisioning.
        // An empty generic package cannot establish that a missing backup is harmless.
        if (
          !pendingTransaction &&
          !systemPermissionRefused &&
          !localError &&
          !booted &&
          error.unavailable === true &&
          (saved || (window.TV_APPS && window.TV_APPS.apps.length))
        ) {
          if (saved) {
            window.TV_APPS = saved.inventory;
            window.CONFIG = saved.config;
          }
          boot(null);
        } else recovery(error);
      });
  })();
});
