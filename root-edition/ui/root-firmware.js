(function () {
  'use strict';
  var panel,
    status,
    hint,
    buttons,
    selected = 0,
    state,
    busy = false,
    generation = 0,
    control,
    returnToSettings;
  function t(source) {
    return window.HomeI18n ? window.HomeI18n.t(source) : source;
  }
  function focus(index) {
    selected = index;
    buttons[index].focus();
  }
  function render(reply) {
    state = null;
    buttons[0].disabled = true;
    buttons[0].setAttribute('aria-checked', 'false');
    hint.textContent = '';
    if (
      !reply ||
      reply.returnValue !== true ||
      typeof reply.enabled !== 'boolean'
    )
      return false;
    state = reply;
    buttons[0].disabled = false;
    buttons[0].setAttribute('aria-checked', String(reply.enabled));
    status.textContent = t(
      reply.enabled
        ? 'Homebrew blocking is set to on.'
        : 'Homebrew blocking is set to off.'
    );
    hint.textContent = t(
      'Changes apply after a TV restart. Standby is not enough. Active blocking is not verified here.'
    );
    return true;
  }
  function error(reply) {
    render(reply && reply.status);
    var reasons = {
      'permission-denied':
        'Homebrew denied this app access. Change the setting in Homebrew Channel. On webOS 11, Homebrew needs compatible API permissions.',
      'service-unavailable':
        'Homebrew service is unavailable. Open Homebrew Channel, then check status.',
      'not-root':
        'Homebrew is not running as root. Check root access in Homebrew Channel.',
      unsupported:
        'Homebrew returned an unsupported configuration response. Check its version, then retry.',
      timeout:
        'Homebrew did not respond in time. Check status before trying again.'
    };
    status.textContent = t(
      reply && reply.errorCode === 'changed'
        ? 'The setting changed elsewhere. Check it before trying again.'
        : reply &&
            (reply.errorCode === 'unconfirmed' || reply.errorCode === 'busy')
          ? 'The change was not confirmed. Check status before trying again.'
          : reasons[reply && reply.errorCode] ||
            'Homebrew Channel with root access is required. Check its settings, then retry.'
    );
  }
  function refresh() {
    if (busy) return;
    var current = ++generation;
    state = null;
    buttons[0].disabled = true;
    buttons[0].setAttribute('aria-checked', 'false');
    status.textContent = t('Checking firmware update blocking…');
    hint.textContent = '';
    control
      .get()
      .then(function (reply) {
        if (current !== generation) return;
        if (!render(reply)) error(reply);
        if (!panel.hidden && selected === 0) focus(buttons[0].disabled ? 1 : 0);
      })
      .catch(function () {
        if (current === generation) {
          error();
          if (!panel.hidden && selected === 0) focus(1);
        }
      });
  }
  function change() {
    if (busy || !state || buttons[0].disabled) return;
    var current = ++generation,
      previous = state;
    busy = true;
    buttons.forEach(function (b) {
      b.disabled = true;
    });
    status.textContent = t('Saving firmware update blocking…');
    control
      .set(!previous.enabled, previous.enabled)
      .then(function (reply) {
        if (current !== generation) return;
        busy = false;
        buttons.forEach(function (b) {
          b.disabled = false;
        });
        if (!render(reply)) error(reply);
        focus(buttons[0].disabled ? 1 : 0);
      })
      .catch(function () {
        if (current !== generation) return;
        busy = false;
        buttons.forEach(function (b) {
          b.disabled = false;
        });
        error({ errorCode: 'unconfirmed' });
        focus(1);
      });
  }
  function close() {
    if (busy) return;
    generation++;
    panel.hidden = true;
    if (window.ThemeRuntime) window.ThemeRuntime.resume('firmware');
    returnToSettings();
  }
  function activate(index) {
    if (busy || buttons[index].disabled) return;
    if (index === 0) change();
    else if (index === 1) refresh();
    else close();
  }
  function build() {
    panel = document.createElement('section');
    panel.className = 'root-settings root-firmware';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-label', t('LG firmware updates'));
    var card = document.createElement('div');
    card.className = 'root-settings-card';
    panel.appendChild(card);
    function text(tag, source, name) {
      var element = document.createElement(tag);
      element.textContent = t(source);
      if (name) element.className = name;
      card.appendChild(element);
      return element;
    }
    text('h1', 'LG firmware updates');
    text(
      'p',
      'Uses Homebrew Channel to block LG firmware servers after a TV restart. This also prevents firmware security updates.'
    );
    text(
      'p',
      'Some TVs check for updates before blocking starts. Existing prompts may remain; router blocking may be needed.',
      'settings-warning'
    );
    text(
      'p',
      'Homebrew keeps this setting after Clean Your TV is removed. You can change it in Homebrew Channel.'
    );
    var actions = document.createElement('div');
    actions.className = 'renewal-actions home-routing-actions';
    card.appendChild(actions);
    buttons = [];
    ['Block LG firmware updates', 'Check status', 'Back'].forEach(
      function (label, i) {
        var button = document.createElement('button');
        button.textContent = t(label);
        if (i === 0) {
          button.className = 'home-routing-switch';
          button.setAttribute('role', 'switch');
          button.setAttribute('aria-checked', 'false');
          button.setAttribute(
            'aria-describedby',
            'rootFirmwareStatus rootFirmwareHint'
          );
        }
        button.onclick = function () {
          selected = i;
          activate(i);
        };
        button.onfocus = function () {
          selected = i;
        };
        actions.appendChild(button);
        buttons.push(button);
      }
    );
    status = text('p', '', 'settings-status');
    status.id = 'rootFirmwareStatus';
    status.setAttribute('aria-live', 'polite');
    hint = text('p', '', 'settings-warning');
    hint.id = 'rootFirmwareHint';
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
        if (busy) return;
        if (event.keyCode === 27 || event.keyCode === 461) {
          close();
          return;
        }
        if (event.keyCode === 13) {
          if (!event.repeat) activate(selected);
          return;
        }
        var direction =
          event.keyCode === 37 ||
          event.keyCode === 38 ||
          (event.keyCode === 9 && event.shiftKey)
            ? -1
            : 1;
        for (var count = 1; count <= buttons.length; count++) {
          var next =
            (selected + direction * count + buttons.length) % buttons.length;
          if (!buttons[next].disabled) {
            focus(next);
            return;
          }
        }
      },
      true
    );
  }
  window.RootFirmware = {
    open: function (call, back) {
      if (window.ThemeRuntime) window.ThemeRuntime.suspend('firmware');
      if (busy) return;
      if (!control) control = window.createRootFirmwareControl(call);
      returnToSettings = back;
      if (!panel) build();
      panel.hidden = false;
      selected = 0;
      refresh();
      focus(1);
      // Keep the intended initial focus on the switch once its state is known.
      selected = 0;
    }
  };
})();
