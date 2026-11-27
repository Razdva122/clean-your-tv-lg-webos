/* Node 8 only. Fixed installed entry; never a generic command or path API. */
'use strict';
var APP =
  '/media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller';
// Initial privileged HBC launch trusts the installed app. Subsequent payload bytes are pinned.
var PAYLOAD_SHA256 = '__CYTV_PAYLOAD_SHA256__';
var PAYLOAD = APP + '/payload',
  DRIVER = PAYLOAD + '/root-updater/install_driver.py';
function fail() {
  throw new Error('Installer prerequisite or request is unsupported');
}
function debloatAction(action) {
  return ['debloat', 'debloat-status', 'debloat-restore'].indexOf(action) >= 0;
}
function parse(args) {
  var action = args[0],
    request = { action: action },
    valueOptions = {
      '--operation': 'operation',
      '--candidate': 'candidate',
      '--settings': 'settings'
    },
    flags = {
      '--prepare-supervisor': 'supervisor',
      '--migrate-packaged-home': 'migrate',
      '--activate-after-install': 'activateAfterInstall',
      '--verify-current': 'current',
      '--resume': 'resume'
    };
  if (
    [
      'inspect',
      'prepare-runtime',
      'install',
      'status',
      'restore',
      'remove',
      'homebrew-remove',
      'homebrew-remove-status',
      'homebrew-remove-tile',
      'activate',
      'debloat',
      'debloat-status',
      'debloat-restore'
    ].indexOf(action) < 0
  )
    fail();
  for (var i = 1; i < args.length; i++) {
    var key = valueOptions[args[i]] || flags[args[i]];
    if (!key || Object.prototype.hasOwnProperty.call(request, key)) fail();
    var option = valueOptions[args[i]];
    if (option && typeof args[i + 1] !== 'string') fail();
    request[key] = option ? args[++i] : true;
  }
  if (
    request.operation !== undefined &&
    !/^[a-f0-9]{32}$/.test(request.operation)
  )
    fail();
  if (
    request.candidate !== undefined &&
    !/^[a-f0-9]{64}$/.test(request.candidate)
  )
    fail();
  var allowed = {
    inspect: ['supervisor'],
    'prepare-runtime': [],
    install: [
      'operation',
      'candidate',
      'supervisor',
      'migrate',
      'activateAfterInstall',
      'resume'
    ],
    status: ['operation', 'current'],
    restore: [],
    remove: ['operation', 'candidate', 'resume'],
    'homebrew-remove': ['operation'],
    'homebrew-remove-status': ['operation'],
    'homebrew-remove-tile': ['operation'],
    activate: [],
    debloat: ['settings'],
    'debloat-status': [],
    'debloat-restore': ['settings']
  }[action];
  Object.keys(request).forEach(function (key) {
    if (key !== 'action' && allowed.indexOf(key) < 0) fail();
  });
  if (
    [
      'install',
      'remove',
      'status',
      'homebrew-remove',
      'homebrew-remove-status',
      'homebrew-remove-tile'
    ].indexOf(action) >= 0 &&
    !request.operation
  )
    fail();
  if (
    ['install', 'remove'].indexOf(action) >= 0 &&
    !request.resume &&
    !request.candidate
  )
    fail();
  if (
    request.resume &&
    (request.candidate ||
      request.supervisor ||
      request.migrate ||
      request.activateAfterInstall)
  )
    fail();
  if (
    debloatAction(action) &&
    action !== 'debloat-status' &&
    (typeof request.settings !== 'string' ||
      !/^[a-zA-Z][a-zA-Z0-9]{0,31}(,[a-zA-Z][a-zA-Z0-9]{0,31}){0,10}$/.test(
        request.settings
      ))
  )
    fail();
  return request;
}
function execute(executable, args) {
  return new Promise(function (resolve, reject) {
    require('child_process').execFile(
      executable,
      args,
      {
        timeout: 120000,
        maxBuffer: 65536,
        env: {
          PATH: '/usr/sbin:/usr/bin:/sbin:/bin',
          LC_ALL: 'C',
          PYTHONDONTWRITEBYTECODE: '1',
          PYTHONNOUSERSITE: '1'
        }
      },
      function (error, stdout) {
        if (error)
          return reject(
            new Error(
              'Installer operation unavailable; inspect status before continuing'
            )
          );
        resolve(stdout);
      }
    );
  });
}
function inspectionEvidence(version) {
  var evidence = {
    checks: {
      'homebrew-access': 'pass',
      'root-user': 'pending',
      'node-version': 'pending',
      'installer-payload': 'pending',
      'python-runtime': 'pending',
      'installer-staging': 'pending',
      'product-state': 'pending',
      'home-compatibility': 'pending'
    },
    tv: {}
  };
  if (
    typeof version === 'string' &&
    /^\d{1,5}\.\d{1,5}\.\d{1,5}$/.test(version)
  ) {
    evidence.tv.node_version = version;
    evidence.tv.node_version_status = 'read';
  }
  return evidence;
}
function withEvidence(result, evidence) {
  if (evidence) {
    result.checks = evidence.checks;
    result.tv = evidence.tv;
  }
  return result;
}
function inspectEdition(result, stage, python, executeRead, evidence) {
  var installation = result.installation,
    fresh = result.state === 'fresh' && !result.active_operation,
    eligible =
      fresh &&
      installation &&
      installation.can_install === true &&
      result.active_operation === null &&
      ((installation.reason === 'no_installation' &&
        installation.clean_removal_verified === undefined) ||
        (installation.reason === 'verified_clean_removal' &&
          installation.clean_removal_verified === true &&
          installation.can_maintain === false)),
    fallback = fresh
      ? { state: 'edition_unconfirmed', code: 'home_interfaces_unconfirmed' }
      : result;
  if (typeof stage.editionInspector !== 'string') return fallback;
  if (eligible) evidence.checks['home-compatibility'] = 'unknown';
  var command = ['-E', '-s', '-B', stage.editionInspector];
  if (!eligible) command.push('--metadata-only');
  return executeRead(python, command)
    .then(function (raw) {
      var observation = JSON.parse(raw),
        decision = observation.decision,
        tv = observation.tv || {};
      ['modelName', 'firmwareVersion', 'sdkVersion'].forEach(function (key) {
        var value = tv[key];
        var pattern =
          key === 'modelName'
            ? /^(?=.*[0-9])(?=.*[A-Z])[A-Z0-9][A-Z0-9._-]{1,47}$/
            : /^[0-9]{1,5}(?:\.[0-9]{1,5}){1,2}(?:-[0-9]{1,6})?$/;
        if (typeof value === 'string' && pattern.test(value))
          evidence.tv[key] = value;
      });
      if (!eligible) return fallback;
      if (decision === 'root') {
        evidence.checks['home-compatibility'] = 'pass';
        return result;
      }
      if (decision === 'external_no_root' || decision === 'external_root') {
        evidence.checks['home-compatibility'] = 'fail';
        return {
          state: 'external_setup',
          code:
            decision === 'external_root'
              ? 'root_setup_on_computer'
              : 'no_root_setup_on_computer'
        };
      }
      return fallback;
    })
    .catch(function () {
      return fallback;
    });
}
function runRemoval(deps, request) {
  return deps.runtime
    .removal(PAYLOAD, PAYLOAD_SHA256, request.operation, request.action)
    .then(function (observed) {
      if (observed) return observed;
      return deps.runtime
        .inspect(PAYLOAD, true, PAYLOAD_SHA256)
        .then(function (state) {
          if (!state.python) fail();
          var removing = request.action === 'homebrew-remove';
          return deps.runtime
            .stage(state, removing ? 'removal' : false)
            .then(function (stage) {
              var args = [
                '-E',
                '-s',
                '-B',
                stage.driver,
                request.action,
                '--operation',
                request.operation
              ];
              if (removing) args.push('--payload', stage.root);
              return deps
                .execute(state.python, args)
                .then(function (raw) {
                  return JSON.parse(raw);
                })
                .then(
                  function (result) {
                    return stage.cleanup().then(function () {
                      return result;
                    });
                  },
                  function (error) {
                    return stage.cleanup().then(function () {
                      throw error;
                    });
                  }
                );
            });
        });
    });
}
function run(args, deps) {
  var evidence,
    boundary = 'node-version';
  function checked(check, status) {
    if (evidence) evidence.checks[check] = status;
  }
  function unsupported(code) {
    return withEvidence({ state: 'unsupported', code: code }, evidence);
  }
  var result = Promise.resolve().then(function () {
    // Parse failures and non-inspection operations keep their existing rejection behavior.
    var request = parse(args),
      runtimeProcess = deps ? deps.process : process,
      version = runtimeProcess.versions.node;
    if (request.action === 'inspect') evidence = inspectionEvidence(version);
    if (parseInt(version.split('.')[0], 10) < 8) fail();
    checked('node-version', 'pass');
    boundary = 'root-user';
    if (!runtimeProcess.geteuid) fail();
    if (runtimeProcess.geteuid() !== 0) {
      checked(boundary, 'fail');
      if (evidence) return unsupported('homebrew_root_required');
      fail();
    }
    checked(boundary, 'pass');
    boundary = 'installer-payload';
    deps = deps || {
      process: process,
      runtime: require('./payload/runtime.js'),
      execute: execute
    };
    if (/^homebrew-remove(?:-status|-tile)?$/.test(request.action))
      return runRemoval(deps, request);
    return deps.runtime
      .inspect(
        PAYLOAD,
        ['status', 'restore', 'remove'].indexOf(request.action) >= 0,
        PAYLOAD_SHA256,
        evidence
          ? function () {
              checked('installer-payload', 'pass');
              boundary = 'python-runtime';
            }
          : undefined
      )
      .then(function (state) {
        if (request.action === 'prepare-runtime')
          return deps.runtime
            .prepare(PAYLOAD, PAYLOAD_SHA256)
            .then(function () {
              return { state: 'runtime_ready', code: 'inspect_required' };
            });
        checked('installer-payload', 'pass');
        if (!state.python) {
          if (!evidence) fail();
          return withEvidence(
            {
              state: 'prerequisites',
              code: 'private_runtime_required',
              payload_sha256: PAYLOAD_SHA256,
              runtime: state
            },
            evidence
          );
        }
        checked('python-runtime', 'pass');
        boundary = 'installer-staging';
        return deps.runtime
          .stage(
            state,
            !request.resume &&
              ['inspect', 'install', 'remove'].indexOf(request.action) >= 0
          )
          .then(function (stage) {
            checked('installer-staging', 'pass');
            boundary = 'product-state';
            var debloat = debloatAction(request.action);
            var command = [
              '-E',
              '-s',
              '-B',
              debloat ? stage.debloat : stage.driver,
              request.action
            ];
            if (debloat && request.settings) command.push(request.settings);
            if (request.operation)
              command.push('--operation', request.operation);
            if (request.resume) command.push('--resume');
            else if (
              ['inspect', 'install', 'remove'].indexOf(request.action) >= 0
            )
              command.push('--payload', stage.root);
            if (request.candidate)
              command.push('--candidate', request.candidate);
            if (request.action === 'inspect' || request.activateAfterInstall)
              command.push('--homebrew-setup');
            if (request.supervisor) command.push('--prepare-supervisor');
            if (request.migrate) command.push('--migrate-packaged-home');
            if (request.activateAfterInstall)
              command.push('--activate-after-install');
            if (request.current) command.push('--verify-current');
            return deps
              .execute(state.python, command)
              .then(function (raw) {
                var result = JSON.parse(raw);
                if (
                  !result ||
                  typeof result !== 'object' ||
                  Array.isArray(result) ||
                  typeof result.state !== 'string'
                )
                  fail();
                if (!evidence) return result;
                checked(
                  'product-state',
                  [
                    'recovery_required',
                    'unsupported',
                    'conflict',
                    'migration_required'
                  ].indexOf(result.state) >= 0
                    ? 'fail'
                    : result.installation &&
                        ['fresh', 'installed'].indexOf(result.state) >= 0
                      ? 'pass'
                      : 'unknown'
                );
                return inspectEdition(
                  result,
                  stage,
                  state.python,
                  deps.execute,
                  evidence
                );
              })
              .then(
                function (result) {
                  if (evidence) result.payload_sha256 = PAYLOAD_SHA256;
                  boundary = 'installer-staging';
                  return stage.cleanup().then(function () {
                    return withEvidence(result, evidence);
                  });
                },
                function (error) {
                  return stage.cleanup().then(function () {
                    throw error;
                  });
                }
              );
          });
      });
  });
  return result.catch(function (error) {
    if (!evidence) throw error;
    checked(boundary, boundary === 'product-state' ? 'unknown' : 'fail');
    return unsupported('installer_unavailable');
  });
}
function main(args) {
  // Old firmware may have neither Promise nor the runtime module's Node APIs.
  // A version from the local executable can explain this installer prerequisite.
  var version = process.versions.node;
  if (/^[0-7]\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version)) {
    var inspection =
      args[0] === 'inspect' &&
      (args.length === 1 ||
        (args.length === 2 && args[1] === '--prepare-supervisor'));
    if (
      inspection &&
      typeof process.geteuid === 'function' &&
      process.geteuid() === 0
    ) {
      var evidence = inspectionEvidence(version);
      evidence.checks['root-user'] = 'pass';
      evidence.checks['node-version'] = 'fail';
      process.stdout.write(
        JSON.stringify(
          withEvidence(
            {
              state: 'external_setup',
              code: 'legacy_node_on_computer',
              payload_sha256: PAYLOAD_SHA256
            },
            evidence
          )
        ) + '\n'
      );
    } else {
      process.stdout.write(
        '{"state":"unsupported","code":"installer_unavailable"}\n'
      );
      process.exitCode = 1;
    }
    return;
  }
  run(args).then(
    function (result) {
      process.stdout.write(JSON.stringify(result) + '\n');
    },
    function () {
      process.stdout.write(
        JSON.stringify({
          state: 'unsupported',
          code: 'installer_unavailable'
        }) + '\n'
      );
      process.exitCode = 1;
    }
  );
}
module.exports = { run: run, PAYLOAD: PAYLOAD, DRIVER: DRIVER };
if (require.main === module) main(process.argv.slice(2));
