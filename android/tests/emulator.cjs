// Debug APK only. Forward its webview_devtools_remote_PID socket to TCP 9228.
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
let socketForCleanup;
(async () => {
  const pages = await fetch('http://127.0.0.1:9228/json/list').then((r) =>
    r.json()
  );
  const target = pages.find(
    (p) => p.url === 'file:///android_asset/ui/index.html'
  );
  assert(target, 'CYTV WebView is not open');
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  socketForCleanup = socket;
  await new Promise((resolve, reject) => {
    socket.onopen = resolve;
    socket.onerror = reject;
  });
  let next = 0;
  const pending = new Map();
  socket.onmessage = (message) => {
    const reply = JSON.parse(message.data);
    if (reply.id) {
      const p = pending.get(reply.id);
      pending.delete(reply.id);
      reply.error ? p.reject(reply.error) : p.resolve(reply.result);
    }
  };
  const call = (method, params) =>
    new Promise((resolve, reject) => {
      const id = ++next;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
  const evaluate = async (expression) => {
    const reply = await call('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true
    });
    if (reply.exceptionDetails)
      throw Error(JSON.stringify(reply.exceptionDetails));
    return reply.result.value;
  };
  const click = (selector) =>
    evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const fill = (selector, value) =>
    evaluate(
      `document.querySelector(${JSON.stringify(selector)}).value=${JSON.stringify(value)}`
    );
  const wait = async (expression, timeout = 60000) => {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      if (await evaluate(expression)) return;
      await new Promise((r) => setTimeout(r, 200));
    }
    throw Error(
      'Timed out: ' +
        expression +
        '\n' +
        (await evaluate('document.body.innerText'))
    );
  };
  const out = path.resolve(__dirname, '../screenshots');
  const adb = process.env.CYTV_ADB || 'adb';
  const capture = async (name) => {
    await evaluate('document.activeElement.blur();scrollTo(0,0)');
    await new Promise((r) => setTimeout(r, 800));
    fs.writeFileSync(
      path.join(out, name + '.png'),
      execFileSync(adb, ['exec-out', 'screencap', '-p'])
    );
  };
  console.log(
    await evaluate(
      '({width:innerWidth,height:innerHeight,scroll:document.documentElement.scrollHeight,native:typeof CYTV,overflow:document.documentElement.scrollWidth>innerWidth})'
    )
  );
  await fill('#host', '10.0.2.2');
  await click('[data-action="inspect"]');
  await wait('!!document.querySelector("[data-edition=no-root]")');
  await click('[data-edition="no-root"]');
  await click('[data-action="connect"]');
  await fill('#host', '192.168.1.50');
  await capture('android-02-no-root');
  await click('[data-action="back"]');
  await click('[data-edition="root"]');
  await click('[data-action="connect"]');
  await capture('android-03-root');
  assert.equal(await evaluate('document.getElementById("port").value'), '22');
  await click('[data-action="back"]');
  await click('[data-edition="no-root"]');
  await click('[data-action="back"]');
  await click('[data-action="tools"]');
  await click('[data-action="choose-status"]');
  await fill('#host', '10.0.2.2');
  await click('[data-action="start"]');
  await wait('!!document.getElementById("prompt-value")', 90000);
  assert.equal(
    await evaluate('document.getElementById("prompt-title").textContent'),
    'Код подключения'
  );
  await fill('#prompt-value', 'ABCDEF');
  await click('[data-action="secret"]');
  await wait('!!document.querySelector("[data-action=to-connection]")', 40000);
  const log = await evaluate('document.getElementById("log-text").textContent');
  assert(!log.includes('ModuleNotFoundError'), log);
  assert(!log.includes('ABCDEF'), log);
  assert(!log.includes('PyException'), log);
  console.log(
    'Native Python callback reached; unavailable test Key Server returned recovery screen without exposing the passphrase.'
  );
  await capture('android-04-recovery');
  if (process.env.CYTV_TEST_ROOT === '1') {
    await click('[data-action="to-connection"]');
    await click('[data-action="back"]');
    await click('[data-edition="root"]');
    await click('[data-action="back"]');
    await click('[data-action="tools"]');
    await click('[data-action="choose-status"]');
    await fill('#host', '10.0.2.2');
    await fill('#port', process.env.CYTV_TEST_SSH_PORT || '32222');
    await click('[data-action="start"]');
    await wait('!!document.querySelector("[data-action=trust]")', 30000);
    assert(
      (
        await evaluate('document.querySelector(".fingerprint").textContent')
      ).startsWith('SHA256:')
    );
    await capture('android-05-ssh-trust');
    await click('[data-action="trust"]');
    await wait('!!document.getElementById("prompt-value")', 30000);
    assert.equal(
      await evaluate('document.getElementById("prompt-title").textContent'),
      'Пароль SSH'
    );
    await fill('#prompt-value', 'DUMMY-INVALID-PASSWORD');
    await click('[data-action="secret"]');
    await wait(
      '!!document.querySelector("[data-action=to-connection]")',
      30000
    );
    assert(
      !(
        await evaluate('document.getElementById("log-text").textContent')
      ).includes('DUMMY-INVALID-PASSWORD')
    );
    console.log(
      'Native Root SSH: host-key fingerprint confirmation and hidden password request passed; incorrect fixture password rejected.'
    );
  }
  socket.close();
})().catch((e) => {
  console.error(e);
  if (socketForCleanup) socketForCleanup.close();
  process.exitCode = 1;
});
