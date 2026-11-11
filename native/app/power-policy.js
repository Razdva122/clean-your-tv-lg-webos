'use strict';
var events = require('./contract-events');
module.exports = function () {
  var asleep = false;
  function observe(p, now) {
    var diagnostics = [];
    function unknown(field, value, rule) {
      var actual = events.describe(value);
      actual.category = 'unknown';
      diagnostics.push(
        events.normalize({
          schema: 1,
          component: 'power',
          operation: 'observe',
          phase: 'normalize',
          field: field,
          expected: rule,
          actual: actual,
          decision: 'retain'
        })
      );
    }
    if (!p || typeof p !== 'object' || Array.isArray(p)) {
      unknown('payload', p, 'power-object');
      p = {};
    }
    var offStates = [
      'Request Power Off',
      'Request Active Standby',
      'Prepare Active Standby',
      'Active Standby',
      'Request Suspend',
      'Prepare Power Off',
      'Suspend'
    ];
    var states = offStates.concat([
      'Active',
      'Screen Off',
      'Screen On',
      'Prepare Power On',
      'Request Power On'
    ]);
    if (p.state !== undefined && states.indexOf(p.state) < 0)
      unknown('state', p.state, 'power-state');
    if (p.onOff !== undefined && p.onOff !== 'on' && p.onOff !== 'off')
      unknown('onOff', p.onOff, 'power-on-off');
    if (
      p.processing !== undefined &&
      typeof p.processing !== 'boolean' &&
      ['Request Power Off', 'Screen On', 'Prepare Power On'].indexOf(
        p.processing
      ) < 0
    )
      unknown('processing', p.processing, 'firmware-processing');
    var poweringOff = p.onOff === 'off' || offStates.indexOf(p.state) !== -1;
    var settledActive = !poweringOff && p.state === 'Active' && !p.processing;
    var resumed = false;
    if (p.state === 'Active Standby' || p.state === 'Suspend') asleep = true;
    else if (p.state === 'Active' && !p.processing && p.onOff !== 'off') {
      resumed = asleep;
      asleep = false;
    }
    return {
      command: poweringOff ? 'T' : p.state === 'Active' ? 'R' : null,
      deadline: poweringOff ? now + 15000 : 0,
      settledActive: settledActive,
      resumed: resumed,
      cancelWakeWait: !settledActive,
      cancelPresentation:
        p.onOff === 'off' ||
        p.state === 'Active Standby' ||
        p.state === 'Suspend',
      diagnostics: diagnostics
    };
  }
  return {
    observe: observe,
    next: function (p) {
      return observe(p, 0).resumed;
    }
  };
};
