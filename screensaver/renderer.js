(function (root) {
  'use strict';
  var doc = root.document;
  var photo = doc.getElementById('photo');
  var video = doc.getElementById('video');
  var clock = doc.getElementById('clock');
  var clockTime = doc.getElementById('clockTime');
  var clockDate = doc.getElementById('clockDate');
  var ambient = doc.getElementById('ambient');
  var owner = null;
  var candidate = null;
  var retired = [];
  var finished = false;
  var startupTimer;
  var embedded = root.parent !== root && root.location.hash === '#cytv-inline';
  function now() {
    return root.performance.now();
  }

  function valid(params) {
    if (!params || typeof params !== 'object') return false;
    var endpoint =
      typeof params.endpoint === 'string' &&
      /^http:\/\/127\.0\.0\.1:([0-9]{1,5})\/screensaver$/.exec(params.endpoint);
    return !!(
      endpoint &&
      +endpoint[1] > 0 &&
      +endpoint[1] <= 65535 &&
      typeof params.sessionId === 'string' &&
      /^[A-Za-z0-9_-]{16,256}$/.test(params.sessionId) &&
      typeof params.generation === 'number' &&
      params.generation >= 0 &&
      params.generation <= 9007199254740991 &&
      Math.floor(params.generation) === params.generation
    );
  }

  function envelope(session, terminal) {
    return {
      schema: 1,
      sessionId: session.sessionId,
      generation: session.generation,
      visible: !terminal && !doc.hidden && session.mediaState === 'ready',
      focused: !terminal && doc.hasFocus(),
      mediaState: terminal ? 'closed' : session.mediaState
    };
  }

  function releaseMedia(session) {
    session.contentEpoch += 1;
    root.clearTimeout(session.mediaTimer);
    root.clearInterval(session.cacheTimer);
    session.cacheTimer = null;
    root.clearInterval(session.ambientTimer);
    ambient.hidden = true;
    ambient.children[0].className = ambient.children[1].className = '';
    setClock(session, false);
    photo.onload = photo.onerror = null;
    video.onplaying = video.onerror = null;
    if (video.hasAttribute('src')) {
      video.pause();
      video.removeAttribute('src');
      video.load();
    }
    photo.removeAttribute('src');
    photo.hidden = video.hidden = clock.hidden = true;
  }

  function dispose(session) {
    root.clearInterval(session.timer);
    if (session.request) session.request.abort();
    session.request = null;
    releaseMedia(session);
  }

  function terminalReport(session) {
    try {
      var xhr = new root.XMLHttpRequest();
      xhr.open('POST', session.endpoint, true);
      xhr.timeout = 1000;
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('X-CYTV-Session', session.sessionId);
      xhr.send(JSON.stringify(envelope(session, true)));
    } catch (_) {}
  }

  function close() {
    if (finished) return;
    finished = true;
    root.clearTimeout(startupTimer);
    cancelCandidate();
    if (owner) {
      dispose(owner);
      if (!embedded) terminalReport(owner);
    }
    if (embedded) root.parent.postMessage('cytv-screensaver-closed', '*');
    else root.close();
  }

  function live(session, epoch) {
    return !finished && owner === session && session.contentEpoch === epoch;
  }

  function moveClock(left, top) {
    clock.style.left = left + '%';
    clock.style.top = top + '%';
  }

  function timeFormatter(presentation) {
    if (!presentation) return null;
    var use12 = presentation.hour12;
    var hourCycle = use12 ? 'h12' : 'h23';
    try {
      var formatter = new Intl.DateTimeFormat(presentation.locale, {
        hour: use12 ? 'numeric' : '2-digit',
        minute: '2-digit',
        hourCycle: hourCycle
      });
      var resolved = formatter.resolvedOptions();
      if (
        resolved.hour12 === use12 &&
        (!resolved.hourCycle || resolved.hourCycle === hourCycle)
      )
        return formatter;
    } catch (_) {}
    return null;
  }

  function clockText(date, presentation, formatter) {
    if (formatter) return formatter.format(date);
    var hour = date.getHours();
    var use12 = presentation && presentation.hour12;
    return (
      (use12 ? hour % 12 || 12 : ('0' + hour).slice(-2)) +
      ':' +
      ('0' + date.getMinutes()).slice(-2) +
      (use12 ? (hour < 12 ? ' AM' : ' PM') : '')
    );
  }

  function setClock(session, visible, overlay, withDate) {
    if (!visible) {
      root.clearInterval(session.clockTimer);
      session.clockTimer = null;
      clock.hidden = true;
      return;
    }
    if (session.clockTimer != null) return;
    clock.className = overlay
      ? 'clock-overlay'
      : withDate
        ? 'ambient-clock'
        : '';
    clockDate.hidden = true;
    var paintedDate = null;
    var formatKey = null;
    var formatter;
    function paint() {
      var date = new Date();
      var presentation = session.clock;
      var locale = presentation ? presentation.locale : undefined;
      var key = presentation ? locale + ':' + presentation.hour12 : '';
      // Intl setup is deferred until after the first ready frame.
      if ((withDate || session.mediaState === 'ready') && formatKey !== key) {
        formatKey = key;
        formatter = timeFormatter(presentation);
      }
      clockTime.textContent = clockText(date, presentation, formatter);
      if (withDate) {
        var dateKey = date.toDateString() + ':' + locale;
        if (paintedDate !== dateKey) {
          paintedDate = dateKey;
          try {
            clockDate.textContent = date.toLocaleDateString(locale, {
              weekday: 'long',
              month: 'long',
              day: 'numeric'
            });
          } catch (_) {
            clockDate.textContent = date.toLocaleDateString();
          }
          clockDate.hidden = false;
        }
      } else {
        // Reposition once per minute without leaving a fixed bright mark.
        var minute = Math.floor(date.getTime() / 60000);
        moveClock(8 + ((minute * 17) % 58), 8 + ((minute * 23) % 72));
      }
    }
    paint();
    clock.hidden = false;
    session.clockTimer = root.setInterval(paint, 1000);
  }

  function showClock(session, error) {
    setClock(session, true, false);
    var epoch = session.contentEpoch;
    root.requestAnimationFrame(function () {
      if (live(session, epoch)) reportMedia(session, error ? 'error' : 'ready');
    });
  }

  function showAmbient(session, error) {
    // Palette and glow inspired by Clean Your TV's ClockScene (Gathin, MIT).
    var colors = [
      '43,92,255',
      '0,163,154',
      '138,63,252',
      '224,102,27',
      '214,51,108'
    ];
    var frame = 0;
    function paint() {
      var layer = ambient.children[frame % 2];
      var color = colors[frame % colors.length];
      var left = frame ? 18 + ((frame * 37) % 64) : 50;
      var top = frame ? 18 + ((frame * 29) % 64) : 50;
      layer.style.backgroundImage =
        'radial-gradient(circle 55vw at ' +
        left +
        '% ' +
        top +
        '%,rgba(' +
        color +
        ',0.25),rgba(' +
        color +
        ',0.08) 55%,transparent)';
      ambient.children[(frame + 1) % 2].className = '';
      layer.className = 'glow-visible';
      moveClock(left, top);
      frame++;
    }
    paint();
    ambient.hidden = false;
    session.ambientTimer = root.setInterval(paint, 60000);
    var epoch = session.contentEpoch;
    root.requestAnimationFrame(function () {
      if (!live(session, epoch)) return;
      reportMedia(session, error ? 'error' : 'ready');
      setClock(session, session.clockOverlay, false, true);
    });
  }

  function mediaUrl(session, url) {
    if (
      typeof url !== 'string' ||
      url.length > 4096 ||
      /[\x00-\x20\\#]/.test(url)
    )
      return false;
    var origin = session.endpoint.slice(0, -12);
    if (url.indexOf(origin + '/screensaver/media/') !== 0) return false;
    var anchor = doc.createElement('a');
    anchor.href = url;
    return (
      anchor.protocol === 'http:' &&
      anchor.host === origin.slice(7) &&
      anchor.pathname.indexOf('/screensaver/media/') === 0 &&
      !anchor.username &&
      !anchor.password
    );
  }

  function bundledBackground(content) {
    return (
      root.CYTVScreensaverSettings &&
      root.CYTVScreensaverSettings.background(content.mode, content.assetId)
    );
  }

  function cacheUrl(content) {
    var settings = root.CYTVScreensaverSettings;
    return settings && settings.personalMediaUrl(content.mode, content.cacheUrl)
      ? content.cacheUrl
      : '';
  }

  function activate(session) {
    if (session.activated) return;
    session.activated = true;
    if (embedded) return;
    var system = root.webOSSystem || root.PalmSystem;
    try {
      if (system && typeof system.activate === 'function') system.activate();
    } catch (_) {}
  }

  function render(session, content) {
    if (!content || typeof content !== 'object') return close();
    var mode = content.mode;
    var bundled = bundledBackground(content);
    var cached = cacheUrl(content);
    var assetPath =
      bundled &&
      (((content.quality === '1080p' || session.hdFallback === bundled.id) &&
        bundled.hdFile) ||
        bundled.file);
    var url = bundled
      ? embedded
        ? content.assets[assetPath]
        : assetPath
      : cached || content.url;
    session.clockOverlay = content.clockOverlay === true;
    session.clock = root.CYTVScreensaverSettings.clockPresentation(
      content.clock
    );
    doc.documentElement.lang = session.clock ? session.clock.locale : 'en';
    var key = mode + '\n' + (typeof url === 'string' ? url : '');
    if (key === session.contentKey) {
      if (mode !== 'clock' && session.mediaState === 'ready')
        setClock(
          session,
          session.clockOverlay,
          mode !== 'ambient',
          mode === 'ambient'
        );
      return;
    }
    session.contentKey = key;
    releaseMedia(session);
    session.mediaState = 'loading';
    var epoch = session.contentEpoch;
    if (mode === 'clock' || mode === 'ambient') {
      activate(session);
      return mode === 'clock'
        ? showClock(session, false)
        : showAmbient(session, false);
    }
    function failed() {
      if (!live(session, epoch)) return;
      if (bundled && bundled.hdFile && assetPath !== bundled.hdFile) {
        session.hdFallback = bundled.id;
        return render(session, content);
      }
      releaseMedia(session);
      showAmbient(session, true);
    }
    if (
      (mode !== 'photo' && mode !== 'video') ||
      (!bundled && !cached && !mediaUrl(session, url))
    )
      return failed();
    activate(session);
    session.mediaTimer = root.setTimeout(failed, 8000);
    function ready() {
      if (!live(session, epoch)) return;
      root.clearTimeout(session.mediaTimer);
      reportMedia(session, 'ready');
      setClock(session, session.clockOverlay, true);
      if (cached && !session.cacheTimer)
        session.cacheTimer = root.setInterval(function () {
          if (
            !live(session, epoch) ||
            doc.hidden ||
            (!embedded && !doc.hasFocus())
          )
            return;
          try {
            var request = new root.XMLHttpRequest();
            request.open('HEAD', cached, true);
            request.timeout = 3000;
            request.send();
          } catch (_) {}
        }, 25000);
    }
    if (mode === 'photo') {
      photo.onload = function () {
        if (!photo.naturalWidth) return failed();
        photo.hidden = false;
        root.requestAnimationFrame(ready);
      };
      photo.onerror = failed;
      photo.src = url;
    } else {
      video.muted = true;
      video.loop = true;
      video.onplaying = function () {
        root.requestAnimationFrame(ready);
      };
      video.onerror = failed;
      // Keep the webOS video surface in layout while its decoder starts.
      video.hidden = false;
      video.src = url;
      try {
        var playing = video.play();
        if (playing && playing.catch) playing.catch(failed);
      } catch (_) {
        failed();
      }
    }
  }

  function reportMedia(session, state) {
    session.mediaState = state;
    if (embedded) {
      root.parent.postMessage('cytv-screensaver-rendered', '*');
      if (!session.timer)
        session.timer = root.setInterval(function () {
          if (
            !finished &&
            owner === session &&
            !doc.hidden &&
            session.mediaState !== 'loading'
          )
            root.parent.postMessage('cytv-screensaver-alive', '*');
        }, 1000);
      return;
    }
    if (state !== 'ready' || doc.hasFocus()) heartbeat(session);
  }

  function heartbeat(session) {
    if (finished || owner !== session) return;
    if (now() - session.lastReply > 5000) return close();
    if (session.request) return;
    var xhr = new root.XMLHttpRequest();
    session.request = xhr;
    function done() {
      if (session.request === xhr) session.request = null;
    }
    xhr.onload = function () {
      done();
      if (finished || owner !== session) return;
      if (xhr.status === 403) return close();
      if (xhr.status !== 200) return;
      var response;
      try {
        if (xhr.responseText.length > 16384) return close();
        response = JSON.parse(xhr.responseText);
      } catch (_) {
        return close();
      }
      if (!response || typeof response.close !== 'boolean') return close();
      if (response.close) return close();
      session.lastReply = now();
      render(session, response.content);
    };
    xhr.onerror = xhr.ontimeout = xhr.onabort = done;
    try {
      xhr.open('POST', session.endpoint, true);
      xhr.timeout = 3000;
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('X-CYTV-Session', session.sessionId);
      xhr.send(JSON.stringify(envelope(session, false)));
    } catch (_) {
      done();
    }
  }

  function identity(session) {
    return session.sessionId + ':' + session.generation;
  }

  function cancelCandidate() {
    var pending = candidate;
    candidate = null;
    if (!pending) return;
    root.clearTimeout(pending.deadline);
    if (pending.request) pending.request.abort();
    pending.request = null;
  }

  function replacement(params) {
    var key = identity(params);
    if (
      identity(owner) === key ||
      retired.indexOf(key) !== -1 ||
      (candidate && identity(candidate) === key)
    )
      return;
    cancelCandidate();
    var session = {
      sessionId: params.sessionId,
      generation: params.generation,
      endpoint: params.endpoint,
      mediaState: 'loading',
      contentEpoch: 0,
      lastReply: now()
    };
    candidate = session;
    function reject() {
      if (candidate === session) cancelCandidate();
    }
    session.deadline = root.setTimeout(reject, 3000);
    var xhr = new root.XMLHttpRequest();
    session.request = xhr;
    xhr.onload = function () {
      if (finished || candidate !== session) return;
      var response;
      try {
        if (xhr.status !== 200 || xhr.responseText.length > 16384)
          return reject();
        response = JSON.parse(xhr.responseText);
      } catch (_) {
        return reject();
      }
      var content = response && response.content;
      if (
        !response ||
        response.close !== false ||
        !content ||
        typeof content !== 'object' ||
        Array.isArray(content) ||
        (content.mode !== 'clock' &&
          content.mode !== 'ambient' &&
          !(
            (content.mode === 'photo' || content.mode === 'video') &&
            (bundledBackground(content) ||
              cacheUrl(content) ||
              mediaUrl(session, content.url))
          ))
      )
        return reject();
      // Generations are opaque owner identities, not ordered counters. Only a
      // successful authenticated candidate response permits replacing a live
      // session; a rejected/stale launch must leave its media and timers alone.
      root.clearTimeout(session.deadline);
      session.request = null;
      candidate = null;
      var previous = owner;
      retired.push(identity(previous));
      if (retired.length > 64) retired.shift();
      dispose(previous);
      terminalReport(previous);
      owner = session;
      held = {};
      dismissing = false;
      session.lastReply = now();
      session.timer = root.setInterval(function () {
        heartbeat(session);
      }, 1000);
      render(session, content);
    };
    xhr.onerror = xhr.ontimeout = reject;
    try {
      xhr.open('POST', session.endpoint, true);
      xhr.timeout = 3000;
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('X-CYTV-Session', session.sessionId);
      xhr.send(JSON.stringify(envelope(session, false)));
    } catch (_) {
      reject();
    }
  }

  function launch(event) {
    if (finished) return;
    var params;
    try {
      var raw = event && event.detail;
      if (!raw) raw = (root.webOSSystem || root.PalmSystem || {}).launchParams;
      if (typeof raw === 'string') {
        if (raw.length > 4096) return;
        raw = JSON.parse(raw);
      }
      if (raw && raw.params) raw = raw.params;
      if (typeof raw === 'string') raw = JSON.parse(raw);
      params = raw;
    } catch (_) {
      return;
    }
    if (!valid(params)) {
      if (!owner) close();
      return;
    }
    if (owner) return replacement(params);
    root.clearTimeout(startupTimer);
    if (owner) dispose(owner);
    held = {};
    dismissing = false;
    owner = {
      sessionId: params.sessionId,
      generation: params.generation,
      endpoint: params.endpoint,
      mediaState: 'loading',
      contentEpoch: 0,
      lastReply: now()
    };
    var session = owner;
    session.timer = root.setInterval(function () {
      heartbeat(session);
    }, 1000);
    heartbeat(session);
  }

  if (embedded) {
    root.addEventListener('message', function (event) {
      if (event.source !== root.parent || owner || finished) return;
      var data = event.data;
      if (!data || data.type !== 'cytv-screensaver-start') return;
      owner = { contentEpoch: 0, mediaState: 'loading' };
      render(owner, data.content);
    });
    return;
  }

  var held = {};
  var dismissing = false;
  function navigation(code) {
    return (
      code === 13 ||
      code === 8 ||
      code === 27 ||
      code === 461 ||
      (code >= 37 && code <= 40) ||
      (code >= 48 && code <= 57) ||
      (code >= 403 && code <= 406)
    );
  }
  function consume(event) {
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  doc.addEventListener(
    'keydown',
    function (event) {
      if (finished) return;
      if (navigation(event.keyCode)) {
        consume(event);
        held[event.keyCode] = true;
        dismissing = true;
      } else close(); // System actions retain their normal platform handling.
    },
    true
  );
  doc.addEventListener(
    'keyup',
    function (event) {
      if (!navigation(event.keyCode)) return;
      consume(event);
      delete held[event.keyCode];
      if (dismissing && Object.keys(held).length === 0) close();
    },
    true
  );
  root.addEventListener('blur', function () {
    if (owner) close();
  });
  root.addEventListener('focus', function () {
    if (owner && owner.mediaState === 'ready') heartbeat(owner);
  });
  doc.addEventListener('visibilitychange', function () {
    if (!owner) return;
    if (doc.hidden) close();
    else if (owner.mediaState === 'ready' && doc.hasFocus()) heartbeat(owner);
  });
  root.addEventListener('pagehide', close);
  doc.addEventListener('webOSLaunch', launch);
  doc.addEventListener('webOSRelaunch', launch);
  startupTimer = root.setTimeout(close, 1000);
  launch();
})(window);
