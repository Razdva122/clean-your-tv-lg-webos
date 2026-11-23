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
// Input sources kept by the opt-in Stay on input at power-on preference.
for (const id of [
  'com.webos.app.hdmi1',
  'com.webos.app.hdmi4',
  'com.webos.app.livetv',
  'com.webos.app.externalinput.av1',
  'com.webos.app.externalinput.component'
])
  a.equal(shouldLaunch.source(id), true, id);
for (const id of [
  null,
  '',
  'com.gathin.tvhome',
  'com.webos.app.home',
  'com.webos.app.cpcover',
  'com.webos.app.hdmi',
  'com.webos.app.livetv.extra',
  'com.example.video'
])
  a.equal(shouldLaunch.source(id), false, String(id));
console.log(
  'PASS: restored launcher avoids duplicate resume request; other states retain recovery'
);
