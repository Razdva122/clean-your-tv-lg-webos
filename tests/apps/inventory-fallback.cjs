const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('node:fs'),
  vm = require('node:vm');
function fixture(root = false, priorityIds) {
  const calls = [],
    timers = new Map();
  let seq = 0,
    result,
    completed = 0,
    now = 0;
  const context = {
    module: { exports: {} },
    document: { querySelector: () => (root ? {} : null) },
    setTimeout(fn, ms) {
      const id = ++seq;
      timers.set(id, { fn, at: now + ms });
      return id;
    },
    clearTimeout(id) {
      timers.delete(id);
    },
    PalmServiceBridge: function () {
      this.cancel = () => {
        this.cancelled = true;
      };
      this.call = (uri, payload) => {
        calls.push(this);
        this.uri = uri;
        this.payload = JSON.parse(payload);
      };
    }
  };
  vm.runInNewContext(
    fs.readFileSync('launcher/app-library.js', 'utf8'),
    context
  );
  context.module.exports.installed((apps) => {
    result = apps;
    completed++;
  }, priorityIds);
  return {
    calls,
    reply: (i, reply) =>
      calls[i].onservicecallback(
        typeof reply === 'string' ? reply : JSON.stringify(reply)
      ),
    advance(ms) {
      const end = now + ms;
      while (true) {
        const next = [...timers]
          .filter(([, t]) => t.at <= end)
          .sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        const [id, t] = next;
        now = t.at;
        timers.delete(id);
        t.fn();
      }
      now = end;
    },
    timeout() {
      const [id, t] = timers.entries().next().value;
      timers.delete(id);
      now = t.at;
      t.fn();
    },
    get result() {
      return result;
    },
    get completed() {
      return completed;
    },
    timers
  };
}
test('only Root passes ordered visible IDs as icon priorities; legacy requests stay empty', () => {
  const ids = ['late', 'first'];
  assert.deepEqual(fixture(true, ids).calls[0].payload, { priorityIds: ids });
  assert.deepEqual(fixture(false, ids).calls[0].payload, {});
  assert.deepEqual(fixture(true).calls[0].payload, {});
});
test('No-root inventory denied by LS2 reads the authorized same-package broker', () => {
  const f = fixture();
  assert.equal(f.calls[0].uri, 'luna://com.local.nativehome.service/listApps');
  f.reply(0, { returnValue: false, errorCode: -1 });
  assert.equal(f.calls[1].uri, 'luna://com.gathin.tvhome.renewal/listApps');
  assert(f.calls[0].cancelled);
  f.reply(1, {
    returnValue: true,
    apps: [{ id: 'org.example.homebrew', title: 'Homebrew' }]
  });
  assert.equal(f.result[0].id, 'org.example.homebrew');
  assert.equal(f.completed, 1);
  assert.equal(f.timers.size, 0);
});
test('direct success including an empty catalog does not request a fallback', () => {
  const f = fixture();
  f.reply(0, { returnValue: true, apps: [] });
  assert.equal(f.result.length, 0);
  assert.equal(f.calls.length, 1);
  assert.equal(f.completed, 1);
});
test('a silent service times out to fallback and late direct replies cannot replace it', () => {
  const f = fixture();
  f.timeout();
  assert.equal(f.calls.length, 2);
  f.reply(0, { returnValue: true, apps: [{ id: 'stale', title: 'Stale' }] });
  assert.equal(f.completed, 0);
  f.reply(1, { returnValue: true, apps: [{ id: 'fresh', title: 'Fresh' }] });
  assert.equal(f.result[0].id, 'fresh');
  f.reply(1, { returnValue: false });
  assert.equal(f.completed, 1);
});
test('fallback failures are bounded and keep the saved catalog path', () => {
  for (const reply of [
    { returnValue: false },
    'not-json',
    { returnValue: true, apps: {} }
  ]) {
    const f = fixture();
    f.reply(0, { returnValue: false });
    f.reply(1, reply);
    assert.equal(f.result, null);
    assert.equal(f.completed, 1);
    assert.equal(f.calls.length, 2);
    assert.equal(f.timers.size, 0);
  }
  const f = fixture();
  f.timeout();
  f.timeout();
  assert.equal(f.result, null);
  assert.equal(f.completed, 1);
  assert.equal(f.timers.size, 0);
});
test('Root inventory never crosses into the No-root broker', () => {
  const f = fixture(true);
  assert.equal(
    f.calls[0].uri,
    'luna://com.cleanyourtv.root.preview.service/listApps'
  );
  f.reply(0, { returnValue: false });
  assert.equal(f.result, null);
  assert.equal(f.calls.length, 1);
});

test('a valid direct inventory taking six seconds retains its original supported budget', () => {
  const f = fixture();
  f.advance(6500);
  assert.equal(
    f.calls.length,
    1,
    'do not abandon a backend whose deadline is eight seconds'
  );
  f.reply(0, {
    returnValue: true,
    apps: [{ id: 'slow', title: 'Slow but valid' }]
  });
  assert.equal(f.result[0].id, 'slow');
  assert.equal(f.completed, 1);
});
