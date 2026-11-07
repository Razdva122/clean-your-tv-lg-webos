(window.HomeI18n && window.HomeI18n.ready
  ? window.HomeI18n.ready
  : function (callback) {
      callback();
    })(function () {
  (function () {
    'use strict';
    var URI = 'luna://com.cleanyourtv.system.updater.service/';
    var panel,
      reading,
      versions,
      message,
      notes,
      notesHeading,
      editionLabel,
      buttons;
    var options = {},
      offer = null,
      transaction = null,
      previous,
      timer,
      generation = 0;
    var busy = false,
      polling = false,
      recovery = false,
      selected = 0,
      errorText = '',
      stickyError = '',
      checkError = '';
    var terminal = ['complete', 'rolled-back', 'aborted'];
    function t(source, params) {
      return window.HomeI18n
        ? window.HomeI18n.t(source, params)
        : String(source).replace(/\{(\w+)\}/g, function (match, key) {
            return params && params[key] !== undefined ? params[key] : match;
          });
    }
    function rpc(method, payload) {
      return new Promise(function (resolve, reject) {
        var bridge,
          done = false,
          timeout;
        function finish(error, result) {
          if (done) return;
          done = true;
          clearTimeout(timeout);
          if (bridge)
            try {
              bridge.cancel();
            } catch (_) {}
          if (error) reject(error);
          else resolve(result);
        }
        function failed(text) {
          var error = Error(
            text || 'System updater operation failed. Open Recovery.'
          );
          error.unavailable =
            /(?:service|bus)[^\n]*(?:does not exist|not found|not registered|not running)|unknown service/i.test(
              text || ''
            );
          finish(error);
        }
        timeout = setTimeout(
          function () {
            finish(
              Error(
                'Updater response timed out. Open Recovery to check status.'
              )
            );
          },
          method === 'check' ? 65000 : 15000
        );
        try {
          bridge = new PalmServiceBridge();
          bridge.onservicecallback = function (raw) {
            try {
              var reply = JSON.parse(raw);
              if (reply.returnValue !== true) return failed(reply.errorText);
              finish(null, reply.result);
            } catch (_) {
              finish(Error('Invalid updater response. Open Recovery.'));
            }
          };
          bridge.call(URI + method, JSON.stringify(payload || {}));
        } catch (error) {
          if (typeof PalmServiceBridge === 'undefined') {
            error.unavailable = true;
          }
          finish(error);
        }
      });
    }
    function visible() {
      return !!panel && !panel.hidden;
    }
    function active() {
      return transaction && terminal.indexOf(transaction.phase) < 0;
    }
    function profileAvailable() {
      return (
        !options.standalone &&
        !!(options.edition === 'root' ? window.RootProfile : window.HomeProfile)
      );
    }
    function enabled() {
      return buttons.filter(function (button) {
        return !button.hidden && !button.disabled;
      });
    }
    function focus(index) {
      var list = enabled();
      if (!list.length) return;
      selected = (index + list.length) % list.length;
      list[selected].focus();
    }
    function close() {
      generation++;
      clearTimeout(timer);
      panel.hidden = true;
      busy = polling = false;
      if (window.ThemeRuntime) window.ThemeRuntime.resume('system-updates');
      var callback = options.onClose;
      if (callback) callback();
      else if (previous && previous.focus) previous.focus();
    }
    function render(preserveFocus) {
      if (!panel) return;
      var focused = document.activeElement;
      editionLabel.textContent =
        options.edition === 'root' ? 'Root' : 'No-root';
      var rows = (offer && offer.components) || [];
      versions.textContent = rows
        .map(function (component) {
          var labels = {
            home: 'Home',
            helper: 'Home Helper',
            updater: 'Home Updater',
            root: 'Root Home',
            'root-updater': 'Root Updater',
            'root-infrastructure': 'Home control runtime'
          };
          return (
            t(labels[component.name] || component.name) +
            ': ' +
            t('Installed: {version}', {
              version: component.installed || t('unknown')
            }) +
            (component.version == null
              ? ''
              : '  →  ' +
                t('Available: {version}', { version: component.version }))
          );
        })
        .join('\n');
      var descriptions = {
        complete: 'Update complete. Your apps and settings are preserved.',
        'rolled-back': 'Previous version and profile restored.',
        aborted:
          'Update stopped before replacement. Check status before trying again.',
        'recovery-required':
          'Recovery required. Refresh status before trying again. Rollback is blocked until the installer has definitely stopped.',
        verifying: 'Checking the updated launcher and restored settings…',
        'verifying-rollback':
          'Checking the restored launcher and saved profile…',
        'rolling-back': 'Restoring previous components and saved profile…'
      };
      var phase = transaction && transaction.phase;
      var displayError =
        stickyError || errorText || (!recovery && !phase && checkError);
      message.textContent = displayError
        ? t(displayError)
        : phase
          ? t(
              descriptions[phase] ||
                'Update state: {status}. Keep the TV powered on.',
              { status: phase }
            )
          : busy
            ? t('Checking for updates…')
            : recovery
              ? t('No previous update is saved for rollback yet.')
              : offer && offer.canInstall
                ? t('A signed system update is available.')
                : t('Your apps and settings stay saved.');
      if (!recovery && phase && checkError)
        message.textContent += '\n' + t(checkError);
      if (
        !recovery &&
        !displayError &&
        offer &&
        !offer.canInstall &&
        offer.reason &&
        !phase
      ) {
        var reasons = {
          'Infrastructure inventory changed; computer migration required':
            'This update requires a computer migration. Keep recovery records.',
          'feed-unavailable':
            'Update information is not available yet. Try again later.',
          'connection-error':
            'Could not connect to check for updates. Check your connection and try again.',
          current: 'All components are up to date.',
          'root-required':
            'Update available. Without root, install it from a computer using the guide.',
          'missing-rollback':
            'A verified recovery package for this version is missing. Run the one-time computer setup.',
          'missing-baseline':
            'A verified recovery package for this version is missing. Run the one-time computer setup.'
        };
        message.textContent +=
          '\n' +
          t(reasons[offer.reason] || 'Update unavailable: {reason}', {
            reason: offer.reason
          });
      }
      if (!profileAvailable() && !recovery)
        message.textContent +=
          '\n' + t('For regular updates, open Home settings.');
      if (
        transaction &&
        transaction.homeResume &&
        transaction.homeResume.status === 'failed'
      )
        message.textContent +=
          '\n' +
          t(
            'Home control could not be restored automatically. Open Home settings.'
          );
      if (transaction && transaction.error)
        message.textContent +=
          '\n' + String(transaction.error.message || transaction.error);
      if (
        transaction &&
        transaction.edition &&
        transaction.edition !== options.edition
      )
        message.textContent +=
          '\n' + t('Recovery belongs to the other installed edition.');
      window.HomeReleaseNotes.render(
        notes,
        (!recovery && offer && offer.notes) || ''
      );
      notesHeading.hidden = notes.hidden = recovery || !offer || !offer.notes;
      buttons[0].hidden = recovery;
      buttons[0].disabled = busy || polling;
      buttons[1].hidden = recovery;
      buttons[1].disabled =
        busy ||
        polling ||
        !!active() ||
        !profileAvailable() ||
        !offer ||
        !offer.canInstall;
      buttons[2].textContent = t(recovery ? 'Refresh status' : 'Recovery');
      buttons[2].disabled = busy || polling;
      buttons[3].hidden = !recovery;
      buttons[3].disabled =
        busy || polling || !transaction || transaction.canRollback !== true;
      buttons[4].textContent = t(options.standalone ? 'Open Home' : 'Back');
      if (visible()) {
        if (preserveFocus && enabled().indexOf(focused) >= 0)
          selected = enabled().indexOf(focused);
        else focus(selected);
      }
    }
    function schedule() {
      clearTimeout(timer);
      if (visible())
        timer = setTimeout(function () {
          refresh(false, true);
        }, 1500);
    }
    function readOffer(edition) {
      return rpc('check', { edition: edition }).then(function (value) {
        // Installed supervisors are immutable; older ones compare release tags only.
        if (
          value &&
          value.canInstall &&
          value.components &&
          value.components.length &&
          value.components.every(function (component) {
            return (
              typeof component.installed === 'string' &&
              component.installed === component.version
            );
          })
        ) {
          value.canInstall = false;
          value.reason = 'current';
        }
        return value;
      });
    }
    function check(edition, fallback) {
      return rpc('status', {}).then(
        function () {
          return readOffer(edition);
        },
        function (error) {
          if (error.unavailable && fallback) return fallback();
          throw error;
        }
      );
    }
    function checkOffer(request) {
      return readOffer(options.edition)
        .then(function (value) {
          if (request === generation) {
            offer = value;
            checkError = '';
          }
        })
        .catch(function () {
          if (request !== generation) return;
          checkError = 'Update information could not be verified.';
          if (offer) offer.canInstall = false;
        });
    }
    function refresh(check, background) {
      if (busy || polling || !visible()) return Promise.resolve();
      var request = generation;
      if (background) polling = true;
      else {
        busy = true;
        render(true);
      }
      return rpc('status', {})
        .then(function (state) {
          if (request !== generation) return;
          transaction = state;
          errorText = '';
          if (check) return checkOffer(request);
        })
        .catch(function (error) {
          if (request === generation) errorText = error.message;
        })
        .then(function () {
          if (request !== generation) return;
          busy = polling = false;
          render(true);
          schedule();
        });
    }
    function operation(method, payload) {
      if (busy || polling || !visible()) return;
      var request = generation;
      busy = true;
      errorText = '';
      clearTimeout(timer);
      render(true);
      rpc(method, payload)
        .then(function (state) {
          if (request === generation && state && state.phase)
            transaction = state;
        })
        .catch(function (error) {
          if (request === generation) errorText = error.message;
        })
        .then(function () {
          if (request !== generation) return;
          busy = false;
          render(true);
          schedule();
        });
    }
    function confirm(settings, callback) {
      if (window.HomeI18n && window.HomeI18n.confirm)
        window.HomeI18n.confirm(settings, callback);
    }
    function install() {
      if (buttons[1].disabled || !visible()) return;
      var request = generation,
        release = offer.release;
      confirm(
        {
          title: 'Install system update?',
          message:
            t('Available: {version}', { version: release }) +
            '\n' +
            t(
              'Home will close during installation. Your apps and settings will be saved.'
            ),
          action: 'Install update'
        },
        function () {
          if (
            request !== generation ||
            buttons[1].disabled ||
            !visible() ||
            offer.release !== release
          )
            return;
          busy = true;
          clearTimeout(timer);
          render(true);
          var capture =
            options.edition === 'root'
              ? Promise.resolve().then(function () {
                  return window.RootProfile.capture({ system: true });
                })
              : new Promise(function (resolve, reject) {
                  window.HomeProfile.capture(function (error, profile) {
                    if (error) reject(error);
                    else resolve(profile);
                  });
                });
          capture
            .then(function (profile) {
              if (request !== generation || !visible()) return;
              if (!profile)
                throw Error(
                  'Could not save your complete profile. Nothing was installed.'
                );
              return rpc('install', {
                edition: options.edition,
                release: release,
                profile: profile
              });
            })
            .then(function (state) {
              if (request === generation && state) transaction = state;
            })
            .catch(function (error) {
              if (request === generation) errorText = error.message;
            })
            .then(function () {
              if (request !== generation) return;
              busy = false;
              render(true);
              schedule();
            });
        }
      );
    }
    function build() {
      function element(tag, parent, id, className, text) {
        var node = document.createElement(tag);
        if (id) node.id = id;
        if (className) node.className = className;
        if (text) node.textContent = t(text);
        parent.appendChild(node);
        return node;
      }
      panel = element(
        'section',
        document.body,
        'systemUpdates',
        'root-settings root-updates'
      );
      panel.hidden = true;
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute('aria-label', t('Software updates'));
      var card = element('div', panel, null, 'root-settings-card');
      var heading = element('div', card, null, 'settings-heading');
      element('h1', heading, null, null, 'Software updates');
      editionLabel = element('span', heading, null, 'settings-edition');
      reading = element('div', card, 'systemUpdateReading', 'update-notes');
      reading.setAttribute('role', 'region');
      reading.setAttribute('aria-label', t('Software updates'));
      versions = element(
        'p',
        reading,
        'systemUpdateVersions',
        'root-update-details'
      );
      message = element(
        'p',
        reading,
        'systemUpdateStatus',
        'root-update-status'
      );
      message.setAttribute('aria-live', 'polite');
      notesHeading = element(
        'h2',
        reading,
        null,
        'update-notes-heading',
        'Release notes'
      );
      notes = element('div', reading, null, 'release-notes-content');
      var actions = element(
        'div',
        card,
        null,
        'renewal-actions update-actions'
      );
      buttons = [
        'Try again',
        'Update all',
        'Recovery',
        'Roll back',
        'Back'
      ].map(function (label, index) {
        var ids = [
          'systemUpdateCheck',
          'systemUpdateInstall',
          'systemUpdateRecovery',
          'systemUpdateRollback',
          'systemUpdateBack'
        ];
        var button = element('button', actions, ids[index], null, label);
        button.onfocus = function () {
          selected = enabled().indexOf(button);
        };
        button.onmouseover = function () {
          button.focus();
        };
        return button;
      });
      buttons[0].onclick = function () {
        stickyError = '';
        refresh(true);
      };
      buttons[1].onclick = install;
      buttons[2].onclick = function () {
        if (busy || polling) return;
        if (!recovery) {
          recovery = true;
          render(true);
          refresh(false);
        } else {
          stickyError = '';
          operation('reconcile', {});
        }
      };
      buttons[3].onclick = function () {
        if (buttons[3].disabled) return;
        var request = generation,
          id = transaction.id;
        confirm(
          {
            title: 'Restore previous system?',
            message: t(
              'Restore all previous components and pre-update settings. Settings changed after the update will be lost. Keep the TV powered on.'
            ),
            action: 'Restore previous system'
          },
          function () {
            if (
              request === generation &&
              transaction &&
              transaction.id === id &&
              !buttons[3].disabled
            )
              operation('rollback', {});
          }
        );
      };
      buttons[4].onclick = function () {
        if (recovery && !options.recovery && !options.standalone) {
          recovery = false;
          render();
          refresh(true);
        } else close();
      };
      element(
        'p',
        card,
        null,
        'update-hint',
        '↑ ↓ Read notes · ← → Choose action · Back Close'
      );
      document.addEventListener(
        'keydown',
        function (event) {
          if (
            !visible() ||
            [9, 13, 27, 37, 38, 39, 40, 461].indexOf(event.keyCode) < 0
          )
            return;
          event.preventDefault();
          event.stopImmediatePropagation();
          if (event.keyCode === 27 || event.keyCode === 461) {
            buttons[4].click();
            return;
          }
          if (event.keyCode === 38 || event.keyCode === 40) {
            window.HomeReleaseNotes.scroll(
              reading,
              event.keyCode === 38 ? -1 : 1
            );
            return;
          }
          if (event.keyCode === 13) {
            var list = enabled();
            if (!event.repeat && list.length)
              list[selected % list.length].click();
            return;
          }
          focus(
            selected +
              (event.keyCode === 37 || (event.keyCode === 9 && event.shiftKey)
                ? -1
                : 1)
          );
        },
        true
      );
    }
    function open(value) {
      if (window.ThemeRuntime) window.ThemeRuntime.suspend('system-updates');
      var request = ++generation,
        supervisorSeen = false;
      clearTimeout(timer);
      options = value || {};
      options.edition = options.edition === 'root' ? 'root' : 'no-root';
      if (!panel) build();
      if (panel.hidden) previous = document.activeElement;
      busy = true;
      polling = false;
      transaction = offer = null;
      stickyError = options.error || '';
      errorText = checkError = '';
      recovery = options.recovery === true;
      selected = 0;
      return rpc('status', {})
        .then(function (state) {
          if (request !== generation) return;
          supervisorSeen = true;
          transaction = state;
          panel.hidden = false;
          render();
          if (!recovery) return checkOffer(request);
        })
        .catch(function (error) {
          if (request !== generation) return;
          if (!supervisorSeen && error.unavailable && options.fallback) {
            panel.hidden = true;
            options.fallback();
            if (window.ThemeRuntime)
              window.ThemeRuntime.resume('system-updates');
            return;
          }
          errorText = error.message;
          panel.hidden = false;
        })
        .then(function () {
          if (request !== generation) return;
          busy = false;
          render();
          schedule();
        });
    }
    window.SystemUpdates = {
      open: open,
      rpc: rpc,
      check: check,
      isOpen: visible
    };
  })();
});
