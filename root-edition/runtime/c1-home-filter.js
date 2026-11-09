/* Private C1 compositor filter. Every uncertain lease leaves Home with LG.
 * genericTimer uses the compositor clock; wall-clock adjustments cannot renew it.
 * No file access, configd writes or stock Home process changes belong here. */
var cytvC1Generation = 0;
var cytvC1LeaseGeneration = 0;
var cytvC1Healthy = false;
var cytvC1Failed = true;
var cytvC1EverArmed = false;
var cytvC1Token = '';
var cytvC1Sequence = 0;
var cytvC1Down = false;
var cytvC1Captured = false;
var cytvC1HomePending = false;
var cytvC1HomeGeneration = 0;

function cytvC1Revoke() {
  cytvC1Healthy = false;
  cytvC1Failed = true;
  cytvC1LeaseGeneration++;
}

function init() {
  var generation = ++cytvC1Generation;
  cytvC1HomeGeneration++;
  cytvC1HomePending = false;
  cytvC1Revoke();
  cytvC1Token = '';
  cytvC1Sequence = 0;
  cytvC1Failed = false;
  cytvC1EverArmed = false;
  try {
    // configd may retain a JS chain after the compositor changed. Establish no
    // lease unless the live loader supplies every API used by this filter.
    if (
      typeof Qt === 'undefined' ||
      typeof Qt.Key_Super_L !== 'number' ||
      !isFinite(Qt.Key_Super_L) ||
      typeof KeyPolicy === 'undefined' ||
      typeof KeyPolicy.NextPolicy !== 'number' ||
      typeof KeyPolicy.Accepted !== 'number' ||
      KeyPolicy.NextPolicy === KeyPolicy.Accepted ||
      typeof genericTimer === 'undefined' ||
      typeof genericTimer.set !== 'function' ||
      typeof applicationManager === 'undefined' ||
      typeof applicationManager.launch !== 'function' ||
      typeof lunaCall === 'undefined' ||
      typeof lunaCall.subscribe !== 'function' ||
      typeof lunaCall.send !== 'function'
    ) {
      cytvC1Revoke();
      return;
    }
    lunaCall.subscribe(
      'com.webos.cleanyourtv.root.lease',
      '/c1Lease',
      JSON.stringify({ subscribe: true }),
      function (payload) {
        if (generation !== cytvC1Generation || cytvC1Failed) return;
        try {
          var reply =
            typeof payload === 'string' ? JSON.parse(payload) : payload;
          if (
            !reply ||
            typeof reply !== 'object' ||
            Array.isArray(reply) ||
            Object.keys(reply).sort().join(',') !==
              'backend,healthy,returnValue,routing,sequence,subscribed,token' ||
            reply.returnValue !== true ||
            reply.subscribed !== true ||
            reply.backend !== 'c1-native-gate' ||
            reply.routing !== 'compositor-keyfilter-v1' ||
            typeof reply.healthy !== 'boolean' ||
            (cytvC1EverArmed && !reply.healthy) ||
            typeof reply.token !== 'string' ||
            !/^[a-f0-9]{32}$/.test(reply.token) ||
            typeof reply.sequence !== 'number' ||
            !isFinite(reply.sequence) ||
            Math.floor(reply.sequence) !== reply.sequence ||
            reply.sequence <= cytvC1Sequence ||
            reply.sequence > 9007199254740991 ||
            (cytvC1Token && reply.token !== cytvC1Token)
          ) {
            cytvC1Revoke();
            return;
          }
          cytvC1Token = reply.token;
          cytvC1Sequence = reply.sequence;
          var leaseGeneration = ++cytvC1LeaseGeneration;
          // Schedule before granting; missing/broken timers must fail open.
          genericTimer.set(1500, function () {
            if (
              generation === cytvC1Generation &&
              leaseGeneration === cytvC1LeaseGeneration
            )
              cytvC1Revoke();
          });
          cytvC1Healthy = reply.healthy;
          if (reply.healthy) cytvC1EverArmed = true;
        } catch (_) {
          cytvC1Revoke();
        }
      },
      true
    );
  } catch (_) {
    cytvC1Revoke();
  }
}

// Cached health may expire between a physical key and a stop. Only the native
// token/stop barrier may launch Root; the compositor can only recover LG Home.
function cytvC1DispatchHome() {
  if (cytvC1HomePending) return true;
  if (typeof lunaCall.send !== 'function') return false;
  var generation = cytvC1Generation;
  var request = ++cytvC1HomeGeneration;
  var token = cytvC1Token;
  var completed = false;
  function finish(ok) {
    if (
      completed ||
      generation !== cytvC1Generation ||
      request !== cytvC1HomeGeneration ||
      token !== cytvC1Token
    )
      return;
    completed = true;
    cytvC1HomePending = false;
    if (!ok) {
      cytvC1Revoke();
      applicationManager.launch('com.webos.app.home', '{}');
    }
  }
  try {
    genericTimer.set(3000, function () {
      finish(false);
    });
    cytvC1HomePending = true;
    lunaCall.send(
      'com.webos.cleanyourtv.root.lease',
      '/c1Home',
      JSON.stringify({ token: token }),
      function (payload) {
        try {
          var reply =
            typeof payload === 'string' ? JSON.parse(payload) : payload;
          finish(
            !!reply &&
              typeof reply === 'object' &&
              !Array.isArray(reply) &&
              Object.keys(reply).sort().join(',') ===
                'backend,returnValue,routing,token' &&
              reply.returnValue === true &&
              reply.backend === 'c1-native-gate' &&
              reply.routing === 'compositor-keyfilter-v1' &&
              reply.token === token
          );
        } catch (_) {
          finish(false);
        }
      }
    );
    return true;
  } catch (_) {
    completed = true;
    cytvC1HomePending = false;
    cytvC1Revoke();
    return false;
  }
}

function cytvC1HomeKey(key, pressed, autoRepeat) {
  try {
    if (key !== Qt.Key_Super_L) return KeyPolicy.NextPolicy;
    if (!pressed) {
      var captured = cytvC1Captured;
      cytvC1Down = false;
      cytvC1Captured = false;
      return captured ? KeyPolicy.Accepted : KeyPolicy.NextPolicy;
    }
    if (cytvC1Down)
      return cytvC1Captured ? KeyPolicy.Accepted : KeyPolicy.NextPolicy;
    cytvC1Down = true;
    // An isolated repeat has no owned press and must stay with LG.
    if (!cytvC1Healthy || autoRepeat) return KeyPolicy.NextPolicy;
    if (!cytvC1DispatchHome()) return KeyPolicy.NextPolicy;
    cytvC1Captured = true;
    return KeyPolicy.Accepted;
  } catch (_) {
    return KeyPolicy.NextPolicy;
  }
}
