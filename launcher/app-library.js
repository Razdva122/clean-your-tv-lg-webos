/* Persistent screen layout, independent of the TV's installed-app inventory. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.AppLibrary = factory();
})(this, function () {
  'use strict';
  var KEY = 'tvhome.layout';
  var internal = [
    'com.gathin.tvhome',
    'com.local.nativehome',
    'com.cleanyourtv.root.preview',
    'com.cleanyourtv.updater'
  ];
  var pickerExcluded = [
    'com.sdk.ares.hostedapp',
    'com.cleanyourtv.root.updater'
  ];
  function unique(ids) {
    return ids.filter(function (id, i) {
      return (
        typeof id === 'string' &&
        ids.indexOf(id) === i &&
        internal.indexOf(id) < 0
      );
    });
  }
  function clean(apps) {
    var seen = Object.create(null);
    return apps
      .filter(function (a) {
        // Apply the same visibility rule to raw, service-normalized and saved catalogs.
        // LG may mark its installed tuner hidden; never synthesize a missing tuner.
        if (
          !a ||
          typeof a.id !== 'string' ||
          !a.id ||
          typeof a.title !== 'string' ||
          (a.id !== 'com.webos.app.livetv' &&
            (a.hidden || a.visible === false)) ||
          internal.indexOf(a.id) >= 0 ||
          seen[a.id]
        )
          return false;
        seen[a.id] = true;
        return true;
      })
      .slice(0, 200)
      .map(function (a) {
        return {
          id: a.id,
          title: a.title.slice(0, 256),
          icon: typeof a.icon === 'string' ? a.icon : '',
          iconColor: a.iconColor || a.bgColor || ''
        };
      });
  }
  function confirmed(ids, apps) {
    return (
      Array.isArray(ids) &&
      ids.length <= 300 &&
      ids.every(function (id, i) {
        return (
          typeof id === 'string' &&
          id.length > 0 &&
          id.length <= 256 &&
          ids.indexOf(id) === i
        );
      }) &&
      apps.every(function (a) {
        return a && ids.indexOf(a.id) >= 0;
      })
    );
  }
  function inputId(id) {
    return /^input:[A-Za-z0-9_.-]{1,250}$/.test(id);
  }
  function create(storage, inventory, config, readInputs) {
    var catalog = clean(inventory),
      hidden = unique(config.hiddenApps || []),
      ids,
      saved,
      showAddApp = true,
      catalogConfirmed = false;
    try {
      saved = JSON.parse(storage.getItem(KEY));
      if (
        !saved ||
        saved.version !== 1 ||
        !Array.isArray(saved.ids) ||
        !Array.isArray(saved.hidden) ||
        !Array.isArray(saved.catalog)
      )
        saved = null;
    } catch (_) {
      saved = null;
    }
    if (saved) {
      showAddApp = saved.showAddApp !== false;
      catalogConfirmed = saved.catalogConfirmed === true;
      catalog = clean(
        catalogConfirmed ? saved.catalog : catalog.concat(saved.catalog)
      );
      hidden = unique(saved.hidden);
      ids = unique(saved.ids);
    } else {
      var legacy;
      try {
        legacy = JSON.parse(storage.getItem('tvhome.order'));
      } catch (_) {}
      var first =
        legacy &&
        legacy.dock === (config.dockApps || []).join(',') &&
        Array.isArray(legacy.ids)
          ? legacy.ids
          : (config.dockApps || []).slice(0, config.columns || 4);
      ids = unique(
        first.concat(
          catalog
            .slice()
            .sort(function (a, b) {
              return a.title.localeCompare(b.title);
            })
            .map(function (a) {
              return a.id;
            })
        )
      );
    }
    function inputTiles() {
      return (readInputs ? readInputs() : [])
        .filter(function (input) {
          return input.source && inputId('input:' + input.appId);
        })
        .map(function (input) {
          return {
            id: 'input:' + input.appId,
            title: input.label,
            input: input
          };
        });
    }
    function find(items, id) {
      for (var i = 0; i < items.length; i++) {
        if (items[i].id === id) return items[i];
      }
    }
    function visible() {
      var items = catalog.concat(inputTiles());
      return ids
        .map(function (id) {
          return find(items, id);
        })
        .filter(function (a) {
          return a && hidden.indexOf(a.id) < 0;
        });
    }
    function save(nextIds, nextHidden, nextShowAddApp) {
      nextIds = unique(nextIds);
      nextHidden = unique(nextHidden);
      // An EIM snapshot can be unavailable during a layout edit. Retain any
      // pinned input that was not rendered and therefore could not be edited.
      ids.forEach(function (id, index) {
        if (
          inputId(id) &&
          nextIds.indexOf(id) < 0 &&
          nextHidden.indexOf(id) < 0
        )
          nextIds.splice(index, 0, id);
      });
      if (
        (nextIds.length > 200 && nextIds.some(inputId)) ||
        (nextHidden.length > 200 && nextHidden.some(inputId))
      )
        throw Error('invalid-layout-size');
      var state = {
        version: 1,
        ids: nextIds,
        hidden: nextHidden,
        catalog: catalog,
        showAddApp: nextShowAddApp === undefined ? showAddApp : nextShowAddApp
      };
      if (catalogConfirmed) state.catalogConfirmed = true;
      storage.setItem(KEY, JSON.stringify(state)); // Commit memory only after durable storage succeeds.
      ids = state.ids;
      hidden = state.hidden;
      showAddApp = state.showAddApp;
    }
    return {
      visible: visible,
      firstInput: function () {
        for (var i = 0; i < ids.length; i++) {
          var id = ids[i];
          if (hidden.indexOf(id) >= 0) continue;
          if (inputId(id)) return id;
          if (find(catalog, id)) return null;
        }
        return null;
      },
      input: function (id) {
        var tile = find(inputTiles(), id);
        return tile && tile.input;
      },
      showAddApp: function () {
        return showAddApp;
      },
      setShowAddApp: function (value) {
        if (typeof value !== 'boolean')
          throw Error('invalid-add-app-visibility');
        save(ids, hidden, value);
      },
      hidden: function () {
        return hidden.slice();
      },
      available: function () {
        var shown = visible().map(function (a) {
          return a.id;
        });
        return catalog
          .concat(inputTiles())
          .filter(function (a) {
            return shown.indexOf(a.id) < 0 && pickerExcluded.indexOf(a.id) < 0;
          })
          .sort(function (a, b) {
            return a.title.localeCompare(b.title);
          });
      },
      save: save,
      add: function (id) {
        if (!find(catalog.concat(inputTiles()), id))
          throw Error('app-unavailable');
        save(
          visible()
            .map(function (a) {
              return a.id;
            })
            .concat(id),
          hidden.filter(function (h) {
            return h !== id;
          })
        );
      },
      refresh: function (apps, installedIds) {
        // TV queries can return only part of the installed inventory. Absence
        // from a response must not erase saved tiles or apps hidden from Home.
        // Preserve packaged/embedded icons, but refresh expiring remote URLs.
        var previous = catalog,
          previousConfirmed = catalogConfirmed;
        var embedded =
          /^data:image\/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}$/;
        var updates = clean(apps).map(function (a) {
          var old = previous.filter(function (b) {
            return b.id === a.id;
          })[0];
          if (
            old &&
            old.icon &&
            (!a.icon ||
              (!/^https?:\/\//i.test(old.icon) && !embedded.test(a.icon)))
          )
            a.icon = old.icon;
          return a;
        });
        var authoritative = confirmed(installedIds, apps);
        catalog = clean(
          updates.concat(previous).filter(function (a) {
            return !authoritative || installedIds.indexOf(a.id) >= 0;
          })
        );
        if (authoritative) {
          catalogConfirmed = true;
          try {
            save(
              ids.filter(function (id) {
                return inputId(id) || installedIds.indexOf(id) >= 0;
              }),
              hidden.filter(function (id) {
                return inputId(id) || installedIds.indexOf(id) >= 0;
              })
            );
          } catch (error) {
            catalog = previous;
            catalogConfirmed = previousConfirmed;
            throw error;
          }
        }
      }
    };
  }
  function installed(callback, priorityIds) {
    var bridge,
      timer,
      done = false,
      generation = 0;
    var root = !!document.querySelector('script[src="root-settings.js"]');
    function cancel() {
      clearTimeout(timer);
      if (bridge)
        try {
          bridge.cancel();
        } catch (_) {}
    }
    function finish(apps, installedIds) {
      if (done) return;
      done = true;
      cancel();
      callback(apps, installedIds);
    }
    function read(fallback) {
      var request = ++generation;
      cancel();
      function failed() {
        if (done || request !== generation) return;
        if (!root && !fallback) read(true);
        else finish(null);
      }
      timer = setTimeout(failed, fallback ? 6000 : 12000);
      try {
        bridge = new PalmServiceBridge();
        bridge.onservicecallback = function (raw) {
          if (done || request !== generation) return;
          var apps = null;
          try {
            var result = JSON.parse(raw);
            if (
              result &&
              result.returnValue === true &&
              Array.isArray(result.apps)
            )
              apps = clean(result.apps);
          } catch (_) {}
          if (apps !== null)
            finish(
              apps,
              confirmed(result.installedIds, result.apps)
                ? result.installedIds
                : undefined
            );
          else failed();
        };
        // A cross-package LS2 refusal need not block the existing native reader.
        var service = root
          ? 'com.cleanyourtv.root.preview.service'
          : fallback
            ? 'com.gathin.tvhome.renewal'
            : 'com.local.nativehome.service';
        bridge.call(
          'luna://' + service + '/listApps',
          root && priorityIds
            ? JSON.stringify({ priorityIds: priorityIds })
            : '{}'
        );
      } catch (_) {
        failed();
      }
    }
    read(false);
  }
  return { create: create, installed: installed, key: KEY };
});
