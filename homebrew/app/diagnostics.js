(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory;
  else root.InstallerDiagnostics = factory(root);
})(this, function (root) {
  'use strict';
  var storageKey = 'cytv.installer.diagnostic.v1',
    sources = ['setup', 'recovery'],
    codes = [
      'unconfirmed',
      'homebrew_exec_denied',
      'homebrew_root_required',
      'homebrew_timeout',
      'homebrew_unreachable',
      'homebrew_invalid_reply',
      'installer_unavailable',
      'status_unavailable',
      'runtime_unconfirmed',
      'private_runtime_required',
      'legacy_node_on_computer',
      'root_setup_on_computer',
      'no_root_setup_on_computer',
      'home_interfaces_unconfirmed',
      'existing_installation',
      'unknown_operation',
      'operation_requires_recovery',
      'installation_requires_recovery',
      'continuation_requires_recovery',
      'worker_snapshot_unavailable',
      'worker_submission_unknown',
      'clean-handoff-refused',
      'clean_removal_requested',
      'historical_completion_is_not_current',
      'installer-runtime-mismatch',
      'tile_home_unavailable',
      'tile_edition_unconfirmed',
      'update_service_unavailable'
    ],
    fields = {
      state:
        'recovery_required unknown unsupported external_setup edition_unconfirmed prerequisites fresh pending complete installed'.split(
          ' '
        ),
      stage:
        'inspect requested blocked preparing reserved snapshot root-deploy root-updater supervisor readback submitting complete activate restore resume-submitted clean-removal-requested package-remove-submitting root-remove-submitting supervisor-disable supervisor-archive restart-required verified-clean'.split(
          ' '
        ),
      detail:
        'restart-required live_original_worker support_stage_remains project_apps_remain restored_routes_changed owned_registration_remains no_root_private_cleanup_required private_members_remain owned_activity_remains owned_input_registration_remains route-changed original-removal-required different-removal-intent unsafe-cleanup-directory unsafe-cleanup-member cleanup-guard-failed package_rejected'.split(
          ' '
        ),
      activation:
        'pending unverified cancelled active finished superseded'.split(' '),
      resume:
        'worker-not-quiescent original-request-unverified original-snapshot-unverified package-terminal-unverified current-package-files-unverified'.split(
          ' '
        )
    };

  function accepted(value, values) {
    return typeof value === 'string' && values.indexOf(value) >= 0;
  }
  function record(source, result, code) {
    result = result || {};
    var failure = result.failure || {},
      output = {
        schema: 1,
        source: accepted(source, sources) ? source : 'setup',
        code: accepted(code, codes)
          ? code
          : accepted(result.code, codes)
            ? result.code
            : 'unconfirmed'
      },
      observed = {
        state: result.state,
        stage: result.stage,
        detail: accepted(failure.inspect_check, fields.detail)
          ? failure.inspect_check
          : failure.package_rejected === true
            ? 'package_rejected'
            : result.reason,
        activation: result.activation && result.activation.state,
        resume: result.resume_reason
      };
    Object.keys(fields).forEach(function (key) {
      if (accepted(observed[key], fields[key])) output[key] = observed[key];
    });
    return output;
  }
  function advice(value) {
    switch (value.code) {
      case 'homebrew_exec_denied':
        return ['homebrewDeniedTitle', 'homebrewDeniedBody'];
      case 'homebrew_root_required':
        return ['rootAccessRequired', 'checkHomebrew'];
      case 'homebrew_timeout':
        return ['responseTimedOut', 'checkOrComputer'];
      case 'homebrew_unreachable':
        return ['homebrewUnavailable', 'checkHomebrew'];
      case 'homebrew_invalid_reply':
        return ['responseUnrecognized', 'checkOrComputer'];
      case 'status_unavailable':
      case 'unknown_operation':
      case 'worker_submission_unknown':
        return ['statusUnavailable', 'checkOriginal'];
      case 'historical_completion_is_not_current':
        return ['statusUnavailable', 'checkOrComputer'];
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
      case 'home_interfaces_unconfirmed':
        return ['homeUnconfirmed', 'editionUnconfirmed'];
      case 'existing_installation':
        return ['olderInstallation', 'existingSetup'];
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
    if (value.state === 'unknown')
      return ['statusUnavailable', 'checkOriginal'];
    return ['reasonUnknown', 'checkOrComputer'];
  }
  function isReport(value) {
    return (
      value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      value.schema === 1 &&
      accepted(value.source, sources) &&
      accepted(value.code, codes) &&
      Object.keys(value).every(function (key) {
        return (
          key === 'schema' ||
          key === 'source' ||
          key === 'code' ||
          (Object.prototype.hasOwnProperty.call(fields, key) &&
            accepted(value[key], fields[key]))
        );
      })
    );
  }
  function save(value) {
    if (!isReport(value)) return false;
    try {
      var text = JSON.stringify(value);
      root.localStorage.setItem(storageKey, text);
      return root.localStorage.getItem(storageKey) === text;
    } catch (_) {
      return false;
    }
  }
  function load() {
    try {
      var raw = root.localStorage.getItem(storageKey);
      if (!raw || raw.length > 1000) return null;
      var value = JSON.parse(raw);
      return isReport(value) ? value : null;
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
    var data = JSON.stringify(value);
    var canvas = append(layout, 'canvas', null, 'diagnostic-qr');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', translate('diagnosticQr'));
    try {
      root.WallpaperQR.render(canvas, data);
    } catch (_) {
      canvas.hidden = true;
    }
    var text = append(layout, 'div');
    if (!canvas.hidden) append(text, 'p', translate('diagnosticQr'));
    append(text, 'pre', JSON.stringify(value, null, 2), 'diagnostic-json');
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
