(function (root) {
  'use strict';
  if (root.CYTVTileLaunch.openDebloat()) return;
  var bridge = root.InstallerBridge,
    i18n = root.InstallerI18n,
    diagnostics = root.InstallerDiagnostics,
    progress = root.InstallerProgress,
    doc = root.document,
    content = doc.getElementById('content'),
    hint = doc.getElementById('hint'),
    key = 'cytv.installer.operation',
    cleanKey = 'cytv.installer.clean-removal';
  var inspected = null,
    job = null,
    operation = null,
    poll = null,
    busy = false,
    confirmation = null,
    opener = null,
    screen = 'checking',
    message = null,
    accessDenied = false,
    transportFailure = null,
    runtimePreparation = null,
    reportView = null,
    cleanOperation = null,
    cleanResult = null,
    cleanFailure = null,
    cleanStorageFailure = false,
    cleanTileResult = null;
  function t(k) {
    var text = root.InstallerDiagnosticI18n(k);
    return text === k ? i18n.t(k) : text;
  }
  function remember(id) {
    if (!/^[a-f0-9]{32}$/.test(id)) throw new Error('invalid_request');
    root.localStorage.setItem(key, id);
    operation = id;
  }
  function dailyHome(edition) {
    try {
      if (edition) root.localStorage.setItem('cytv.tile.home', edition);
      else root.localStorage.removeItem('cytv.tile.home');
      return root.localStorage.getItem('cytv.tile.home') === edition;
    } catch (_) {
      return false;
    }
  }
  function forgetOperation() {
    operation = null;
    try {
      root.localStorage.removeItem(key);
    } catch (_) {}
  }
  try {
    var saved = root.localStorage.getItem(key);
    if (/^[a-f0-9]{32}$/.test(saved || '')) operation = saved;
    var savedClean = root.localStorage.getItem(cleanKey);
    if (/^[a-f0-9]{32}$/.test(savedClean || '')) cleanOperation = savedClean;
  } catch (_) {}
  function element(tag, text, className) {
    var node = doc.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function paragraph(keyName) {
    content.appendChild(element('p', t(keyName)));
  }
  function controls() {
    var node = element('div', undefined, 'actions');
    content.appendChild(node);
    return node;
  }
  function button(parent, id, text, action, style) {
    var node = element('button', text, style);
    node.id = id;
    node.type = 'button';
    node.onclick = action;
    parent.appendChild(node);
    return node;
  }
  function focus(id) {
    var target =
      doc.getElementById(id) ||
      content.querySelector('button:not([disabled])') ||
      doc.getElementById('language');
    if (target) {
      target.focus();
      target.scrollIntoView(false);
    }
  }
  function begin(name, title) {
    screen = name;
    clearTimeout(poll);
    content.textContent = '';
    content.removeAttribute('data-confirm-action');
    content.removeAttribute('data-clean-state');
    content.removeAttribute('data-clean-stage');
    content.setAttribute('data-screen', name);
    content.appendChild(element('h2', t(title)));
    doc.getElementById('language').textContent = t('language');
    hint.textContent = t('navigation');
  }
  function observedChecks() {
    return progress.observe(
      inspected,
      job,
      transportFailure,
      screen === 'checking',
      runtimePreparation
    );
  }
  function drawChecks() {
    var checks = observedChecks(),
      installation = job && job.action === 'install',
      names = installation ? progress.installation : progress.preflight,
      label = function (key) {
        return root.InstallerProgressText(doc.documentElement.lang, key);
      },
      section = element('section', undefined, 'check-panel'),
      title = element(
        'h3',
        label(installation ? 'installationTitle' : 'preflightTitle')
      ),
      list = element('ol', undefined, 'check-steps');
    title.id = 'setup-checklist-title';
    section.id = 'setup-checklist';
    section.setAttribute('aria-labelledby', title.id);
    section.appendChild(title);
    names.forEach(function (key) {
      var status = checks[key],
        row = element('li', undefined, 'check-step check-' + status),
        icon = element(
          'span',
          { pending: '', running: '', pass: '✓', fail: '!', unknown: '?' }[
            status
          ],
          'check-marker'
        ),
        name = element('span', label(key), 'check-name');
      row.setAttribute('data-check', key);
      row.setAttribute('data-status', status);
      if (status === 'running') row.setAttribute('aria-current', 'step');
      icon.setAttribute('aria-hidden', 'true');
      row.appendChild(icon);
      row.appendChild(name);
      row.appendChild(element('span', label(status), 'check-status'));
      list.appendChild(row);
    });
    section.appendChild(list);
    var existing = doc.getElementById(section.id);
    if (existing) content.replaceChild(section, existing);
    else content.appendChild(section);
  }
  function ask(action, from, copy) {
    confirmation = action;
    opener = from;
    begin(
      'confirm',
      action === 'install'
        ? 'review'
        : action === 'clean-remove'
          ? 'remove'
          : action === 'remove-installer'
            ? 'removeInstaller'
            : action === 'activate'
              ? 'activate'
              : action === 'restore'
                ? 'restore'
                : 'prerequisites'
    );
    content.setAttribute('data-confirm-action', action);
    paragraph(copy);
    if (action === 'clean-remove') paragraph('cleanKeepInstaller');
    var actions = controls();
    button(actions, 'cancel', t('cancel'), cancel);
    button(actions, 'confirm', t('confirm'), submit, 'primary');
    focus('cancel');
  }
  function cancel() {
    confirmation = null;
    render();
    focus(opener);
  }
  function versions() {
    var v = inspected.installation.versions;
    if (!v || typeof v.root !== 'string') return;
    var node = element('p', 'Clean Your TV · ' + v.root);
    node.id = 'versions';
    content.appendChild(node);
  }
  function canInstall(result) {
    return (
      result.state === 'fresh' &&
      result.installation &&
      result.installation.can_install === true &&
      result.installation.migrate_available === false
    );
  }
  function managedHome(result) {
    return (
      result &&
      result.state === 'installed' &&
      result.installation &&
      result.installation.can_maintain === true &&
      result.installation.tile_protocol === 1
    );
  }
  function canPrepareForSetup() {
    return (
      inspected.state === 'prerequisites' &&
      !operation &&
      /^[a-f0-9]{64}$/.test(inspected.payload_sha256 || '')
    );
  }
  function addDiagnostics(value, code, hideAdvice) {
    var data = null;
    var actions = content.querySelector('.actions');
    if (value || code) {
      var checks = observedChecks();
      var order =
        value && value.action === 'install'
          ? progress.installation.concat(progress.preflight)
          : progress.preflight;
      var failed = order.filter(function (key) {
        return checks[key] === 'fail';
      });
      data = diagnostics.record(
        'setup',
        Object.assign({}, inspected, value, {
          checks: checks,
          tv: (value && value.tv) || (inspected && inspected.tv),
          phase:
            code === 'homebrew_exec_denied'
              ? 'homebrew-access'
              : failed[0] || (value && value.phase)
        }),
        code
      );
    }
    if (data && !hideAdvice && code !== 'homebrew_exec_denied') {
      var description = element('div');
      diagnostics.explain(description, data, t);
      content.insertBefore(description, actions);
    }
    var previous = diagnostics.load();
    if (!data && !previous) return;
    actions = actions || controls();
    if (data) {
      var save = button(
        actions,
        'save-report',
        t('saveDiagnostic'),
        function () {
          openReport(data, diagnostics.save(data), 'save-report');
        }
      );
      var refreshButton = actions.querySelector('#refresh');
      actions.insertBefore(
        save,
        refreshButton ? refreshButton.nextSibling : actions.firstChild
      );
    }
    if (previous)
      button(actions, 'open-report', t('viewDiagnostic'), function () {
        openReport(previous, true, 'open-report');
      });
  }
  function openReport(value, saved, entry) {
    reportView = { value: value, saved: saved, entry: entry };
    renderReport();
  }
  function renderReport() {
    begin('diagnostic-report', 'diagnosticTitle');
    diagnostics.render(content, reportView.value, t, reportView.saved);
    button(controls(), 'back', t('back'), closeReport, 'primary');
    focus('back');
  }
  function closeReport() {
    var entry = reportView.entry;
    reportView = null;
    render();
    focus(entry);
  }
  function failureCode(error, action) {
    if (error && error.diagnosticCode) return error.diagnosticCode;
    if (error && error.message === 'runtime_unconfirmed')
      return 'runtime_unconfirmed';
    if (operation) return 'status_unavailable';
    if (action === 'prepare-runtime') return 'runtime_unconfirmed';
    return 'installer_unavailable';
  }
  var cleanStages = {
    requested: 'cleanRestoring',
    'original-writers-fenced': 'cleanRestoring',
    'controls-restored': 'restoreDone',
    'package-removal': 'cleanPackages',
    'private-cleanup': 'cleanFiles',
    'restart-required': 'restartNeeded',
    'verified-clean': 'cleanVerified'
  };
  function cleanVerified() {
    return (
      cleanResult &&
      cleanResult.state === 'complete' &&
      cleanResult.current === true &&
      cleanResult.restart_required !== true
    );
  }
  function canContinueClean() {
    return (
      cleanResult &&
      !cleanFailure &&
      cleanResult.state !== 'complete' &&
      (cleanResult.can_resume === true ||
        (cleanResult.state === 'unknown' &&
          cleanResult.stage === 'unknown' &&
          cleanResult.code === 'unknown-operation'))
    );
  }
  function renderClean() {
    var result = cleanResult || { action: 'remove', state: 'unknown' };
    var tileRemoved = cleanTileResult === 'done';
    var state =
      cleanVerified() || tileRemoved
        ? 'complete'
        : result.state === 'complete'
          ? 'unknown'
          : result.state;
    var stage = Object.prototype.hasOwnProperty.call(cleanStages, result.stage)
      ? result.stage
      : null;
    var pending = state === 'pending' || busy;
    begin('clean-removal', 'remove');
    content.setAttribute('data-clean-state', pending ? 'pending' : state);
    if (stage && !(stage === 'verified-clean' && !cleanVerified()))
      content.setAttribute('data-clean-stage', stage);
    if (cleanTileResult) paragraph(cleanTileResult);
    else if (cleanVerified()) paragraph('cleanVerified');
    else if (result.restart_required === true) {
      paragraph('restartNeeded');
      paragraph('restartAndRetry');
    } else if (pending) {
      paragraph(stage ? cleanStages[stage] : 'checking');
    } else if (canContinueClean()) paragraph('cleanContinue');
    var actions = controls();
    if (!tileRemoved)
      button(actions, 'refresh', t('refresh'), refresh, 'primary').disabled =
        busy;
    if (!busy && canContinueClean())
      button(
        actions,
        'continue-removal',
        t(
          result.restart_required === true
            ? 'cleanContinueAfterRestart'
            : 'continueOriginal'
        ),
        function () {
          if (canContinueClean()) requestClean('cleanRemove');
        }
      );
    if (!busy && cleanVerified() && !cleanTileResult) {
      button(
        actions,
        'remove-installer',
        t('removeInstaller'),
        function () {
          ask('remove-installer', 'remove-installer', 'removeInstallerConfirm');
        },
        'danger'
      );
    }
    button(actions, 'close', t('close'), close).disabled = busy;
    addDiagnostics(
      !busy &&
        !tileRemoved &&
        (cleanFailure || state !== 'pending' || result.restart_required)
        ? result
        : null,
      cleanFailure,
      cleanVerified() ||
        result.restart_required === true ||
        (canContinueClean() && result.code === 'removal-pending') ||
        !!cleanTileResult
    );
    focus(tileRemoved ? 'close' : 'refresh');
    if (
      !busy &&
      pending &&
      !doc.hidden &&
      !result.restart_required &&
      !canContinueClean()
    )
      poll = setTimeout(refresh, 8000);
  }
  function requestClean(method) {
    if (busy || !cleanOperation) return;
    var previous = doc.activeElement && doc.activeElement.id;
    busy = true;
    cleanFailure = null;
    cleanTileResult = null;
    if (method !== 'cleanStatus') cleanResult = null;
    renderClean();
    Promise.resolve()
      .then(function () {
        return bridge[method](cleanOperation);
      })
      .then(function (result) {
        if (
          result.action !== 'remove' ||
          ['pending', 'recovery_required', 'complete', 'unknown'].indexOf(
            result.state
          ) < 0 ||
          (result.operation !== undefined &&
            result.operation !== cleanOperation)
        )
          throw new Error('homebrew_invalid_reply');
        if (method === 'removeInstaller') {
          if (
            result.code === 'installer-removed' &&
            result.state === 'complete' &&
            result.current === true
          ) {
            cleanTileResult = 'done';
          } else {
            cleanTileResult = 'cleanTileUnverified';
            cleanFailure = result.code || 'status_unavailable';
          }
        } else cleanResult = result;
        if (cleanVerified()) dailyHome(null);
      })
      .catch(function (error) {
        cleanResult = null;
        if (method === 'removeInstaller')
          cleanTileResult = 'cleanTileUnverified';
        cleanFailure =
          error.diagnosticCode ||
          (error.message === 'homebrew_invalid_reply'
            ? error.message
            : 'status_unavailable');
      })
      .then(function () {
        busy = false;
        render();
        focus(previous);
      });
  }
  function render() {
    if (reportView) {
      renderReport();
      return;
    }
    if (cleanOperation) {
      renderClean();
      return;
    }
    if (accessDenied) {
      begin('homebrew-access', 'homebrewDeniedTitle');
      drawChecks();
      paragraph('homebrewDeniedBody');
      if (operation) {
        paragraph('lost');
        content.appendChild(
          element('p', t('request') + ': ' + operation, 'details')
        );
      }
      var denied = controls();
      button(denied, 'refresh', t('refresh'), refresh);
      button(denied, 'close', t('close'), close);
      addDiagnostics(job, 'homebrew_exec_denied');
      focus('refresh');
      return;
    }
    if (!inspected) {
      begin('checking', 'checking');
      drawChecks();
      return;
    }
    if (job) {
      var pending =
          job.state === 'pending' ||
          (job.state === 'complete' &&
            job.current === true &&
            job.activation &&
            job.activation.state === 'pending'),
        unknown = job.state === 'unknown';
      begin(
        pending ? 'progress' : 'recovery',
        pending ? 'progress' : 'recovery'
      );
      if (!job.action || job.action === 'install') drawChecks();
      if (
        pending ||
        message === 'activationUnverified' ||
        unknown ||
        message === 'lost'
      )
        paragraph(message || (pending ? 'progressBody' : 'unknown'));
      var jobs = controls();
      button(jobs, 'refresh', t('refresh'), refresh, 'primary');
      if (
        job.can_resume === true &&
        (job.action === 'install' || job.action === 'remove')
      )
        button(
          jobs,
          'resume',
          t('continueOriginal') +
            ' · ' +
            t(job.action === 'install' ? 'install' : 'remove'),
          function () {
            ask('resume', 'resume', 'resumeConfirm');
          }
        );
      button(jobs, 'restore', t('restore'), function () {
        ask('restore', 'restore', 'restoreConfirm');
      });
      button(jobs, 'close', t('close'), close);
      button(jobs, 'details', t('details'), function () {
        var old = doc.getElementById('technical');
        if (old) {
          old.parentNode.removeChild(old);
          return;
        }
        var node = element('div', undefined, 'details');
        if (operation)
          node.appendChild(element('p', t('request') + ': ' + operation));
        node.appendChild(
          element(
            'p',
            JSON.stringify(diagnostics.record('setup', job, transportFailure))
          )
        );
        node.id = 'technical';
        content.appendChild(node);
      });
      addDiagnostics(
        !pending || transportFailure ? job : null,
        transportFailure
      );
      focus('refresh');
      if (pending && !doc.hidden) poll = setTimeout(pollStatus, 8000);
      return;
    }
    var state = inspected.state;
    if (runtimePreparation === 'fail' || runtimePreparation === 'unknown') {
      begin('prerequisites', 'prerequisites');
      drawChecks();
      var runtimeActions = controls();
      button(runtimeActions, 'refresh', t('refresh'), refresh, 'primary');
      button(runtimeActions, 'close', t('close'), close);
      addDiagnostics(inspected, transportFailure);
    } else if (state === 'prerequisites' && !canPrepareForSetup()) {
      begin('prerequisites', 'prerequisites');
      drawChecks();
      paragraph('runtimeBody');
      button(
        controls(),
        'prepare',
        t('prepare'),
        function () {
          ask('prepare-runtime', 'prepare', 'runtimeConfirm');
        },
        'primary'
      );
      addDiagnostics(inspected, transportFailure);
    } else if (managedHome(inspected)) {
      begin('installed', 'installed');
      versions();
      paragraph(message || 'readyHome');
      var maintenance = controls();
      button(
        maintenance,
        'activate',
        t('activate'),
        function () {
          ask('activate', 'activate', 'activateConfirm');
        },
        'primary'
      );
      button(maintenance, 'restore', t('restore'), function () {
        ask('restore', 'restore', 'restoreConfirm');
      });
      button(
        maintenance,
        'remove',
        t('remove'),
        function () {
          ask('clean-remove', 'remove', 'removeProductConfirm');
        },
        'danger'
      );
      paragraph('retained');
      if (cleanStorageFailure) paragraph('cleanRequestNotSaved');
      addDiagnostics(transportFailure ? inspected : null, transportFailure);
    } else if (
      (state === 'installed' &&
        inspected.installation &&
        inspected.installation.can_maintain === true) ||
      (state === 'fresh' &&
        inspected.installation &&
        inspected.installation.migrate_available === true)
    ) {
      begin('existing-installation', 'recovery');
      var existing = controls();
      button(existing, 'refresh', t('refresh'), refresh);
      button(existing, 'close', t('close'), close);
      addDiagnostics(inspected, 'existing_installation');
    } else if (canInstall(inspected) || canPrepareForSetup()) {
      var preparing = state === 'prerequisites';
      begin(preparing ? 'prerequisites' : 'review', 'review');
      drawChecks();
      paragraph('reviewBody');
      if (preparing) paragraph('runtimeBody');
      var actions = controls();
      button(
        actions,
        'install',
        t('installAndActivate'),
        function () {
          ask(
            'install',
            'install',
            preparing ? 'prepareInstallConfirm' : 'installConfirm'
          );
        },
        'primary'
      );
      button(actions, 'close', t('close'), close);
      addDiagnostics(transportFailure ? inspected : null, transportFailure);
    } else if (state === 'external_setup' || state === 'edition_unconfirmed') {
      begin('edition-advice', 'unsupported');
      drawChecks();
      var next = controls();
      button(next, 'refresh', t('refresh'), refresh);
      button(next, 'close', t('close'), close);
      addDiagnostics(inspected, transportFailure);
    } else if (state === 'unsupported') {
      begin('unsupported', 'unsupported');
      drawChecks();
      button(controls(), 'refresh', t('refresh'), refresh);
      addDiagnostics(inspected, transportFailure);
    } else {
      begin('recovery', 'recovery');
      drawChecks();
      var recover = controls();
      button(recover, 'refresh', t('refresh'), refresh);
      button(recover, 'restore', t('restore'), function () {
        ask('restore', 'restore', 'restoreConfirm');
      });
      addDiagnostics(inspected, transportFailure);
    }
    focus('');
  }
  // Package completion and completion of the requested Home activation are
  // independent. Reopening this screen only reads the original operation.
  function activationStatus(status) {
    if (
      status.action !== 'install' ||
      status.state !== 'complete' ||
      !status.activation
    )
      return false;
    var state = status.activation.state;
    if (state === 'finished' || state === 'superseded') {
      message = null;
      job = null;
      forgetOperation();
      return true;
    }
    if (
      status.current === true &&
      (state === 'active' || state === 'cancelled')
    ) {
      message = state === 'active' ? 'activationDone' : 'activationCancelled';
      job = null;
      forgetOperation();
      return true;
    }
    job = status;
    message =
      state === 'pending' && status.current === true
        ? 'activationPending'
        : 'activationUnverified';
    return true;
  }
  function refresh(focusId) {
    if (busy) return;
    if (cleanOperation) return requestClean('cleanStatus');
    busy = true;
    clearTimeout(poll);
    var previous = doc.activeElement && doc.activeElement.id;
    if (!inspected) {
      begin('checking', 'checking');
      drawChecks();
    }
    bridge
      .inspect({ prepareSupervisor: true })
      .then(function (result) {
        accessDenied = false;
        transportFailure = null;
        if (message === 'lost' || message === 'failed') message = null;
        inspected = result;
        runtimePreparation = null;
        var active = result.active_operation;
        if (active && /^[a-f0-9]{32}$/.test(active.operation || ''))
          remember(active.operation);
        if (
          operation &&
          result.state !== 'prerequisites' &&
          result.state !== 'unsupported'
        )
          return bridge.status(operation).then(function (status) {
            if (activationStatus(status)) return;
            if (
              status.state === 'complete' &&
              (status.current === true ||
                (result.state === 'installed' &&
                  result.installation &&
                  result.installation.can_maintain === true))
            ) {
              job = null;
              if (status.action === 'remove') {
                dailyHome(null);
                forgetOperation();
              }
            } else job = status;
          });
        job = null;
      })
      .then(
        function () {
          busy = false;
          if (
            !operation &&
            !job &&
            managedHome(inspected) &&
            !inspected.active_operation
          ) {
            var savedHome = dailyHome('root');
            if (savedHome && root.location.hash === '#open') {
              // Continue to the verified Home without changing button routing.
              root.location.replace('index.html');
              return;
            }
          }
          render();
          focus(typeof focusId === 'string' ? focusId : previous);
        },
        function (error) {
          busy = false;
          accessDenied = error.message === 'homebrew_exec_denied';
          transportFailure = failureCode(error, 'inspect');
          if (operation) {
            job = job || { state: 'unknown' };
            message = 'lost';
          } else {
            inspected = { state: 'unsupported' };
          }
          render();
        }
      );
  }
  function pollStatus() {
    if (busy || !operation || doc.hidden) return;
    busy = true;
    var previous = doc.activeElement && doc.activeElement.id;
    bridge.status(operation).then(
      function (result) {
        busy = false;
        transportFailure = null;
        if (message === 'lost') message = null;
        job = result;
        if (activationStatus(result)) {
          if (!job) {
            refresh();
            return;
          }
          render();
          focus(previous);
          return;
        }
        if (result.state === 'complete' && result.current === true) {
          job = null;
          refresh();
          return;
        }
        render();
        focus(previous);
      },
      function (error) {
        busy = false;
        accessDenied = error.message === 'homebrew_exec_denied';
        transportFailure = failureCode(error, 'status');
        message = 'lost';
        render();
        focus(previous);
      }
    );
  }
  function uuid() {
    if (!root.crypto || !root.crypto.getRandomValues)
      throw new Error('secure_id_required');
    var bytes = new Uint8Array(16);
    root.crypto.getRandomValues(bytes);
    return Array.prototype.map
      .call(bytes, function (b) {
        return ('0' + b.toString(16)).slice(-2);
      })
      .join('');
  }
  function startInstall() {
    remember(uuid());
    job = {
      operation: operation,
      action: 'install',
      state: 'pending',
      stage: 'submitting'
    };
    message = null;
    render();
    var options = {
      operation: operation,
      candidate: inspected.candidate_sha256
    };
    options.prepareSupervisor = true;
    options.migrate = false;
    options.activateAfterInstall = true;
    return bridge.start(options);
  }

  function prepareRuntime() {
    runtimePreparation = 'running';
    begin('checking', 'checking');
    drawChecks();
    paragraph('runtimeBody');
    return bridge.prepareRuntime().then(function (result) {
      if (result.state !== 'runtime_ready')
        throw new Error('runtime_unconfirmed');
      runtimePreparation = 'pass';
      drawChecks();
      return result;
    });
  }
  function prepareAndInstall() {
    var reviewedPayload = inspected.payload_sha256;
    return prepareRuntime()
      .then(function () {
        return bridge.inspect({ prepareSupervisor: true });
      })
      .then(function (current) {
        if (
          current.payload_sha256 !== reviewedPayload ||
          current.active_operation ||
          !canInstall(current) ||
          !/^[a-f0-9]{64}$/.test(current.candidate_sha256 || '') ||
          operation ||
          doc.hidden
        )
          return null;
        inspected = current;
        runtimePreparation = null;
        return startInstall();
      });
  }
  function submit() {
    if (busy || !confirmation) return;
    var action = confirmation;
    confirmation = null;
    if (action === 'clean-remove') {
      try {
        var id = root.localStorage.getItem(cleanKey);
        if (/^[a-f0-9]{32}$/.test(id || '')) {
          cleanOperation = id;
          refresh();
          return;
        }
        id = uuid();
        root.localStorage.setItem(cleanKey, id);
        if (root.localStorage.getItem(cleanKey) !== id)
          throw new Error('request_not_saved');
        cleanOperation = id;
      } catch (_) {
        cleanStorageFailure = true;
        render();
        focus('remove');
        return;
      }
      requestClean('cleanRemove');
      return;
    }
    if (action === 'remove-installer') {
      if (cleanVerified()) requestClean('removeInstaller');
      else refresh();
      return;
    }
    busy = true;
    var promise;
    try {
      if (action === 'install') {
        promise = canPrepareForSetup() ? prepareAndInstall() : startInstall();
      } else if (action === 'prepare-runtime') promise = prepareRuntime();
      else if (action === 'activate') promise = bridge.activate();
      else if (action === 'resume') {
        if (!job || job.can_resume !== true) throw new Error('not_recoverable');
        promise = bridge.resume(operation, job.action);
        job.can_resume = false;
      } else promise = bridge.restore();
    } catch (error) {
      busy = false;
      transportFailure = failureCode(error, action);
      if (runtimePreparation === 'running') runtimePreparation = 'unknown';
      message = 'failed';
      render();
      return;
    }
    if (action === 'activate' || action === 'restore') {
      begin('checking', 'checking');
      paragraph(action === 'activate' ? 'activateConfirm' : 'restoreConfirm');
    }
    promise.then(
      function (result) {
        busy = false;
        transportFailure = null;
        if (result === null) {
          refresh();
          return;
        }
        if (action === 'install' || action === 'resume') {
          job = result.action
            ? result
            : Object.assign(
                { action: action === 'resume' ? job.action : action },
                result
              );
          message = null;
          render();
          return;
        }
        if (result.state === 'complete' || result.state === 'runtime_ready') {
          message =
            action === 'activate'
              ? 'activationDone'
              : action === 'restore'
                ? 'restoreDone'
                : null;
          refresh();
        } else {
          message = 'failed';
          inspected = result;
          render();
        }
      },
      function (error) {
        busy = false;
        accessDenied = error.message === 'homebrew_exec_denied';
        transportFailure = failureCode(error, action);
        if (runtimePreparation === 'running')
          runtimePreparation =
            transportFailure === 'runtime_unconfirmed' ? 'fail' : 'unknown';
        message = operation ? 'lost' : 'failed';
        if (operation) job = job || { state: 'unknown' };
        render();
      }
    );
  }
  function close() {
    if (root.close) root.close();
  }
  doc.getElementById('language').onclick = function () {
    if (busy) return;
    var old = screen;
    begin('language', 'language');
    var list = controls();
    Object.keys(i18n.names).forEach(function (code) {
      var choice = button(list, 'lang-' + code, i18n.names[code], function () {
        i18n.set(code);
        render();
        focus('language');
      });
      choice.lang = code;
    });
    button(list, 'back', t('back'), function () {
      screen = old;
      render();
      focus('language');
    });
    focus('lang-' + doc.documentElement.lang);
  };
  doc.addEventListener('keydown', function (event) {
    var code = event.keyCode,
      keyName = event.key,
      back =
        code === 461 ||
        code === 27 ||
        code === 8 ||
        keyName === 'Escape' ||
        keyName === 'Backspace';
    if (back) {
      event.preventDefault();
      if (busy) return;
      if (screen === 'diagnostic-report') closeReport();
      else if (screen === 'confirm') cancel();
      else if (screen === 'language') {
        render();
        focus('language');
      } else if (screen === 'progress') {
        hint.textContent = t('progressBody');
      } else close();
      return;
    }
    if (keyName === 'Enter' || code === 13) {
      if (doc.activeElement && doc.activeElement.tagName === 'BUTTON') {
        event.preventDefault();
        doc.activeElement.click();
      }
      return;
    }
    if (
      [37, 38, 39, 40].indexOf(code) < 0 &&
      ['ArrowLeft', 'ArrowUp', 'ArrowRight', 'ArrowDown'].indexOf(keyName) < 0
    )
      return;
    event.preventDefault();
    var nodes = Array.prototype.filter.call(
        doc.querySelectorAll('button'),
        function (n) {
          return !n.disabled && !n.hidden && n.offsetWidth > 0;
        }
      ),
      index = nodes.indexOf(doc.activeElement),
      delta =
        code === 37 ||
        code === 38 ||
        keyName === 'ArrowLeft' ||
        keyName === 'ArrowUp'
          ? -1
          : 1;
    if (nodes.length) {
      var next = nodes[(index + delta + nodes.length) % nodes.length];
      next.focus();
      next.scrollIntoView(false);
    }
  });
  doc.addEventListener('visibilitychange', function () {
    clearTimeout(poll);
    if (!doc.hidden && !reportView) refresh();
  });
  doc.addEventListener('webOSRelaunch', function (event) {
    if (root.CYTVTileLaunch.openDebloat(event)) return;
    if (
      !cleanOperation &&
      !operation &&
      !busy &&
      !confirmation &&
      !root.CYTVTileLaunch.maintenanceRequested(event)
    ) {
      try {
        if (root.localStorage.getItem('cytv.tile.home') === 'root') {
          root.location.replace('index.html');
          return;
        }
      } catch (_) {}
    }
    refresh();
  });
  render();
  refresh();
})(window);
