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
  const expected = [
    'cs',
    'en',
    'de',
    'es',
    'pt-BR',
    'fr',
    'it',
    'ko',
    'hi',
    'pl',
    'ru',
    'zh-Hans',
    'zh-Hant'
  ];
  for (const code of expected) {
    await click('.language');
    assert.equal(
      await evaluate(
        'document.querySelectorAll("#language-picker [role=radio]").length'
      ),
      expected.length
    );
    await click('[data-language="' + code + '"]');
    assert.equal(await evaluate('document.documentElement.lang'), code);
    assert.equal(
      await evaluate('document.querySelector(".language").textContent'),
      code.toUpperCase()
    );
    assert.equal(
      await evaluate('document.documentElement.scrollWidth<=innerWidth'),
      true
    );
    if (['de', 'ko', 'hi', 'ru'].includes(code))
      await capture('android-language-' + code);
  }
  await click('.language');
  await capture('android-language-picker');
  await click('[data-action="close-language"]');
  await call('Page.reload', {});
  await wait('!!document.querySelector(".language")');
  assert.equal(
    await evaluate('document.documentElement.lang'),
    expected.at(-1)
  );
  console.log(
    'Native APK: thirteen languages, current header, complete picker, persistence and screenshots passed.'
  );
  socket.close();
})().catch((e) => {
  console.error(e);
  if (socketForCleanup) socketForCleanup.close();
  process.exitCode = 1;
});
