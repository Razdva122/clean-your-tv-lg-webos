'use strict';

var assert = require('assert');
var http = require('http');
var transport = require('../screensaver/transport');
var create = require('../screensaver/controller').create;
var channel;
var controller;
var done = false;
var watchdog = setTimeout(function () {
  cleanup();
  throw new Error('Screensaver loopback compatibility check timed out');
}, 5000);

function cleanup() {
  clearTimeout(watchdog);
  if (controller) controller.dispose();
}

controller = create({
  generation: 1,
  context: function () {
    return { popupSupported: true, ownerHealthy: true, previewEligible: true };
  },
  listen: function (current, update, ready, serveMedia) {
    transport.listen(
      current,
      update,
      function (error, value) {
        assert.ifError(error);
        channel = value;
        ready(null, value);
        controller.enable();
        assert.strictEqual(controller.preview(), true);
      },
      serveMedia
    );
  },
  launch: function (id, params, result) {
    var body = JSON.stringify({
      schema: 1,
      sessionId: params.sessionId,
      generation: params.generation,
      visible: true,
      focused: true,
      mediaState: 'ready'
    });
    var url = require('url').parse(channel.endpoint);
    url.method = 'POST';
    url.headers = {
      'X-CYTV-Session': params.sessionId,
      'Content-Length': Buffer.byteLength(body)
    };
    var request = http.request(url, function (response) {
      assert.strictEqual(response.statusCode, 200);
      response.on('data', function () {});
      response.on('end', function () {
        assert.strictEqual(controller.getSession().state, 'visible');
        done = true;
        cleanup();
        console.log(
          'Screensaver loopback/controller passed on ' + process.version
        );
      });
    });
    request.on('error', function (error) {
      cleanup();
      throw error;
    });
    request.end(body);
    result(true);
  }
});

process.on('exit', function () {
  assert.strictEqual(done, true);
});
