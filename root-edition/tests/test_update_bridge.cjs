'use strict';
const assert = require('assert'),
  bridge = require('../updater/bridge');
const execute = async (method, payload) => ({ method, payload });
function msg(id) {
  return { ls2Message: { applicationID: () => id } };
}
(async () => {
  const b = bridge(execute),
    root = msg('com.cleanyourtv.root.preview 123'),
    recovery = msg('com.cleanyourtv.root.updater');
  assert.equal((await b(root, 'status', {})).method, 'status');
  assert.equal((await b(recovery, 'rollback', {})).method, 'rollback');
  await assert.rejects(() =>
    b(msg('org.other'), 'install', { version: '0.2.0', profile: {} })
  );
  await assert.rejects(() =>
    b(recovery, 'ready', { transaction: 'a'.repeat(32), version: '0.2.0' })
  );
  await assert.rejects(() =>
    b(root, 'install', { version: '0.2.0', profile: {}, url: 'https://evil' })
  );
  await assert.rejects(() =>
    b(root, 'ready', { transaction: '../../bad', version: '0.2.0' })
  );
  await assert.rejects(() => b(root, 'shell', {}));
  console.log(
    'PASS Root updater bus authorization and strict command boundary'
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
