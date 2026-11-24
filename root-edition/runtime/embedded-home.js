/* Adapter for the stock embedded Home policy and the shared C1 lease filter. */
var KeyPolicy;
var genericTimer;
var lunaCall;
var applicationManager;
var included = Qt.include('c1-home-filter.js');
var stockIncluded = Qt.include('qrc:///keypolicies.js');
var attachment = null;

function alertGates(root) {
  var pending = [root],
    gates = [],
    seen = [];
  while (pending.length) {
    var item = pending.shift();
    if (!item || seen.indexOf(item) !== -1) continue;
    if (seen.length >= 2048) return null;
    seen.push(item);
    if (typeof item.modalAlertsVisible === 'boolean') gates.push(item);
    var children = item.children;
    if (children) {
      for (var i = 0; i < children.length; i++) pending.push(children[i]);
    }
  }
  return gates.length ? gates : null;
}

function attach(ysm, api) {
  if (attachment) return null;
  try {
    if (
      !included ||
      included.status !== 0 ||
      !stockIncluded ||
      stockIncluded.status !== 0 ||
      !ysm ||
      !ysm.keyFilter ||
      !ysm.access ||
      !ysm.access.keyFilter ||
      typeof ysm.goHome !== 'function' ||
      !api ||
      typeof api.later !== 'function' ||
      typeof api.subscribe !== 'function' ||
      typeof api.send !== 'function'
    )
      return null;
    var filter = ysm.keyFilter;
    var enums = [
      typeof NotAccepted === 'undefined' ? null : NotAccepted,
      typeof Accepted === 'undefined' ? null : Accepted,
      typeof NextPolicy === 'undefined' ? null : NextPolicy
    ];
    for (var e = 0; e < enums.length; e++) {
      if (
        typeof enums[e] !== 'number' ||
        !isFinite(enums[e]) ||
        Math.floor(enums[e]) !== enums[e] ||
        enums.indexOf(enums[e]) !== e
      )
        return null;
    }
    if (
      filter.pressFunction !== 'handleKeyPressed' ||
      filter.releaseFunction !== 'handleKeyReleased' ||
      typeof filter.handleKeyEvents !== 'function' ||
      typeof filter.handleKeyPressed !== 'function' ||
      typeof filter.handleKeyReleased !== 'function'
    )
      return null;
    KeyPolicy = {
      NotAccepted: enums[0],
      Accepted: enums[1],
      NextPolicy: enums[2]
    };
    var before = filter.keyPolicies;
    if (!Array.isArray(before)) return null;
    var index = -1;
    for (var i = 0; i < before.length; i++) {
      if (
        typeof before[i] === 'function' &&
        before[i].name === 'handleSystemKeys'
      ) {
        if (index !== -1) return null;
        index = i;
      }
    }
    if (index < 0) return null;
    var gates = alertGates(ysm);
    if (!gates) return null;
    var stock = before[index];
    var down = false,
      captured = false,
      delegated = false,
      retiring = false;

    function allowed() {
      try {
        if (
          retiring ||
          ysm.smartTvReady !== true ||
          ysm.access.ribbon !== true ||
          ysm.access.keyFilter.home !== true
        )
          return false;
        for (var i = 0; i < gates.length; i++) {
          if (gates[i].modalAlertsVisible !== false) return false;
        }
        return true;
      } catch (_) {
        return false;
      }
    }

    function remove() {
      var current = filter.keyPolicies;
      if (!Array.isArray(current)) return;
      var restored = current.slice();
      var changed = false;
      for (var i = 0; i < restored.length; i++) {
        if (restored[i] === route) {
          restored[i] = stock;
          changed = true;
        }
      }
      if (changed) filter.keyPolicies = restored;
    }

    function route(key, pressed, repeat) {
      if (key !== Qt.Key_Super_L) return stock(key, pressed, repeat);
      if (pressed && !repeat) {
        if (down && delegated) cytvC1HomeKey(key, false, false);
        down = true;
        delegated = allowed();
        captured =
          delegated && cytvC1HomeKey(key, true, false) === KeyPolicy.Accepted;
      } else if (pressed && down && delegated) {
        cytvC1HomeKey(key, true, repeat);
      }
      var owned = captured;
      // Qt can synthesize release/press pairs while a key remains held.
      if (!pressed && !repeat) {
        if (delegated) cytvC1HomeKey(key, false, false);
        down = false;
        captured = false;
        delegated = false;
        if (retiring) remove();
      }
      return owned ? KeyPolicy.Accepted : stock(key, pressed, repeat);
    }

    genericTimer = { set: api.later };
    lunaCall = {
      subscribe: function (service, method, payload, callback) {
        if (
          !attachment ||
          retiring ||
          service !== 'com.webos.cleanyourtv.root.lease' ||
          method !== '/c1Lease'
        )
          throw Error('Inactive embedded Home subscription');
        var request = JSON.parse(payload);
        if (
          !request ||
          request.subscribe !== true ||
          Object.keys(request).length !== 1
        )
          throw Error('Unexpected embedded Home subscription');
        request.adapter = 'embedded-qml-v1';
        api.subscribe(service, method, JSON.stringify(request), callback);
      },
      send: api.send
    };
    applicationManager = {
      launch: function (id) {
        if (id !== 'com.webos.app.home')
          throw Error('Unexpected embedded Home destination');
        if (ysm.state === 'hidden') ysm.goHome();
      }
    };
    var after = before.slice();
    after[index] = route;
    filter.keyPolicies = after;
    if (filter.keyPolicies[index] !== route) return null;
    attachment = {
      retire: function () {
        retiring = true;
        cytvC1Revoke();
        if (!down || !captured) remove();
      }
    };
    init(true);
    return attachment;
  } catch (_) {
    if (attachment) attachment.retire();
    return null;
  }
}
