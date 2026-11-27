'use strict';
const assert = require('node:assert/strict');
const diagnostics = require('../app/diagnostics.js')({});

const hostile = {
  state: 'recovery_required',
  code: 'operation_requires_recovery',
  stage: 'blocked',
  operation: 'a'.repeat(32),
  reason: 'restart-required',
  failure: {
    inspect_check: 'live_original_worker',
    errorText: 'test-secret /var/private 192.168.2.3',
    exception_type: 'OSError'
  }
};
const record = diagnostics.record('setup', hostile);
assert.equal(record.schema, 1);
assert.equal(record.source, 'setup');
assert.equal(record.code, 'operation_requires_recovery');
assert.equal(record.state, 'recovery_required');
assert.equal(record.stage, 'blocked');
assert.equal(record.detail, 'live_original_worker');
assert.deepEqual(record.failure, { exception_type: 'OSError' });
assert(!JSON.stringify(record).includes('test-secret'));
assert(!JSON.stringify(record).includes(hostile.operation));
assert.deepEqual(diagnostics.advice(record), [
  'restartNeeded',
  'restartAndRetry'
]);

const retained = diagnostics.record('setup', {
  state: 'recovery_required',
  code: 'inspected',
  installation: { reason: 'retained_operation' }
});
assert.equal(retained.code, 'retained_operation');
assert.deepEqual(diagnostics.advice(retained), [
  'statusUnavailable',
  'checkOriginal'
]);

const unknown = diagnostics.record('setup', {
  state: 'x'.repeat(30),
  code: 'private-serial-12345',
  stage: '/tmp/user',
  reason: 'do not export this',
  failure: { inspect_check: '192.168.2.3' }
});
assert.equal(unknown.code, 'unconfirmed');
assert.equal(unknown.stage, undefined);
assert.equal(unknown.detail, undefined);
assert.deepEqual(diagnostics.advice(unknown), [
  'reasonUnknown',
  'checkOrComputer'
]);
assert.deepEqual(
  diagnostics.advice(diagnostics.record('setup', {}, 'homebrew_exec_denied')),
  ['homebrewDeniedTitle', 'homebrewDeniedBody']
);
assert.deepEqual(
  diagnostics.advice(
    diagnostics.record('recovery', {}, 'update_service_unavailable')
  ),
  ['updateServiceUnavailable', 'computerRecovery']
);
assert.deepEqual(
  diagnostics.advice(
    diagnostics.record('setup', {
      state: 'recovery_required',
      failure: { package_rejected: true }
    })
  ),
  ['packageRejected', 'checkOrComputer']
);
assert.deepEqual(
  diagnostics.advice(
    diagnostics.record('setup', {
      state: 'complete',
      activation: { state: 'unverified' }
    })
  ),
  ['activationUnverified', 'checkOrComputer']
);

const reportFormat = require('../app/report-format.js');
const memory = new Map();
const storage = {
  getItem: (key) => memory.get(key),
  setItem: (key, value) => memory.set(key, value)
};
const saved = require('../app/diagnostics.js')({ localStorage: storage });
assert.equal(saved.save(record), true);
assert.deepEqual(saved.load(), record);
const key = [...memory.keys()][0];
memory.set(key, JSON.stringify({ ...record, password: 'test-secret' }));
assert.equal(saved.load(), null, 'unexpected saved fields cannot be displayed');
memory.set(
  key,
  reportFormat.serialize(record).replace('live_original_worker', 'test-secret')
);
assert.equal(saved.load(), null, 'stored values are validated again');
memory.delete(key);
memory.set(
  'cytv.installer.diagnostic.v1',
  JSON.stringify({ schema: 1, source: 'setup', code: 'homebrew_exec_denied' })
);
assert.equal(
  saved.load().code,
  'homebrew_exec_denied',
  'the earlier report remains available'
);
const blocked = require('../app/diagnostics.js')({
  get localStorage() {
    throw Error('storage denied');
  }
});
assert.equal(blocked.save(record), false);
assert.equal(blocked.load(), null);
assert.equal(
  saved.save({ ...record, serial: 'test-secret' }),
  false,
  'unvalidated input cannot be written'
);

const exported = reportFormat.canonical({
  ...record,
  timestamp: '2026-11-26T15:50:04.100Z',
  action: 'remove',
  edition: 'root',
  checks: { 'root-user': 'pass', 'install-readback': 'fail', hidden: 'secret' },
  tv: {
    modelName: 'OLED55C3RLA',
    firmwareVersion: '43.21.71',
    sdkVersion: '8.3.0-7',
    node_version: '192.168.0.1',
    serial: 'private'
  },
  versions: {
    installer: '0.1.0',
    cytv: '0.24.3',
    root: '0.25.0',
    homebrew: '192.168.0.1'
  }
});
assert.equal(exported.schema, 1);
assert.equal(exported.frontend, 'homebrew');
assert.equal(exported.action, 'uninstall');
assert.equal(exported.reason_code, 'operation_requires_recovery');
assert.deepEqual(exported.desktop, {
  os: null,
  architecture: null,
  python: null
});
assert.deepEqual(exported.tv, {
  modelName: 'OLED55C3RLA',
  firmwareVersion: '43.21.71',
  sdkVersion: '8.3.0-7'
});
assert.equal(exported.homebrew.versions.homebrew, undefined);
assert.deepEqual(exported.checks, {
  'root-user': 'pass',
  'install-readback': 'fail'
});
assert.equal(exported.status.product.stage, 'blocked');
assert.equal(exported.homebrew.detail, 'live_original_worker');
assert.equal(
  reportFormat.filename(exported),
  'diagnostic-homebrew-20261126T155004.json'
);
const url = new URL(reportFormat.url(exported));
assert.equal(url.origin, 'https://razdva122.github.io');
assert.equal(url.pathname, '/clean-your-tv-lg-webos/support/homebrew/');
assert.equal(url.search, '', 'report does not leave the URL fragment');
assert.deepEqual(reportFormat.decode(url.hash), exported);
assert.equal(reportFormat.decode(hashWithPrivateInput(url.hash)), null);
assert.equal(reportFormat.decode('%{malloc!'), null);
assert(!JSON.stringify(exported).includes('private'));
function hashWithPrivateInput(hash) {
  const fields = JSON.parse(
    Buffer.from(hash.slice(1), 'base64url').toString('ascii')
  );
  fields[6].serial = 'private';
  return (
    '#' + Buffer.from(JSON.stringify(fields), 'ascii').toString('base64url')
  );
}

const fs = require('node:fs'),
  path = require('node:path'),
  vm = require('node:vm');
const qrPage = vm.createContext({});
vm.runInContext(
  fs.readFileSync(
    path.join(__dirname, '../../launcher/wallpaper-qr.js'),
    'utf8'
  ),
  qrPage
);
const detailed = reportFormat.canonical({
  ...record,
  timestamp: '2026-11-26T15:50:04.100Z',
  code: 'continuation_requires_recovery',
  stage: 'root-remove-submitting',
  detail: 'different-removal-intent',
  resume: 'current-package-files-unverified',
  activation: 'unverified',
  failure: {
    exception_type: 'FileNotFoundError',
    errno: 4095,
    exit_status: 255
  },
  tv: {
    modelName: 'OLED55C3RLA' + 'X'.repeat(30),
    firmwareVersion: '43.21.71',
    sdkVersion: '11.2.0',
    node_version: '16.19.1',
    node_version_status: 'read'
  },
  versions: {
    installer: '1.0.1',
    cytv: '0.24.3',
    homebrew: '0.8.0',
    root: '2.3.1',
    root_updater: '0.4.0',
    system_updater: '0.6.1',
    home: '0.8.9',
    helper: '1.2.1',
    candidate_root: '2.3.1',
    candidate_root_updater: '0.4.0',
    candidate_system_updater: '0.6.1'
  },
  checks: Object.fromEntries(
    (
      'homebrew-access root-user node-version installer-payload python-runtime ' +
      'installer-staging product-state home-compatibility home-settings home-profiles packages startup home-button ' +
      'python3 python-json python-fcntl python-version luna-send apps-directory luna-services-directory ' +
      'install-request install-root install-updates install-readback activate-home'
    )
      .split(' ')
      .map((key) => [key, 'unknown'])
  )
});
const detailedUrl = reportFormat.url(detailed);
const matrix = qrPage.WallpaperQR.matrix(detailedUrl);
const pixelSize = 3;
const size = (matrix.length + 8) * pixelSize;
const rgba = new Uint8ClampedArray(size * size * 4).fill(255);
matrix.forEach((row, y) =>
  row.forEach((dark, x) => {
    if (!dark) return;
    for (let dy = 0; dy < pixelSize; dy++) {
      const top = ((y + 4) * pixelSize + dy) * size;
      for (let dx = 0; dx < pixelSize; dx++) {
        const offset = (top + (x + 4) * pixelSize + dx) * 4;
        rgba.fill(0, offset, offset + 3);
      }
    }
  })
);
const scanned = require('jsqr')(rgba, size, size);
assert.equal(
  scanned.data,
  detailedUrl,
  'detailed report remains decodable at reduced rendering size'
);
assert.deepEqual(reportFormat.decode(new URL(scanned.data).hash), detailed);
console.log(
  'PASS bounded Homebrew report, desktop-compatible export, QR transfer and legacy persistence'
);
