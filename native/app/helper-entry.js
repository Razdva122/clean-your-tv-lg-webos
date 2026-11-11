'use strict';
// The tile is informational. Only boot callbacks and an explicit UI action start
// the controller; opening Helper must never clear an emergency-stop latch.
var root = '/media/developer/apps/usr/palm/applications/com.local.nativehome';
var params;
try {
  params = JSON.parse(process.argv[2] || '{}');
} catch (_) {
  params = {};
}
if (
  params.nativeHomeAuto === true ||
  params.nativeHomeStart === true ||
  (typeof params.nativeHomeSetup === 'string' &&
    /^[IS][a-f0-9]{32}$/.test(params.nativeHomeSetup))
) {
  var start = { nativeHomeAuto: params.nativeHomeAuto === true };
  if (typeof params.nativeHomeSetup === 'string')
    start.nativeHomeSetup = params.nativeHomeSetup;
  var child = require('child_process').spawn(
    root + '/detach',
    [JSON.stringify(start), '--controller'],
    { detached: true, stdio: 'ignore' }
  );
  child.on('error', function () {
    process.exit(1);
  });
  child.unref();
} else {
  // Anonymous public-bus caller: the controller already owns the app LS2 name.
  require('child_process').execFile(
    '/usr/bin/luna-send-pub',
    [
      '-n',
      '1',
      'luna://com.webos.applicationManager/launch',
      JSON.stringify({ id: 'com.gathin.tvhome', params: { showHelper: true } })
    ],
    { timeout: 5000 },
    function (error) {
      process.exit(error ? 1 : 0);
    }
  );
}
