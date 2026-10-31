/* Standard on-TV column picker shared by Root and No-root. */
(function () {
  'use strict';
  var panel, buttons = [], selected = 0, previous;
  function t(text, params) { return window.HomeI18n ? HomeI18n.t(text, params) : text; }
  function isAvailable() { return !!window.HomeLayoutState && window.HomeLayoutState.state().allowColumnOverride !== false; }
  function refreshAvailability(event) {
    var available = isAvailable(), entry = document.getElementById('homeColumns');
    if (isOpen() && !available) close();
    // Hiding the entry can clear activeElement before later layout listeners.
    if (event && entry && document.activeElement === entry) event.homeColumnsFocus = entry;
    if (entry) {
      if (window.HomeLayoutState) entry.textContent = t('Columns: {count}', {count: window.HomeLayoutState.state().columns});
      entry.parentNode.classList.add('home-columns-entry');
      entry.parentNode.setAttribute('aria-hidden', String(!available));
      entry.hidden = !available; entry.parentNode.classList.toggle('hidden', !available);
    }
    return available;
  }
  function isOpen() { return !!panel && !panel.hidden; }
  function focus(index) { selected = (index + buttons.length) % buttons.length; buttons[selected].focus(); }
  function close() {
    panel.hidden = true;
    if (window.ThemeRuntime) ThemeRuntime.resume('columns');
    if (previous && previous.focus) previous.focus();
  }
  function render() {
    var state = window.HomeLayoutState.state();
    buttons.slice(0, 9).forEach(function (button, index) {
      button.textContent = index ? String(index) : t('By theme ({count})', {count: state.themeColumns});
      button.setAttribute('aria-pressed', String(index === (state.override || 0)));
    });
  }
  function build() {
    panel = document.createElement('section'); panel.id = 'homeLayoutPanel'; panel.hidden = true;
    panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true'); panel.setAttribute('aria-labelledby', 'homeLayoutTitle');
    var card = document.createElement('div'); card.className = 'layout-card'; panel.appendChild(card);
    var title = document.createElement('h2'); title.id = 'homeLayoutTitle'; title.textContent = t('Columns'); card.appendChild(title);
    var hint = document.createElement('p'); hint.textContent = t('Choose 1–8 columns. Your choice overrides the theme.'); card.appendChild(hint);
    var choices = document.createElement('div'); choices.className = 'layout-choices'; card.appendChild(choices);
    var error = document.createElement('p'); error.id = 'homeLayoutError'; error.setAttribute('role', 'alert'); card.appendChild(error);
    for (var count = 0; count <= 8; count++) (function (value) {
      var button = document.createElement('button'); button.type = 'button'; button.setAttribute('data-columns', value || 'auto');
      if (value) button.setAttribute('aria-label', t('Columns: {count}', {count: value}));
      button.onclick = function () {
        try { window.HomeLayoutState.setColumns(value || null); error.textContent = ''; render(); }
        catch (_) { error.textContent = t('Could not save columns. Please try again.'); }
      };
      button.onfocus = function () { selected = buttons.indexOf(button); };
      choices.appendChild(button); buttons.push(button);
    }(count));
    var back = document.createElement('button'); back.type = 'button'; back.textContent = t('Back'); back.onclick = close; card.appendChild(back); buttons.push(back);
    back.onfocus = function () { selected = buttons.indexOf(back); };
    document.body.appendChild(panel);
  }
  document.addEventListener('focusin', function (event) {
    if (!isOpen()) return;
    var confirmation = document.getElementById('homeConfirmation'), language = document.getElementById('languagePicker');
    if (confirmation && !confirmation.hidden || language && !language.hidden) return;
    var index = buttons.indexOf(event.target);
    if (index >= 0) selected = index;
    else buttons[selected].focus();
  }, true);
  document.addEventListener('keydown', function (event) {
    if (!isOpen() || [9, 13, 27, 37, 38, 39, 40, 461].indexOf(event.keyCode) < 0) return;
    event.preventDefault(); event.stopImmediatePropagation();
    if (event.keyCode === 27 || event.keyCode === 461) return close();
    if (event.keyCode === 13) { if (!event.repeat) buttons[selected].click(); return; }
    focus(selected + (event.keyCode === 37 || event.keyCode === 38 || event.keyCode === 9 && event.shiftKey ? -1 : 1));
  }, true);
  document.addEventListener('home-layout-change', refreshAvailability);
  window.HomeLayoutPanel = {isOpen: isOpen, isAvailable: isAvailable, refreshAvailability: refreshAvailability, open: function () {
    if (isOpen() || !isAvailable()) return;
    if (!panel) build();
    previous = document.activeElement;
    if (window.ThemeRuntime) ThemeRuntime.suspend('columns');
    panel.hidden = false; document.getElementById('homeLayoutError').textContent = '';
    render(); focus(window.HomeLayoutState.state().override || 0);
  }};
}());
