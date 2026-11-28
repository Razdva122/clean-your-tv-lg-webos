'use strict';
var assert = require('assert'),
  fs = require('fs'),
  vm = require('vm'),
  path = require('path');
var ID = 'a'.repeat(32),
  SHA = 'b'.repeat(64),
  calls = [];
function loadBridge(reply) {
  var context = {
    Promise: Promise,
    setTimeout: setTimeout,
    clearTimeout: clearTimeout,
    module: { exports: {} },
    PalmServiceBridge: function () {
      this.cancel = function () {};
      this.call = function (uri, body) {
        calls.push({ uri: uri, body: JSON.parse(body) });
        this.onservicecallback(JSON.stringify(reply));
      };
    }
  };
  vm.runInNewContext(
    fs.readFileSync(path.join(__dirname, '../app/bridge.js'), 'utf8'),
    context
  );
  return context.module.exports;
}
async function rejects(fn, expectedMessage) {
  var failed = false;
  try {
    await fn();
  } catch (e) {
    failed = true;
    if (expectedMessage) assert.strictEqual(e.message, expectedMessage);
  }
  assert(failed, 'must reject');
}
(async function () {
  var bootstrapSource = fs.readFileSync(
    path.join(__dirname, '../bootstrap.js'),
    'utf8'
  );
  function runLegacy(version, uid, args) {
    var stdout = '';
    var entry = { exports: {} };
    function requireNothing() {
      throw Error('legacy inspect loaded a dependency');
    }
    requireNothing.main = entry;
    vm.runInNewContext(bootstrapSource, {
      module: entry,
      require: requireNothing,
      Promise: undefined,
      process: {
        versions: { node: version },
        geteuid: function () {
          return uid;
        },
        argv: ['node', 'bootstrap.js'].concat(args),
        stdout: {
          write: function (line) {
            stdout += line;
          }
        }
      }
    });
    return JSON.parse(stdout);
  }
  var legacy = runLegacy('0.10.15', 0, ['inspect']);
  assert.equal(legacy.code, 'legacy_node_on_computer');
  assert.equal(legacy.checks['homebrew-access'], 'pass');
  assert.equal(legacy.checks['root-user'], 'pass');
  assert.equal(legacy.checks['node-version'], 'fail');
  assert.equal(legacy.checks['installer-payload'], 'pending');
  assert.equal(legacy.tv.node_version, '0.10.15');
  assert.equal(
    runLegacy('0.12.2', 0, ['status']).code,
    'installer_unavailable'
  );
  assert.equal(
    runLegacy('7.9.0', 1000, ['inspect']).code,
    'installer_unavailable'
  );
  assert.equal(
    runLegacy('0.12.2', 0, ['inspect', '--unknown']).code,
    'installer_unavailable'
  );
  assert(
    fs.existsSync(path.join(__dirname, '../app/bridge.js')),
    'fixed Homebrew bridge is required'
  );
  var bridge = loadBridge({
    returnValue: true,
    stdoutString: JSON.stringify({
      state: 'fresh',
      installation: { can_install: true }
    })
  });
  for (var bad of [
    { operation: ID, candidate: SHA, path: '/tmp/x' },
    { operation: '$(id)', candidate: SHA },
    { operation: ID, candidate: 'A'.repeat(64) },
    { operation: ID, candidate: SHA, prepareSupervisor: 'true' },
    { operation: ID, candidate: SHA, activateAfterInstall: 'true' },
    { operation: ID, candidate: SHA, url: 'https://example.com' }
  ])
    await rejects(function () {
      return bridge.start(bad);
    });
  assert.equal(calls.length, 0, 'invalid options never reach HBC');
  await bridge.start({
    operation: ID,
    candidate: SHA,
    prepareSupervisor: true,
    migrate: false,
    activateAfterInstall: true
  });
  assert.equal(calls[0].uri, 'luna://org.webosbrew.hbchannel.service/exec');
  assert.equal(
    calls[0].body.command,
    '/usr/bin/node /media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller/bootstrap.js install --operation ' +
      ID +
      ' --candidate ' +
      SHA +
      ' --prepare-supervisor --activate-after-install'
  );
  await bridge.status(ID);
  assert(
    calls[1].body.command.endsWith(
      'status --operation ' + ID + ' --verify-current'
    )
  );
  await bridge.resume(ID, 'remove');
  assert(
    calls[2].body.command.endsWith('remove --operation ' + ID + ' --resume')
  );
  await bridge.startNoRoot({ operation: ID, candidate: SHA });
  assert(
    calls
      .at(-1)
      .body.command.endsWith(
        'no-root-start --operation ' + ID + ' --candidate ' + SHA
      )
  );
  await bridge.noRootStatus(ID);
  assert(
    calls.at(-1).body.command.endsWith('no-root-status --operation ' + ID)
  );
  await bridge.resumeNoRoot(ID);
  assert(
    calls.at(-1).body.command.endsWith('no-root-resume --operation ' + ID)
  );
  var afterNoRoot = calls.length;
  await rejects(() =>
    bridge.startNoRoot({ operation: ID, candidate: SHA, host: '127.0.0.1' })
  );
  await rejects(() => bridge.startNoRoot({ operation: ID, candidate: 'bad' }));
  await rejects(() => bridge.noRootStatus('$(id)'));
  assert.equal(calls.length, afterNoRoot);
  var candidateReads = 0,
    operationReads = 0,
    supervisorReads = 0,
    migrateReads = 0;
  var accessor = {};
  Object.defineProperties(accessor, {
    operation: {
      enumerable: true,
      get: function () {
        operationReads++;
        return operationReads === 1 ? ID : '; printf OPERATION_INJECTION';
      }
    },
    candidate: {
      enumerable: true,
      get: function () {
        candidateReads++;
        return candidateReads <= 2 ? SHA : '; printf BRIDGE_INJECTION';
      }
    }
  });
  var beforeAccessor = calls.length;
  await bridge.start(accessor);
  assert.equal(
    candidateReads,
    1,
    'candidate getter is read once before validation and construction'
  );
  assert.equal(operationReads, 1);
  assert.equal(calls.length, beforeAccessor + 1);
  assert.equal(
    calls[calls.length - 1].body.command,
    '/usr/bin/node /media/developer/apps/usr/palm/applications/io.github.razdva122.cytvinstaller/bootstrap.js install --operation ' +
      ID +
      ' --candidate ' +
      SHA
  );
  await bridge.start({
    operation: ID,
    candidate: SHA,
    get prepareSupervisor() {
      supervisorReads++;
      return supervisorReads === 1 ? false : '; printf FLAG_INJECTION';
    },
    get migrate() {
      migrateReads++;
      return migrateReads === 1 ? false : true;
    }
  });
  assert.equal(supervisorReads, 1);
  assert.equal(migrateReads, 1);
  assert(calls[calls.length - 1].body.command.endsWith('--candidate ' + SHA));
  var inspectReads = 0;
  await bridge.inspect({
    get prepareSupervisor() {
      inspectReads++;
      return inspectReads === 1 ? false : true;
    }
  });
  assert.equal(inspectReads, 1);
  assert(calls[calls.length - 1].body.command.endsWith(' inspect'));
  var beforeCoercion = calls.length,
    coercions = 0,
    coercible = {
      toString: function () {
        coercions++;
        return SHA + '; printf COERCION_INJECTION';
      }
    };
  for (var objectOptions of [
    { operation: ID, candidate: coercible },
    { operation: coercible, candidate: SHA },
    { operation: ID, candidate: SHA, prepareSupervisor: coercible },
    { operation: ID, candidate: SHA, migrate: coercible }
  ])
    await rejects(function () {
      return bridge.start(objectOptions);
    });
  assert.equal(
    calls.length,
    beforeCoercion,
    'coercible objects never reach HBC'
  );
  assert.equal(coercions, 0, 'tokens must remain validated primitives');
  // LS2 denial is distinct from missing service/root/backend failure; never expose raw text.
  for (var denialText of [
    'Denied method call "exec" for category "/"',
    'Denied method call "exec" for category "/".'
  ]) {
    bridge = loadBridge({
      returnValue: false,
      errorCode: -1,
      errorText: denialText
    });
    await rejects(() => bridge.inspect(), 'homebrew_exec_denied');
    await rejects(
      () => bridge.start({ operation: ID, candidate: SHA }),
      'homebrew_exec_denied'
    );
  }
  for (var errorReply of [
    { returnValue: false, errorText: 'Unknown method' },
    {
      returnValue: false,
      errorText:
        'private diagnostics Denied method call "exec" for category "/"'
    },
    {
      returnValue: true,
      errorText: 'Denied method call "exec" for category "/"',
      stdoutString: 'not json'
    },
    {
      returnValue: false,
      errorText: 'Denied method call "inspect" for category "/"'
    }
  ]) {
    bridge = loadBridge(errorReply);
    await rejects(() => bridge.inspect(), 'installer_unavailable');
  }
  bridge = loadBridge({ returnValue: true, stdout: '{}' });
  await rejects(function () {
    return bridge.inspect();
  });
  bridge = loadBridge({ returnValue: false, errorText: 'Unknown method' });
  await rejects(function () {
    return bridge.inspect();
  });
  bridge = loadBridge({
    returnValue: true,
    stdoutString: 'private diagnostics'
  });
  await rejects(function () {
    return bridge.inspect();
  });
  var bootstrap = require('../bootstrap.js'),
    executed = [],
    prepares = 0,
    inspects = 0,
    cleanups = 0;
  var deps = {
    process: {
      geteuid: function () {
        return 0;
      },
      versions: { node: '8.12.0' }
    },
    runtime: {
      stage: function (state, full) {
        return Promise.resolve({
          root: '/private/stage',
          driver: '/private/stage/root-updater/install_driver.py',
          editionInspector: '/private/stage/edition/edition.py',
          debloat: '/private/stage/edition/debloat.py',
          cleanup: function () {
            cleanups++;
            return Promise.resolve();
          }
        });
      },
      inspect: function (p) {
        inspects++;
        assert.equal(
          p,
          '/media/developer/apps/usr/palm/applications/' +
            require('../app/appinfo.json').id +
            '/payload'
        );
        return Promise.resolve({
          python: '/usr/bin/python3',
          privateRuntimeRequired: false
        });
      },
      prepare: function () {
        prepares++;
        return Promise.resolve('/usr/bin/python3');
      }
    },
    execute: function (exe, args) {
      executed.push({ exe: exe, args: args });
      return Promise.resolve(JSON.stringify({ state: 'fresh' }));
    }
  };
  for (var badArgs of [
    ['install', '--operation', ID, '--candidate', SHA, '--url', 'x'],
    ['status', '--operation', 'A'.repeat(32)],
    [
      'remove',
      '--operation',
      ID,
      '--candidate',
      SHA,
      '--activate-after-install'
    ],
    ['install', '--operation', ID, '--resume', '--activate-after-install'],
    [
      'install',
      '--operation',
      ID,
      '--candidate',
      SHA,
      '--prepare-supervisor',
      'true'
    ],
    ['inspect', '--resume'],
    ['remove', '--operation', ID],
    ['activate', '--payload', '/tmp'],
    ['no-root-start', '--operation', ID],
    [
      'no-root-start',
      '--operation',
      ID,
      '--candidate',
      SHA,
      '--payload',
      '/tmp'
    ],
    ['no-root-status', '--operation', ID, '--candidate', SHA],
    ['no-root-resume'],
    ['debloat-status', '--settings', 'lmt'],
    ['debloat', '--settings', 'lmt;whoami'],
    ['debloat-restore', '--settings'],
    ['debloat', '--settings', 'lmt', '--operation', ID]
  ])
    await rejects(function () {
      return bootstrap.run(badArgs, deps);
    });
  assert.equal(inspects, 0, 'backend validates before runtime or effects');
  await bootstrap.run(['inspect'], deps);
  assert.equal(prepares, 0);
  assert.equal(
    executed[0].args[3],
    '/private/stage/root-updater/install_driver.py'
  );
  assert.equal(
    executed[0].args[executed[0].args.indexOf('--payload') + 1],
    '/private/stage'
  );
  assert(executed[1].args.includes('--metadata-only'));
  await bootstrap.run(['status', '--operation', ID, '--verify-current'], deps);
  assert(executed[2].args.indexOf('--verify-current') >= 0);
  await bootstrap.run(['remove', '--operation', ID, '--resume'], deps);
  assert(executed[3].args.indexOf('--resume') >= 0);
  assert(
    executed[3].args.indexOf('--payload') < 0,
    'resume uses original snapshot'
  );
  await bootstrap.run(
    [
      'install',
      '--operation',
      ID,
      '--candidate',
      SHA,
      '--activate-after-install'
    ],
    deps
  );
  assert(
    executed[executed.length - 1].args.includes('--activate-after-install')
  );
  var recoverySelections = [];
  deps.runtime.inspect = function (root, recovery) {
    recoverySelections.push(recovery);
    return Promise.resolve({ python: '/usr/bin/python3' });
  };
  await bootstrap.run(['status', '--operation', ID], deps);
  await bootstrap.run(['restore'], deps);
  await bootstrap.run(['remove', '--operation', ID, '--candidate', SHA], deps);
  await bootstrap.run(['inspect'], deps);
  assert.deepEqual(recoverySelections, [true, true, true, false]);
  var originalExecute = deps.execute;
  var fresh = {
    state: 'fresh',
    active_operation: null,
    installation: { can_install: true, reason: 'no_installation' }
  };
  var probeCount = 0;
  var verdict = 'root';
  deps.execute = function (exe, args) {
    if (args[3] === '/private/stage/edition/edition.py') {
      if (!args.includes('--metadata-only')) probeCount++;
      assert.deepEqual(args.slice(0, 3), ['-E', '-s', '-B']);
      return Promise.resolve(
        JSON.stringify({
          decision: verdict,
          tv: {
            modelName: 'OLED55C3PUA',
            sdkVersion: '8.3.0-7',
            firmwareVersion: '1.2.3-private',
            serialNumber: 'private'
          }
        })
      );
    }
    return Promise.resolve(JSON.stringify(fresh));
  };
  for (var scenario of [
    ['root', 'fresh', undefined, 'pass'],
    ['external_root', 'external_setup', 'root_setup_on_computer', 'fail'],
    ['external_no_root', 'external_setup', 'no_root_setup_on_computer', 'fail'],
    [
      'unconfirmed',
      'edition_unconfirmed',
      'home_interfaces_unconfirmed',
      'unknown'
    ],
    ['bad', 'edition_unconfirmed', 'home_interfaces_unconfirmed', 'unknown']
  ]) {
    verdict = scenario[0];
    var inspection = await bootstrap.run(['inspect'], deps);
    assert.equal(inspection.state, scenario[1]);
    assert.equal(inspection.code, scenario[2]);
    assert.equal(typeof inspection.payload_sha256, 'string');
    assert.deepEqual(inspection.checks, {
      'homebrew-access': 'pass',
      'root-user': 'pass',
      'node-version': 'pass',
      'installer-payload': 'pass',
      'python-runtime': 'pass',
      'installer-staging': 'pass',
      'product-state': 'pass',
      'home-compatibility': scenario[3]
    });
    assert.deepEqual(inspection.tv, {
      node_version: '8.12.0',
      node_version_status: 'read',
      modelName: 'OLED55C3PUA',
      sdkVersion: '8.3.0-7'
    });
    if (verdict !== 'root') assert.equal(inspection.installation, undefined);
  }
  var ordinaryStage = deps.runtime.stage;
  var probeExecute = deps.execute;
  var noRootAvailability = { state: 'unknown' };
  var noRootAdmission = {
    state: 'eligible',
    candidate_sha256: SHA,
    versions: { home: '1.2.3' }
  };
  var noRootCalls = [];
  deps.runtime.stage = function (state, kind) {
    return ordinaryStage(state, kind).then(function (stage) {
      stage.noRoot = '/private/stage/edition/no_root.py';
      return stage;
    });
  };
  deps.execute = function (exe, args) {
    if (args[3] !== '/private/stage/edition/no_root.py')
      return probeExecute(exe, args);
    noRootCalls.push(args.slice(4));
    assert.equal(args[args.indexOf('--payload') + 1], '/private/stage');
    var answer = {
      status: noRootAvailability,
      inspect: noRootAdmission,
      start: { state: 'pending', operation: ID, stage: 'pairing' },
      resume: { state: 'pending', operation: ID, stage: 'installing' }
    }[args[4]];
    return Promise.resolve(JSON.stringify(answer));
  };
  verdict = 'root';
  assert.equal((await bootstrap.run(['inspect'], deps)).state, 'fresh');
  assert.deepEqual(
    noRootCalls.map((args) => args[0]),
    ['status']
  );
  verdict = 'external_no_root';
  var noRootReady = await bootstrap.run(['inspect'], deps);
  assert.equal(noRootReady.state, 'no_root_ready');
  assert.equal(noRootReady.edition, 'no-root');
  assert.equal(noRootReady.candidate_sha256, SHA);
  assert.deepEqual(
    noRootCalls.map((args) => args[0]),
    ['status', 'status', 'inspect']
  );
  var noRootStarted = await bootstrap.run(
    ['no-root-start', '--operation', ID, '--candidate', SHA],
    deps
  );
  assert.equal(noRootStarted.state, 'pending');
  assert.equal(noRootStarted.edition, 'no-root');
  assert(noRootCalls.at(-1).includes(ID));
  assert(noRootCalls.at(-1).includes(SHA));
  noRootAvailability = { state: 'pending', operation: ID, stage: 'pairing' };
  assert.equal((await bootstrap.run(['inspect'], deps)).state, 'pending');
  assert.equal(
    (await bootstrap.run(['no-root-status', '--operation', ID], deps))
      .operation,
    ID
  );
  assert.equal(
    (await bootstrap.run(['no-root-resume', '--operation', ID], deps)).stage,
    'installing'
  );
  noRootAvailability = {
    state: 'recovery_required',
    stage: 'complete',
    operation: ID,
    code: 'current-state-unverified'
  };
  verdict = 'root';
  assert.equal(
    (await bootstrap.run(['inspect'], deps)).state,
    'recovery_required'
  );
  Object.assign(fresh.installation, {
    reason: 'verified_clean_removal',
    clean_removal_verified: true,
    can_maintain: false
  });
  const afterRemoval = await bootstrap.run(['inspect'], deps);
  assert.equal(afterRemoval.state, 'fresh');
  assert.equal(afterRemoval.superseded_no_root_operation, ID);
  noRootAvailability.stage = 'packages';
  assert.equal(
    (await bootstrap.run(['inspect'], deps)).state,
    'recovery_required'
  );
  Object.assign(fresh.installation, { reason: 'no_installation' });
  delete fresh.installation.can_maintain;
  verdict = 'external_no_root';
  deps.runtime.stage = ordinaryStage;
  deps.execute = probeExecute;
  fresh.installation.clean_removal_verified = true;
  assert.equal(
    (await bootstrap.run(['inspect'], deps)).state,
    'edition_unconfirmed'
  );
  fresh.installation.reason = 'verified_clean_removal';
  fresh.installation.can_maintain = false;
  verdict = 'external_no_root';
  assert.equal(
    (await bootstrap.run(['inspect'], deps)).code,
    'no_root_setup_on_computer'
  );
  delete fresh.installation.clean_removal_verified;
  fresh.installation.reason = 'no_installation';
  fresh.active_operation = { state: 'pending' };
  assert((await bootstrap.run(['inspect'], deps)).active_operation);
  delete fresh.active_operation;
  assert.equal(
    (await bootstrap.run(['inspect'], deps)).state,
    'edition_unconfirmed'
  );
  assert.equal(probeCount, 9);
  for (const state of ['conflict', 'migration_required', 'recovery_required']) {
    fresh.state = state;
    const inspected = await bootstrap.run(['inspect'], deps);
    assert.equal(inspected.state, state);
    assert.equal(inspected.checks['product-state'], 'fail');
    assert.equal(inspected.checks['home-compatibility'], 'pending');
    assert.equal(inspected.tv.modelName, 'OLED55C3PUA');
  }
  assert.equal(
    probeCount,
    9,
    'metadata alone does not repeat the admission probe'
  );
  deps.execute = originalExecute;
  deps.runtime.inspect = function () {
    return Promise.resolve({
      python: null,
      privateRuntimeRequired: true,
      requiredSpace: 335544320
    });
  };
  var prerequisites = await bootstrap.run(['inspect'], deps);
  assert.equal(prerequisites.state, 'prerequisites');
  assert.equal(prerequisites.checks['installer-payload'], 'pass');
  assert.equal(prerequisites.checks['python-runtime'], 'pending');
  assert.equal(prerequisites.checks['installer-staging'], 'pending');
  assert.equal(prepares, 0);
  await rejects(function () {
    return bootstrap.run(
      ['install', '--operation', ID, '--candidate', SHA],
      deps
    );
  });
  assert.equal(prepares, 0);
  await bootstrap.run(['prepare-runtime'], deps);
  assert.equal(prepares, 1);
  deps.runtime.inspect = function () {
    return Promise.resolve({ python: '/usr/bin/python3' });
  };
  var priorInspect = deps.runtime.inspect;
  for (var verified of [false, true]) {
    deps.runtime.inspect = function (root, recovery, pin, payloadVerified) {
      if (verified) payloadVerified();
      return Promise.reject(new Error('private path mock-secret'));
    };
    var failedInspect = await bootstrap.run(['inspect'], deps);
    assert.equal(failedInspect.code, 'installer_unavailable');
    assert.equal(
      failedInspect.checks['installer-payload'],
      verified ? 'pass' : 'fail'
    );
    assert.equal(
      failedInspect.checks['python-runtime'],
      verified ? 'fail' : 'pending'
    );
    assert.equal(failedInspect.checks['product-state'], 'pending');
    assert(!JSON.stringify(failedInspect).includes('mock-secret'));
  }
  deps.runtime.inspect = priorInspect;
  var priorStage = deps.runtime.stage;
  deps.runtime.stage = function () {
    return Promise.reject(new Error('private path mock-secret'));
  };
  var failedStage = await bootstrap.run(['inspect'], deps);
  assert.equal(failedStage.checks['python-runtime'], 'pass');
  assert.equal(failedStage.checks['installer-staging'], 'fail');
  assert.equal(failedStage.checks['product-state'], 'pending');
  deps.runtime.stage = priorStage;
  var priorCleanups = cleanups;
  deps.execute = function () {
    return Promise.resolve('invalid json');
  };
  var unreadableState = await bootstrap.run(['inspect'], deps);
  assert.equal(unreadableState.code, 'installer_unavailable');
  assert.equal(unreadableState.checks['installer-staging'], 'pass');
  assert.equal(unreadableState.checks['product-state'], 'unknown');
  assert.equal(unreadableState.checks['home-compatibility'], 'pending');
  assert.equal(
    cleanups,
    priorCleanups + 1,
    'invalid child output still cleans this private stage after exit'
  );
  deps.execute = function () {
    return Promise.reject(new Error('child exited'));
  };
  await rejects(function () {
    return bootstrap.run(['restore'], deps);
  });
  assert.equal(
    cleanups,
    priorCleanups + 2,
    'failed child still cleans this private stage after exit'
  );
  deps.execute = function (exe, args) {
    executed.push({ exe: exe, args: args });
    return Promise.resolve(JSON.stringify({ state: 'debloat' }));
  };
  var allDebloat =
    'homePromotion,contentRecommendation,screenSaverAd,livePromotion,promotionStreamer,webOSPromotionVideo,livePlus,adCookie,lmt,aiNudge,sportsAlarm,dbgLogUpload,faultLogUpload';
  for (var fixture of [
    [['debloat', '--settings', allDebloat], [allDebloat]],
    [['debloat-status'], []],
    [['debloat', '--settings', 'homePromotion,lmt'], ['homePromotion,lmt']],
    [['debloat-restore', '--settings', 'lmt'], ['lmt']]
  ]) {
    assert.equal((await bootstrap.run(fixture[0], deps)).state, 'debloat');
    assert.deepEqual(
      executed[executed.length - 1].args,
      [
        '-E',
        '-s',
        '-B',
        '/private/stage/edition/debloat.py',
        fixture[0][0]
      ].concat(fixture[1])
    );
  }
  var cleanupBridge = loadBridge({
    returnValue: true,
    stdoutString: JSON.stringify({ state: 'recovery_required' })
  });
  for (var [method, action] of [
    ['cleanRemove', 'homebrew-remove'],
    ['cleanStatus', 'homebrew-remove-status'],
    ['removeInstaller', 'homebrew-remove-tile']
  ]) {
    await rejects(function () {
      return cleanupBridge[method](ID + ' --payload /tmp');
    });
    await cleanupBridge[method](ID);
    assert(
      calls[calls.length - 1].body.command.endsWith(
        ' ' + action + ' --operation ' + ID
      )
    );
    await rejects(function () {
      return bootstrap.run(
        [action, '--operation', ID, '--payload', '/tmp'],
        deps
      );
    });
    await rejects(function () {
      return bootstrap.run([action, '--operation'], deps);
    });
  }
  var collected = [];
  deps.runtime.removal = function (payload, pin, id, action) {
    collected.push([id, action]);
    return Promise.resolve(
      action === 'homebrew-remove-tile' ? { state: 'complete' } : null
    );
  };
  deps.runtime.stage = function (state, full) {
    collected.push(full);
    return priorStage(state, full);
  };
  deps.execute = function (exe, args) {
    executed.push({ exe: exe, args: args });
    return Promise.resolve(JSON.stringify({ state: 'recovery_required' }));
  };
  await bootstrap.run(['homebrew-remove-status', '--operation', ID], deps);
  assert(!executed[executed.length - 1].args.includes('--payload'));
  await bootstrap.run(['homebrew-remove', '--operation', ID], deps);
  assert(executed[executed.length - 1].args.includes('--payload'));
  assert.equal(
    (await bootstrap.run(['homebrew-remove-tile', '--operation', ID], deps))
      .state,
    'complete'
  );
  assert.deepEqual(collected, [
    [ID, 'homebrew-remove-status'],
    false,
    [ID, 'homebrew-remove'],
    'removal',
    [ID, 'homebrew-remove-tile']
  ]);
  var fenced = [];
  var fenceStatus = 'pending';
  deps.runtime.inspect = function () {
    return Promise.resolve({
      python: '/usr/bin/python3',
      context: { manifest: { files: { 'edition/no_root.py': {} } } }
    });
  };
  deps.runtime.stage = function (state, kind) {
    return priorStage(state, kind).then(function (stage) {
      stage.noRoot = '/private/stage/edition/no_root.py';
      return stage;
    });
  };
  deps.execute = function (executable, args) {
    fenced.push(args.slice(4));
    return Promise.resolve(
      JSON.stringify({
        state: args[4] === 'prepare-remove' ? fenceStatus : 'complete'
      })
    );
  };
  assert.equal(
    (await bootstrap.run(['homebrew-remove', '--operation', ID], deps)).state,
    'pending'
  );
  assert.deepEqual(
    fenced.map((args) => args[0]),
    ['prepare-remove']
  );
  assert.deepEqual(fenced[0].slice(-2), ['--removal', ID]);
  fenceStatus = 'removal_ready';
  assert.equal(
    (await bootstrap.run(['homebrew-remove', '--operation', ID], deps)).state,
    'complete'
  );
  assert.deepEqual(
    fenced.map((args) => args[0]),
    ['prepare-remove', 'prepare-remove', 'homebrew-remove']
  );
  deps.runtime.stage = priorStage;
  deps.process.geteuid = function () {
    return 1000;
  };
  var beforeRootGate = inspects;
  var denied = await bootstrap.run(['inspect'], deps);
  assert.equal(denied.state, 'unsupported');
  assert.equal(denied.code, 'homebrew_root_required');
  assert.equal(denied.checks['homebrew-access'], 'pass');
  assert.equal(denied.checks['root-user'], 'fail');
  assert.equal(denied.checks['installer-payload'], 'pending');
  await rejects(function () {
    return bootstrap.run(['debloat', '--settings', 'lmt'], deps);
  });
  assert.equal(inspects, beforeRootGate);

  deps.process.geteuid = function () {
    return 0;
  };
  deps.process.versions.node = '0.12.2';
  var unavailable = await bootstrap.run(['inspect'], deps);
  assert.equal(unavailable.state, 'unsupported');
  assert.equal(unavailable.checks['node-version'], 'fail');
  assert.equal(unavailable.checks['root-user'], 'pending');
  console.log(
    'PASS fixed HBC exec reply, exact LS2 denial classification, input boundaries, root/Node gates, read-only prerequisites/status, explicit runtime and original resume'
  );
})().catch(function (e) {
  console.error(e);
  process.exitCode = 1;
});
