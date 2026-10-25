(window.HomeI18n && window.HomeI18n.ready ? window.HomeI18n.ready : function (callback) { callback(); })(function () {
(function () {
  'use strict';
  function t(source, params) { if (window.HomeI18n) return window.HomeI18n.t(source, params); return String(source).replace(/\{(\w+)\}/g, function (_, key) { return params && params[key] !== undefined ? params[key] : '{' + key + '}'; }); }
  var panel, message, buttons, selected = 0, busy = false, previous, rootStatus = null, toggleState = {};
  var checkingUpdates = false;
  function checkUpdates() {
    if (checkingUpdates || !window.RootUpdates || !window.RootUpdates.rpc) return;
    checkingUpdates = true;
    window.RootUpdates.rpc('check', {}).then(function (offer) {
      if (!offer) return;
      var available = offer.canInstall === true || offer.reason === 'missing-rollback';
      buttons[4].setAttribute('data-update-available', String(available));
      buttons[4].setAttribute('aria-label', t(available ? 'Software updates. Update available.' : 'Software updates'));
    }).catch(function () {}).then(function () { checkingUpdates = false; });
  }
  function request(uri, payload, timeout) {
    return new Promise(function (resolve, reject) {
      var bridge, timer, done = false;
      function finish(error, reply) {
        if (done) return;
        done = true; clearTimeout(timer);
        if (bridge) try { bridge.cancel(); } catch (_) {}
        if (error) reject(error); else resolve(reply);
      }
      timer = setTimeout(function () { finish(new Error('Response timed out. Check status before retrying.')); }, timeout);
      try {
        bridge = new PalmServiceBridge();
        bridge.onservicecallback = function (raw) {
          try { finish(null, JSON.parse(raw)); } catch (_) { finish(new Error('Invalid service response')); }
        };
        bridge.call(uri, JSON.stringify(payload));
      } catch (error) { finish(error); }
    });
  }
  function launch(id) {
    return request('luna://com.webos.applicationManager/launch', {id:id}, 10000).then(function (r) {
      if (r.returnValue !== true) throw new Error('Could not open LG Home. Try again.');
    });
  }
  var exit = createRootExit(function (method) {
    return request('luna://com.cleanyourtv.root.preview.service/' + method, {}, method === 'restore' ? 620000 : 15000);
  }, function () { return Promise.resolve(); });
  function control(method, payload) {
    return request('luna://com.cleanyourtv.root.preview.service/' + method, payload || {}, 30000).then(function (reply) {
      if (!reply || reply.returnValue !== true || !reply.result || reply.result.returnValue !== true)
        throw new Error(reply && reply.errorText || 'Root control did not confirm success. Check status before retrying.');
      return reply.result.result;
    });
  }
  function refreshMode() {
    rootStatus = null; buttons[3].disabled = true;
    message.textContent = t('Checking Home control…');
    return control('status').then(function (status) {
      rootStatus = status;
      var phase = status.intent && status.intent.phase, active = phase === 'active';
      buttons[3].setAttribute('aria-checked', String(active));
      buttons[3].disabled = !!phase && phase !== 'active' && phase !== 'disabled';
      message.textContent = t(active ? 'Home and return from apps open Clean Your TV.' : buttons[3].disabled ? 'Changing Home control…' : 'Home and return from apps open LG Home.');
      if (!panel.hidden && buttons[selected].disabled) move(1);
    }).catch(function (e) { message.textContent = t(e.message); });
  }
  function changeMode() {
    if (!rootStatus || buttons[3].disabled || busy) return;
    var active = rootStatus.intent && rootStatus.intent.phase === 'active';
    busy = true; buttons.forEach(function (b) { b.disabled = true; });
    message.textContent = t(active ? 'Turning off Home control…' : 'Turning on Home control…');
    (active ? exit() : control('enable')).then(function () {
      busy = false; buttons.forEach(function (b) { b.disabled = false; });
      return refreshMode().then(function () { if (!panel.hidden) focus(3); });
    }).catch(function (e) {
      busy = false; buttons.forEach(function (b) { b.disabled = false; });
      var error = e.message;
      refreshMode().then(function () { message.textContent = t(error); });
    });
  }
  function refreshToggles() {
    request('luna://com.cleanyourtv.root.preview.service/getToggles', {}, 10000).then(function (r) {
      if (r && r.returnValue && r.toggles) {
        toggleState = r.toggles;
        if (buttons[7]) buttons[7].setAttribute('aria-checked', String(!!toggleState.earcFix));
        if (buttons[8]) buttons[8].setAttribute('aria-checked', String(!!toggleState.disableBluetooth));
        if (buttons[9]) buttons[9].setAttribute('aria-checked', String(!!toggleState.disableMicrophone));
      }
    }).catch(function () {});
  }
  function toggleSetting(key, buttonIndex) {
    if (busy) return;
    var next = !toggleState[key];
    busy = true; buttons.forEach(function (b) { b.disabled = true; });
    request('luna://com.cleanyourtv.root.preview.service/setToggle', {key: key, value: next}, 10000).then(function (r) {
      busy = false; buttons.forEach(function (b) { b.disabled = false; });
      if (r && r.returnValue && r.toggles) {
        toggleState = r.toggles;
        buttons[buttonIndex].setAttribute('aria-checked', String(!!toggleState[key]));
      }
      if (!panel.hidden) focus(buttonIndex);
    }).catch(function (e) {
      busy = false; buttons.forEach(function (b) { b.disabled = false; });
      message.textContent = t(e.message);
      if (!panel.hidden) focus(buttonIndex);
    });
  }
  var order = [3, 1, 7, 8, 9, 5, 4, 6, 0, 2];
  function focus(index) {
    selected = index;
    if (!buttons[selected].disabled) buttons[selected].focus();
  }
  function move(direction) {
    var index = order.indexOf(selected);
    for (var count = 0; count < order.length; count++) {
      index = (index + direction + order.length) % order.length;
      if (!buttons[order[index]].disabled) return focus(order[index]);
    }
  }
  function close() {
    if (busy) return;
    panel.hidden = true;
    if (previous && previous.focus) previous.focus();
  }
  function activate(index) {
    if (busy || buttons[index].disabled) return;
    if (index === 2) return close();
    if (index === 5) { if (window.HomeI18n) window.HomeI18n.openLanguagePicker(); return; }
    if (index === 3) return changeMode();
    if (index === 7) return toggleSetting('earcFix', 7);
    if (index === 8) return toggleSetting('disableBluetooth', 8);
    if (index === 9) return toggleSetting('disableMicrophone', 9);
    if (index === 6) {
      if (!window.RootFirmware) return;
      panel.hidden = true;
      window.RootFirmware.open(request, function () { panel.hidden = false; focus(6); });
      return;
    }
    if (index === 4) {
      if (!window.RootUpdates) { message.textContent = t('Software updates require the one-time computer setup.'); return; }
      panel.hidden = true;
      window.RootUpdates.open({onClose:function () { panel.hidden = false; focus(4); refreshMode(); checkUpdates(); }}); return;
    }
    if (index === 0) { launch('com.palm.app.settings').catch(function (e) { message.textContent = t(e.message); }); return; }
    busy = true; buttons.forEach(function (b) { b.disabled = true; });
    message.textContent = t('Opening LG Home…');
    launch('com.webos.app.home').then(function () { busy = false; close(); }).catch(function (e) {
      busy = false; message.textContent = t(e.message);
    }).finally(function () { buttons.forEach(function (b) { b.disabled = false; }); if (!panel.hidden) focus(1); });
  }
  function build() {
    panel = document.createElement('section'); panel.className = 'root-settings'; panel.hidden = true;
    panel.setAttribute('role','dialog'); panel.setAttribute('aria-modal','true'); panel.setAttribute('aria-label',t('Home settings'));
    var card = document.createElement('div'); card.className = 'root-settings-card settings-main'; panel.appendChild(card);
    function text(parent, tag, value, className) {
      var element = document.createElement(tag); element.textContent = t(value);
      if (className) element.className = className;
      parent.appendChild(element); return element;
    }
    var heading = document.createElement('div'); heading.className = 'settings-heading'; card.appendChild(heading);
    text(heading, 'h1', 'Home settings'); text(heading, 'span', 'Root Edition', 'settings-edition');
    var home = document.createElement('section'); home.className = 'settings-home'; card.appendChild(home);
    text(home, 'h2', 'Your Home screen');
    message = text(home, 'p', '', 'settings-status'); message.setAttribute('aria-live','polite');
    var homeActions = document.createElement('div'); homeActions.className = 'renewal-actions home-routing-actions'; home.appendChild(homeActions);
    var system = document.createElement('section'); system.className = 'settings-section'; card.appendChild(system);
    text(system, 'h2', 'System');
    var systemToggles = document.createElement('div'); systemToggles.className = 'renewal-actions home-routing-actions'; system.appendChild(systemToggles);
    var more = document.createElement('section'); more.className = 'settings-section'; card.appendChild(more);
    var links = document.createElement('div'); links.className = 'renewal-actions settings-links'; more.appendChild(links);
    var firmware = document.createElement('div'); firmware.className = 'renewal-actions settings-firmware'; more.appendChild(firmware);
    var footer = document.createElement('div'); footer.className = 'settings-footer'; card.appendChild(footer);
    text(footer, 'p', 'Hold Back for 1.2 seconds to open LG Home.');
    var back = document.createElement('div'); back.className = 'renewal-actions'; footer.appendChild(back);
    buttons = [];
    order.forEach(function (i) {
      var labels = ['TV settings','Open LG Home','Back to Home','Change Home','Software updates','Language','LG firmware updates','eARC audio delay fix','Block Bluetooth','Block microphone'];
      var b = document.createElement('button'); b.textContent = t(labels[i]);
      if (i === 3 || i === 7 || i === 8 || i === 9) { b.className = 'home-routing-switch'; b.setAttribute('role','switch'); b.setAttribute('aria-checked','false'); }
      var target = i === 7 || i === 8 || i === 9 ? systemToggles : i === 6 ? firmware : i === 3 || i === 1 ? homeActions : i === 4 || i === 0 || i === 5 ? links : back;
      if (i === 1) {
        b.className = 'home-visit-button';
        b.setAttribute('aria-describedby', 'rootHomeVisitHint');
      }
      b.onclick = function () { selected = i; activate(i); };
      b.onfocus = function () { selected = i; };
      if (i === 4) { var dot = document.createElement('span'); dot.className = 'settings-update-dot'; dot.setAttribute('aria-hidden','true'); b.appendChild(dot); }
      if (i === 4 || i === 0 || i === 5) { var arrow = document.createElement('span'); arrow.className = 'settings-chevron'; arrow.setAttribute('aria-hidden','true'); b.appendChild(arrow); }
      target.appendChild(b);
      buttons[i] = b;
    });
    text(home, 'p', 'Open LG Home once, keeping your Home choice.', 'home-visit-hint').id = 'rootHomeVisitHint';
    document.body.appendChild(panel);
    document.addEventListener('keydown', function (e) {
      if (panel.hidden) return;
      if ([9,13,27,37,38,39,40,461].indexOf(e.keyCode) === -1) return;
      e.preventDefault(); e.stopImmediatePropagation();
      if (busy) return;
      if (e.keyCode === 461 || e.keyCode === 27) return close();
      if (e.keyCode === 13) { if (!e.repeat) activate(selected); return; }
      move(e.keyCode === 37 || e.keyCode === 38 || (e.keyCode === 9 && e.shiftKey) ? -1 : 1);
    }, true);
  }
  window.RenewalPanel = {
    isOpen: function () { return !!panel && !panel.hidden; },
    open: function () {
      if (!panel) build();
      if (!panel.hidden) return;
      previous = document.activeElement;
      message.textContent = t('Checking whether Home control is on…');
      panel.hidden = false; focus(3); refreshMode().then(function () { if (!panel.hidden && !busy && !buttons[3].disabled) focus(3); });
      checkUpdates();
      refreshToggles();
    }
  };
}());

});
