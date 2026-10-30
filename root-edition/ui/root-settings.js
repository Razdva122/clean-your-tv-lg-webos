(window.HomeI18n && window.HomeI18n.ready ? window.HomeI18n.ready : function (callback) { callback(); })(function () {
(function () {
  'use strict';
  function t(source, params) { if (window.HomeI18n) return window.HomeI18n.t(source, params); return String(source).replace(/\{(\w+)\}/g, function (_, key) { return params && params[key] !== undefined ? params[key] : '{' + key + '}'; }); }
  var panel, message, buttons, selected = 0, busy = false, previous, rootStatus = null;
  var checkingUpdates = false, categories;
  function checkUpdates() {
    if (checkingUpdates || !window.RootUpdates || !window.RootUpdates.rpc) return;
    checkingUpdates = true;
    function badge(available) {
      buttons[4].setAttribute('data-update-available', String(available));
      if (categories) categories.setUpdateAvailable(available);
      buttons[4].setAttribute('aria-label', t(available ? 'Software updates. Update available.' : 'Software updates'));
    }
    function legacy() {
      return window.RootUpdates.rpc('check', {}).then(function (offer) {
        if (offer) badge(offer.canInstall === true || offer.reason === 'missing-rollback');
      });
    }
    var check = window.SystemUpdates ? window.SystemUpdates.check('root', legacy).then(function (offer) { if (offer) badge(offer.canInstall === true); }) : legacy();
    check.catch(function () {}).then(function () { checkingUpdates = false; });
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
      if (!panel.hidden && buttons[selected].disabled && (!categories || document.activeElement === buttons[selected])) move(1);
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
  var order = [3, 1, 9, 8, 10, 11, 5, 4, 0, 7, 6, 2];
  function focus(index) {
    selected = index;
    if (!buttons[selected].disabled && !buttons[selected].hidden) buttons[selected].focus();
  }
  function move(direction) {
    var index = order.indexOf(selected);
    for (var count = 0; count < order.length; count++) {
      index = (index + direction + order.length) % order.length;
      if (!buttons[order[index]].disabled && !buttons[order[index]].hidden) return focus(order[index]);
    }
  }
  function close() {
    if (busy) return;
    if(window.HomeThemePanel)HomeThemePanel.unmount();
    panel.hidden = true;
    if (window.ThemeRuntime) window.ThemeRuntime.resume('settings');
    if (previous && previous.focus) previous.focus();
  }
  function activate(index) {
    if (busy || buttons[index].disabled) return;
    if (index === 2) return close();
    if (index === 5) { if (window.HomeI18n) window.HomeI18n.openLanguagePicker(); return; }
    if (index === 9) { if (window.HomeThemePanel) window.HomeThemePanel.open(); return; }
    if (index === 8) { if (window.HomeLayoutPanel) window.HomeLayoutPanel.open(); return; }
    if (index === 10) { if (window.HomeAppControls) HomeAppControls.toggle(); return; }
    if (index === 11) { if (window.HomeAppControls) { close(); HomeAppControls.add(); } return; }
    if (index === 3) return changeMode();
    if (index === 7) {
      if (!window.RootAudio) return;
      panel.hidden = true;
      window.RootAudio.open(request, function () { panel.hidden = false; focus(7); });
      return;
    }
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
    var more = document.createElement('section'); more.className = 'settings-section'; card.appendChild(more);
    var themes = document.createElement('div'); themes.className = 'renewal-actions settings-layout'; more.appendChild(themes);
    var layout = document.createElement('div'); layout.className = 'renewal-actions settings-layout'; more.appendChild(layout);
    var apps = document.createElement('div'); apps.className = 'renewal-actions settings-layout'; more.appendChild(apps);
    var links = document.createElement('div'); links.className = 'renewal-actions settings-links'; more.appendChild(links);
    var firmware = document.createElement('div'); firmware.className = 'renewal-actions settings-firmware'; more.appendChild(firmware);
    var footer = document.createElement('div'); footer.className = 'settings-footer'; card.appendChild(footer);
    var back = document.createElement('div'); back.className = 'renewal-actions'; footer.appendChild(back);
    buttons = [];
    order.forEach(function (i) {
      var labels = ['TV settings','Open LG Home','Back to Home','Change Home','Software updates','Language','LG firmware updates','HDMI sound','Columns','Themes','Show Add app tile','Add app'];
      var b = document.createElement('button'); b.textContent = t(labels[i]);
      if (i === 3) { b.className = 'home-routing-switch'; b.setAttribute('role','switch'); b.setAttribute('aria-checked','false'); }
      var target = i === 10 || i === 11 ? apps : i === 9 ? themes : i === 8 ? layout : i === 6 || i === 7 ? firmware : i === 3 || i === 1 ? homeActions : i === 4 || i === 0 || i === 5 ? links : back;
      if (i === 10) { b.id = 'homeShowAddApp'; b.className = 'home-routing-switch'; b.setAttribute('role','switch'); b.setAttribute('aria-checked','true'); }
      if (i === 11) b.id = 'homeAddApp';
      if (i === 9) { b.hidden=true; b.disabled=true; }
      if (i === 8) b.id = 'homeColumns';
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
    themes.id='homeThemeHost';if(window.HomeThemePanel)HomeThemePanel.mount(themes);
    var appsError = text(apps, 'p', ''); appsError.id = 'homeAppsError'; appsError.setAttribute('role','alert');
    text(home, 'p', 'Open LG Home once, keeping your Home choice.', 'home-visit-hint').id = 'rootHomeVisitHint';
    if(window.SettingsCategories) categories = SettingsCategories.attach(panel, card, [
      {id:'home',label:'Your Home screen',elements:[home]},
      {id:'appearance',label:'Appearance',elements:[layout,apps]},
      {id:'themes',label:'Themes',elements:[themes]},
      {id:'language',label:'Language',elements:[buttons[5]]},
      {id:'updates',label:'Software updates',elements:[buttons[4],buttons[6]]},
      {id:'advanced',label:'Advanced',elements:[buttons[0],buttons[7]]}
    ]);
    document.body.appendChild(panel);
    document.addEventListener('keydown', function (e) {
      if (panel.hidden || window.HomeThemePanel&&HomeThemePanel.handlesKey(e)) return;
      if ([9,13,27,37,38,39,40,461].indexOf(e.keyCode) === -1) return;
      e.preventDefault(); e.stopImmediatePropagation();
      if (busy) return;
      if (e.keyCode === 461 || e.keyCode === 27) return close();
      if (e.keyCode === 13) { if (!e.repeat) activate(selected); return; }
      move(e.keyCode === 37 || e.keyCode === 38 || (e.keyCode === 9 && e.shiftKey) ? -1 : 1);
    }, true);
  }
  document.addEventListener('home-layout-change', function (event) { if (panel && !panel.hidden && buttons[selected].hidden && event.homeColumnsFocus === buttons[selected]) move(1); });
  window.RenewalPanel = {
    isOpen: function () { return !!panel && !panel.hidden; },
    open: function () {
      if (!panel) build();
      if (!panel.hidden) return;
      if (window.HomeAppControls) HomeAppControls.refresh();
      if (window.HomeLayoutPanel) HomeLayoutPanel.refreshAvailability();
      if (window.ThemeRuntime) window.ThemeRuntime.suspend('settings');
      previous = document.activeElement;
      message.textContent = t('Checking whether Home control is on…');
      panel.hidden = false; focus(3); refreshMode(); if(categories)categories.open();
      checkUpdates();
    }
  };
}());

});
