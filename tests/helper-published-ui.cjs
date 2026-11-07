// Execute /status from the exact published IPK, then feed its reply to the panel.
// Only the TV filesystem, LS2 transport and DOM are simulated; no TV is contacted.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { createHash } = require('node:crypto');
const { execFileSync } = require('node:child_process');
const ipk = 'native/published/com.local.nativehome_0.6.17_arm.ipk';
assert.equal(
  createHash('sha256').update(fs.readFileSync(ipk)).digest('hex'),
  '165d933c17f1ed24f0ab65986293c7488b0b5d875db5f7b1215e46f24d422f92'
);
const files = JSON.parse(
  execFileSync(
    process.env.PYTHON || 'python3',
    [
      '-c',
      "import json,sys; from pathlib import Path; from cytv.package import data_files; print(json.dumps({n:b.decode() for n,b in data_files(Path(sys.argv[1]).read_bytes()).items() if n.startswith('usr/palm/services/') and n.endswith('.js')}))",
      ipk
    ],
    { encoding: 'utf8' }
  )
);
const prefix = 'usr/palm/services/com.local.nativehome.service/';
function publishedStatus(blocked = false) {
  const boot = { exports: {} },
    methods = {};
  vm.runInNewContext(files[prefix + 'boot-state.js'], {
    module: boot,
    exports: boot.exports
  });
  vm.runInNewContext(files[prefix + 'service.js'], {
    console,
    __dirname: '/service',
    require(name) {
      if (name === 'webos-service')
        return class {
          register(method, handler) {
            methods[method] = handler;
          }
        };
      if (name === './boot-state') return boot.exports;
      if (name.endsWith('/state-permissions')) return () => true;
      if (name === 'fs')
        return {
          readFileSync(path) {
            if (path === '/proc/sys/kernel/random/boot_id') return 'test-boot';
            if (path === '/proc/stat') return 'btime 1';
            throw Object.assign(Error('absent'), { code: 'ENOENT' });
          },
          statSync() {
            if (!blocked)
              throw Object.assign(Error('absent'), { code: 'ENOENT' });
          }
        };
      throw Error('Unexpected dependency: ' + name);
    }
  });
  let reply;
  methods.status({
    respond(value) {
      reply = JSON.parse(JSON.stringify(value));
    }
  });
  assert.equal(reply.returnValue, true);
  assert.equal(
    Object.hasOwn(reply, 'running'),
    false,
    'published protocol has no running field'
  );
  return reply;
}
function panel(statusReply, homeReply) {
  if (arguments.length === 1) homeReply = { returnValue: true, enabled: true };
  const elements = [],
    calls = [],
    timers = new Map();
  let timer = 0;
  const document = {
    body: { appendChild() {} },
    addEventListener() {},
    createElement(tag) {
      const element = {
        tag,
        hidden: false,
        disabled: false,
        appendChild() {},
        setAttribute() {},
        focus() {
          document.activeElement = this;
        }
      };
      elements.push(element);
      return element;
    }
  };
  const window = {
    HomeI18n: {
      ready: (callback) => callback(),
      t: (text) => text,
      confirm(options, callback) {
        window.confirmStart = callback;
      }
    }
  };
  vm.runInNewContext(fs.readFileSync('launcher/helper-control.js', 'utf8'), {
    window,
    document,
    setTimeout(callback) {
      timers.set(++timer, callback);
      return timer;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    PalmServiceBridge: class {
      cancel() {}
      call(uri, raw) {
        calls.push({ uri, params: JSON.parse(raw) });
        const reply = uri.endsWith('/status')
          ? statusReply
          : uri.endsWith('/homeStatus')
            ? homeReply
            : { returnValue: true };
        if (reply !== undefined) this.onservicecallback(JSON.stringify(reply));
      }
    }
  });
  window.HomeHelper.open();
  return {
    window,
    calls,
    timers,
    buttons: elements.filter((e) => e.tag === 'button'),
    status: elements.filter((e) => e.tag === 'p')[1]
  };
}
for (const enabled of [true, false]) {
  const ui = panel(publishedStatus(), { returnValue: true, enabled });
  assert.equal(
    ui.status.textContent,
    enabled
      ? 'Home and return from apps open Clean Your TV.'
      : 'Home and return from apps open LG Home.'
  );
  assert.equal(
    ui.buttons[1].disabled,
    false,
    'published Helper permits Home settings'
  );
  assert.equal(
    ui.buttons[2].hidden,
    true,
    'a responsive legacy controller needs no restart'
  );
  assert.equal(
    ui.calls.some((c) => c.uri.endsWith('/launch')),
    false
  );
}
// A blocked Helper is never probed; running:false is confirmed through homeStatus,
// because a jailed service (webOS 3.x) cannot see a live controller.
for (const [reply, home, calls] of [
  [publishedStatus(true), undefined, 1],
  [
    { returnValue: true, running: false, blocked: false },
    { returnValue: false },
    2
  ]
]) {
  const ui = home ? panel(reply, home) : panel(reply);
  assert.equal(
    ui.buttons[2].hidden,
    false,
    'stopped or blocked Helper can be explicitly started'
  );
  assert.equal(
    ui.calls.length,
    calls,
    'do not start a stopped Helper while checking it'
  );
  ui.buttons[2].onclick();
  assert.equal(
    ui.calls.length,
    calls,
    'opening confirmation cannot start Helper'
  );
  ui.window.confirmStart();
  assert.equal(
    ui.calls.filter(
      (c) => c.params.params && c.params.params.nativeHomeStart === true
    ).length,
    1
  );
}
assert.equal(
  panel({ returnValue: true, running: true }).buttons[1].disabled,
  false,
  'current protocol remains supported'
);
{
  const ui = panel({ returnValue: true, running: false, blocked: false });
  assert.equal(
    ui.buttons[2].hidden,
    true,
    'a controller answering homeStatus is running even if a jailed service cannot see it'
  );
}
// #196: an LS2 refusal is independent of the authenticated same-package broker.
for (const enabled of [true, false]) {
  const ui = panel(
    { returnValue: false, errorCode: -1 },
    { returnValue: true, enabled }
  );
  assert.equal(
    ui.buttons[1].disabled,
    false,
    'cross-package refusal must not hide responsive Home settings'
  );
  assert.equal(
    ui.buttons[2].hidden,
    true,
    'responsive controller needs no restart'
  );
  assert.equal(ui.calls.length, 2);
  assert.equal(
    ui.calls.some((c) => c.uri.endsWith('/launch')),
    false
  );
}
for (const reply of [
  {
    returnValue: false,
    errorCode: -1,
    errorText: 'Denied method call "status" for category "/"'
  },
  { returnValue: false },
  { returnValue: true, running: null },
  { returnValue: true, running: 'true' },
  null,
  undefined
]) {
  const ui = panel(reply, { returnValue: false });
  if (reply === undefined)
    for (const callback of [...ui.timers.values()]) callback();
  assert.equal(ui.buttons[1].disabled, true);
  assert.equal(
    ui.buttons[2].hidden,
    false,
    'unknown status still permits a confirmed manual start'
  );
  assert.match(ui.status.textContent, /status could not be checked/);
  assert.equal(
    ui.calls.length,
    reply && reply.returnValue === false ? 2 : 1,
    'only explicit service refusals probe the independent broker'
  );
  const beforeStart = ui.calls.length;
  ui.buttons[2].onclick();
  assert.equal(
    ui.calls.length,
    beforeStart,
    'Start must wait for confirmation'
  );
  ui.window.confirmStart();
  assert.equal(
    ui.calls.filter(
      (c) => c.params.params && c.params.params.nativeHomeStart === true
    ).length,
    1
  );
}
for (const home of [
  { returnValue: false },
  { returnValue: true, enabled: 'true' },
  null,
  undefined
]) {
  const ui = panel(publishedStatus(), home);
  if (home === undefined)
    for (const callback of [...ui.timers.values()]) callback();
  assert.equal(
    ui.buttons[1].disabled,
    true,
    'failed Home control must not look healthy'
  );
  assert.equal(
    ui.calls.some((c) => c.uri.endsWith('/launch')),
    false
  );
}
console.log(
  'PASS published Helper 0.6.17 panel: both Home choices, safety stop, explicit restart, current and invalid protocols, failed Home control'
);
