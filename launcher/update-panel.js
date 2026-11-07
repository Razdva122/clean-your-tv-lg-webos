(window.HomeI18n
  ? HomeI18n.ready
  : function (callback) {
      callback();
    })(function () {
  (function () {
    'use strict';
    function tr(s, p) {
      return window.HomeI18n
        ? HomeI18n.t(s, p)
        : s.replace(/\{(\w+)\}/g, function (m, k) {
            return p && p[k] !== undefined ? p[k] : m;
          });
    }
    function ht(s) {
      return window.HomeI18n ? HomeI18n.html(s) : s;
    }
    var URI = 'luna://com.cleanyourtv.updater.service/';
    var panel = document.createElement('section');
    panel.id = 'updatePanel';
    panel.className = 'hidden';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-label', tr('Software updates'));
    panel.innerHTML = ht(
      '<div class="renewal-card update-card"><div class="settings-heading"><h2>Software updates</h2><span class="settings-edition">No-root</span></div><div id="updateReading" class="update-notes" role="region" aria-label="Software updates"><p id="updateVersions" class="update-versions"></p><p id="updateStatus" class="root-update-status" aria-live="polite">Checking for updates…</p><h3 id="updateNotesHeading" class="update-notes-heading">Release notes</h3><div id="updateNotes" class="release-notes-content"></div></div><div class="renewal-actions update-actions"><button id="updateCheck" hidden>Try again</button><button id="updateInstall" disabled>Update Home</button><button id="updateRecovery">Recovery</button><button id="updateBack">Back</button></div><p class="update-hint">↑ ↓ Read notes · ← → Choose action · Back Close</p></div>'
    );
    document.body.appendChild(panel);
    var notesHeading = document.getElementById('updateNotesHeading'),
      reading = document.getElementById('updateReading'),
      versions = document.getElementById('updateVersions'),
      status = document.getElementById('updateStatus'),
      notes = document.getElementById('updateNotes'),
      install = document.getElementById('updateInstall'),
      check = document.getElementById('updateCheck');
    var buttons = Array.prototype.slice.call(panel.querySelectorAll('button')),
      index = 0,
      offer = null,
      busy = false,
      onClose = null,
      previous;
    function rpc(method, payload, cb) {
      var b,
        done = false,
        timer = setTimeout(
          function () {
            finish(null);
          },
          method === 'install' ? 190000 : 65000
        );
      function finish(r) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (b)
          try {
            b.cancel();
          } catch (_) {}
        cb(r && r.returnValue === true ? r.result : null);
      }
      try {
        b = new PalmServiceBridge();
        b.onservicecallback = function (raw) {
          try {
            finish(JSON.parse(raw));
          } catch (_) {
            finish(null);
          }
        };
        b.call(URI + method, JSON.stringify(payload || {}));
      } catch (_) {
        finish(null);
      }
    }
    function focus(i, direction) {
      direction = direction || 1;
      for (var n = 0; n < buttons.length; n++, i += direction) {
        var j = (i + buttons.length) % buttons.length;
        if (!buttons[j].disabled && !buttons[j].hidden) {
          index = j;
          buttons[j].focus();
          return;
        }
      }
    }
    function show(text) {
      status.textContent = text;
    }
    function currentOrNewer(candidate, installed) {
      var a = String(candidate).split('.'),
        b = String(installed).split('.');
      if (a.length !== 3 || b.length !== 3) return false;
      for (var n = 0; n < 3; n++)
        if (!/^\d+$/.test(a[n]) || !/^\d+$/.test(b[n])) return false;
      for (var i = 0; i < 3; i++)
        if (Number(a[i]) !== Number(b[i])) return Number(a[i]) > Number(b[i]);
      return true;
    }
    function checkNow() {
      if (busy) return;
      busy = true;
      check.hidden = true;
      check.disabled = true;
      install.disabled = true;
      show(tr('Checking for updates…'));
      rpc('check', {}, function (r) {
        busy = false;
        check.disabled = false;
        offer = r;
        if (!r || !r.candidate) {
          window.HomeReleaseNotes.render(notes, '');
          notesHeading.hidden = notes.hidden = true;
          versions.textContent =
            r && r.home ? tr('Installed: {version}', { version: r.home }) : '';
          check.hidden = false;
          show(
            tr(
              'Update service or signed release unavailable. Install the separate Home Updater package once, then retry. Your current Home is unchanged.'
            )
          );
          if (!panel.classList.contains('hidden')) focus(0);
          return;
        }
        var candidate = currentOrNewer(r.candidate.home, r.home)
          ? r.candidate
          : null;
        window.HomeReleaseNotes.render(
          notes,
          (candidate && candidate.notes) || ''
        );
        notesHeading.hidden = notes.hidden = !candidate || !candidate.notes;
        install.disabled = !r.canInstall;
        versions.textContent =
          tr('Installed: {version}', { version: r.home }) +
          (candidate
            ? '  →  ' + tr('Available: {version}', { version: candidate.home })
            : '');
        var labels = {
          current: tr('Home is up to date.'),
          'newer-installed': tr(
            'Your installed Home is newer than this release.'
          ),
          'helper-update-required': tr(
            'Update Home Helper using the installation guide first.'
          ),
          available: r.canInstall
            ? tr('A signed Home update is available.')
            : r.root
              ? tr(
                  'Update available, but a verified recovery package for your installed version is missing.'
                )
              : tr(
                  'Update available. Without root, install it from a computer using the guide.'
                )
        };
        show(labels[r.state] || tr('Check pending'));
        if (!panel.classList.contains('hidden')) focus(0);
      });
    }
    check.onclick = checkNow;
    function installUpdate() {
      if (
        busy ||
        !offer ||
        !offer.canInstall ||
        panel.classList.contains('hidden')
      )
        return;
      busy = true;
      install.disabled = true;
      check.disabled = true;
      show(tr('Saving apps, icons and settings…'));
      window.HomeProfile.capture(function (error, profile) {
        if (error) {
          busy = false;
          check.disabled = false;
          show(
            tr('Could not save your complete profile. Nothing was installed.')
          );
          return;
        }
        show(
          tr(
            'Installing Home… Keep the TV on. If this screen closes, open Home again or use Home Updater for recovery.'
          )
        );
        rpc(
          'install',
          { version: offer.candidate.home, profile: profile },
          function (r) {
            busy = false;
            check.disabled = false;
            show(
              r
                ? tr(
                    'Update state: {status}. Reopen Home when installation finishes.',
                    { status: r.status }
                  )
                : tr(
                    'Update outcome is not confirmed. Open Home Updater → Recovery before retrying.'
                  )
            );
          }
        );
      });
    }
    install.onclick = function () {
      if (busy || !offer || !offer.canInstall) return;
      window.HomeI18n.confirm(
        {
          title: 'Install Home update?',
          message:
            'Home will close during installation. Your apps and settings will be saved.',
          action: 'Install update'
        },
        installUpdate
      );
    };
    document.getElementById('updateRecovery').onclick = function () {
      if (busy) return;
      rpc('reconcile', {}, function (r) {
        show(
          r
            ? tr(
                'Recovery state: {status}. Use Home Updater to restore the previous version if offered.',
                { status: r.status }
              )
            : tr(
                'No recovery result available. Your helper has not been changed.'
              )
        );
      });
    };
    function close() {
      panel.classList.add('hidden');
      if (window.ThemeRuntime) ThemeRuntime.resume('legacy-updates');
      if (onClose) {
        var callback = onClose;
        onClose = null;
        callback();
      } else if (previous && previous.focus) previous.focus();
    }
    document.getElementById('updateBack').onclick = close;
    buttons.forEach(function (b, i) {
      b.onfocus = function () {
        index = i;
      };
      b.addEventListener('mouseover', function () {
        focus(i);
      });
    });
    document.addEventListener(
      'keydown',
      function (e) {
        if (panel.classList.contains('hidden')) return;
        if ([9, 37, 38, 39, 40, 13, 461, 27].indexOf(e.keyCode) < 0) return;
        e.preventDefault();
        e.stopImmediatePropagation();
        if (e.keyCode === 38 || e.keyCode === 40) {
          window.HomeReleaseNotes.scroll(reading, e.keyCode === 38 ? -1 : 1);
          return;
        }
        if (e.keyCode === 461 || e.keyCode === 27) close();
        else if (e.keyCode === 13) {
          if (!e.repeat) buttons[index].click();
        } else {
          var direction =
            e.keyCode === 37 ||
            e.keyCode === 38 ||
            (e.keyCode === 9 && e.shiftKey)
              ? -1
              : 1;
          focus(index + direction, direction);
        }
      },
      true
    );
    function legacyOpen(options) {
      if (window.ThemeRuntime) ThemeRuntime.suspend('legacy-updates');
      previous = document.activeElement;
      onClose = (options && options.onClose) || null;
      panel.classList.remove('hidden');
      checkNow();
      focus(0);
    }
    window.HomeUpdates = {
      open: function (options) {
        if (window.SystemUpdates) {
          panel.classList.add('hidden');
          var value = {
            edition: 'no-root',
            onClose: options && options.onClose,
            fallback: function () {
              legacyOpen(options);
            }
          };
          return window.SystemUpdates.open(value);
        }
        return legacyOpen(options);
      },
      rpc: rpc
    };
  })();
});
