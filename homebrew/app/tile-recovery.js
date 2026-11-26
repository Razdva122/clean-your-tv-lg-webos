window.HomeI18n.ready(function () {
  'use strict';
  var bound = window.CYTVTileEdition;
  var edition = bound;
  if (bound === null) {
    try {
      edition = localStorage.getItem('cytv.tile.home');
    } catch (_) {}
  }
  var doc = document;
  var statusRequested = window.location.hash === '#status';
  var known = edition === 'root' || edition === 'no-root';
  var panel = doc.getElementById('tileActions');
  var open = doc.getElementById('retry');
  var recover = doc.getElementById('recover');
  var setup = doc.getElementById('setup');
  var main = doc.getElementById('tile-main');
  var report = doc.getElementById('tile-report-body');
  var issue = doc.getElementById('tile-issue');
  var openSaved = doc.getElementById('open-report');
  var save = doc.getElementById('save-report');
  var diagnostics = window.InstallerDiagnostics;
  var reason = !known
    ? 'tile_edition_unconfirmed'
    : statusRequested
      ? null
      : 'tile_home_unavailable';
  function t(key) {
    var text = window.InstallerDiagnosticI18n(key);
    return text === key ? window.HomeI18n.t(key) : text;
  }
  function showReport(value, persisted, entry) {
    main.hidden = true;
    report.hidden = false;
    report.textContent = '';
    var heading = doc.createElement('h2');
    heading.textContent = t('diagnosticTitle');
    report.appendChild(heading);
    diagnostics.render(report, value, t, persisted);
    var back = doc.createElement('button');
    back.type = 'button';
    back.id = 'back';
    back.textContent = t('Back');
    back.onclick = function () {
      report.hidden = true;
      main.hidden = false;
      showIssue();
      entry.focus();
      entry.scrollIntoView(false);
    };
    report.appendChild(back);
    back.focus();
  }
  function showIssue() {
    issue.textContent = '';
    if (reason)
      diagnostics.explain(
        issue,
        diagnostics.record('recovery', null, reason),
        t
      );
    save.textContent = t('saveDiagnostic');
    save.hidden = !reason;
    openSaved.textContent = t('viewDiagnostic');
    openSaved.hidden = !diagnostics.load();
  }
  save.onclick = function () {
    if (!reason) return;
    var value = diagnostics.record('recovery', null, reason);
    showReport(value, diagnostics.save(value), save);
  };
  openSaved.onclick = function () {
    var value = diagnostics.load();
    if (value) showReport(value, true, openSaved);
  };
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
      showIssue();
      recover.focus();
    }
    window.SystemUpdates.open({
      edition: edition,
      standalone: true,
      singleTile: true,
      recovery: true,
      onClose: back,
      fallback: function () {
        reason = 'update_service_unavailable';
        window.SystemUpdates.openExternal({ edition: edition, onClose: back });
      }
    });
  };
  function buttons() {
    return [open, recover, setup, save, openSaved].filter(function (button) {
      return !button.hidden && !button.disabled;
    });
  }
  showIssue();
  var available = buttons();
  if (available.length) available[0].focus();
  if (known && statusRequested) recover.click();
  doc.addEventListener('keydown', function (event) {
    if (panel.hidden) return;
    var key = event.keyCode;
    if (key === 461 || key === 27) {
      event.preventDefault();
      if (!report.hidden) doc.getElementById('back').click();
      else window.close();
    } else if (report.hidden && [37, 38, 39, 40].indexOf(key) >= 0) {
      var available = buttons();
      if (!available.length) return;
      event.preventDefault();
      var delta = key === 37 || key === 38 ? -1 : 1;
      var button =
        available[
          (available.indexOf(doc.activeElement) + available.length + delta) %
            available.length
        ];
      button.focus();
      button.scrollIntoView(false);
    }
  });
});
