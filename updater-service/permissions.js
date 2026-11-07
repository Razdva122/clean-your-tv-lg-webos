'use strict';
// Offline plan only. Does not write files, register manifests, or contact a TV.
module.exports = function (root) {
  if (['/var/luna-service2-dev', '/var/luna-service2'].indexOf(root) < 0)
    throw Error('unsupported-ls2-root');
  var id = 'com.cleanyourtv.updater.permissions',
    ui = 'com.cleanyourtv.updater.ui',
    backend = 'com.cleanyourtv.updater.backend';
  var api = {},
    clients = {};
  api[ui] = [
    'check',
    'status',
    'restore',
    'install',
    'reconcile',
    'healthy',
    'rollback'
  ].map(function (m) {
    return 'com.cleanyourtv.updater.service/' + m;
  });
  api[backend] = ['checkRoot', 'getAppInfo', 'install']
    .map(function (m) {
      return 'org.webosbrew.hbchannel.service/' + m;
    })
    .concat(
      [
        'status',
        'pauseForUpdate',
        'importUpdatePause',
        'resumeAfterUpdate'
      ].map(function (m) {
        return 'com.gathin.tvhome.renewal/' + m;
      })
    );
  clients['com.gathin.tvhome-*'] = [ui];
  clients['com.cleanyourtv.updater-*'] = [ui];
  clients['com.cleanyourtv.updater.service*'] = [backend];
  // services.json requiredACG is not inherited by the packaged JS service on C3.
  var renewalActivity = 'com.cleanyourtv.updater.renewalActivity';
  api[renewalActivity] = [
    'com.webos.service.activitymanager/create',
    'com.webos.service.activitymanager/cancel'
  ];
  clients['com.gathin.tvhome.renewal*'] = [renewalActivity];
  var apiPath = root + '/api-permissions.d/' + id + '.json',
    clientPath = root + '/client-permissions.d/' + id + '.json';
  var manifest = {
    id: id,
    version: '1.0.0',
    roleFiles: [],
    serviceFiles: [],
    apiPermissionFiles: [apiPath],
    clientPermissionFiles: [clientPath]
  };
  function file(path, value) {
    var content = JSON.stringify(value, null, 2) + '\n';
    return {
      path: path,
      content: content,
      sha256: require('crypto')
        .createHash('sha256')
        .update(content)
        .digest('hex')
    };
  }
  return {
    schema: 1,
    experimental: true,
    files: [
      file(apiPath, api),
      file(clientPath, clients),
      file(root + '/manifests.d/' + id + '.json', manifest)
    ]
  };
};
