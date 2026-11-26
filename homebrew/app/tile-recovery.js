window.HomeI18n.ready(function () {
  'use strict';
  var bound = window.CYTVTileEdition;
  var edition = bound;
  if (bound === null) {
    try {
      edition = localStorage.getItem('cytv.tile.home');
    } catch (_) {}
  }
  var statusRequested = window.location.hash === '#status';
  document.getElementById('launchFailure').hidden = statusRequested;
  var known = edition === 'root' || edition === 'no-root';
  var panel = document.getElementById('tileActions');
  var open = document.getElementById('retry');
  var recover = document.getElementById('recover');
  var setup = document.getElementById('setup');
  open.disabled = recover.disabled = !known;
  setup.hidden = bound !== null;
  open.onclick = function () {
    window.location.replace('index.html#openHome');
  };
  setup.onclick = function () {
    window.location.replace('setup.html');
  };
  recover.onclick = function () {
    if (!known) return;
    panel.hidden = true;
    function back() {
      panel.hidden = false;
      recover.focus();
    }
    window.SystemUpdates.open({
      edition: edition,
      standalone: true,
      singleTile: true,
      recovery: true,
      onClose: back,
      fallback: function () {
        window.SystemUpdates.openExternal({ edition: edition, onClose: back });
      }
    });
  };
  var buttons = [open, recover, setup].filter(function (button) {
    return !button.hidden && !button.disabled;
  });
  if (buttons.length) buttons[0].focus();
  if (known && statusRequested) recover.click();
  document.addEventListener('keydown', function (event) {
    if (panel.hidden) return;
    var key = event.keyCode;
    if (key === 461 || key === 27) {
      event.preventDefault();
      window.close();
    } else if ([37, 38, 39, 40].indexOf(key) >= 0 && buttons.length) {
      event.preventDefault();
      var delta = key === 37 || key === 38 ? -1 : 1;
      buttons[
        (buttons.indexOf(document.activeElement) + buttons.length + delta) %
          buttons.length
      ].focus();
    }
  });
});
