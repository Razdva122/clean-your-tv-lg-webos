'use strict';
var fs = require('fs'),
  cp = require('child_process'),
  policy = require('./runtime-policy');
function monotonic() {
  var t = process.hrtime();
  return t[0] * 1000 + t[1] / 1e6;
}
var root = '/media/developer/apps/usr/palm/applications/com.local.nativehome';
var data = root + '/state';
var launchParams = JSON.parse(process.argv[2] || '{}'),
  automatic = launchParams.nativeHomeAuto === true;
function block(close) {
  fs.writeFileSync(data + '/blocked', 'stopped', { mode: 420 });
  invalidatePresentation(close !== false);
}
if (
  automatic &&
  (fs.existsSync(data + '/blocked') || fs.existsSync(data + '/watchdog'))
)
  process.exit(0);
if (
  !require('./state-permissions')(
    data,
    function (x) {
      console.error(JSON.stringify(x));
    },
    true
  )
)
  throw Error('Helper control initialization failed');
var logPath = data + '/controller.log',
  pidPath = data + '/controller.pid';
fs.writeFileSync(pidPath, String(process.pid));
fs.writeFileSync(logPath, '');
function log(x) {
  try {
    fs.appendFileSync(
      logPath,
      JSON.stringify(Object.assign({ time: Date.now() }, x)) + '\n'
    );
  } catch (e) {
    try {
      console.error('Helper log failed: ' + String(e));
      console.error(x);
    } catch (ignore) {}
  }
}
process.on('uncaughtException', function (e) {
  try {
    block();
  } catch (ignore) {}
  stopping = true;
  clearTimeout(restartTimer);
  clearInterval(timer);
  log({ error: String(e), stack: e && e.stack });
  setTimeout(function () {
    process.exit(2);
  }, 2500);
  try {
    if (child) child.stdin.end();
  } catch (ignore) {}
});
var Service = require('/usr/lib/node_modules/webos-service');
var service = new Service('com.local.nativehome');
service.activityManager.create('native-home-controller', function () {});
if (!automatic) {
  ['blocked', 'watchdog'].forEach(function (name) {
    try {
      fs.unlinkSync(data + '/' + name);
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
    }
  });
}
var lastForeground = null,
  lastForegroundAt = null,
  monitor = 'starting',
  monitorReason = null,
  shouldResumeLaunch = require('./resume-policy');
var child,
  ready = false,
  stopping = false,
  lastAck = monotonic(),
  buffer = '',
  lastCommand = '',
  launching = false,
  resumePendingUntil = 0;
var restarts = [],
  restartTimer = null,
  cleaning = false,
  stopRequested = false,
  irHomeTimer = null;
// The standard IR remote is observed, not grabbed, so webOS also opens its own Home
// on IR Home. Launching custom Home after this delay lands it above LG Home.
// ponytail: fixed delay from #207, not measured per model; replace it with a
// foreground signal if webOS ever reports its Home bar.
var IR_HOME_DELAY = 700;
var homeCloseState = 'idle',
  homeCloseWaiters = [],
  terminalUI = false,
  homeLaunchPending = false,
  homeLaunchUnknown = false;
var presentation = require('./presentation-context')({
  now: monotonic,
  content: function (id) {
    return (
      id !== 'com.gathin.tvhome' &&
      id !== 'com.webos.app.home' &&
      id !== 'com.webos.app.cpcover' &&
      ((watchedApps || []).indexOf(id) !== -1 ||
        /^com\.webos\.app\.hdmi[1-4]$/.test(id))
    );
  }
});
function closeOwnedHome() {
  if (homeCloseState !== 'idle' || !service) return;
  homeCloseState = 'pending';
  var settled = false,
    timer = setTimeout(function () {
      finish('unknown');
    }, 3000);
  function finish(state) {
    if (settled) return;
    settled = true;
    clearTimeout(timer);
    homeCloseState = state;
    if (state !== 'closed')
      log({ event: 'presentation-close-failed', result: state });
    var waiters = homeCloseWaiters;
    homeCloseWaiters = [];
    waiters.forEach(function (done) {
      done(state !== 'unknown');
    });
  }
  try {
    service.call(
      'luna://com.webos.applicationManager/closeByAppId',
      { id: 'com.gathin.tvhome' },
      function (m) {
        finish(
          m.payload && m.payload.returnValue === true
            ? 'closed'
            : m.payload && m.payload.returnValue === false
              ? 'idle'
              : 'unknown'
        );
      }
    );
  } catch (e) {
    finish('unknown');
  }
}
function afterHomeClose(done) {
  if (homeCloseState === 'pending') homeCloseWaiters.push(done);
  else done(homeCloseState !== 'unknown');
}
function invalidatePresentation(close) {
  if (presentation) presentation.invalidate();
  if (close) closeOwnedHome();
}
function refreshPresentation(generation, done) {
  function finish(id) {
    if (presentation.generation() !== generation) {
      done(false);
      return;
    }
    presentation.observe(generation, id);
    done(true);
  }
  if (!screenWatch || typeof screenWatch.foreground !== 'function') {
    finish(null);
    return;
  }
  screenWatch.foreground(finish);
}
function launchHome(reason, done) {
  // A deferred close reply cannot transfer an old activation to a new relay.
  var worker = child;
  var retained =
    reason === 'home' &&
    lastForeground === 'com.gathin.tvhome' &&
    presentation.active();
  var generation = presentation.begin(reason, retained);
  function open(current) {
    if (
      !current ||
      stopping ||
      stopRequested ||
      child !== worker ||
      (worker &&
        (worker.reason !== undefined ||
          worker.exited ||
          worker.watchdogKill)) ||
      visitingLG ||
      generation !== presentation.generation()
    ) {
      if (done) done(true);
      return;
    }
    afterHomeClose(function (known) {
      if (
        stopping ||
        stopRequested ||
        child !== worker ||
        (worker &&
          (worker.reason !== undefined ||
            worker.exited ||
            worker.watchdogKill)) ||
        visitingLG ||
        generation !== presentation.generation()
      ) {
        if (done) done(true);
        return;
      }
      if (!known) {
        if (done) done(false);
        return;
      }
      homeCloseState = 'idle';
      var params =
        reason === 'home'
          ? { cytvHome: { reason: 'home', generation: generation } }
          : { reason: reason };
      homeLaunchPending = true;
      launch(
        'com.gathin.tvhome',
        function (ok, known) {
          // A later accepted launch cannot settle an older timed-out SAM request.
          homeLaunchPending = false;
          homeLaunchUnknown = homeLaunchUnknown || !known;
          if (stopping || stopRequested || visitingLG) {
            if (homeCloseState === 'closed') homeCloseState = 'idle';
            invalidatePresentation(!terminalUI);
          }
          if (done) done(ok);
        },
        params
      );
    });
  }
  // The canonical Home is a CARD. Its activation must not wait for an overlay
  // underlay observation; retained legacy context RPCs remain independently fenced.
  open(true);
}
var resumeGuardUntil = 0,
  resumeRetries = 0,
  lgHomeSince = null,
  lastLaunchSettledAt = 0;
// Opt-in, bounded observation only; never changes routing or starts another watcher.
var diagnosticUntil = 0,
  diagnosticNext = 0,
  homeSequence = 0,
  lastHomeAt = null,
  launchSequence = 0,
  diagnosticSession = null;
function diagnostic(trigger, details) {
  if (!diagnosticUntil) return;
  var now = monotonic();
  if (now >= diagnosticUntil && trigger !== 'expired') {
    diagnostic('expired');
    diagnosticUntil = 0;
    return;
  }
  log(
    Object.assign(
      {
        event: 'home-diagnostic',
        session: diagnosticSession,
        trigger: trigger,
        homeSequence: homeSequence,
        sinceHomeMs: lastHomeAt === null ? null : Math.round(now - lastHomeAt),
        foreground: lastForeground,
        foregroundSource: 'subscription-cache',
        foregroundAgeMs:
          lastForegroundAt === null ? null : Math.round(now - lastForegroundAt),
        monitor: monitor,
        monitorReason: monitorReason,
        ready: ready,
        enabled: homeControl ? homeControl.enabled() : null,
        launching: launching,
        visitingLG: !!visitingLG
      },
      details || {}
    )
  );
}
function diagnosticCommand(cmd, nonce) {
  if (cmd === 'diagnostics-start') {
    diagnosticSession =
      typeof nonce === 'string' && /^[a-f0-9]{32}$/.test(nonce) ? nonce : null;
    diagnosticUntil = monotonic() + 60000;
    diagnosticNext = monotonic() + 1000;
    homeSequence = 0;
    lastHomeAt = null;
    diagnostic('started', { durationMs: 60000 });
  }
  if (cmd === 'diagnostics-stop') {
    diagnostic('stopped');
    diagnosticUntil = 0;
  }
}
function screenLog(x) {
  if (x.event.indexOf('screen-watch-') === 0) {
    monitor = x.event;
    monitorReason = x.reason || null;
  }
  log(x);
  diagnostic('monitor');
}
function cancelResume() {
  resumePendingUntil = 0;
  resumeGuardUntil = 0;
  lgHomeSince = null;
}
log({
  event: 'start',
  pid: process.pid,
  uid: process.getuid(),
  automatic: automatic,
  diagnosticsSchema: 1
});
function launch(id, done, params) {
  var request = ++launchSequence;
  diagnostic('launch-request', { launchSequence: request, id: id });
  var settled = false;
  var deadline = setTimeout(function () {
    if (settled) return;
    settled = true;
    lastLaunchSettledAt = monotonic();
    log({ event: 'launch-timeout', id: id });
    diagnostic('launch-timeout', { launchSequence: request, id: id });
    if (done) done(false, false);
  }, 3000);
  service.call(
    'luna://com.webos.applicationManager/launch',
    params ? { id: id, params: params } : { id: id },
    function (m) {
      if (settled) return;
      settled = true;
      lastLaunchSettledAt = monotonic();
      clearTimeout(deadline);
      log({ event: 'launch', id: id, result: m.payload });
      diagnostic('launch-result', {
        launchSequence: request,
        id: id,
        returnValue: !!(m.payload && m.payload.returnValue === true)
      });
      if (done)
        done(
          m.payload && m.payload.returnValue === true,
          !!(m.payload && typeof m.payload.returnValue === 'boolean')
        );
    }
  );
}
var visitingLG = false,
  suppressReturnUntil = 0;
function visitLG(done) {
  cancelIrHome();
  if (visitingLG) {
    if (done) done(false);
    return;
  }
  visitingLG = true;
  invalidatePresentation(true);
  cancelResume();
  suppressReturnUntil = monotonic() + 7000;
  var deadline = monotonic() + 3500;
  function open() {
    if (launching && monotonic() < deadline) {
      setTimeout(open, 50);
      return;
    }
    if (launching || stopping) {
      visitingLG = false;
      if (done) done(false);
      return;
    }
    if (screenPolicy) screenPolicy.reset();
    launch('com.webos.app.home', function (ok) {
      visitingLG = false;
      if (done) done(ok);
    });
  }
  open();
}
var homeControl = require('./home-control')(
  fs,
  data,
  function (enabled) {
    cancelIrHome();
    cancelResume();
    if (screenPolicy) screenPolicy.reset();
    if (child) child.stdin.write(enabled ? 'E' : 'D');
    if (!enabled) invalidatePresentation(true);
  },
  visitLG
);
// Keep the legacy channel for older Home packages during upgrade/rollback.
// New Home submits only through its own service directory, visible in its jail.
var homeChannels = [
  { directory: data, last: '' },
  {
    directory:
      '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control',
    last: ''
  },
  {
    directory:
      '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control',
    last: '',
    inputOnly: true
  },
  {
    directory:
      '/media/developer/apps/usr/palm/services/com.gathin.tvhome.renewal/state/home-control',
    last: '',
    catalogOnly: true
  }
];
var inputStatusPending = null,
  catalogPending = null;
function readCatalog() {
  if (!catalogPending) {
    catalogPending = Promise.resolve().then(function () {
      return require('./app-inventory')({ timeout: 3000 });
    });
    catalogPending = catalogPending.then(
      function (apps) {
        catalogPending = null;
        return apps;
      },
      function () {
        catalogPending = null;
        throw Error('App inventory unavailable');
      }
    );
  }
  return catalogPending;
}
function readInputs() {
  if (!inputStatusPending) {
    inputStatusPending = Promise.resolve().then(function () {
      return require('./app-inventory')({ inputs: true, timeout: 3000 });
    });
    inputStatusPending = inputStatusPending.then(
      function (devices) {
        inputStatusPending = null;
        return devices;
      },
      function () {
        inputStatusPending = null;
        throw Error('Input status unavailable');
      }
    );
  }
  return inputStatusPending;
}
function readHomeRequest(channel) {
  var directory = channel.directory,
    prefix = channel.catalogOnly
      ? 'catalog'
      : channel.inputOnly
        ? 'input'
        : 'home';
  var request;
  try {
    request = JSON.parse(
      fs.readFileSync(directory + '/' + prefix + '-request.json', 'utf8')
    );
  } catch (e) {
    return;
  }
  if (
    !request ||
    typeof request.id !== 'string' ||
    !/^[a-f0-9]{32}$/.test(request.id) ||
    request.id === channel.last
  )
    return;
  channel.last = request.id;
  if (
    typeof request.expires !== 'number' ||
    request.expires < Date.now() ||
    request.expires > Date.now() + 6000
  )
    return;
  if (
    (channel.inputOnly && request.method !== 'inputStatus') ||
    (channel.catalogOnly && request.method !== 'listApps')
  )
    return;
  if (
    channel.catalogOnly &&
    (stopping ||
      stopRequested ||
      fs.existsSync(data + '/blocked') ||
      (child && child.reason !== undefined))
  )
    return;
  function respond(result) {
    result.id = request.id;
    try {
      fs.writeFileSync(
        directory + '/' + prefix + '-response.tmp',
        JSON.stringify(result),
        { mode: 432 }
      );
      fs.chmodSync(directory + '/' + prefix + '-response.tmp', 432);
      fs.renameSync(
        directory + '/' + prefix + '-response.tmp',
        directory + '/' + prefix + '-response.json'
      );
    } catch (e) {
      log({ event: 'home-response-error', error: String(e) });
    }
  }
  try {
    if (
      !channel.inputOnly &&
      directory !== data &&
      request.method === 'presentationContext'
    ) {
      var generation = presentation.generation();
      refreshPresentation(generation, function (current) {
        if (
          !current ||
          stopping ||
          stopRequested ||
          (child && child.reason !== undefined) ||
          request.expires <= Date.now()
        )
          return;
        respond(presentation.context());
      });
    } else if (
      !channel.inputOnly &&
      directory !== data &&
      request.method === 'presentationDismissed'
    ) {
      var dismissed = presentation.dismiss(request.generation);
      if (dismissed) {
        cancelResume();
        screenPolicy.reset();
        suppressReturnUntil = monotonic() + 7000;
      }
      respond({
        returnValue: dismissed,
        dismissed: dismissed,
        generation: request.generation
      });
    } else if (request.method === 'homeStatus')
      respond({ returnValue: true, enabled: homeControl.enabled() });
    else if (request.method === 'setHomeControl') {
      homeControl.set(request.enabled);
      respond({ returnValue: true, enabled: homeControl.enabled() });
    } else if (request.method === 'openLGHome')
      visitLG(function (ok) {
        respond({ returnValue: ok });
      });
    else if (channel.catalogOnly && request.method === 'listApps')
      readCatalog().then(
        function (apps) {
          if (
            !stopping &&
            !stopRequested &&
            !fs.existsSync(data + '/blocked') &&
            !(child && child.reason !== undefined) &&
            request.expires > Date.now()
          )
            respond({ returnValue: true, apps: apps });
        },
        function () {
          if (
            !stopping &&
            !stopRequested &&
            !fs.existsSync(data + '/blocked') &&
            !(child && child.reason !== undefined) &&
            request.expires > Date.now()
          )
            respond({
              returnValue: false,
              errorText: 'App inventory unavailable'
            });
        }
      );
    else if (channel.inputOnly && request.method === 'inputStatus')
      readInputs().then(
        function (devices) {
          if (
            !stopping &&
            !stopRequested &&
            !fs.existsSync(data + '/blocked') &&
            request.expires > Date.now()
          )
            respond({ returnValue: true, devices: devices });
        },
        function () {
          if (
            !stopping &&
            !stopRequested &&
            !fs.existsSync(data + '/blocked') &&
            request.expires > Date.now()
          )
            respond({
              returnValue: false,
              errorText: 'Input status unavailable'
            });
        }
      );
    else respond({ returnValue: false, errorText: 'Invalid Home request' });
  } catch (e) {
    respond({ returnValue: false, errorText: String(e) });
  }
}
// A watchdog latch also prevents a new controller from restarting an orphaned
// relay. Only this live controller's successful READY may clear it, never blocked.
function watchdogLatch() {
  fs.writeFileSync(data + '/watchdog', 'stopped', { mode: 420 });
}
function readStop() {
  try {
    if (
      JSON.parse(fs.readFileSync(data + '/control.json', 'utf8')).cmd === 'stop'
    ) {
      stopRequested = true;
      cancelIrHome();
      block(false);
      cancelResume();
    }
  } catch (e) {
    if (e.code && e.code !== 'ENOENT') throw e;
  }
  return stopRequested;
}
function cleanupRelay(done) {
  cleaning = true;
  var settled = false,
    c;
  var deadline = setTimeout(function () {
    if (c) c.kill('SIGKILL');
    complete(false);
  }, 2500);
  function complete(ok) {
    if (settled) return;
    settled = true;
    clearTimeout(deadline);
    cleaning = false;
    done(ok);
  }
  try {
    c = cp.spawn(root + '/relay', ['cleanup'], { stdio: 'ignore' });
    c.on('error', function () {
      complete(false);
    });
    c.on('close', function (code, signal) {
      log({ event: 'cleanup', code: code, signal: signal });
      complete(code === 0 && !signal);
    });
  } catch (e) {
    complete(false);
  }
}
function finish(code, signal, needsCleanup, relayReason) {
  if (stopping) return;
  stopping = true;
  terminalUI =
    code === 22 || code === 27 || relayReason === 27 || stopRequested;
  invalidatePresentation(!terminalUI);
  clearTimeout(restartTimer);
  cancelIrHome();
  cancelResume();
  if (screenWatch) screenWatch.close();
  clearInterval(timer);
  log({ event: 'worker-exit', code: code, signal: signal });
  if (relayReason === 27 || policy.shouldBlock(code, signal))
    block(!terminalUI);
  // A signal can replace the OS exit code after the relay reported emergency.
  // Keep the real code/signal above for cleanup policy and diagnostics.
  function end() {
    try {
      fs.unlinkSync(pidPath);
    } catch (e) {}
    process.exit(relayReason === 27 ? 27 : code === 22 ? 0 : code || 0);
  }
  // Let an already-issued custom-Home request settle before the final LG launch.
  var finishDeadline = monotonic() + 3200,
    relayClean = true;
  function failed(reason) {
    log({ event: 'terminal-ui-failed', reason: reason });
    end();
  }
  function cleaned() {
    if (!terminalUI) {
      end();
      return;
    }
    if ((launching || homeLaunchPending) && monotonic() < finishDeadline) {
      setTimeout(cleaned, 50);
      return;
    }
    if (launching || homeLaunchPending) {
      failed('home-launch-pending');
      return;
    }
    // Normal LG activation backgrounds the single CARD. Cross-app close permission
    // is unnecessary; unknown owned launches still must never race this request.
    if (!relayClean) {
      failed('input-cleanup-failed');
      return;
    }
    if (homeLaunchUnknown) {
      failed('home-launch-unknown');
      return;
    }
    launch('com.webos.app.home', function (ok) {
      if (!ok) {
        failed('lg-launch-unconfirmed');
        return;
      }
      log({
        event: 'terminal-ui-requested',
        homeClosed: false,
        lgLaunchAccepted: true
      });
      setTimeout(end, 300);
    });
  }
  if (needsCleanup || ready)
    cleanupRelay(function (ok) {
      relayClean = ok;
      if (!ok) block(!terminalUI);
      cleaned();
    });
  else cleaned();
}
function workerClosed(worker, code, signal) {
  if (child !== worker || stopping) return;
  cancelIrHome();
  var needsCleanup = ready || !!signal;
  child = null;
  ready = false;
  buffer = '';
  readStop();
  var retry =
    (worker.reason === undefined || worker.reason === 20) &&
    ((code === 20 && !signal) ||
      (worker.watchdogKill &&
        signal === 'SIGKILL' &&
        worker.reason === undefined));
  if (!retry || stopRequested || fs.existsSync(data + '/blocked')) {
    finish(code, signal, needsCleanup, worker.reason);
    return;
  }
  var now = monotonic();
  restarts = restarts.filter(function (t) {
    return now - t < 600000;
  });
  if (restarts.length >= 5) {
    log({ event: 'worker-restart-limit' });
    finish(20, null, needsCleanup);
    return;
  }
  restarts.push(now);
  watchdogLatch();
  log({
    event: 'worker-restart',
    code: code,
    signal: signal,
    attempt: restarts.length
  });
  cleanupRelay(function (ok) {
    if (stopping) return;
    if (!ok) {
      finish(11);
      return;
    }
    if (readStop() || fs.existsSync(data + '/blocked')) {
      finish(0);
      return;
    }
    restartTimer = setTimeout(function () {
      restartTimer = null;
      if (stopping) return;
      if (readStop() || fs.existsSync(data + '/blocked')) {
        finish(0);
        return;
      }
      start(true);
    }, 1500);
  });
}
function start(recovering) {
  if (stopping || readStop()) {
    if (!stopping) finish(0);
    return;
  }
  lastAck = monotonic();
  buffer = '';
  ready = false;
  var worker = cp.spawn(root + '/relay', [], {
    stdio: ['pipe', 'pipe', 'pipe']
  });
  child = worker;
  log({ event: 'worker-start', pid: worker.pid });
  worker.stderr.on('data', function (b) {
    if (child === worker) log({ stderr: String(b) });
  });
  worker.on('error', function (e) {
    if (child !== worker || stopping) return;
    log({ error: String(e) });
    finish(1);
  });
  // close follows exit AND stdio drain; the old relay/lock cannot overlap a retry.
  worker.on('exit', function () {
    worker.exited = true;
    if (child === worker) cancelIrHome();
  });
  worker.on('close', function (code, signal) {
    workerClosed(worker, code, signal);
  });
  worker.stdout.on('data', function (b) {
    if (child !== worker || stopping) return;
    buffer += b;
    var i;
    while ((i = buffer.indexOf('\n')) >= 0) {
      var line = buffer.slice(0, i);
      buffer = buffer.slice(i + 1);
      if (line === 'P') {
        lastAck = monotonic();
        continue;
      }
      log({ event: 'worker', message: line });
      if (/^EXIT [0-9]+$/.test(line)) {
        worker.reason = Number(line.slice(5));
        cancelIrHome();
      }
      if (worker.reason !== undefined || worker.watchdogKill || worker.exited)
        continue;
      if (line === 'BACK_DOWN') {
        cancelResume();
        screenPolicy.back(true, monotonic());
      }
      if (line === 'BACK_UP') screenPolicy.back(false, monotonic());
      if (line === 'HOME' || line === 'IRHOME') {
        screenPolicy.clearBack();
        homeSequence++;
        lastHomeAt = monotonic();
        diagnostic('home');
      }
      if (line === 'READY') {
        if (readStop() || fs.existsSync(data + '/blocked')) {
          worker.stdin.write('Q');
          continue;
        }
        ready = true;
        lastAck = monotonic();
        if (recovering) {
          try {
            fs.unlinkSync(data + '/watchdog');
          } catch (e) {
            if (e.code !== 'ENOENT') throw e;
          }
          recovering = false;
        }
        worker.stdin.write(homeControl.enabled() ? 'E' : 'D');
      }
      if (line === 'LGHOME' && !stopRequested) visitLG();
      if (line === 'HOME') {
        cancelIrHome();
        openHome(worker);
      }
      // Repeated IR Home presses restart the delay, so they open Home once.
      if (line === 'IRHOME') {
        clearTimeout(irHomeTimer);
        irHomeTimer = setTimeout(function () {
          irHomeTimer = null;
          if (child === worker && ready && !stopping) openHome(worker);
        }, IR_HOME_DELAY);
      }
    }
  });
  worker.stdin.on('error', function () {});
}
function cancelIrHome() {
  clearTimeout(irHomeTimer);
  irHomeTimer = null;
}
function openHome(worker) {
  if (
    child !== worker ||
    !ready ||
    stopping ||
    worker.exited ||
    worker.watchdogKill ||
    worker.reason !== undefined ||
    !homeControl.enabled() ||
    visitingLG ||
    stopRequested ||
    launching
  )
    return;
  suppressReturnUntil = 0;
  launching = true;
  launchHome('home', function (ok) {
    launching = false;
    if (!ok && child === worker) worker.stdin.end();
  });
}
var timer = setInterval(function () {
  if (stopping) return;
  if (readStop()) {
    if (child) child.stdin.write('Q');
    else if (!cleaning) finish(0);
  }
  if (stopping) return;
  homeChannels.forEach(readHomeRequest);
  try {
    var raw = fs.readFileSync(data + '/control.json', 'utf8');
    if (raw !== lastCommand) {
      lastCommand = raw;
      var command = JSON.parse(raw);
      diagnosticCommand(command.cmd, command.nonce);
      if (command.cmd === 'startup-status')
        service.call(
          'luna://com.local.nativehome.service/status',
          {},
          function (r) {
            log({ event: 'startup-status', result: r.payload });
          }
        );
      if (command.cmd === 'stall-worker' && child) child.stdin.write('S');
      if (command.cmd === 'stall-controller') {
        cp.spawn(root + '/resume', [String(process.pid)], { stdio: 'ignore' });
        log({ event: 'simulate-controller-stall' });
        process.kill(process.pid, 'SIGSTOP');
      }
    }
  } catch (e) {}
  if (
    resumePendingUntil &&
    ready &&
    !launching &&
    !visitingLG &&
    homeControl.enabled()
  ) {
    var resumeDue = resumePendingUntil;
    resumePendingUntil = 0;
    if (!shouldResumeLaunch(lastForeground)) {
      log({ event: 'resume-already-foreground' });
    } else if (monotonic() <= resumeDue) {
      launching = true;
      log({ event: 'resume-launch' });
      launchHome('wake', function (ok) {
        launching = false;
        if (!ok) log({ event: 'resume-launch-failed' });
      });
    }
  }
  // A successful Luna reply only acknowledges the request. LG Home can win
  // later, including while a launch is in flight, so check the current level.
  var now = monotonic();
  if (diagnosticUntil && now >= diagnosticNext) {
    diagnostic('sample');
    diagnosticNext = now + 1000;
  }
  if (resumeGuardUntil && now >= resumeGuardUntil) cancelResume();
  if (
    resumeGuardUntil &&
    resumeRetries < 2 &&
    ready &&
    !launching &&
    !visitingLG &&
    homeControl.enabled() &&
    lastForeground === 'com.webos.app.home' &&
    lgHomeSince !== null &&
    now - lgHomeSince >= 1500 &&
    now - lastLaunchSettledAt >= 5000
  ) {
    resumeRetries++;
    launching = true;
    log({ event: 'resume-retry', attempt: resumeRetries });
    launchHome('return', function (ok) {
      launching = false;
      if (!ok) log({ event: 'resume-retry-failed' });
    });
  }
  if (
    child &&
    child.reason === undefined &&
    !child.watchdogKill &&
    !child.exited
  ) {
    if (policy.expired(lastAck, monotonic())) {
      log({ event: 'worker-watchdog' });
      watchdogLatch();
      child.watchdogKill = true;
      cancelIrHome();
      child.kill('SIGKILL');
      return;
    }
    child.stdin.write('P');
  }
}, 400);
setTimeout(
  function () {
    if (stopping || readStop()) {
      if (!stopping) finish(0);
      return;
    }
    if (!homeControl.enabled()) {
      start();
      return;
    }
    launchHome('startup', function (ok) {
      if (stopping) return;
      if (ok) start();
      else {
        block();
        process.exit(3);
      }
    });
  },
  automatic ? 0 : 1000
);

process.on('exit', function (code) {
  log({ event: 'controller-exit', code: code });
});

service.call('luna://com.local.nativehome.service/status', {}, function (m) {
  log({ event: 'startup-status', result: m.payload });
  if (
    !m.payload ||
    !m.payload.returnValue ||
    (m.payload.state.enabled && m.payload.state.schema === 3)
  )
    return;
  service.call('luna://com.local.nativehome.service/enable', {}, function (a) {
    if (!a.payload || !a.payload.returnValue) {
      log({ event: 'startup-arm-error', result: a.payload });
      return;
    }
    service.call(
      'luna://com.palm.activitymanager/create',
      {
        activity: {
          name: 'com.local.nativehome.boot',
          description: 'Bounded Native Home once per boot',
          type: { foreground: true, persist: true },
          schedule: { interval: '10s', precise: true },
          callback: {
            method: 'luna://com.local.nativehome.service/tick',
            params: {}
          }
        },
        start: true,
        replace: true,
        subscribe: false
      },
      function (r) {
        log({ event: 'startup-create', result: r.payload });
      }
    );
  });
});

var powerPolicy = require('./power-policy')();
var watchedApps = [];
try {
  watchedApps = JSON.parse(fs.readFileSync(data + '/apps.json', 'utf8'));
  if (!Array.isArray(watchedApps)) watchedApps = [];
} catch (e) {}
var screenPolicy = require('./screen-policy')(watchedApps);
var screenWatch = require('./screen-watch')(
  data,
  screenLog,
  function (id) {
    if (id === 'com.webos.app.home') {
      if (lgHomeSince === null) lgHomeSince = monotonic();
    } else {
      lgHomeSince = null;
      if (id && id !== 'com.webos.app.cpcover' && id !== 'com.gathin.tvhome')
        cancelResume();
    }
    if (
      lastForeground !== null &&
      id !== 'com.gathin.tvhome' &&
      id !== lastForeground
    )
      invalidatePresentation(false);
    lastForeground = id;
    lastForegroundAt = monotonic();
    log({ event: 'foreground', id: id });
    diagnostic('foreground');
    var exited = screenPolicy.next(id, monotonic());
    if (
      exited &&
      homeControl.enabled() &&
      !visitingLG &&
      monotonic() > suppressReturnUntil &&
      ready &&
      !stopping &&
      !launching
    ) {
      resumeGuardUntil = monotonic() + 30000;
      resumeRetries = 0;
      launching = true;
      log({ event: 'return-after-exit' });
      launchHome('return', function (ok) {
        launching = false;
        if (!ok) log({ event: 'return-after-exit-failed' });
      });
    }
  },
  function () {
    invalidatePresentation(false);
    lastForeground = null;
    lastForegroundAt = null;
    monitor = 'reset';
    monitorReason = null;
    lgHomeSince = null;
    screenPolicy.reset();
    diagnostic('monitor-reset');
  },
  function (p) {
    log({
      event: 'power',
      state: p.state,
      processing: p.processing,
      onOff: p.onOff
    });
    if (
      p.onOff === 'off' ||
      p.state === 'Active Standby' ||
      p.state === 'Suspend'
    ) {
      invalidatePresentation(false);
      cancelResume();
    }
    if (
      powerPolicy.next(p) &&
      homeControl.enabled() &&
      !visitingLG &&
      !stopping
    ) {
      var now = monotonic();
      resumePendingUntil = now + 10000;
      resumeGuardUntil = now + 30000;
      resumeRetries = 0;
      lgHomeSince = lastForeground === 'com.webos.app.home' ? now : null;
    }
  }
);
