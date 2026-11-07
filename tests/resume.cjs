const a = require('node:assert/strict');
const shouldLaunch = require('../native/app/resume-policy');
a.equal(
  shouldLaunch('com.gathin.tvhome'),
  false,
  'already restored: no duplicate launch'
);
for (const id of [
  null,
  '',
  'com.webos.app.home',
  'com.webos.app.cpcover',
  'com.example.video'
])
  a.equal(shouldLaunch(id), true);
console.log(
  'PASS: restored launcher avoids duplicate resume request; other states retain recovery'
);
