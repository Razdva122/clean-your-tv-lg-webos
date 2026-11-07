(window.HomeI18n && window.HomeI18n.ready
  ? window.HomeI18n.ready
  : function (callback) {
      callback();
    })(function () {
  (function () {
    'use strict';
    function legacy() {
      var buttons = ['open', 'refresh', 'restore', 'details'].map(
          function (id) {
            return document.getElementById(id);
          }
        ),
        index = 0,
        busy = false,
        polling = false,
        generation = 0,
        timer,
        saved = null;
      function tr(source, params) {
        return window.HomeI18n
          ? window.HomeI18n.t(source, params)
          : source.replace(/\{(\w+)\}/g, function (_, key) {
              return params[key];
            });
      }
      function text(s) {
        document.getElementById('status').textContent = tr(s);
      }
      function guidance(s) {
        document.getElementById('guidance').textContent = tr(s);
      }
      function diagnostics(s) {
        document.getElementById('diagnostic').textContent = s || '';
      }
      if (window.HomeI18n) {
        document.title = tr('Home Updater');
        window.HomeI18n.apply(document.body);
      }
      function call(method, payload, cb) {
        var b,
          done = false,
          t = setTimeout(function () {
            finish(null, true);
          }, 190000);
        function finish(r, failed) {
          if (done) return;
          done = true;
          clearTimeout(t);
          if (b)
            try {
              b.cancel();
            } catch (_) {}
          cb(r, !!failed);
        }
        try {
          b = new PalmServiceBridge();
          b.onservicecallback = function (raw) {
            try {
              var r = JSON.parse(raw);
              finish(r.result, r.returnValue !== true);
            } catch (_) {
              finish(null, true);
            }
          };
          b.call(
            'luna://com.cleanyourtv.updater.service/' + method,
            JSON.stringify(payload)
          );
        } catch (_) {
          finish(null, true);
        }
      }
      function render(s, failed) {
        saved = failed ? null : s;
        buttons[2].textContent = tr('Restore previous Home');
        buttons[2].hidden = buttons[2].disabled = !!(
          failed ||
          !s ||
          !s.prior ||
          ['awaiting-launch', 'complete'].indexOf(s.status) < 0
        );
        if (buttons[2].hidden && index === 2) {
          index = 0;
          buttons[0].focus();
        }
        diagnostics(
          failed
            ? 'service-unavailable'
            : s
              ? JSON.stringify(
                  { status: s.status, error: s.error || null },
                  null,
                  2
                )
              : 'No transaction'
        );
        if (failed) {
          text('Status is unavailable.');
          guidance(
            'Try refreshing. If this continues, reinstall the complete Home package from your computer.'
          );
          return;
        }
        if (
          !s ||
          ['complete', 'rolled-back', 'aborted'].indexOf(s.status) >= 0
        ) {
          text('No recovery needed.');
          guidance(
            s && s.status === 'rolled-back'
              ? 'The previous version has already been restored.'
              : s && s.status === 'complete'
                ? 'Open Home to continue. If the update caused a problem, you can restore the previous version.'
                : 'Open Home to continue.'
          );
          return;
        }
        if (['recovery-required', 'renewal-recovery'].indexOf(s.status) >= 0) {
          text('Recovery needs attention.');
          guidance(
            'Refresh status first. If recovery remains unavailable, use the installer on your computer.'
          );
          return;
        }
        text(
          s.status === 'rolling-back'
            ? 'Restoring… Keep the TV on.'
            : 'An update is in progress.'
        );
        guidance('Keep the TV powered on. Status will refresh automatically.');
      }
      function schedule() {
        clearTimeout(timer);
        if (
          saved &&
          ['complete', 'rolled-back', 'aborted'].indexOf(saved.status) < 0
        )
          timer = setTimeout(refresh, 2000);
      }
      function refresh() {
        if (busy || polling) return;
        polling = true;
        var request = ++generation;
        buttons[2].disabled = true;
        call('reconcile', {}, function (s, failed) {
          polling = false;
          if (request !== generation) return;
          render(s, failed);
          schedule();
        });
      }
      document.addEventListener('webOSRelaunch', refresh);
      document.addEventListener('visibilitychange', function () {
        if (!document.hidden) refresh();
      });
      buttons[1].onclick = refresh;
      buttons[2].onclick = function () {
        if (busy || polling || buttons[2].disabled || buttons[2].hidden) return;
        var request = generation;
        window.HomeI18n.confirm(
          {
            title: 'Restore previous Home?',
            message: tr(
              'Restore the previous Home version and pre-update settings. Settings changed after the update will be lost. Keep the TV powered on.'
            ),
            action: 'Restore previous Home'
          },
          function () {
            if (
              busy ||
              polling ||
              request !== generation ||
              buttons[2].disabled
            )
              return;
            busy = true;
            clearTimeout(timer);
            buttons[2].disabled = true;
            text('Restoring… Keep the TV on.');
            call('rollback', {}, function (s, failed) {
              busy = false;
              render(s, failed);
              schedule();
            });
          }
        );
      };
      buttons[0].onclick = function () {
        var b;
        try {
          b = new PalmServiceBridge();
          b.onservicecallback = function (raw) {
            b.cancel();
            try {
              if (JSON.parse(raw).returnValue === true) return;
            } catch (_) {}
            text('Could not open Home.');
            guidance(
              'Refresh status first. If recovery remains unavailable, use the installer on your computer.'
            );
          };
          b.call(
            'luna://com.webos.applicationManager/launch',
            JSON.stringify({ id: 'com.gathin.tvhome' })
          );
        } catch (_) {
          text('Could not open Home.');
        }
      };
      buttons[3].onclick = function () {
        var detail = document.getElementById('diagnostic');
        detail.hidden = !detail.hidden;
        buttons[3].textContent = tr(
          detail.hidden ? 'Show diagnostics' : 'Hide diagnostics'
        );
        buttons[3].setAttribute('aria-expanded', String(!detail.hidden));
      };
      document.addEventListener('keydown', function (e) {
        if ([9, 27, 37, 38, 39, 40, 13, 461].indexOf(e.keyCode) < 0) return;
        e.preventDefault();
        if (e.keyCode === 27 || e.keyCode === 461) {
          buttons[0].click();
          return;
        }
        if (e.keyCode === 38 || e.keyCode === 40) {
          var reading = document.getElementById('recoveryReading');
          reading.scrollTop +=
            (e.keyCode === 38 ? -1 : 1) *
            Math.max(80, Math.floor(reading.clientHeight * 0.75));
          return;
        }
        if (e.keyCode === 13) {
          if (!e.repeat) buttons[index].click();
          return;
        }
        var step = e.keyCode === 37 || (e.keyCode === 9 && e.shiftKey) ? -1 : 1;
        for (var n = 1; n <= buttons.length; n++) {
          var next = (index + step * n + buttons.length) % buttons.length;
          if (!buttons[next].hidden && !buttons[next].disabled) {
            index = next;
            buttons[index].focus();
            break;
          }
        }
      });
      buttons.forEach(function (b, i) {
        b.onfocus = function () {
          index = i;
        };
        b.onmouseover = function () {
          index = i;
          b.focus();
        };
      });
      buttons[0].focus();
      text('Reading status…');
      refresh();
    }
    if (window.SystemUpdates) {
      var legacyPanel = document.getElementById('legacyRecovery'),
        systemMode = true;
      if (legacyPanel) legacyPanel.hidden = true;
      function openHome() {
        var bridge;
        try {
          bridge = new PalmServiceBridge();
          bridge.onservicecallback = function (raw) {
            bridge.cancel();
            try {
              if (JSON.parse(raw).returnValue === true) return;
            } catch (_) {}
            openSystem();
          };
          bridge.call(
            'luna://com.webos.applicationManager/launch',
            JSON.stringify({ id: 'com.gathin.tvhome' })
          );
        } catch (_) {
          openSystem();
        }
      }
      function openSystem() {
        return window.SystemUpdates.open({
          edition: 'no-root',
          standalone: true,
          recovery: true,
          onClose: openHome,
          fallback: function () {
            systemMode = false;
            if (legacyPanel) legacyPanel.hidden = false;
            legacy();
          }
        });
      }
      document.addEventListener('webOSRelaunch', function () {
        if (systemMode) openSystem();
      });
      document.addEventListener('visibilitychange', function () {
        if (systemMode && !document.hidden && !window.SystemUpdates.isOpen())
          openSystem();
      });
      openSystem();
    } else legacy();
  })();
});
