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
function parse(args) {
  var action = args[0],
    request = { action: action },
    valueOptions = { '--operation': 'operation', '--candidate': 'candidate' },
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
      'activate'
    ].indexOf(action) < 0
  )
    fail();
  for (var i = 1; i < args.length; i++) {
    var key = valueOptions[args[i]] || flags[args[i]];
    if (!key || Object.prototype.hasOwnProperty.call(request, key)) fail();
    request[key] = valueOptions[args[i]] ? args[++i] : true;
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
    activate: []
  }[action];
  Object.keys(request).forEach(function (key) {
    if (key !== 'action' && allowed.indexOf(key) < 0) fail();
  });
  if (
    ['install', 'remove', 'status'].indexOf(action) >= 0 &&
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
function inspectEdition(result, stage, python, executeRead) {
  if (result.state !== 'fresh' || result.active_operation) return result;
  var unknown = {
    state: 'edition_unconfirmed',
    code: 'home_interfaces_unconfirmed'
  };
  if (
    !result.installation ||
    result.installation.can_install !== true ||
    !(
      (result.installation.reason === 'no_installation' &&
        result.installation.clean_removal_verified === undefined) ||
      (result.installation.reason === 'verified_clean_removal' &&
        result.installation.clean_removal_verified === true &&
        result.installation.can_maintain === false)
    ) ||
    result.active_operation !== null ||
    typeof stage.editionInspector !== 'string'
  )
    return unknown;
  return executeRead(python, ['-E', '-s', '-B', stage.editionInspector])
    .then(function (raw) {
      var decision = JSON.parse(raw).decision;
      if (decision === 'root') return result;
      if (decision === 'external_no_root' || decision === 'external_root')
        return {
          state: 'external_setup',
          code:
            decision === 'external_root'
              ? 'root_setup_on_computer'
              : 'no_root_setup_on_computer'
        };
      return unknown;
    })
    .catch(function () {
      return unknown;
    });
}
function run(args, deps) {
  return Promise.resolve().then(function () {
    var request = parse(args);
    deps = deps || {
      process: process,
      runtime: require('./payload/runtime.js'),
      execute: execute
    };
    if (
      !deps.process.geteuid ||
      deps.process.geteuid() !== 0 ||
      parseInt(deps.process.versions.node.split('.')[0], 10) < 8
    )
      fail();
    return deps.runtime
      .inspect(
        PAYLOAD,
        ['status', 'restore', 'remove'].indexOf(request.action) >= 0,
        PAYLOAD_SHA256
      )
      .then(function (state) {
        if (request.action === 'prepare-runtime')
          return deps.runtime
            .prepare(PAYLOAD, PAYLOAD_SHA256)
            .then(function () {
              return { state: 'runtime_ready', code: 'inspect_required' };
            });
        if (!state.python) {
          if (request.action !== 'inspect') fail();
          return {
            state: 'prerequisites',
            code: 'private_runtime_required',
            payload_sha256: PAYLOAD_SHA256,
            runtime: state
          };
        }
        return deps.runtime
          .stage(
            state,
            !request.resume &&
              ['inspect', 'install', 'remove'].indexOf(request.action) >= 0
          )
          .then(function (stage) {
            var command = ['-E', '-s', '-B', stage.driver, request.action];
            if (request.operation)
              command.push('--operation', request.operation);
            if (request.resume) command.push('--resume');
            else if (
              ['inspect', 'install', 'remove'].indexOf(request.action) >= 0
            )
              command.push('--payload', stage.root);
            if (request.candidate)
              command.push('--candidate', request.candidate);
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
                return request.action === 'inspect'
                  ? inspectEdition(result, stage, state.python, deps.execute)
                  : result;
              })
              .then(
                function (result) {
                  if (request.action === 'inspect')
                    result.payload_sha256 = PAYLOAD_SHA256;
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
      process.stdout.write(
        JSON.stringify({
          state: 'external_setup',
          code: 'legacy_node_on_computer',
          payload_sha256: PAYLOAD_SHA256
        }) + '\n'
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
