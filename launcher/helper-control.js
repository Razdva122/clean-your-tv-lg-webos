/* Manual Helper entry shares Home's TV UI; boot launches never open this panel. */
(window.HomeI18n
  ? window.HomeI18n.ready
  : function (f) {
      f();
    })(function () {
  (function () {
    'use strict';
    var panel,
      buttons,
      status,
      details,
      diagnostic,
      previous,
      index = 0,
      busy = false,
      generation = 0;
    function t(s) {
      return window.HomeI18n ? window.HomeI18n.t(s) : s;
    }
    function rpc(uri, p, cb) {
      var bridge,
        done = false,
        timer = setTimeout(function () {
          finish(null, 'timeout');
        }, 6000);
      function finish(r, outcome) {
        if (done) return;
        done = true;
        clearTimeout(timer);
        if (bridge)
          try {
            bridge.cancel();
          } catch (_) {}
        cb(r, outcome);
      }
      try {
        bridge = new PalmServiceBridge();
        bridge.onservicecallback = function (raw) {
          var r;
          try {
            r = JSON.parse(raw);
          } catch (_) {
            finish(null, 'invalid-json');
            return;
          }
          finish(
            r,
            !r ||
              typeof r !== 'object' ||
              Array.isArray(r) ||
              typeof r.returnValue !== 'boolean'
              ? 'invalid-response'
              : r.returnValue
                ? 'success'
                : 'rejected'
          );
        };
        bridge.call(uri, JSON.stringify(p));
      } catch (_) {
        finish(null, 'transport-error');
      }
    }
    // This allowlist describes only replies observed by this panel's existing calls.
    function safeStatus(r, outcome, home) {
      var result = { outcome: outcome, errorCode: null, returnValue: null };
      if (
        r &&
        typeof r.errorCode === 'number' &&
        isFinite(r.errorCode) &&
        Math.floor(r.errorCode) === r.errorCode &&
        Math.abs(r.errorCode) <= 2147483647
      )
        result.errorCode = r.errorCode;
      ['returnValue']
        .concat(home ? ['enabled'] : ['running', 'blocked'])
        .forEach(function (key) {
          result[key] = r && typeof r[key] === 'boolean' ? r[key] : null;
        });
      return result;
    }
    function renderDiagnostics() {
      details.textContent = JSON.stringify(diagnostic, null, 2);
    }
    function showDiagnostics(show) {
      details.hidden = !show;
      buttons[4].textContent = t(
        show ? 'Hide diagnostics' : 'Show diagnostics'
      );
      buttons[4].setAttribute('aria-expanded', String(show));
      if (show) {
        renderDiagnostics();
        details.focus();
      } else focus(4);
    }
    function focus(i) {
      for (var n = 0; n < buttons.length; n++) {
        index = (i + n + buttons.length) % buttons.length;
        if (!buttons[index].hidden && !buttons[index].disabled) {
          buttons[index].focus();
          return;
        }
      }
    }
    function close() {
      generation++;
      panel.hidden = true;
      if (previous && previous.focus) previous.focus();
    }
    // While Home control is being checked only diagnostics stay available; Back/Exit still closes the panel.
    function checking(on) {
      [0, 2, 3].forEach(function (i) {
        buttons[i].disabled = on;
      });
      if (!on && document.activeElement !== details) focus(index);
    }
    function refresh() {
      var request = ++generation;
      checking(true);
      diagnostic = {
        schema: 1,
        source: 'home-helper-panel',
        helper_status: safeStatus(null, 'pending', false),
        home_status: safeStatus(null, null, true)
      };
      renderDiagnostics();
      buttons[2].hidden = true;
      if (index === 2) focus(0);
      buttons[1].disabled = true;
      status.textContent = t('Checking Home control…');
      rpc(
        'luna://com.local.nativehome.service/status',
        {},
        function (r, outcome) {
          if (request !== generation || panel.hidden) return;
          diagnostic.helper_status = safeStatus(r, outcome, false);
          renderDiagnostics();
          // A service refusal does not establish whether the independent Home broker works.
          var refused = outcome === 'rejected';
          if (
            !refused &&
            (!r ||
              r.returnValue !== true ||
              (r.running !== undefined && typeof r.running !== 'boolean'))
          ) {
            status.textContent = t(
              'Helper status could not be checked on this TV. Start Helper only when you are ready to use Home control again.'
            );
            buttons[2].hidden = false;
            checking(false);
            return;
          }
          if (!refused && r.blocked) {
            status.textContent = t(
              'Helper was stopped for safety. Start it only when you are ready to use Home control again.'
            );
            buttons[2].hidden = false;
            checking(false);
            return;
          }
          // Published Helper 0.6.17 omits running; homeStatus confirms control is responding.
          // A jailed service (webOS 3.x) cannot see the controller and reports running:false,
          // so only a homeStatus failure confirms that Helper is stopped.
          diagnostic.home_status = safeStatus(null, 'pending', true);
          renderDiagnostics();
          rpc(
            'luna://com.gathin.tvhome.renewal/homeStatus',
            {},
            function (s, outcome) {
              if (request !== generation || panel.hidden) return;
              checking(false);
              diagnostic.home_status = safeStatus(s, outcome, true);
              renderDiagnostics();
              if (
                !refused &&
                r.running === false &&
                (!s || s.returnValue !== true)
              ) {
                status.textContent = t(
                  'Helper is stopped. Start it to use the Home button and return from apps.'
                );
                buttons[2].hidden = false;
                return;
              }
              buttons[1].disabled =
                !s || s.returnValue !== true || typeof s.enabled !== 'boolean';
              if (refused && buttons[1].disabled) {
                status.textContent = t(
                  'Helper status could not be checked on this TV. Start Helper only when you are ready to use Home control again.'
                );
                buttons[2].hidden = false;
                return;
              }
              status.textContent = t(
                buttons[1].disabled
                  ? 'Home status is unknown. The Home button may still work.'
                  : s.enabled
                    ? 'Home and return from apps open Clean Your TV.'
                    : 'Home and return from apps open LG Home.'
              );
            }
          );
        }
      );
    }
    function build() {
      panel = document.createElement('section');
      panel.className = 'root-settings helper-panel';
      panel.hidden = true;
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute('aria-label', t('Home Helper'));
      var card = document.createElement('div');
      card.className = 'root-settings-card';
      panel.appendChild(card);
      var title = document.createElement('h1');
      title.textContent = t('Home Helper');
      card.appendChild(title);
      var intro = document.createElement('p');
      intro.textContent = t(
        'Helper opens Home with your remote and helps you return to Home after turning on the TV.'
      );
      card.appendChild(intro);
      status = document.createElement('p');
      status.className = 'settings-status';
      status.setAttribute('aria-live', 'polite');
      card.appendChild(status);
      var actions = document.createElement('div');
      actions.className = 'renewal-actions';
      card.appendChild(actions);
      buttons = [
        'Open Home',
        'Home button settings',
        'Start Helper',
        'Refresh status',
        'Show diagnostics'
      ].map(function (label, i) {
        var b = document.createElement('button');
        b.textContent = t(label);
        b.onfocus = function () {
          index = i;
        };
        b.onclick = function () {
          if (i === 4) return showDiagnostics(details.hidden);
          if (busy) return;
          if (i === 0) return close();
          if (i === 1) {
            close();
            window.RenewalPanel.open();
            return;
          }
          if (i === 3) return refresh();
          window.HomeI18n.confirm(
            {
              title: 'Start Helper?',
              message: t(
                'Start Helper to use Home control again. Your saved Home screen choice will be used.'
              ),
              action: 'Start Helper'
            },
            function () {
              if (panel.hidden || busy) return;
              busy = true;
              buttons[2].disabled = true;
              status.textContent = t('Starting Helper…');
              rpc(
                'luna://com.webos.applicationManager/launch',
                {
                  id: 'com.local.nativehome',
                  params: { nativeHomeStart: true }
                },
                function (r) {
                  busy = false;
                  buttons[2].disabled = false;
                  if (!r || !r.returnValue) {
                    status.textContent = t(
                      'Helper is unavailable. Reinstall the complete Home package from your computer.'
                    );
                    return;
                  }
                  setTimeout(function () {
                    if (!panel.hidden) refresh();
                  }, 1500);
                }
              );
            }
          );
        };
        actions.appendChild(b);
        return b;
      });
      buttons[4].setAttribute('aria-expanded', 'false');
      buttons[4].setAttribute('aria-controls', 'helperPanelDiagnostics');
      details = document.createElement('pre');
      details.id = 'helperPanelDiagnostics';
      details.className = 'helper-panel-diagnostics';
      details.hidden = true;
      details.setAttribute('tabindex', '0');
      details.setAttribute('aria-label', t('Show diagnostics'));
      card.appendChild(details);
      document.body.appendChild(panel);
      document.addEventListener(
        'keydown',
        function (e) {
          if (
            panel.hidden ||
            [9, 13, 27, 37, 38, 39, 40, 461].indexOf(e.keyCode) < 0
          )
            return;
          e.preventDefault();
          e.stopImmediatePropagation();
          if (document.activeElement === details) {
            if (e.keyCode === 38 || e.keyCode === 40) {
              details.scrollTop += e.keyCode === 38 ? -80 : 80;
              return;
            }
            if (e.keyCode === 27 || e.keyCode === 461 || e.keyCode === 13)
              return showDiagnostics(false);
            focus(4);
            return;
          }
          if (e.keyCode === 27 || e.keyCode === 461) return close();
          if (e.keyCode === 13) {
            if (!e.repeat && !buttons[index].hidden && !buttons[index].disabled)
              buttons[index].click();
            return;
          }
          var step =
            e.keyCode === 37 ||
            e.keyCode === 38 ||
            (e.keyCode === 9 && e.shiftKey)
              ? -1
              : 1;
          for (var n = 1; n <= buttons.length; n++) {
            var next = (index + step * n + buttons.length) % buttons.length;
            if (!buttons[next].hidden && !buttons[next].disabled) {
              focus(next);
              break;
            }
          }
        },
        true
      );
    }
    function open() {
      if (!panel) build();
      if (panel.hidden) previous = document.activeElement;
      panel.hidden = false;
      showDiagnostics(false);
      focus(0);
      refresh();
    }
    function launchParams(event) {
      try {
        var raw = event && event.detail;
        if (raw && raw.params) raw = raw.params;
        var params = typeof raw === 'string' ? JSON.parse(raw) : raw;
        if (params && typeof params.showHelper === 'boolean')
          return params.showHelper;
        raw = window.PalmSystem && window.PalmSystem.launchParams;
        params = typeof raw === 'string' ? JSON.parse(raw) : raw;
        return params && params.showHelper === true;
      } catch (_) {
        return false;
      }
    }
    document.addEventListener('webOSRelaunch', function (e) {
      if (launchParams(e)) open();
    });
    window.HomeHelper = { open: open };
    if (launchParams()) open();
  })();
});
