/* Standalone probe: no app launching, context query, media, storage or Home hook. */
(function () {
  'use strict';
  var system = window.webOSSystem || window.PalmSystem;
  var buttons = document.querySelectorAll('#ribbon button');
  var closed = false;
  var timer;

  function mode(value) {
    document.body.setAttribute('data-mode', value === 'overlay' ? 'overlay' : 'full');
    document.getElementById('status').textContent = value === 'overlay' ? 'Overlay · explicit test mode' : 'Fullscreen fallback';
  }
  function close() {
    if (closed) return;
    closed = true;
    window.clearTimeout(timer);
    document.body.setAttribute('data-mode', 'closed');
    window.close();
  }
  function initialMode() {
    try {
      var params = system ? system.launchParams : {};
      if (typeof params === 'string') params = JSON.parse(params);
      // Browser query is for the explicit local preview only, never a TV context hint.
      if (!system && window.location.search === '?mode=overlay') return 'overlay';
      return params && !Array.isArray(params) && params.mode === 'overlay' ? 'overlay' : 'full';
    } catch (_) { return 'full'; }
  }
  document.getElementById('overlay').onclick = function () { mode('overlay'); };
  document.getElementById('full').onclick = function () { mode('full'); };
  document.getElementById('close').onclick = close;
  document.addEventListener('keydown', function (event) {
    if (closed) return;
    var key = event.keyCode;
    if (key === 461 || key === 27) { event.preventDefault(); close(); return; }
    if (key !== 37 && key !== 39) return;
    var index = 0;
    for (var i = 0; i < buttons.length; i++) if (buttons[i] === document.activeElement) index = i;
    buttons[(index + (key === 39 ? 1 : buttons.length - 1)) % buttons.length].focus();
    event.preventDefault();
  });
  // Repeat launch is an explicit dismissal request; it never re-arms the lifetime.
  document.addEventListener('webOSRelaunch', close);
  mode(initialMode());
  buttons[0].focus();
  timer = window.setTimeout(close, 60000);
  if (system && typeof system.activate === 'function') system.activate();
}());
