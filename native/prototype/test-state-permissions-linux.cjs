// Real kernel ownership/permission enforcement, run with sudo on Linux CI.
const a = require('node:assert/strict'),
  fs = require('fs'),
  os = require('os'),
  path = require('path'),
  cp = require('child_process');
if (process.platform !== 'linux' || process.getuid() !== 0) {
  console.log(
    'SKIP: real multi-UID permissions require Linux root (covered by CI)'
  );
} else {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-uids-')),
    state = path.join(root, 'state'),
    key = path.join(state, 'ssap-key.json');
  const modulePath = require.resolve('../app/state-permissions');
  // Copy the runtime to a traversable temporary directory, independent of checkout permissions.
  fs.copyFileSync(modulePath, path.join(root, 'state-permissions.js'));
  fs.copyFileSync(
    require.resolve('../app/contract-events'),
    path.join(root, 'contract-events.js')
  );
  fs.chmodSync(root, 0o755);
  function run(uid, script, primary = 5000, groups = [5000]) {
    const result = cp.spawnSync(
      process.execPath,
      [
        '-e',
        'process.setgroups(' +
          JSON.stringify(groups) +
          ');process.setgid(' +
          primary +
          ');process.setuid(' +
          uid +
          ');' +
          script
      ],
      { encoding: 'utf8', cwd: root }
    );
    a.equal(result.status, 0, result.stderr || result.stdout);
  }
  // Canonical sessions restore cwd after dropping UID; do not inherit a
  // checkout behind a runner-private home directory. Keep bounded diagnostics.
  const log =
      'function(e){if(e.contract)process.stderr.write(JSON.stringify(e.contract)+"\\n");}',
    check =
      'if(!require(' +
      JSON.stringify(path.join(root, 'state-permissions.js')) +
      ')(' +
      JSON.stringify(state) +
      ',' +
      log +
      '))process.exit(1);';
  try {
    fs.mkdirSync(state);
    fs.chownSync(state, 5999, 5000);
    fs.chmodSync(state, 0o775);
    fs.writeFileSync(key, '{"key":"test-key"}');
    fs.chownSync(key, 5580, 5000);
    fs.chmodSync(key, 0o775);
    fs.writeFileSync(path.join(state, 'apps.json'), '["test.app"]');
    fs.chownSync(path.join(state, 'apps.json'), 5580, 5000);
    fs.chmodSync(path.join(state, 'apps.json'), 0o775);
    run(5367, check);
    a.equal(fs.statSync(key).uid, 5367);
    a.equal(fs.statSync(key).gid, 5000);
    a.equal(fs.statSync(key).mode & 0o777, 0o640);
    run(
      5380,
      check +
        'if(JSON.parse(require("fs").readFileSync(' +
        JSON.stringify(key) +
        ')).key!=="test-key")process.exit(2);'
    );
    fs.chmodSync(state, 0o777);
    run(
      5367,
      check +
        'if(JSON.parse(require("fs").readFileSync(' +
        JSON.stringify(key) +
        ')).key!=="test-key")process.exit(2);'
    );
    a.equal(fs.statSync(state).mode & 0o7777, 0o777);
    const control = path.join(state, 'control.json');
    for (const mode of [0o640, 0o660]) {
      fs.writeFileSync(control, '{"cmd":"stop"}');
      fs.chownSync(control, 5999, 5000);
      fs.chmodSync(control, mode);
      run(
        6575,
        'if(!require(' +
          JSON.stringify(path.join(root, 'state-permissions.js')) +
          ')(' +
          JSON.stringify(state) +
          ',' +
          log +
          ',true))process.exit(4);',
        6575
      );
      a.equal(fs.statSync(control).uid, 6575);
      a.equal(fs.statSync(control).gid, 5000);
      a.equal(fs.statSync(control).mode & 0o777, 0o660);
      a.equal(fs.readFileSync(control, 'utf8'), '{}');
      a.equal(JSON.parse(fs.readFileSync(key)).key, 'test-key');
      run(
        5999,
        'require("fs").writeFileSync(' +
          JSON.stringify(control) +
          ',' +
          JSON.stringify('{"cmd":"stop"}') +
          ');'
      );
    }
    // Actual Root-SSH ownership after package-mode expansion, then controller
    // bootstrap under its supplementary jailer group and the next installer.
    const boot = path.join(root, 'boot-state');
    fs.mkdirSync(boot);
    fs.chownSync(boot, 5999, 5000);
    fs.chmodSync(boot, 0o777);
    const bootFiles = {
      'ssap-key.json': '{"key":"boot-key"}',
      'apps.json': '["test.app"]',
      'control.json': '{"cmd":"stop"}',
      'controller.pid': 'invalid stale PID',
      'controller.log': 'untrusted old log',
      'home-control.json': '{"enabled":false}',
      'startup-state.json': '{"enabled":true,"boot":"previous","schema":3}',
      blocked: 'emergency',
      watchdog: 'watchdog'
    };
    for (const [name, content] of Object.entries(bootFiles)) {
      const file = path.join(boot, name);
      fs.writeFileSync(file, content);
      fs.chownSync(file, 5999, 5000);
      fs.chmodSync(file, 0o777);
    }
    const bootModule = JSON.stringify(path.join(root, 'state-permissions.js')),
      bootPath = JSON.stringify(boot),
      appsInode = fs.statSync(path.join(boot, 'apps.json')).ino;
    run(
      5431,
      'var p=require(' +
        bootModule +
        '),d=' +
        bootPath +
        ';if(!p(d,null,true))process.exit(7);p.atomicRecord(d,"pid","123");p.appendLog(d,"fresh log");',
      5431
    );
    a.equal(fs.statSync(path.join(boot, 'ssap-key.json')).uid, 5431);
    a.equal(fs.statSync(path.join(boot, 'ssap-key.json')).gid, 5000);
    a.equal(fs.statSync(path.join(boot, 'ssap-key.json')).mode & 0o777, 0o640);
    a.equal(fs.statSync(path.join(boot, 'apps.json')).ino, appsInode);
    a.equal(fs.statSync(path.join(boot, 'apps.json')).uid, 5999);
    // The app UID can still use the published explicit Start path while the
    // packaged owner retains the expanded state directory.
    const bootStorage = 'var p=require(' + bootModule + '),d=' + bootPath + ';';
    run(
      5431,
      bootStorage + 'if(p.stopGeneration(d,"manual")!==null)process.exit(8);',
      5431
    );
    a.equal(fs.existsSync(path.join(boot, 'stop-generation')), false);
    a.equal(fs.statSync(boot).mode & 0o777, 0o777);
    const bootHash = require('crypto')
      .createHash('sha256')
      .update(bootFiles['ssap-key.json'])
      .digest('hex');
    run(
      0,
      'require(' +
        bootModule +
        ').prepareConfiguration(' +
        bootPath +
        ',{expectedHash:' +
        JSON.stringify(bootHash) +
        '});'
    );
    a.equal(fs.statSync(path.join(boot, 'apps.json')).ino, appsInode);
    a.equal(fs.statSync(path.join(boot, 'apps.json')).uid, 5999);
    a.equal(fs.statSync(path.join(boot, 'apps.json')).mode & 0o777, 0o644);
    for (const name of [
      'home-control.json',
      'startup-state.json',
      'blocked',
      'watchdog'
    ])
      a.equal(fs.readFileSync(path.join(boot, name), 'utf8'), bootFiles[name]);
    // Actual host adapter, without a later upload that could hide wrong ownership.
    const adapter = cp
      .execFileSync(
        process.env.PYTHON || 'python3',
        [
          '-c',
          'from cytv.no_root_observer import STATE_CHECK; print(STATE_CHECK)'
        ],
        { cwd: path.resolve(__dirname, '../..'), encoding: 'utf8' }
      )
      .split(
        '/media/developer/apps/usr/palm/applications/com.local.nativehome/state'
      )
      .join(boot);
    const privateCwd = path.join(root, 'root-private');
    fs.mkdirSync(privateCwd, { mode: 0o700 });
    fs.chownSync(path.join(boot, 'ssap-key.json'), 5431, 5000);
    fs.chmodSync(path.join(boot, 'ssap-key.json'), 0o775);
    fs.chmodSync(path.join(boot, 'apps.json'), 0o777);
    fs.chmodSync(boot, 0o777);
    run(
      0,
      'process.chdir(' +
        JSON.stringify(privateCwd) +
        ');process.argv=["node",' +
        JSON.stringify('repair-key-mode:' + bootHash) +
        ',' +
        bootPath +
        '];' +
        adapter
    );
    a.equal(fs.statSync(path.join(boot, 'ssap-key.json')).uid, 5999);
    a.equal(fs.statSync(path.join(boot, 'apps.json')).uid, 5999);
    a.equal(fs.statSync(path.join(boot, 'apps.json')).ino, appsInode);
    fs.chmodSync(path.join(boot, 'ssap-key.json'), 0o777);
    run(
      5431,
      'if(!require(' +
        bootModule +
        ')(' +
        bootPath +
        ',null,true))process.exit(8);',
      5431
    );
    a.equal(fs.statSync(path.join(boot, 'ssap-key.json')).mode & 0o777, 0o640);
    // Root SSH normalizes the packaged owner's directory before issuing a
    // usable setup baseline. The real app UID can read it and publish Stop.
    fs.chmodSync(boot, 0o777);
    run(
      0,
      bootStorage +
        'if(!/^S[a-f0-9]{32}$/.test(p.stopGeneration(d,"install")))process.exit(9);'
    );
    const generation = path.join(boot, 'stop-generation');
    const baseline = fs.readFileSync(generation, 'utf8');
    a.equal(fs.statSync(boot).mode & 0o777, 0o770);
    a.equal(fs.statSync(generation).gid, 5000);
    run(
      5431,
      bootStorage +
        'if(p.stopGeneration(d)!==' +
        JSON.stringify(baseline) +
        ')process.exit(10);p.publishStopGeneration(d);',
      5431
    );
    a.notEqual(fs.readFileSync(generation, 'utf8'), baseline);
    // Developer Mode setup can still atomically upload a new key after repair.
    run(
      5580,
      'var fs=require("fs"),p=' +
        JSON.stringify(key) +
        ';fs.writeFileSync(p+".new",\'{"key":"updated-key"}\',{mode:0o640});fs.renameSync(p+".new",p);'
    );
    run(5367, check);
    a.equal(JSON.parse(fs.readFileSync(key)).key, 'updated-key');
    fs.chmodSync(key, 0o775);
    fs.chmodSync(state, 0o755);
    run(
      5367,
      'if(require(' +
        JSON.stringify(path.join(root, 'state-permissions.js')) +
        ')(' +
        JSON.stringify(state) +
        ',' +
        log +
        '))process.exit(3);'
    );
    a.equal(fs.statSync(key).mode & 0o777, 0o775);
    const renewal = path.join(root, 'renewal-state'),
      channel = path.join(renewal, 'home-control');
    fs.mkdirSync(renewal);
    fs.mkdirSync(channel);
    for (const dir of [renewal, channel]) {
      fs.chownSync(dir, 5999, 5000);
      fs.chmodSync(dir, 0o2770);
    }
    for (const prefix of ['home', 'input', 'catalog'])
      for (const suffix of ['request', 'response']) {
        const kind = prefix + '-' + suffix,
          output = path.join(channel, kind + '.json');
        fs.writeFileSync(output, 'untrusted old output');
        fs.chownSync(output, 5999, 5000);
        fs.chmodSync(output, 0o777);
        run(
          5367,
          'require(' +
            bootModule +
            ').atomicRecord(' +
            JSON.stringify(channel) +
            ',' +
            JSON.stringify(kind) +
            ',"fresh");',
          5367
        );
        a.equal(fs.readFileSync(output, 'utf8'), 'fresh');
        a.equal(fs.statSync(output).mode & 0o777, 0o660);
        a.equal(fs.statSync(output).gid, 5000);
      }
    const drifted = path.join(renewal, 'drifted'),
      privateChannel = path.join(drifted, '.private'),
      quotedDrifted = JSON.stringify(drifted);
    fs.mkdirSync(drifted);
    fs.chownSync(drifted, 5999, 5000);
    fs.chmodSync(drifted, 0o775);
    run(
      6923,
      'require(' +
        bootModule +
        ').atomicRecord(' +
        quotedDrifted +
        ',"catalog-request","fresh");'
    );
    a.equal(fs.statSync(drifted).mode & 0o7777, 0o775);
    a.equal(fs.statSync(drifted).uid, 5999);
    a.deepEqual(fs.readdirSync(drifted), ['.private']);
    a.equal(fs.statSync(privateChannel).mode & 0o7777, 0o2770);
    a.equal(fs.statSync(privateChannel).uid, 6923);
    a.equal(fs.statSync(privateChannel).gid, 5000);
    const restored = fs.statSync(
      path.join(privateChannel, 'catalog-request.json')
    );
    a.equal(restored.mode & 0o7777, 0o660);
    a.equal(restored.gid, 5000);
    run(
      5431,
      'var s=require(' +
        bootModule +
        '),d=' +
        quotedDrifted +
        ';if(s.readChannelRecord(d,"catalog-request")!=="fresh")process.exit(8);s.atomicRecord(d,"catalog-response","answer");'
    );
    run(
      6923,
      'if(require(' +
        bootModule +
        ').readChannelRecord(' +
        quotedDrifted +
        ',"catalog-response")!=="answer")process.exit(8);'
    );
    run(
      6580,
      'var f=require("fs");try{f.readFileSync(' +
        JSON.stringify(path.join(privateChannel, 'catalog-request.json')) +
        ');process.exit(9)}catch(e){if(e.code!=="EACCES")throw e}',
      6580,
      []
    );
    const request = path.join(channel, 'home-request'),
      response = path.join(channel, 'home-response');
    run(
      5367,
      'var fs=require("fs"),p=' +
        JSON.stringify(request) +
        ';fs.writeFileSync(p+".tmp",JSON.stringify({id:"test"}),{mode:0o660});fs.chmodSync(p+".tmp",0o660);fs.renameSync(p+".tmp",p+".json");',
      5367
    );
    a.equal(
      fs.statSync(request + '.json').gid,
      5000,
      'setgid overrides the service primary group'
    );
    run(
      6575,
      'var fs=require("fs");if(JSON.parse(fs.readFileSync(' +
        JSON.stringify(request + '.json') +
        ')).id!=="test")process.exit(5);var p=' +
        JSON.stringify(response) +
        ';fs.writeFileSync(p+".tmp",JSON.stringify({id:"test",enabled:true}),{mode:0o660});fs.chmodSync(p+".tmp",0o660);fs.renameSync(p+".tmp",p+".json");',
      6575
    );
    a.equal(
      fs.statSync(response + '.json').gid,
      5000,
      'controller reply inherits the same group'
    );
    run(
      5367,
      'if(!JSON.parse(require("fs").readFileSync(' +
        JSON.stringify(response + '.json') +
        ')).enabled)process.exit(6);',
      5367
    );
    // A rejected Helper service call uses trusted SSH stop code. The live
    // controller must still be able to execute block() under another UID.
    fs.chmodSync(state, 0o770);
    const stop = cp
      .execFileSync(
        process.env.PYTHON || 'python3',
        ['-c', 'from cytv.helper_stop import PROGRAM; print(PROGRAM)'],
        { encoding: 'utf8' }
      )
      .replaceAll(
        '/media/developer/apps/usr/palm/applications/com.local.nativehome/state',
        state
      )
      .replaceAll(
        '/media/developer/apps/usr/palm/applications/com.local.nativehome',
        root
      );
    run(5999, stop, 5999);
    const blocked = path.join(state, 'blocked');
    a.equal(
      fs.statSync(blocked).gid,
      5000,
      'SSH stop latch shares the controller group even with another primary gid'
    );
    run(
      6575,
      'var fs=require("fs");if(JSON.parse(fs.readFileSync(' +
        JSON.stringify(control) +
        ')).cmd!=="stop")process.exit(7);fs.writeFileSync(' +
        JSON.stringify(blocked) +
        ',"stopped");',
      6575
    );
    a.equal(
      fs.readFileSync(blocked, 'utf8'),
      'stopped',
      'controller block() retains an orderly stop path'
    );
    // Root SSH does not join the No-root jailer group. A normal disable
    // reply can leave controller.pid pending, so its checked Stop must work.
    const latchBeforeRoot = fs.statSync(blocked);
    run(
      0,
      'require("node:assert/strict").deepEqual(process.getgroups(),[0]);' +
        stop,
      0,
      [0]
    );
    a.equal(fs.statSync(blocked).ino, latchBeforeRoot.ino);
    a.equal(fs.readFileSync(blocked, 'utf8'), 'stopped');
    a.equal(fs.statSync(control).uid, 0);
    a.equal(fs.statSync(control).gid, 5000);
    fs.unlinkSync(blocked);
    run(0, stop, 0, [0]);
    a.equal(fs.statSync(blocked).uid, 0);
    a.equal(fs.statSync(blocked).gid, 5000);
    a.equal(fs.statSync(blocked).mode & 0o777, 0o664);
    a.equal(fs.readFileSync(control, 'utf8'), '{"cmd":"stop"}');
    run(
      6575,
      'require("fs").writeFileSync(' +
        JSON.stringify(blocked) +
        ',"root-stop-observed");',
      6575
    );
    a.equal(fs.readFileSync(blocked, 'utf8'), 'root-stop-observed');
    console.log(
      'PASS: real installer/developer/helper/service UIDs, shared group, Root without jailer membership, reconfiguration, denied replacement and setgid Home IPC'
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
}
