(function (root) {
  'use strict';
  var doc = root.document,
    marker = 'cytv.home.post-install',
    service = 'luna://org.webosbrew.hbchannel.service/exec',
    command =
      '/usr/bin/node /media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller/bootstrap.js ',
    labels = {
      homePromotion: 'Turn off sponsored tiles',
      contentRecommendation: 'Turn off content recommendations',
      screenSaverAd: 'Turn off screen saver ads',
      livePromotion: 'Turn off promotions while watching',
      promotionStreamer: 'Turn off LG promotional streams',
      webOSPromotionVideo: 'Turn off webOS promotional video',
      livePlus: 'Turn off Live Plus',
      adCookie: 'Turn off advertising cookies',
      lmt: 'Limit ad tracking',
      aiNudge: 'Turn off Smart Tips',
      sportsAlarm: 'Turn off sports notifications'
    },
    outcomes = {
      already: 'Already in the requested state',
      verified: 'Successfully applied and verified',
      unavailable: 'This setting is unavailable on this TV.',
      'write-rejected':
        'LG rejected this change. Check the setting in LG Settings.',
      'write-unavailable': 'LG Settings could not be reached. Check again.',
      'verify-unavailable':
        'The change could not be verified. Check LG Settings.',
      'verify-mismatch': 'LG kept a different value. Check LG Settings.',
      'journal-failed':
        'The original value could not be saved. The setting was skipped.',
      restored: 'Restored and verified',
      'restore-already': 'Already at the saved original value',
      'restore-unavailable': 'This setting is unavailable on this TV.',
      'restore-unverified':
        'The change could not be verified. Check LG Settings.',
      'restore-rejected':
        'The TV rejected the request to restore this setting.',
      'restore-failed': 'Could not restore the setting'
    },
    panel,
    card,
    previous,
    view,
    busy = false,
    opened,
    settings,
    selected = {},
    results = {},
    themes = [],
    previews = [],
    notice = '';
  function t(key) {
    return root.HomeI18n.t(key);
  }
  function node(parent, type, value) {
    var result = doc.createElement(type);
    if (value) result.textContent = t(value);
    parent.appendChild(result);
    return result;
  }
  function button(parent, value, action) {
    var control = node(parent, 'button', value);
    control.type = 'button';
    control.onclick = action;
    return control;
  }
  function available() {
    try {
      return /^[a-f0-9]{32}$/.test(root.localStorage.getItem(marker) || '');
    } catch (_) {
      return !!opened;
    }
  }
  function request(action, keys) {
    if (root.CYTVDebloatPage !== true)
      return Promise.reject(new Error('Open the installer settings'));
    var settingsAction = action === 'debloat' || action === 'debloat-restore';
    if (
      (!settingsAction && action !== 'debloat-status') ||
      (settingsAction &&
        (!keys.length ||
          keys.some(function (key) {
            return !Object.prototype.hasOwnProperty.call(labels, key);
          })))
    )
      return Promise.reject(new Error('Invalid LG settings selection'));
    return new Promise(function (resolve, reject) {
      var bridge = new root.PalmServiceBridge(),
        timer = setTimeout(function () {
          finish();
        }, 125000),
        done = false;
      function finish(value) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        try {
          bridge.cancel();
        } catch (_) {}
        if (value && value.state === 'debloat') resolve(value);
        else reject(new Error('LG settings unavailable'));
      }
      bridge.onservicecallback = function (raw) {
        try {
          var reply = JSON.parse(raw);
          finish(
            reply.returnValue === true &&
              typeof reply.stdoutString === 'string' &&
              reply.stdoutString.length <= 16384 &&
              JSON.parse(reply.stdoutString)
          );
        } catch (_) {
          finish();
        }
      };
      try {
        bridge.call(
          service,
          JSON.stringify({
            command:
              command +
              action +
              (settingsAction ? ' --settings ' + keys.join(',') : '')
          })
        );
      } catch (_) {
        finish();
      }
    });
  }
  function launchApplication(destination, guideUrl) {
    if (busy) return;
    var returnHome = destination === 'home';
    busy = true;
    notice = '';
    render();
    function finish() {
      if (done) return;
      done = true;
      clearTimeout(timeout);
      if (bridge) {
        try {
          bridge.cancel();
        } catch (_) {}
      }
      busy = false;
      if (!accepted)
        notice =
          guideUrl ||
          'Homebrew could not access LG Settings. Check status and try again.';
      render();
    }
    var bridge,
      done = false,
      accepted = false,
      timeout = setTimeout(finish, 8000);
    try {
      bridge = new root.PalmServiceBridge();
      bridge.onservicecallback = function (raw) {
        try {
          accepted = JSON.parse(raw).returnValue === true;
        } catch (_) {}
        finish();
      };
      bridge.call(
        'luna://com.webos.applicationManager/launch',
        JSON.stringify(
          returnHome
            ? { id: 'com.cleanyourtv.root.preview' }
            : guideUrl
              ? { id: 'com.webos.app.browser', params: { target: guideUrl } }
              : {
                  id: 'io.github.razdva122.cytvinstaller',
                  params: { cytvDebloat: true }
                }
        )
      );
    } catch (_) {
      finish();
    }
  }
  function focusFirst() {
    var first = card.querySelector('button:not(:disabled)');
    if (first) first.focus();
  }
  function close() {
    panel.hidden = true;
    if (root.ThemeRuntime) root.ThemeRuntime.resume('post-install');
    if (previous && previous.focus) previous.focus();
  }
  function main() {
    view = 'main';
    notice = '';
    render();
  }
  function showThemes() {
    view = 'themes';
    notice = '';
    themes = [];
    busy = true;
    render();
    var catalog = root.ThemeData
      ? root.ThemeData.request('theme-catalog.json', 65536, true)
          .then(function (bytes) {
            var value = JSON.parse(root.ThemeData.decode(bytes));
            return Array.isArray(value.themes) ? value.themes : [];
          })
          .catch(function () {
            return [];
          })
      : Promise.resolve([]);
    Promise.all([root.ThemeManager.list(), catalog])
      .then(function (result) {
        previews = result[1];
        themes = result[0].filter(function (item) {
          return item.builtin === true && !item.unavailable;
        });
      })
      .catch(function () {
        notice = 'The themes could not be loaded. Try opening Themes again.';
      })
      .then(function () {
        busy = false;
        render();
      });
  }
  function selectTheme(item) {
    if (busy) return;
    busy = true;
    notice = '';
    render();
    root.ThemeManager.selectInstalled(item)
      .then(
        function () {
          notice = 'Theme applied';
        },
        function () {
          notice = 'The theme could not be applied. Select it again.';
        }
      )
      .then(function () {
        busy = false;
        render();
        var current = card.querySelector('[aria-pressed="true"]');
        if (current) current.focus();
      });
  }
  function readSettings() {
    view = 'debloat';
    notice = '';
    settings = null;
    selected = {};
    results = {};
    changeSettings('debloat-status', []);
  }
  function changeSettings(action, keys) {
    if (busy) return;
    busy = true;
    notice = '';
    render();
    request(action, keys)
      .then(
        function (reply) {
          if (reply.settings)
            settings = Object.assign({}, settings, reply.settings);
          results = reply.results || {};
          selected = {};
          if (reply.code === 'busy')
            notice =
              'Clean Your TV is busy. Finish the other operation and check again.';
          else if (reply.code === 'not_available')
            notice =
              'Homebrew could not access LG Settings. Check status and try again.';
          else if (reply.code === 'journal_failed')
            notice =
              'The original value could not be saved. The setting was skipped.';
        },
        function () {
          notice =
            'Homebrew could not access LG Settings. Check status and try again.';
        }
      )
      .then(function () {
        busy = false;
        render();
      });
  }
  function renderDebloat() {
    var status = node(
      card,
      'p',
      notice ||
        (busy
          ? 'Checking LG settings…'
          : 'Select which LG ads and recommendations to change.')
    );
    status.setAttribute('role', 'status');
    var rows = node(card, 'div');
    rows.className = 'cytv-setup-settings';
    var actions = node(card, 'div');
    actions.className = 'renewal-actions';
    var apply = button(actions, 'Apply selected settings', function () {
      changeSettings('debloat', Object.keys(selected));
    });
    apply.id = 'cytvDebloatApply';
    var restore = button(actions, 'Restore selected settings', function () {
      changeSettings(
        'debloat-restore',
        Object.keys(selected).filter(function (key) {
          return settings[key].saved === true;
        })
      );
    });
    function update() {
      var keys = Object.keys(selected);
      apply.disabled =
        busy ||
        !keys.length ||
        keys.some(function (key) {
          return settings[key].value !== 'on' && settings[key].value !== 'off';
        });
      restore.disabled =
        busy ||
        !keys.some(function (key) {
          return settings[key].saved === true;
        });
    }
    if (settings)
      Object.keys(labels).forEach(function (key) {
        var option = settings[key];
        if (!option) return;
        var row = node(rows, 'div'),
          control = button(row, labels[key], function () {
            if (selected[key]) delete selected[key];
            else selected[key] = true;
            control.setAttribute('aria-checked', String(!!selected[key]));
            update();
          }),
          detail = Object.prototype.hasOwnProperty.call(outcomes, results[key])
            ? outcomes[results[key]]
            : option.value === 'on'
              ? 'On'
              : option.value === 'off'
                ? 'Off'
                : 'This setting is unavailable on this TV.';
        control.id = 'cytvDebloat-' + key;
        control.setAttribute('role', 'checkbox');
        control.setAttribute('aria-checked', String(!!selected[key]));
        control.disabled =
          busy ||
          (option.value !== 'on' &&
            option.value !== 'off' &&
            option.saved !== true);
        node(row, 'span', detail);
        if (
          (results[key] === 'write-rejected' ||
            results[key] === 'restore-rejected') &&
          /^[a-z-]+$/.test(option.guide || '')
        ) {
          var file =
            root.HomeI18n.language() === 'ru' ? 'PRIVACY.ru.md' : 'PRIVACY.md';
          var guideUrl =
            'https://github.com/Razdva122/clean-your-tv-lg-webos/blob/release/next/docs/' +
            file +
            '#' +
            option.guide;
          button(row, 'Open privacy guide', function () {
            launchApplication('guide', guideUrl);
          }).disabled = busy;
        }
      });
    update();
    button(actions, 'Check status', readSettings).disabled = busy;
    button(actions, 'Back', function () {
      launchApplication('home');
    }).disabled = busy;
  }
  function render() {
    card.textContent = '';
    if (view === 'debloat') {
      node(card, 'h1', 'Adjust LG settings');
      renderDebloat();
    } else {
      node(card, 'h1', view === 'themes' ? 'Themes' : 'Set up your TV');
      var status = node(
        card,
        'p',
        notice ||
          (view === 'main'
            ? 'Choose a theme and adjust LG settings whenever you like.'
            : busy
              ? 'Loading themes…'
              : 'Choose a theme for your Home.')
      );
      status.setAttribute('role', 'status');
      var actions = node(card, 'div');
      actions.className = 'renewal-actions';
      if (view === 'themes') {
        var choices = node(card, 'div');
        choices.className = 'cytv-setup-themes';
        card.insertBefore(choices, actions);
        themes.forEach(function (item) {
          var choice = button(choices, item.title, function () {
            selectTheme(item);
          });
          choice.setAttribute(
            'aria-pressed',
            String(root.ThemeManager.current().id === item.id)
          );
          var preview = previews.find(function (entry) {
            return (
              entry.id === item.id &&
              entry.builtin === true &&
              typeof entry.preview === 'string' &&
              /^(?:theme-catalog|themes)\/[\w/.-]+\.(?:png|jpg)$/.test(
                entry.preview
              ) &&
              entry.preview.indexOf('..') === -1
            );
          });
          if (preview) {
            var image = doc.createElement('img');
            image.alt = '';
            image.src = preview.preview;
            image.onerror = function () {
              image.hidden = true;
            };
            choice.insertBefore(image, choice.firstChild);
          }
          choice.disabled = busy;
        });
        button(actions, 'Back', main).disabled = busy;
      } else {
        actions.className += ' cytv-setup-main-actions';
        button(actions, 'Themes', showThemes);
        button(actions, 'Adjust LG settings', function () {
          launchApplication('debloat');
        }).disabled = busy;
        button(actions, 'Open Home', close);
      }
    }
    focusFirst();
  }
  function keydown(event) {
    if (
      !panel ||
      panel.hidden ||
      [9, 13, 27, 37, 38, 39, 40, 461].indexOf(event.keyCode) < 0
    )
      return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if (busy) return;
    if (event.keyCode === 27 || event.keyCode === 461) {
      if (view === 'debloat') launchApplication('home');
      else if (view === 'main') close();
      else main();
    } else if (event.keyCode === 13) {
      if (!event.repeat && card.contains(doc.activeElement))
        doc.activeElement.click();
    } else {
      var buttons = Array.prototype.slice.call(
        card.querySelectorAll('button:not(:disabled)')
      );
      var current = buttons.indexOf(doc.activeElement),
        direction =
          event.keyCode === 37 ||
          event.keyCode === 38 ||
          (event.keyCode === 9 && event.shiftKey)
            ? -1
            : 1;
      if (buttons.length)
        buttons[
          (current + direction + buttons.length) % buttons.length
        ].focus();
    }
  }
  function open(debloat) {
    if (!panel) {
      panel = node(doc.body, 'section');
      panel.id = 'cytvPostInstall';
      panel.className = 'root-settings cytv-post-install';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute(
        'aria-label',
        t(debloat ? 'Adjust LG settings' : 'Set up your TV')
      );
      card = node(panel, 'div');
      card.className = 'root-settings-card';
      doc.addEventListener('keydown', keydown, true);
    }
    if (panel.hidden || !view) previous = doc.activeElement;
    panel.hidden = false;
    if (root.ThemeRuntime) root.ThemeRuntime.suspend('post-install');
    if (debloat) readSettings();
    else main();
  }
  function launch(event) {
    var id;
    try {
      var raw = event
        ? event.detail
        : root.PalmSystem && root.PalmSystem.launchParams;
      if (raw && raw.params) raw = raw.params;
      var params =
        typeof raw === 'string' && raw.length <= 4096 ? JSON.parse(raw) : raw;
      if (params && params.params) params = params.params;
      id = params && params.cytvPostInstall;
    } catch (_) {
      return;
    }
    if (typeof id !== 'string' || !/^[a-f0-9]{32}$/.test(id) || id === opened)
      return;
    opened = id;
    try {
      if (root.localStorage.getItem(marker) === id) return;
      root.localStorage.setItem(marker, id);
    } catch (_) {}
    open();
  }
  root.RootPostInstall = {
    available: available,
    isOpen: function () {
      return !!panel && !panel.hidden;
    },
    open: function () {
      if (available() && root.CYTVDebloatPage !== true) open(false);
    },
    openDebloat: function () {
      if (root.CYTVDebloatPage === true) open(true);
    }
  };
  root.HomeI18n.ready(function () {
    if (root.CYTVDebloatPage === true) {
      root.RootPostInstall.openDebloat();
      return;
    }
    doc.addEventListener('webOSRelaunch', launch);
    launch();
  });
})(window);
