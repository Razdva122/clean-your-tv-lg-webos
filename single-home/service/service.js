'use strict';
var Service = require('webos-service');
var bus = new Service('io.github.razdva122.cytvhomepilot.service');
require('./controller')(
  bus,
  require('./storage')(bus),
  require('./pairing'),
  require('./boot').clock
);
