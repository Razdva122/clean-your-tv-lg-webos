const assert = require('node:assert/strict');
const fs = require('node:fs');
assert(
  fs.existsSync('updater-service/permissions.js'),
  'offline permission planner is required'
);
const plan = require('../../updater-service/permissions');
const p = plan('/var/luna-service2-dev');
assert.equal(p.files.length, 3);
assert.equal(new Set(p.files.map((f) => f.path)).size, 3);
const api = JSON.parse(
  p.files.find((f) => f.path.includes('api-permissions.d')).content
);
const clients = JSON.parse(
  p.files.find((f) => f.path.includes('client-permissions.d')).content
);
const manifest = JSON.parse(
  p.files.find((f) => f.path.includes('manifests.d')).content
);
assert.deepEqual(clients['com.cleanyourtv.updater.service*'], [
  'com.cleanyourtv.updater.backend'
]);
assert(
  api['com.cleanyourtv.updater.backend'].includes(
    'org.webosbrew.hbchannel.service/install'
  )
);
assert(
  api['com.cleanyourtv.updater.backend'].includes(
    'com.gathin.tvhome.renewal/importUpdatePause'
  )
);
assert(
  Object.values(api)
    .flat()
    .every(
      (method) =>
        !method.includes('*') &&
        !method.endsWith('/exec') &&
        !method.includes('systemProfile')
    )
);
assert(!JSON.stringify(clients).includes('"all"'));
assert(!JSON.stringify(clients).includes('"public"'));
assert.equal(manifest.roleFiles.length, 0);
assert.equal(manifest.serviceFiles.length, 0);
for (const f of p.files) {
  assert.equal(
    f.sha256,
    require('node:crypto').createHash('sha256').update(f.content).digest('hex')
  );
  assert(f.path.includes('com.cleanyourtv.updater.permissions'));
}
assert.throws(() => plan('/tmp/unexpected'));
assert.deepEqual(plan('/var/luna-service2-dev'), p);

assert.deepEqual(api['com.cleanyourtv.updater.renewalActivity'], [
  'com.webos.service.activitymanager/create',
  'com.webos.service.activitymanager/cancel'
]);
assert.deepEqual(clients['com.gathin.tvhome.renewal*'], [
  'com.cleanyourtv.updater.renewalActivity'
]);
console.log('PASS deterministic narrow LS2 plan, isolated paths and hashes');
