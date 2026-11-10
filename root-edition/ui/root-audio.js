(function () {
  'use strict';
  var panel,
    status,
    hint,
    buttons,
    selected = 2,
    state = null,
    busy = false,
    generation = 0,
    request,
    back;
  var service = 'luna://com.cleanyourtv.root.preview.service/';
  function t(source) {
    return window.HomeI18n ? window.HomeI18n.t(source) : source;
  }
  function focus(index) {
    selected = index;
    buttons[index].focus();
  }
  function draw(value) {
    state =
      value && value.returnValue === true && typeof value.enabled === 'boolean'
        ? value
        : null;
    buttons[0].textContent = t(
      state && state.needsRestore
        ? 'Restore saved eARC setting'
        : state && state.canRestoreRoute
          ? 'Restore HDMI output'
          : 'Reconnect eARC'
    );
    buttons[0].disabled =
      busy ||
      !state ||
      !(state.needsRestore
        ? state.canRestoreSetting
        : state.canRestart || state.canRestoreRoute);
    buttons[1].setAttribute(
      'aria-checked',
      state ? String(state.enabled) : 'false'
    );
    buttons[1].disabled =
      busy ||
      !state ||
      (!state.enabled &&
        (!state.autoSupported || state.needsRestore || !state.canRestart));
    hint.textContent = t(
      state && state.needsRestore
        ? 'An interrupted attempt may have left eARC off. Restore the saved setting only if you want eARC on.'
        : 'For delayed or missing HDMI sound. Reconnecting briefly interrupts audio.'
    );
    if (!state)
      status.textContent = t(
        'Audio recovery is unavailable. Check LG sound settings, then retry.'
      );
    else if (busy)
      status.textContent = t(
        'Reconnecting. You can go back while recovery finishes.'
      );
    else if (state.enabled && !state.observer)
      status.textContent = t(
        'Automatic recovery is saved but its power observer is unavailable. Check status.'
      );
    else if (state.needsRestore)
      status.textContent = t(
        'A previous attempt needs explicit setting restoration.'
      );
    else if (state.last && state.last.result === 'settings-restored')
      status.textContent = t('eARC setting restored. Check the sound.');
    else if (state.last && state.last.result === 'route-restored')
      status.textContent = t('HDMI output restored. Check the sound.');
    else if (state.last && state.last.result !== 'unsupported')
      status.textContent = t(
        'Audio recovery was not confirmed. Check LG sound settings, then retry.'
      );
    else
      status.textContent = t(
        state.canRestart || state.canRestoreRoute
          ? 'HDMI recovery is available.'
          : 'This audio mode cannot be reconnected here. Use LG sound settings.'
      );
  }
  function refresh() {
    var current = ++generation;
    draw(null);
    panel.setAttribute('aria-busy', 'true');
    buttons[2].disabled = true;
    status.textContent = t('Checking HDMI audio…');
    return request(service + 'status', { audio: 'status' }, 60000)
      .then(function (reply) {
        if (current !== generation) return;
        panel.setAttribute('aria-busy', 'false');
        buttons[2].disabled = false;
        draw(reply);
        if (!panel.hidden && buttons[selected].disabled) focus(2);
      })
      .catch(function () {
        if (current === generation) {
          panel.setAttribute('aria-busy', 'false');
          buttons[2].disabled = false;
          draw(null);
        }
      });
  }
  function change(index) {
    if (busy || !state || buttons[index].disabled) return;
    var current = ++generation,
      old = state;
    busy = true;
    draw(old);
    var method = 'enable';
    var payload =
      index === 1
        ? { audio: 'configure', enabled: !old.enabled }
        : {
            audio: 'recover',
            operation: old.needsRestore
              ? 'restore-setting'
              : old.canRestoreRoute
                ? 'restore-hdmi'
                : 'restart-earc'
          };
    request(service + method, payload, 60000)
      .then(function (reply) {
        busy = false;
        if (current !== generation) {
          if (!panel.hidden) refresh();
          return;
        }
        return refresh().then(function () {
          if (!panel.hidden && (!reply || reply.returnValue !== true))
            status.textContent = t(
              'Audio recovery was not confirmed. Check LG sound settings, then retry.'
            );
          if (!panel.hidden) focus(buttons[index].disabled ? 2 : index);
        });
      })
      .catch(function () {
        busy = false;
        if (current !== generation) {
          if (!panel.hidden) refresh();
          return;
        }
        draw(null);
        if (!panel.hidden) focus(2);
      });
  }
  function close() {
    generation++;
    panel.hidden = true;
    if (window.ThemeRuntime) window.ThemeRuntime.resume('audio');
    back();
  }
  function activate(index) {
    if (buttons[index].disabled) return;
    if (index < 2) change(index);
    else if (index === 2) refresh();
    else close();
  }
  function build() {
    panel = document.createElement('section');
    panel.className = 'root-settings root-audio';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-label', t('HDMI sound'));
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
    text('h1', 'HDMI sound');
    hint = text(
      'p',
      'For delayed or missing HDMI sound. Reconnecting briefly interrupts audio.'
    );
    var actions = document.createElement('div');
    actions.className = 'renewal-actions';
    card.appendChild(actions);
    buttons = [];
    [
      'Reconnect eARC',
      'Recover after power-on',
      'Check status',
      'Back'
    ].forEach(function (label, index) {
      var button = document.createElement('button');
      button.textContent = t(label);
      if (index === 1) {
        button.className = 'home-routing-switch';
        button.setAttribute('role', 'switch');
        button.setAttribute('aria-checked', 'false');
        button.setAttribute('aria-describedby', 'rootAudioAutomatic');
      }
      button.onclick = function () {
        selected = index;
        activate(index);
      };
      button.onfocus = function () {
        selected = index;
      };
      actions.appendChild(button);
      buttons.push(button);
    });
    text(
      'p',
      'Experimental. Reconnects after power-on and standby wake, even when sound already works. Off by default.',
      'settings-warning'
    ).id = 'rootAudioAutomatic';
    status = text('p', '', 'settings-status');
    status.setAttribute('aria-live', 'polite');
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
  window.RootAudio = {
    open: function (call, returnToSettings) {
      if (window.ThemeRuntime) window.ThemeRuntime.suspend('audio');
      request = call;
      back = returnToSettings;
      if (!panel) build();
      panel.hidden = false;
      focus(2);
      refresh().then(function () {
        if (!panel.hidden && !busy && state && !buttons[0].disabled) focus(0);
      });
    }
  };
})();
