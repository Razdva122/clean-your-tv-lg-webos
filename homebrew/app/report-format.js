(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CYTVHomebrewReport = factory();
})(this, function () {
  'use strict';
  var base =
      'https://razdva122.github.io/clean-your-tv-lg-webos/support/homebrew/',
    maxFragment = 1400,
    own = Object.prototype.hasOwnProperty,
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
      'invalid_snapshot',
      'component_mismatch',
      'supported_migration',
      'retained_operation',
      'unsupported_device',
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
        'conflict migration_required recovery_required unknown unsupported external_setup edition_unconfirmed prerequisites fresh pending complete installed'.split(
          ' '
        ),
      stage:
        'inspect requested blocked preparing reserved snapshot root-deploy root-updater supervisor readback submitting submitted complete activate restore resume-submitted clean-removal-requested package-remove-submitting root-remove-submitting supervisor-disable supervisor-archive restart-required verified-clean'.split(
          ' '
        ),
      detail:
        'restart-required live_original_worker support_stage_remains project_apps_remain restored_routes_changed owned_registration_remains no_root_private_cleanup_required private_members_remain owned_activity_remains owned_input_registration_remains route-changed original-removal-required different-removal-intent unsafe-cleanup-directory unsafe-cleanup-member cleanup-guard-failed package_rejected invalid_snapshot component_mismatch supported_migration retained_operation unsupported_device'.split(
          ' '
        ),
      activation:
        'pending unverified cancelled active finished superseded'.split(' '),
      resume:
        'worker-not-quiescent original-request-unverified original-snapshot-unverified package-terminal-unverified current-package-files-unverified'.split(
          ' '
        )
    };
  var statuses = ['pending', 'running', 'pass', 'fail', 'unknown'],
    checks = (
      'homebrew-access root-user node-version installer-payload python-runtime installer-staging product-state home-compatibility ' +
      'home-settings home-profiles packages startup home-button python3 python-json python-fcntl python-version luna-send ' +
      'apps-directory luna-services-directory install-request install-root install-updates install-readback activate-home'
    ).split(' '),
    actions = [
      'install',
      'uninstall',
      'recover',
      'restore',
      'status',
      'debloat'
    ],
    editions = ['root', 'no-root'],
    phases = [
      'homebrew-access',
      'preflight',
      'setup',
      'activate',
      'status',
      'recovery',
      'debloat'
    ].concat(fields.stage),
    exceptionTypes = [
      'CalledProcessError',
      'TimeoutExpired',
      'ValueError',
      'RuntimeError',
      'OSError',
      'PermissionError',
      'FileNotFoundError',
      'TypeError',
      'KeyError',
      'TimeoutError'
    ],
    versions = [
      'cytv',
      'installer',
      'homebrew',
      'root',
      'root_updater',
      'system_updater',
      'home',
      'helper',
      'candidate_root',
      'candidate_root_updater',
      'candidate_system_updater'
    ],
    privacy =
      'No addresses, SSH identities, exception text, credentials, app inventory, environment or raw TV logs are collected.';

  phases = phases.concat(checks);

  function accepted(value, values) {
    return typeof value === 'string' && values.indexOf(value) >= 0;
  }
  function mapping(value) {
    return value && typeof value === 'object' && !Array.isArray(value)
      ? value
      : {};
  }
  function select(value, keys, parse) {
    var projected = {};
    value = mapping(value);
    keys.forEach(function (key) {
      if (!own.call(value, key)) return;
      var item = parse(value[key], key);
      if (item !== null) projected[key] = item;
    });
    return projected;
  }
  function match(value, expression, limit) {
    return typeof value === 'string' &&
      value.length <= limit &&
      expression.test(value)
      ? value
      : null;
  }
  function version(value) {
    return match(value, /^\d{1,5}(?:\.\d{1,5}){2}$/, 20);
  }
  function timestamp(value) {
    if (!match(value, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/, 24))
      return null;
    var date = new Date(value);
    return !isNaN(date.getTime()) && date.toISOString() === value
      ? value
      : null;
  }
  function cleanObservation(input) {
    input = mapping(input);
    var result = {
      schema: 1,
      timestamp: timestamp(input.timestamp),
      action:
        input.action === 'remove'
          ? 'uninstall'
          : accepted(input.action, actions)
            ? input.action
            : input.source === 'recovery'
              ? 'recover'
              : 'install',
      edition: accepted(input.edition, editions) ? input.edition : null,
      phase: accepted(input.phase, phases)
        ? input.phase
        : accepted(input.stage, fields.stage)
          ? input.stage
          : input.source === 'recovery'
            ? 'recovery'
            : 'preflight',
      code: accepted(input.code, codes) ? input.code : 'unconfirmed',
      tv: select(
        input.tv,
        [
          'modelName',
          'firmwareVersion',
          'sdkVersion',
          'node_version',
          'node_version_status'
        ],
        function (value, key) {
          if (key === 'modelName')
            return match(
              value,
              /^(?=.*\d)(?=.*[A-Z])[A-Z0-9][A-Z0-9._-]{1,47}$/,
              48
            );
          if (key === 'node_version_status')
            return accepted(value, [
              'read',
              'missing',
              'launch-error',
              'invalid-output',
              'unavailable'
            ])
              ? value
              : null;
          return key === 'node_version'
            ? version(value)
            : match(value, /^\d{1,5}(?:\.\d{1,5}){1,2}(?:-\d{1,6})?$/, 24);
        }
      ),
      checks: select(input.checks, checks, function (value) {
        if (value && typeof value === 'object') value = value.status;
        return accepted(value, statuses) ? value : null;
      }),
      versions: select(input.versions, versions, version),
      source: accepted(input.source, sources) ? input.source : 'setup'
    };
    Object.keys(fields).forEach(function (key) {
      if (accepted(input[key], fields[key])) result[key] = input[key];
    });
    result.failure = select(
      input.failure,
      ['exception_type', 'errno', 'exit_status'],
      function (value, key) {
        if (key === 'exception_type')
          return accepted(value, exceptionTypes) ? value : null;
        var min = key === 'errno' ? 0 : -255,
          max = key === 'errno' ? 4095 : 255;
        return typeof value === 'number' &&
          Math.floor(value) === value &&
          value >= min &&
          value <= max
          ? value
          : null;
      }
    );
    return result;
  }
  function canonical(input) {
    var value = cleanObservation(input),
      product = { code: value.code },
      tvComponents = select(
        value.versions,
        ['home', 'helper', 'root', 'root_updater', 'system_updater'],
        version
      ),
      report = {
        schema: 1,
        cytv_version: value.versions.cytv || null,
        timestamp_utc: value.timestamp,
        desktop: { os: null, architecture: null, python: null },
        frontend: 'homebrew',
        action: value.action,
        edition: value.edition,
        phase: value.phase,
        error_type: value.failure.exception_type || null,
        pending:
          value.state === 'pending' || value.state === 'recovery_required'
            ? { action: value.action, stage: value.stage || null }
            : null,
        trace: [],
        tv: value.tv,
        checks: value.checks,
        privacy: privacy,
        reason_code: value.code,
        status: { product: product },
        contract_events: [],
        contract_telemetry: 'unavailable',
        homebrew: { source: value.source, versions: value.versions }
      };
    if (value.state) product.state = value.state;
    if (value.stage) product.stage = value.stage;
    if (Object.keys(value.failure).length) product.failure = value.failure;
    if (Object.keys(tvComponents).length)
      report.status.components = tvComponents;
    ['detail', 'activation', 'resume'].forEach(function (key) {
      if (value[key]) report.homebrew[key] = value[key];
    });
    return report;
  }
  function packChecks(value) {
    return checks
      .map(function (key) {
        var index = statuses.indexOf(value[key]);
        return index < 0 ? '-' : String(index);
      })
      .join('')
      .replace(/-+$/, '');
  }
  function unpackChecks(value) {
    if (
      typeof value !== 'string' ||
      value.length > checks.length ||
      !/^[0-4-]*$/.test(value)
    )
      return null;
    var observation = {};
    for (var i = 0; i < value.length; i++) {
      if (value[i] !== '-') observation[checks[i]] = statuses[Number(value[i])];
    }
    return observation;
  }
  function toWire(value) {
    return [
      1,
      value.timestamp,
      value.action,
      value.edition,
      value.phase,
      value.code,
      value.tv,
      packChecks(value.checks),
      value.state || null,
      value.detail || null,
      value.activation || null,
      value.resume || null,
      value.versions,
      value.source,
      value.stage || null,
      value.failure
    ];
  }
  function fromWire(value) {
    if (!Array.isArray(value) || value.length !== 16 || value[0] !== 1)
      return null;
    var clean = cleanObservation({
      timestamp: value[1],
      action: value[2],
      edition: value[3],
      phase: value[4],
      code: value[5],
      tv: value[6],
      checks: unpackChecks(value[7]),
      state: value[8],
      detail: value[9],
      activation: value[10],
      resume: value[11],
      versions: value[12],
      source: value[13],
      stage: value[14],
      failure: value[15]
    });
    // The sender emits exactly this projection, including key order. Unknown input
    // never reaches the downloaded report or issue draft.
    return JSON.stringify(toWire(clean)) === JSON.stringify(value)
      ? clean
      : null;
  }
  function serialize(input) {
    return JSON.stringify(toWire(cleanObservation(input)));
  }
  function deserialize(text) {
    if (typeof text !== 'string' || text.length > maxFragment) return null;
    try {
      return fromWire(JSON.parse(text));
    } catch (_) {
      return null;
    }
  }
  function encode(text) {
    // All source values are ASCII after projection.
    return btoa(text)
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  }
  function decode(hash) {
    if (typeof hash !== 'string' || hash.length > maxFragment + 1) return null;
    try {
      var data = hash.charAt(0) === '#' ? hash.slice(1) : hash;
      if (!/^[a-zA-Z0-9_-]+$/.test(data)) return null;
      var text = atob(data.replace(/-/g, '+').replace(/_/g, '/'));
      var value = deserialize(text);
      return value && encode(text) === data ? canonical(value) : null;
    } catch (_) {
      return null;
    }
  }
  function url(report) {
    var homebrew = mapping(report.homebrew),
      product = mapping(mapping(report.status).product);
    var hash = encode(
      serialize({
        timestamp: report.timestamp_utc,
        action: report.action,
        edition: report.edition,
        phase: report.phase,
        code: report.reason_code,
        tv: report.tv,
        checks: report.checks,
        state: product.state,
        stage: product.stage,
        failure: product.failure,
        detail: homebrew.detail,
        activation: homebrew.activation,
        resume: homebrew.resume,
        versions: homebrew.versions,
        source: homebrew.source
      })
    );
    if (hash.length > maxFragment)
      throw Error('Homebrew report exceeds QR capacity');
    return base + '#' + hash;
  }
  function filename(report) {
    var value = timestamp(report.timestamp_utc);
    return (
      'diagnostic-homebrew' +
      (value ? '-' + value.slice(0, 19).replace(/[:-]/g, '') : '') +
      '.json'
    );
  }

  return {
    accepted: accepted,
    fields: fields,
    codes: codes,
    cleanObservation: cleanObservation,
    canonical: canonical,
    serialize: serialize,
    deserialize: deserialize,
    decode: decode,
    url: url,
    filename: filename
  };
});
