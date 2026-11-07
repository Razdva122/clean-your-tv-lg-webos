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
    var panel,
      message,
      buttons,
      visitHint,
      selected = 0,
      busy = false,
      previous,
      rootStatus = null;
    var checkingUpdates = false,
      categories,
      statusGeneration = 0,
      statusTimer,
      windowGeneration = 0,
      refreshTail = Promise.resolve();
    var sourceGroup,
      sourceHint,
      sourceStatus = null,
      sourceUnavailable = false,
      sourceKeys = ['tv', 'youtube'];
    var sources = { tv: true, youtube: false };
    function renderSources() {
      var enabled =
        !busy &&
        !!sourceStatus &&
        sourceStatus.active === true &&
        !!rootStatus &&
        rootStatus.intent &&
        rootStatus.intent.phase === 'active';
      sourceGroup.setAttribute('aria-disabled', String(!enabled));
      sourceHint.textContent = t(
        rootStatus &&
          rootStatus.intent &&
          rootStatus.intent.phase === 'disabled'
          ? 'Available when Change Home is on.'
          : sourceUnavailable
            ? 'Startup sources unavailable. Reopen Settings to check again.'
            : !sourceStatus
              ? 'Checking startup sources…'
              : sourceStatus.active
                ? 'Choose which previous sources open Clean Your TV first.'
                : 'Available when Change Home is on.'
      );
      sourceKeys.forEach(function (key, index) {
        buttons[15 + index].disabled = !enabled;
        buttons[15 + index].setAttribute('aria-checked', String(sources[key]));
      });
      if (
        !enabled &&
        !busy &&
        selected >= 15 &&
        document.activeElement === buttons[selected]
      )
        focus(1);
    }
    function readSources(status) {
      if (
        !status ||
        typeof status.active !== 'boolean' ||
        !status.sources ||
        Object.keys(status.sources).sort().join(',') !== 'tv,youtube' ||
        sourceKeys.some(function (key) {
          return typeof status.sources[key] !== 'boolean';
        })
      )
        throw new Error('Invalid service response');
      sourceStatus = status;
      sources = status.sources;
      renderSources();
    }
    function refreshSources(generation) {
      return control('status', { startup: 'status' })
        .then(function (status) {
          if (
            generation !== statusGeneration ||
            panel.hidden ||
            document.hidden
          )
            return;
          readSources(status);
          if (
            selected >= 15 &&
            buttons[selected].disabled &&
            (!categories || document.activeElement === buttons[selected])
          )
            move(1);
        })
        .catch(function () {
          if (
            generation !== statusGeneration ||
            panel.hidden ||
            document.hidden
          )
            return;
          sourceStatus = null;
          sourceUnavailable = true;
          renderSources();
        });
    }
    function changeSource(index) {
      if (!sourceStatus || buttons[index].disabled || busy) return;
      var next = { tv: sources.tv, youtube: sources.youtube };
      next[sourceKeys[index - 15]] = !next[sourceKeys[index - 15]];
      stopModePoll();
      busy = true;
      buttons.forEach(function (button) {
        button.disabled = true;
      });
      renderSources();
      var generation = statusGeneration,
        error;
      control('enable', { startup: 'configure', sources: next })
        .then(function (status) {
          if (
            generation === statusGeneration &&
            !panel.hidden &&
            !document.hidden
          )
            readSources(status);
        })
        .catch(function (e) {
          error = e.message;
        })
        .then(function () {
          busy = false;
          buttons.forEach(function (button) {
            button.disabled = false;
          });
          refreshMode().then(function () {
            if (!panel.hidden && !buttons[index].disabled) focus(index);
            if (error) message.textContent = t(error);
          });
        });
    }
    function checkUpdates() {
      if (checkingUpdates || !window.RootUpdates || !window.RootUpdates.rpc)
        return;
      checkingUpdates = true;
      function badge(available) {
        buttons[4].setAttribute('data-update-available', String(available));
        if (categories) categories.setUpdateAvailable(available);
        buttons[4].setAttribute(
          'aria-label',
          t(
            available
              ? 'Software updates. Update available.'
              : 'Software updates'
          )
        );
      }
      function legacy() {
        return window.RootUpdates.rpc('check', {}).then(function (offer) {
          if (offer)
            badge(
              offer.canInstall === true || offer.reason === 'missing-rollback'
            );
        });
      }
      var check = window.SystemUpdates
        ? window.SystemUpdates.check('root', legacy).then(function (offer) {
            if (offer) badge(offer.canInstall === true);
          })
        : legacy();
      check
        .catch(function () {})
        .then(function () {
          checkingUpdates = false;
        });
    }

    function request(uri, payload, timeout) {
      return new Promise(function (resolve, reject) {
        var bridge,
          timer,
          done = false;
        function finish(error, reply) {
          if (done) return;
          done = true;
          clearTimeout(timer);
          if (bridge)
            try {
              bridge.cancel();
            } catch (_) {}
          if (error) reject(error);
          else resolve(reply);
        }
        timer = setTimeout(function () {
          finish(
            new Error('Response timed out. Check status before retrying.')
          );
        }, timeout);
        try {
          bridge = new PalmServiceBridge();
          bridge.onservicecallback = function (raw) {
            try {
              finish(null, JSON.parse(raw));
            } catch (_) {
              finish(new Error('Invalid service response'));
            }
          };
          bridge.call(uri, JSON.stringify(payload));
        } catch (error) {
          finish(error);
        }
      });
    }
    function launch(id) {
      return request(
        'luna://com.webos.applicationManager/launch',
        { id: id },
        10000
      ).then(function (r) {
        if (r.returnValue !== true)
          throw new Error('Could not open LG Home. Try again.');
      });
    }
    function leaveHome() {
      var ticket = windowGeneration;
      return launch('com.webos.app.home').then(function () {
        // A newer relaunch/window owner must not be closed by this old reply.
        if (windowGeneration === ticket) window.close();
      });
    }
    var exit = createRootExit(function (method) {
      return request(
        'luna://com.cleanyourtv.root.preview.service/' + method,
        {},
        method === 'restore' ? 620000 : 15000
      );
    }, leaveHome);
    function control(method, payload) {
      var gateEnable =
        method === 'enable' &&
        rootStatus &&
        rootStatus.effective &&
        rootStatus.effective.backend === 'c1-native-gate';
      return request(
        'luna://com.cleanyourtv.root.preview.service/' + method,
        payload || {},
        gateEnable ? 100000 : 30000
      ).then(function (reply) {
        if (
          !reply ||
          reply.returnValue !== true ||
          !reply.result ||
          reply.result.returnValue !== true
        )
          throw new Error(
            (reply && reply.errorText) ||
              'Root control did not confirm success. Check status before retrying.'
          );
        return reply.result.result;
      });
    }
    function stopModePoll() {
      clearTimeout(statusTimer);
      statusTimer = null;
    }
    function invalidateMode() {
      stopModePoll();
      statusGeneration++;
      rootStatus = null;
      sourceStatus = null;
      sourceUnavailable = false;
      renderSources();
      buttons[3].disabled = true;
      buttons[12].hidden = true;
      buttons[12].disabled = true;
    }
    function refreshMode() {
      invalidateMode();
      var generation = statusGeneration,
        remainingPolls = 10;

      message.textContent = t('Checking Home control…');
      function read() {
        if (
          generation !== statusGeneration ||
          panel.hidden ||
          document.hidden ||
          busy
        )
          return;
        return refreshSources(generation)
          .then(function () {
            if (
              generation !== statusGeneration ||
              panel.hidden ||
              document.hidden ||
              busy
            )
              return;
            return control('status');
          })
          .then(function (status) {
            if (
              generation !== statusGeneration ||
              panel.hidden ||
              document.hidden ||
              busy
            )
              return;
            if (
              !status ||
              typeof status !== 'object' ||
              !('intent' in status) ||
              (status.intent !== null &&
                (!status.intent || typeof status.intent.phase !== 'string'))
            )
              throw new Error('Invalid service response');
            rootStatus = status;
            renderSources();
            visitHint.hidden = !!(
              status.effective && status.effective.backend === 'c1-native-gate'
            );
            var phase = status.intent && status.intent.phase,
              active = phase === 'active';
            buttons[3].setAttribute('aria-checked', String(active));
            buttons[3].disabled =
              !!phase && phase !== 'active' && phase !== 'disabled';
            message.textContent = t(
              active
                ? 'Home and return from apps open Clean Your TV.'
                : buttons[3].disabled
                  ? 'Changing Home control…'
                  : 'Home and return from apps open LG Home.'
            );
            if (buttons[3].disabled) {
              if (!remainingPolls--)
                throw new Error(
                  'Response timed out. Check status before retrying.'
                );
              // Do not hold refreshTail (or a completed UI action) during the wait.
              statusTimer = setTimeout(function () {
                if (
                  generation !== statusGeneration ||
                  panel.hidden ||
                  document.hidden ||
                  busy
                )
                  return;
                statusTimer = null;
                refreshTail = refreshTail.then(read, read);
              }, 1000);
            }
            if (
              !panel.hidden &&
              buttons[selected].disabled &&
              (!categories || document.activeElement === buttons[selected])
            )
              move(1);
          })
          .catch(function (e) {
            if (
              generation !== statusGeneration ||
              panel.hidden ||
              document.hidden ||
              busy
            )
              return;
            rootStatus = null;
            sourceStatus = null;
            renderSources();
            buttons[3].disabled = true;
            message.textContent = t(e.message);
            buttons[12].hidden = false;
            buttons[12].disabled = false;
            if (!categories || document.activeElement === buttons[selected])
              focus(12);
          });
      }
      // Serialize lifecycle reads; queued stale generations do no service work.
      refreshTail = refreshTail.then(read, read);
      return refreshTail;
    }
    function resumeMode() {
      if (!panel) return;
      invalidateMode();
      if (!panel.hidden && !document.hidden && !busy) refreshMode();
    }
    document.addEventListener('visibilitychange', function () {
      if (!document.hidden) windowGeneration++;
      resumeMode();
    });
    document.addEventListener('webOSRelaunch', function () {
      windowGeneration++;
      resumeMode();
    });
    function changeMode() {
      if (!rootStatus || buttons[3].disabled || busy) return;
      var active = rootStatus.intent && rootStatus.intent.phase === 'active';
      stopModePoll();
      busy = true;
      buttons.forEach(function (b) {
        b.disabled = true;
      });
      message.textContent = t(
        active ? 'Turning off Home control…' : 'Turning on Home control…'
      );
      (active ? exit() : control('enable'))
        .then(function () {
          busy = false;
          buttons.forEach(function (b) {
            b.disabled = false;
          });
          return refreshMode().then(function () {
            if (!panel.hidden) focus(3);
          });
        })
        .catch(function (e) {
          busy = false;
          buttons.forEach(function (b) {
            b.disabled = false;
          });
          var error = e.message;
          refreshMode().then(function () {
            message.textContent = t(error);
          });
        });
    }
    var order = [3, 1, 12, 15, 16, 9, 8, 10, 11, 14, 5, 4, 0, 7, 6, 2];
    function focus(index) {
      selected = index;
      if (!buttons[selected].disabled && !buttons[selected].hidden)
        buttons[selected].focus();
    }
    function move(direction) {
      var index = order.indexOf(selected);
      for (var count = 0; count < order.length; count++) {
        index = (index + direction + order.length) % order.length;
        if (!buttons[order[index]].disabled && !buttons[order[index]].hidden)
          return focus(order[index]);
      }
    }
    function close() {
      if (busy) return;
      if (window.HomeWallpaperPanel) HomeWallpaperPanel.unmount();
      if (window.HomeThemePanel) HomeThemePanel.unmount();
      invalidateMode();
      panel.hidden = true;
      if (window.ThemeRuntime) window.ThemeRuntime.resume('settings');
      if (previous && previous.focus) previous.focus();
    }
    function activate(index) {
      if (busy || buttons[index].disabled) return;
      if (index === 2) return close();
      if (index === 12) {
        refreshMode();
        focus(1);
        return;
      }
      if (index === 5) {
        if (window.HomeI18n) window.HomeI18n.openLanguagePicker();
        return;
      }
      if (index === 9) {
        if (window.HomeThemePanel) window.HomeThemePanel.open();
        return;
      }
      if (index === 8) {
        if (window.HomeLayoutPanel) window.HomeLayoutPanel.open();
        return;
      }
      if (index === 10) {
        if (window.HomeAppControls) HomeAppControls.toggle();
        return;
      }
      if (index === 14) {
        if (window.HomeInputShelf) HomeInputShelf.togglePreview();
        return;
      }
      if (index === 11) {
        if (window.HomeAppControls) {
          close();
          HomeAppControls.add();
        }
        return;
      }
      if (index === 3) return changeMode();
      if (index >= 15 && index <= 16) return changeSource(index);
      if (index === 7) {
        if (!window.RootAudio) return;
        invalidateMode();
        panel.hidden = true;
        window.RootAudio.open(request, function () {
          panel.hidden = false;
          refreshMode();
          focus(7);
        });
        return;
      }
      if (index === 6) {
        if (!window.RootFirmware) return;
        invalidateMode();
        panel.hidden = true;
        window.RootFirmware.open(request, function () {
          panel.hidden = false;
          refreshMode();
          focus(6);
        });
        return;
      }
      if (index === 4) {
        if (!window.RootUpdates) {
          message.textContent = t(
            'Software updates require the one-time computer setup.'
          );
          return;
        }
        invalidateMode();
        panel.hidden = true;
        window.RootUpdates.open({
          onClose: function () {
            panel.hidden = false;
            focus(4);
            refreshMode();
            checkUpdates();
          }
        });
        return;
      }
      if (index === 0) {
        launch('com.palm.app.settings').catch(function (e) {
          message.textContent = t(e.message);
        });
        return;
      }
      stopModePoll();
      busy = true;
      buttons.forEach(function (b) {
        b.disabled = true;
      });
      message.textContent = t('Opening LG Home…');
      var gateVisit =
        rootStatus &&
        rootStatus.effective &&
        rootStatus.effective.backend === 'c1-native-gate';
      (gateVisit ? exit() : leaveHome())
        .then(function () {
          busy = false;
          close();
        })
        .catch(function (e) {
          busy = false;
          message.textContent = t(e.message);
        })
        .finally(function () {
          buttons.forEach(function (b) {
            b.disabled = false;
          });
          if (!panel.hidden) {
            refreshMode();
            focus(1);
          }
        });
    }
    function build() {
      panel = document.createElement('section');
      panel.className = 'root-settings';
      panel.hidden = true;
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute('aria-label', t('Home settings'));
      var card = document.createElement('div');
      card.className = 'root-settings-card settings-main';
      panel.appendChild(card);
      function text(parent, tag, value, className) {
        var element = document.createElement(tag);
        element.textContent = t(value);
        if (className) element.className = className;
        parent.appendChild(element);
        return element;
      }
      var heading = document.createElement('div');
      heading.className = 'settings-heading';
      card.appendChild(heading);
      text(heading, 'h1', 'Home settings');
      text(heading, 'span', 'Root Edition', 'settings-edition');
      var home = document.createElement('section');
      home.className = 'settings-home';
      card.appendChild(home);
      text(home, 'h2', 'Your Home screen');
      message = text(home, 'p', '', 'settings-status');
      message.setAttribute('aria-live', 'polite');
      var homeActions = document.createElement('div');
      homeActions.className = 'renewal-actions home-routing-actions';
      home.appendChild(homeActions);
      visitHint = text(
        home,
        'p',
        'Open LG Home once, keeping your Home choice.',
        'home-visit-hint'
      );
      visitHint.id = 'rootHomeVisitHint';
      sourceGroup = document.createElement('section');
      sourceGroup.className = 'startup-sources';
      sourceGroup.setAttribute('aria-label', t('Open Clean Your TV first'));
      home.appendChild(sourceGroup);
      text(sourceGroup, 'h3', 'Open Clean Your TV first');
      var sourceActions = document.createElement('div');
      sourceActions.className = 'renewal-actions startup-source-actions';
      sourceGroup.appendChild(sourceActions);
      sourceHint = text(
        sourceGroup,
        'p',
        'Available when Change Home is on.',
        'home-visit-hint'
      );
      sourceHint.id = 'rootStartupHint';
      var more = document.createElement('section');
      more.className = 'settings-section';
      card.appendChild(more);
      var themes = document.createElement('div');
      themes.className = 'renewal-actions settings-layout';
      more.appendChild(themes);
      var layout = document.createElement('div');
      layout.className = 'renewal-actions settings-layout';
      more.appendChild(layout);
      var apps = document.createElement('div');
      apps.className = 'renewal-actions settings-layout';
      more.appendChild(apps);
      var links = document.createElement('div');
      links.className = 'renewal-actions settings-links';
      more.appendChild(links);
      var firmware = document.createElement('div');
      firmware.className = 'renewal-actions settings-firmware';
      more.appendChild(firmware);
      var footer = document.createElement('div');
      footer.className = 'settings-footer';
      card.appendChild(footer);
      var back = document.createElement('div');
      back.className = 'renewal-actions';
      footer.appendChild(back);
      buttons = [];
      [3, 1, 9, 8, 10, 11, 14, 5, 4, 0, 7, 6, 2, 12, 15, 16].forEach(
        function (i) {
          var labels = [
            'TV settings',
            'Open LG Home',
            'Back to Home',
            'Change Home',
            'Software updates',
            'Language',
            'LG firmware updates',
            'HDMI sound',
            'Columns',
            'Themes',
            'Show Add app tile',
            'Add app',
            'Check status',
            'Show inputs on Home',
            'Preview inputs on focus',
            'LG Channels / Live TV',
            'YouTube'
          ];
          var b = document.createElement('button');
          b.textContent = t(labels[i]);
          if (i === 12) {
            b.hidden = true;
            b.disabled = true;
          }
          if (i === 3) {
            b.className = 'home-routing-switch';
            b.setAttribute('role', 'switch');
            b.setAttribute('aria-checked', 'false');
          }
          var target =
            i >= 15
              ? sourceActions
              : i === 10 || i === 11 || i === 14
                ? apps
                : i === 9
                  ? themes
                  : i === 8
                    ? layout
                    : i === 6 || i === 7
                      ? firmware
                      : i === 3 || i === 12 || i === 1
                        ? homeActions
                        : i === 4 || i === 0 || i === 5
                          ? links
                          : back;
          if (i === 10) {
            b.id = 'homeShowAddApp';
            b.className = 'home-routing-switch';
            b.setAttribute('role', 'switch');
            b.setAttribute('aria-checked', 'true');
          }
          if (i === 14) {
            b.id = 'homePreviewInputs';
            b.className = 'home-routing-switch';
            b.setAttribute('role', 'switch');
            b.setAttribute('aria-checked', 'true');
          }
          if (i >= 15) {
            b.className = 'home-routing-switch';
            b.setAttribute('role', 'switch');
            b.setAttribute('aria-checked', String(sources[sourceKeys[i - 15]]));
            b.setAttribute('aria-describedby', 'rootStartupHint');
            b.disabled = true;
          }
          if (i === 11) b.id = 'homeAddApp';
          if (i === 9) {
            b.hidden = true;
            b.disabled = true;
          }
          if (i === 8) b.id = 'homeColumns';
          if (i === 1) {
            b.className = 'home-visit-button';
            b.setAttribute('aria-describedby', 'rootHomeVisitHint');
          }
          b.onclick = function () {
            selected = i;
            activate(i);
          };
          b.onfocus = function () {
            selected = i;
          };
          if (i === 4) {
            var dot = document.createElement('span');
            dot.className = 'settings-update-dot';
            dot.setAttribute('aria-hidden', 'true');
            b.appendChild(dot);
          }
          if (i === 4 || i === 0 || i === 5) {
            var arrow = document.createElement('span');
            arrow.className = 'settings-chevron';
            arrow.setAttribute('aria-hidden', 'true');
            b.appendChild(arrow);
          }
          target.appendChild(b);
          buttons[i] = b;
        }
      );
      themes.id = 'homeThemeHost';
      if (window.HomeThemePanel) HomeThemePanel.mount(themes);
      var appsError = text(apps, 'p', '');
      appsError.id = 'homeAppsError';
      appsError.setAttribute('role', 'alert');
      var wallpapers = document.createElement('div');
      if (window.HomeWallpaperPanel) HomeWallpaperPanel.mount(wallpapers);
      if (window.SettingsCategories)
        categories = SettingsCategories.attach(panel, card, [
          { id: 'home', label: 'Your Home screen', elements: [home] },
          { id: 'appearance', label: 'Appearance', elements: [layout, apps] },
          { id: 'themes', label: 'Themes', elements: [themes] },
          { id: 'wallpapers', label: 'Wallpapers', elements: [wallpapers] },
          { id: 'language', label: 'Language', elements: [buttons[5]] },
          {
            id: 'updates',
            label: 'Software updates',
            elements: [buttons[4], buttons[6]]
          },
          {
            id: 'advanced',
            label: 'Advanced',
            elements: [buttons[0], buttons[7]]
          }
        ]);
      document.body.appendChild(panel);
      document.addEventListener(
        'keydown',
        function (e) {
          if (
            panel.hidden ||
            (window.HomeThemePanel && HomeThemePanel.handlesKey(e))
          )
            return;
          if ([9, 13, 27, 37, 38, 39, 40, 461].indexOf(e.keyCode) === -1)
            return;
          e.preventDefault();
          e.stopImmediatePropagation();
          if (busy) return;
          if (e.keyCode === 461 || e.keyCode === 27) return close();
          if (e.keyCode === 13) {
            if (!e.repeat) activate(selected);
            return;
          }
          move(
            e.keyCode === 37 ||
              e.keyCode === 38 ||
              (e.keyCode === 9 && e.shiftKey)
              ? -1
              : 1
          );
        },
        true
      );
    }
    document.addEventListener('home-layout-change', function (event) {
      if (
        panel &&
        !panel.hidden &&
        buttons[selected].hidden &&
        event.homeColumnsFocus === buttons[selected]
      )
        move(1);
    });
    window.RenewalPanel = {
      isOpen: function () {
        return !!panel && !panel.hidden;
      },
      open: function () {
        if (!panel) build();
        if (!panel.hidden) return;
        if (window.HomeAppControls) HomeAppControls.refresh();
        if (window.HomeInputShelf) HomeInputShelf.refresh();
        if (window.HomeLayoutPanel) HomeLayoutPanel.refreshAvailability();
        if (window.ThemeRuntime) window.ThemeRuntime.suspend('settings');
        previous = document.activeElement;
        message.textContent = t('Checking whether Home control is on…');
        panel.hidden = false;
        selected = 3;
        refreshMode().then(function () {
          if (!categories && !panel.hidden && selected === 3) focus(3);
        });
        if (categories) categories.open();
        checkUpdates();
      }
    };
  })();
});
