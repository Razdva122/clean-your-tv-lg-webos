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
      title,
      message,
      details,
      reading,
      notes,
      notesHeading,
      buttons,
      previous,
      selected = 0,
      timer,
      onClose;
    var busy = false,
      polling = false,
      recovery = false,
      offer = null,
      transaction = null,
      errorText = '';
    var recoveryParent = false,
      settleUntil = 0,
      standalone = false,
      introduction,
      diagnostic,
      diagnosticButton,
      hint;
    var terminal = ['complete', 'rolled-back', 'aborted'];
    function unprovisioned() {
      var error = Error(
        'Updater unavailable. Run the one-time computer setup for Software updates.'
      );
      error.unavailable = true;
      return error;
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
        timeout = setTimeout(function () {
          finish(
            Error('Updater response timed out. Open Recovery to check status.')
          );
        }, 110000);
        try {
          bridge = new PalmServiceBridge();
          bridge.onservicecallback = function (raw) {
            try {
              var reply = JSON.parse(raw);
              if (reply.returnValue !== true)
                return finish(
                  /does not exist|not found|unknown service|not registered/i.test(
                    reply.errorText || ''
                  )
                    ? unprovisioned()
                    : Error(
                        reply.errorText ||
                          'Updater operation failed. Open Recovery.'
                      )
                );
              finish(null, reply.result);
            } catch (_) {
              finish(Error('Invalid updater response. Open Recovery.'));
            }
          };
          bridge.call(
            'luna://com.cleanyourtv.root.updater.service/' + method,
            JSON.stringify(payload || {})
          );
        } catch (_) {
          finish(unprovisioned());
        }
      });
    }
    function active() {
      return transaction && terminal.indexOf(transaction.phase) < 0;
    }
    function enabled() {
      var list = buttons.filter(function (b) {
        return !b.hidden && !b.disabled;
      });
      var primary = list.indexOf(buttons[7]);
      if (standalone && primary > 0) list.unshift(list.splice(primary, 1)[0]);
      return list;
    }
    function focus(index) {
      var list = enabled();
      if (!list.length) return;
      selected = (index + list.length) % list.length;
      list[selected].focus();
    }
    function close() {
      clearTimeout(timer);
      panel.hidden = true;
      if (window.ThemeRuntime)
        window.ThemeRuntime.resume('legacy-root-updates');
      if (onClose) {
        var callback = onClose;
        onClose = null;
        callback();
      } else if (previous && previous.focus) previous.focus();
    }
    function back() {
      if (recoveryParent) {
        recovery = false;
        recoveryParent = false;
        selected = enabled().indexOf(buttons[3]);
        render();
        focus(enabled().indexOf(buttons[3]));
        return;
      }
      close();
    }
    function rollbackAllowed() {
      return !!(
        transaction &&
        transaction.prior &&
        transaction.prior.version &&
        ['complete', 'recovery-required'].indexOf(transaction.phase) >= 0 &&
        transaction.installEvidence &&
        transaction.installEvidence.terminal &&
        !transaction.rollbackAttempted
      );
    }
    function currentOrNewer(candidate, installed) {
      var a = String(candidate).split('.'),
        b = String(installed).split('.');
      if (a.length !== 3 || b.length !== 3) return false;
      for (var i = 0; i < 3; i++) {
        if (!/^\d+$/.test(a[i]) || !/^\d+$/.test(b[i])) return false;
      }
      for (var j = 0; j < 3; j++) {
        if (Number(a[j]) !== Number(b[j])) return Number(a[j]) > Number(b[j]);
      }
      return true;
    }
    function show(index, visible, disabled) {
      buttons[index].hidden = !visible;
      buttons[index].disabled = !!disabled;
    }
    function render(preserveFocus) {
      var phase = transaction && transaction.phase;
      title.textContent = t(
        standalone ? 'Root Updater' : recovery ? 'Recovery' : 'Software updates'
      );
      introduction.hidden = !standalone;
      panel.className = standalone
        ? 'root-settings root-updates companion-app'
        : 'root-settings root-updates';
      buttons[7].className = standalone ? 'companion-primary' : '';
      hint.textContent = t(
        standalone
          ? '← → Choose action · Back Open Home'
          : '↑ ↓ Read notes · ← → Choose action · Back Close'
      );
      diagnostic.textContent =
        errorText ||
        (transaction
          ? JSON.stringify(
              { phase: transaction.phase, error: transaction.error || null },
              null,
              2
            )
          : '');
      diagnosticButton.hidden = !diagnostic.textContent;
      if (diagnosticButton.hidden) diagnostic.hidden = true;
      panel.setAttribute('aria-label', title.textContent);
      var descriptions = {
        preparing: 'Preparing update and preserving your launcher profile…',
        downloading:
          'Downloading and verifying both update and rollback packages…',
        'backed-up': 'Profile and rollback package verified.',
        'restoring-route': 'Restoring LG Home before installation…',
        installing: 'Installing Root update. Keep the TV powered on.',
        'awaiting-launch': 'Opening the updated Root launcher…',
        verifying: 'Checking the updated launcher and restored settings…',
        complete: 'Update complete. Your apps and settings are preserved.',
        'rolling-back':
          'Restoring the previous Root package and saved profile…',
        'verifying-rollback':
          'Checking the restored Root launcher and saved profile…',
        'rolled-back': 'Previous Root version and profile restored.',
        'recovery-required':
          'Recovery required. LG Home remains selected. Recover status first; rollback stays blocked until the installer has definitely stopped.',
        aborted:
          'Update stopped before replacement. Check status before trying again.'
      };
      message.textContent = t(
        errorText ||
          descriptions[phase] ||
          (recovery
            ? 'Inspect the independent updater and recover a previous transaction.'
            : busy
              ? 'Checking for updates…'
              : offer && offer.canInstall
                ? 'A new version of Home is available.'
                : 'Your apps and settings stay saved.')
      );
      if (standalone) {
        if (errorText)
          message.textContent =
            t(
              errorText === 'Could not open Home.'
                ? 'Could not open Home.'
                : 'Status is unavailable.'
            ) +
            '\n' +
            t(
              'Try refreshing. If this continues, reinstall the complete Home package from your computer.'
            );
        else if (phase === 'recovery-required')
          message.textContent =
            t('Recovery needs attention.') +
            '\n' +
            t(
              'Refresh status first. If recovery remains unavailable, use the installer on your computer.'
            );
        else if (!transaction && !busy)
          message.textContent =
            t('No recovery needed.') + '\n' + t('Open Home to continue.');
      }
      if (
        transaction &&
        transaction.homeResume &&
        transaction.homeResume.status === 'failed'
      )
        message.textContent +=
          ' ' +
          t(
            'Home control could not be restored automatically. Open Home settings.'
          );
      if (
        transaction &&
        transaction.homeResume &&
        transaction.homeResume.status === 'restored'
      )
        message.textContent +=
          ' ' + t('Your previous Home screen choice has been restored.');
      if (
        transaction &&
        transaction.homeResume &&
        transaction.homeResume.status === 'cancelled'
      )
        message.textContent +=
          ' ' +
          t(
            'Home control remains off because it was disabled during the update.'
          );
      var installed = offer && offer.installed;
      details.textContent = t('Installed: {version}', {
        version:
          (installed && installed.version) ||
          installed ||
          window.ROOT_VERSION ||
          t('unknown')
      });
      var candidate =
        !recovery &&
        offer &&
        offer.candidate &&
        currentOrNewer(
          offer.candidate.version,
          (installed && installed.version) || installed || window.ROOT_VERSION
        )
          ? offer.candidate
          : null;
      if (candidate)
        details.textContent +=
          '  →  ' + t('Available: {version}', { version: candidate.version });
      window.HomeReleaseNotes.render(
        notes,
        (candidate && candidate.notes) || ''
      );
      notesHeading.hidden = !candidate || !candidate.notes;
      notes.hidden = recovery || !candidate || !candidate.notes;
      if (!recovery && offer && !offer.canInstall && offer.reason) {
        var reasons = {
          current: 'This Root version is up to date.',
          'missing-rollback':
            'A verified recovery package for this version is missing. Run the one-time computer setup.'
        };
        message.textContent +=
          '\n' +
          t(
            reasons[offer.reason] ||
              'This release cannot be installed with the current setup.'
          );
      }
      if (recovery) {
        details.textContent = '';
        if (transaction && transaction.prior)
          details.textContent = t('Rollback version: {version}', {
            version: transaction.prior.version
          });
        if (
          !transaction ||
          !transaction.prior ||
          !transaction.prior.version ||
          phase === 'aborted'
        )
          details.textContent +=
            '\n' + t('No saved update is available to roll back.');
        else if (phase === 'complete')
          details.textContent +=
            '\n' + t('Rollback remains available until the next update.');
        else if (phase === 'rolled-back')
          details.textContent +=
            '\n' + t('The previous version has already been restored.');
        else if (!rollbackAllowed())
          details.textContent +=
            '\n' +
            t(
              'Rollback is blocked until the installer has definitely stopped. Refresh status to check.'
            );
        else
          details.textContent +=
            '\n' +
            t('The previous Home version and saved settings will be restored.');
      }
      buttons[3].textContent = t(recovery ? 'Refresh status' : 'Recovery');
      show(0, !recovery && !!errorText, busy || active());
      show(1, !recovery, busy || active() || !offer || !offer.canInstall);
      show(2, false);
      show(3, true, busy);
      show(4, recovery && rollbackAllowed(), busy);
      show(5, false);
      show(
        6,
        !!(
          transaction &&
          transaction.homeResume &&
          ['failed', 'skipped'].indexOf(transaction.homeResume.status) >= 0
        ),
        busy
      );
      show(7, true, false);
      buttons[7].textContent = t(standalone ? 'Open Home' : 'Back');
      if (!panel.hidden) {
        var current = enabled().indexOf(document.activeElement);
        if (preserveFocus && current >= 0) selected = current;
        else focus(standalone ? enabled().indexOf(buttons[7]) : selected);
      }
    }
    function schedule() {
      clearTimeout(timer);
      if (!panel.hidden && (active() || settleUntil > Date.now()))
        timer = setTimeout(function () {
          refresh(false, true);
        }, 1500);
    }
    function refresh(check, background) {
      if (busy || polling) return Promise.resolve();
      if (background) polling = true;
      else {
        busy = true;
        render();
      }
      return rpc('status', {})
        .then(function (state) {
          var wasActive = active();
          transaction = state;
          if (
            wasActive &&
            transaction &&
            ['complete', 'rolled-back'].indexOf(transaction.phase) >= 0 &&
            transaction.homeResumePhase !== transaction.phase
          )
            settleUntil = Date.now() + 15000;
          if (transaction && transaction.homeResumePhase === transaction.phase)
            settleUntil = 0;
          if (check && !recovery)
            return rpc('check', {}).then(function (value) {
              offer = value;
            });
        })
        .then(function () {
          if (
            check ||
            (transaction && terminal.indexOf(transaction.phase) >= 0)
          )
            errorText = '';
        })
        .catch(function (error) {
          errorText = error.message;
        })
        .then(function () {
          if (background) polling = false;
          else busy = false;
          render(background);
          schedule();
        });
    }
    function operation(method, payload) {
      if (busy) return;
      busy = true;
      errorText = '';
      render();
      rpc(method, payload)
        .then(function (state) {
          if (state && state.phase) transaction = state;
        })
        .catch(function (error) {
          errorText = error.message;
        })
        .then(function () {
          busy = false;
          render();
          return refresh(false);
        });
    }
    function activate(index) {
      if (buttons[index].hidden || buttons[index].disabled) return;
      if (index === 7) return back();
      if (index === 8) {
        diagnostic.hidden = !diagnostic.hidden;
        diagnosticButton.textContent = t(
          diagnostic.hidden ? 'Show diagnostics' : 'Hide diagnostics'
        );
        diagnosticButton.setAttribute(
          'aria-expanded',
          String(!diagnostic.hidden)
        );
        return;
      }
      if (busy) return;
      if (index === 0) return refresh(true);
      if (index === 1)
        return window.HomeI18n.confirm(
          {
            title: 'Install Home update?',
            message:
              t('Available: {version}', { version: offer.candidate.version }) +
              '\n' +
              t(
                'Home will close during installation. Your apps and settings will be saved.'
              ),
            action: 'Install update'
          },
          function () {
            if (
              busy ||
              panel.hidden ||
              recovery ||
              active() ||
              !offer ||
              !offer.canInstall ||
              !window.RootProfile
            )
              return;
            busy = true;
            render();
            window.RootProfile.capture()
              .then(function (profile) {
                return rpc('install', {
                  version: offer.candidate.version,
                  profile: profile
                });
              })
              .then(function (state) {
                transaction = state;
              })
              .catch(function (error) {
                errorText = error.message;
              })
              .then(function () {
                busy = false;
                render();
                schedule();
              });
            return;
          }
        );
      if (index === 3) {
        if (!recovery) {
          recovery = true;
          recoveryParent = true;
          selected = 0;
          errorText = '';
          render();
          return refresh(false);
        }
        return operation('reconcile', {});
      }
      if (index === 4)
        return window.HomeI18n.confirm(
          {
            title: 'Restore previous Home?',
            message: t(
              'Restore Home {version} and pre-update settings? Settings changed after the update will be lost. Keep the TV powered on.',
              {
                version:
                  (transaction.prior && transaction.prior.version) ||
                  t('unknown')
              }
            ),
            action: 'Restore previous Home'
          },
          function () {
            if (!buttons[4].hidden && !buttons[4].disabled)
              operation('rollback', {});
          }
        );
      if (index === 6) {
        close();
        if (window.RenewalPanel) window.RenewalPanel.open();
      }
    }
    function build() {
      panel = document.createElement('section');
      panel.className = 'root-settings root-updates';
      panel.hidden = true;
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute('aria-label', t('Root Software updates'));
      var card = document.createElement('div');
      card.className = 'root-settings-card';
      panel.appendChild(card);
      var heading = document.createElement('div');
      heading.className = 'settings-heading';
      card.appendChild(heading);
      title = document.createElement('h1');
      title.textContent = t('Software updates');
      heading.appendChild(title);
      var edition = document.createElement('span');
      edition.className = 'settings-edition';
      edition.textContent = 'Root';
      heading.appendChild(edition);
      message = document.createElement('p');
      message.className = 'root-update-status';
      message.setAttribute('aria-live', 'polite');
      details = document.createElement('p');
      details.className = 'root-update-details';
      card.appendChild(details);
      card.appendChild(message);
      notesHeading = document.createElement('h2');
      notesHeading.className = 'update-notes-heading';
      notesHeading.textContent = t('Release notes');
      card.appendChild(notesHeading);
      notes = document.createElement('div');
      notes.className = 'release-notes-content';
      card.appendChild(notes);
      reading = document.createElement('div');
      reading.className = 'update-notes';
      reading.setAttribute('role', 'region');
      reading.setAttribute('aria-label', t('Software updates'));
      introduction = document.createElement('p');
      introduction.textContent = t(
        'If Home stops working after an update, use this app to restore the previous version. For regular updates, open Home settings.'
      );
      reading.appendChild(introduction);
      [details, message, notesHeading, notes].forEach(function (element) {
        card.removeChild(element);
        reading.appendChild(element);
      });
      card.appendChild(reading);
      diagnostic = document.createElement('p');
      diagnostic.className = 'root-update-details';
      diagnostic.hidden = true;
      reading.appendChild(diagnostic);
      var actions = document.createElement('div');
      actions.className = 'renewal-actions update-actions';
      card.appendChild(actions);
      buttons = [
        'Try again',
        'Update',
        'Install update',
        'Recovery',
        'Roll back',
        '',
        'Root mode settings',
        'Back',
        'Show diagnostics'
      ].map(function (label, index) {
        var button = document.createElement('button');
        button.textContent = t(label);
        button.onclick = function () {
          activate(index);
        };
        button.onfocus = function () {
          selected = enabled().indexOf(button);
        };
        actions.appendChild(button);
        return button;
      });
      diagnosticButton = buttons[8];
      diagnosticButton.setAttribute('aria-expanded', 'false');
      hint = document.createElement('p');
      hint.className = 'update-hint';
      hint.textContent = t('↑ ↓ Read notes · ← → Choose action · Back Close');
      card.appendChild(hint);
      document.body.appendChild(panel);
      document.addEventListener(
        'keydown',
        function (event) {
          if (
            panel.hidden ||
            [9, 13, 27, 37, 38, 39, 40, 461].indexOf(event.keyCode) < 0
          )
            return;
          event.preventDefault();
          event.stopImmediatePropagation();
          if (event.keyCode === 27 || event.keyCode === 461) return back();
          if (event.keyCode === 38 || event.keyCode === 40) {
            window.HomeReleaseNotes.scroll(
              reading,
              event.keyCode === 38 ? -1 : 1
            );
            return;
          }
          var list = enabled();
          if (!list.length) return;
          if (event.keyCode === 13) {
            if (!event.repeat) list[selected % list.length].onclick();
            return;
          }
          focus(
            selected +
              (event.keyCode === 37 ||
              event.keyCode === 38 ||
              (event.keyCode === 9 && event.shiftKey)
                ? -1
                : 1)
          );
        },
        true
      );
    }
    function legacyOpen(options) {
      if (window.ThemeRuntime)
        window.ThemeRuntime.suspend('legacy-root-updates');
      options = options || {};
      if (!panel) build();
      if (panel.hidden) previous = document.activeElement;
      onClose = options.onClose || null;
      standalone = options.standalone === true;
      diagnostic.hidden = true;
      diagnosticButton.textContent = t('Show diagnostics');
      diagnosticButton.setAttribute('aria-expanded', 'false');
      recovery = options.recovery === true;
      recoveryParent = false;
      settleUntil = 0;
      selected = 0;
      errorText = options.error || '';
      panel.hidden = false;
      render();
      if (!options.error) refresh(!recovery);
    }
    function open(options) {
      if (!window.SystemUpdates) return legacyOpen(options);
      options = options || {};
      if (panel) {
        panel.hidden = true;
        clearTimeout(timer);
      }
      return window.SystemUpdates.open({
        edition: 'root',
        onClose: options.onClose,
        standalone: options.standalone,
        recovery: options.recovery,
        error: options.error,
        fallback: function () {
          legacyOpen(options);
        }
      });
    }
    window.RootUpdates = {
      rpc: rpc,
      open: open,
      isOpen: function () {
        return (
          (!!panel && !panel.hidden) ||
          !!(window.SystemUpdates && window.SystemUpdates.isOpen())
        );
      }
    };
  })();
});
