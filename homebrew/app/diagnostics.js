(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports)
    module.exports = function (environment) {
      return factory(environment, require('./report-format.js'));
    };
  else root.InstallerDiagnostics = factory(root, root.CYTVHomebrewReport);
})(this, function (root, format) {
  'use strict';
  var storageKey = 'cytv.installer.diagnostic.v2',
    legacyStorage = 'cytv.installer.diagnostic.v1',
    fields = format.fields,
    accepted = format.accepted;

  function record(source, result, code) {
    result = result || {};
    var failure = result.failure || {},
      metadata = root.CYTVReportVersion || {},
      suppliedCandidate = root.InstallerCandidate || {},
      installed = (result.installation && result.installation.versions) || {},
      alternative = result.edition === 'no-root' ? result.versions || {} : {},
      productReason = result.installation && result.installation.reason,
      activity =
        result.action === 'remove'
          ? 'uninstall'
          : source === 'recovery'
            ? 'recover'
            : result.action || 'install';
    return format.cleanObservation({
      source: source,
      timestamp: new Date().toISOString(),
      action: activity,
      edition:
        result.edition ||
        root.CYTVTileEdition ||
        (source === 'setup' ? 'root' : null),
      phase:
        typeof result.phase === 'string'
          ? result.phase
          : code === 'homebrew_exec_denied'
            ? 'homebrew-access'
            : null,
      code: accepted(code, format.codes)
        ? code
        : accepted(result.code, format.codes)
          ? result.code
          : productReason,
      state: result.state,
      stage: result.stage,
      detail: accepted(failure.inspect_check, fields.detail)
        ? failure.inspect_check
        : failure.package_rejected === true
          ? 'package_rejected'
          : result.reason ||
            (result.installation && result.installation.reason),
      activation: result.activation && result.activation.state,
      resume: result.resume_reason,
      failure: failure,
      checks: result.checks,
      tv: result.tv,
      versions: {
        cytv: metadata.cytv,
        installer: metadata.installer,
        homebrew: result.tv && result.tv.homebrew_version,
        home: installed.home || alternative.home,
        helper: installed.helper || alternative.helper,
        root: installed.root,
        root_updater: installed['root-updater'],
        system_updater: installed.supervisor || installed['system-updater'],
        candidate_root: suppliedCandidate.root,
        candidate_root_updater: suppliedCandidate['root-updater'],
        candidate_system_updater: suppliedCandidate.supervisor
      }
    });
  }
  function advice(value) {
    switch (value.code) {
      case 'homebrew_exec_denied':
        return ['homebrewDeniedTitle', 'homebrewDeniedBody'];
      case 'homebrew_root_required':
      case 'root-access-required':
        return ['rootAccessRequired', 'checkHomebrew'];
      case 'homebrew_timeout':
        return ['responseTimedOut', 'checkOrComputer'];
      case 'homebrew_unreachable':
        return ['homebrewUnavailable', 'checkHomebrew'];
      case 'homebrew_invalid_reply':
        return ['responseUnrecognized', 'checkOrComputer'];
      case 'status_unavailable':
      case 'unknown_operation':
      case 'unknown-operation':
      case 'worker_submission_unknown':
        return [
          'statusUnavailable',
          value.action === 'uninstall' ? 'checkOrComputer' : 'checkOriginal'
        ];
      case 'historical_completion_is_not_current':
      case 'removal-not-current':
        return ['statusUnavailable', 'checkOrComputer'];
      case 'restart-required':
        return ['restartNeeded', 'restartAndRetry'];
      case 'ownership-conflict':
        return ['statusUnavailable', 'computerRecovery'];
      case 'root-worker-busy':
        return ['progress', 'checkOrComputer'];
      case 'worker_snapshot_unavailable':
        return ['workerUnavailable', 'checkOriginal'];
      case 'private_runtime_required':
      case 'runtime_unconfirmed':
      case 'installer-runtime-mismatch':
        return ['runtimeUnavailable', 'runtimeRetry'];
      case 'legacy_node_on_computer':
        return ['olderRuntime', 'legacyNodeSetup'];
      case 'root_setup_on_computer':
        return ['rootBackendNeeded', 'externalRootSetup'];
      case 'no_root_setup_on_computer':
        return ['rootBackendUnsupported', 'noRootHandoff'];
      case 'pairing-rejected':
      case 'pairing-timeout':
      case 'inventory-unavailable':
        return ['noRootPairingFailed', 'noRootPairingNext'];
      case 'pairing-unavailable':
      case 'no-root-prerequisites':
      case 'no-root-payload-invalid':
      case 'root-admission-changed':
        return ['rootBackendUnsupported', 'noRootUnavailable'];
      case 'current-state-unverified':
      case 'original-work-unverified':
      case 'original-worker-interrupted':
      case 'worker-unavailable':
      case 'no-root-removal-mismatch':
      case 'no-root-worker-busy':
        return ['statusUnavailable', 'checkOriginal'];
      case 'home_interfaces_unconfirmed':
        return ['homeUnconfirmed', 'editionUnconfirmed'];
      case 'existing_installation':
      case 'supported_migration':
        return ['olderInstallation', 'existingSetup'];
      case 'retained_operation':
        return ['statusUnavailable', 'checkOriginal'];
      case 'component_mismatch':
        return ['componentsRemain', 'computerRecovery'];
      case 'tile_home_unavailable':
        return ['tileHomeUnavailable', 'tileRecoveryNext'];
      case 'tile_edition_unconfirmed':
        return ['tileEditionUnavailable', 'computerRecovery'];
      case 'update_service_unavailable':
        return ['updateServiceUnavailable', 'computerRecovery'];
    }
    if (
      [
        'restart-required',
        'restart_required',
        'live_original_worker',
        'support_stage_remains'
      ].indexOf(value.detail) >= 0
    )
      return ['restartNeeded', 'restartAndRetry'];
    if (value.detail === 'package_rejected')
      return ['packageRejected', 'checkOrComputer'];
    if (value.detail === 'project_apps_remain')
      return ['componentsRemain', 'computerRecovery'];
    if (
      value.activation === 'unverified' ||
      (value.state === 'complete' &&
        (value.activation === 'active' || value.activation === 'pending'))
    )
      return ['activationUnverified', 'checkOrComputer'];
    if (value.detail === 'supported_migration')
      return ['olderInstallation', 'existingSetup'];
    if (value.state === 'unknown' || value.detail === 'retained_operation')
      return ['statusUnavailable', 'checkOriginal'];
    return ['reasonUnknown', 'checkOrComputer'];
  }
  function save(value) {
    try {
      if (
        JSON.stringify(value) !== JSON.stringify(format.cleanObservation(value))
      )
        return false;
      // Only the compact projection is persisted. Exposed fields have already
      // passed the same validation used when the report reaches the phone.
      var text = format.serialize(value);
      root.localStorage.setItem(storageKey, text);
      return root.localStorage.getItem(storageKey) === text;
    } catch (_) {
      return false;
    }
  }
  function load() {
    try {
      var raw = root.localStorage.getItem(storageKey);
      if (raw) return format.deserialize(raw);
      raw = root.localStorage.getItem(legacyStorage);
      if (!raw || raw.length > 1000) return null;
      var value = JSON.parse(raw);
      if (
        !value ||
        value.schema !== 1 ||
        !accepted(value.code, format.codes) ||
        !accepted(value.source, ['setup', 'recovery']) ||
        !Object.keys(value).every(function (key) {
          return (
            ['schema', 'source', 'code'].indexOf(key) >= 0 ||
            (Object.prototype.hasOwnProperty.call(fields, key) &&
              accepted(value[key], fields[key]))
          );
        })
      )
        return null;
      return format.cleanObservation(value);
    } catch (_) {
      return null;
    }
  }
  function append(parent, tag, text, id) {
    var node = root.document.createElement(tag);
    if (text) node.textContent = text;
    if (id) node.id = id;
    parent.appendChild(node);
    return node;
  }
  function explain(parent, value, translate) {
    var lines = advice(value);
    append(parent, 'p', translate(lines[0]), 'diagnostic-reason');
    append(parent, 'p', translate(lines[1]), 'diagnostic-next');
  }
  function render(parent, value, translate, stored) {
    append(
      parent,
      'p',
      translate(stored ? 'diagnosticSaved' : 'diagnosticNotSaved'),
      'diagnostic-storage'
    );
    var layout = append(parent, 'div', null, 'diagnostic-layout');
    var report = format.canonical(value);
    var canvas = append(layout, 'canvas', null, 'diagnostic-qr');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', translate('diagnosticQr'));
    try {
      root.WallpaperQR.render(canvas, format.url(report));
    } catch (_) {
      canvas.hidden = true;
    }
    var text = append(layout, 'div');
    if (!canvas.hidden) append(text, 'p', translate('diagnosticQr'));
    append(text, 'pre', JSON.stringify(report, null, 2), 'diagnostic-json');
  }
  return {
    record: record,
    advice: advice,
    save: save,
    load: load,
    explain: explain,
    render: render
  };
});
