'use strict';
// ws 6 uses the original Node streams/URL/Buffer APIs after Babel + safe-buffer.
// Keep the current ws implementation on runtimes supported by its upstream.
module.exports =
  Number(process.versions.node.split('.')[0]) < 10
    ? require('./vendor/ws-legacy')
    : require('./vendor/ws');
