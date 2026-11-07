#!/usr/bin/env node
'use strict';
// Emit a reviewable plan; deliberately no apply mode.
console.log(
  JSON.stringify(
    require('../updater-service/permissions')(
      process.argv[2] || '/var/luna-service2-dev'
    ),
    null,
    2
  )
);
