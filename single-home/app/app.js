(function () {
  'use strict';
  var service = 'luna://io.github.razdva122.cytvhomepilot.service/';
  var ru = !/^en(?:-|$)/i.test(navigator.language || 'ru');
  var words = {
    setup: ['Настройка Home', 'Set up Home'],
    settings: ['Подключение к телевизору', 'TV connection'],
    back: ['На главный экран', 'Back to Home'],
    connect: ['Сопряжение с телевизором', 'TV pairing'],
    paired: ['Телевизор сопряжён', 'TV paired'],
    first: [
      'Разрешите доступ к списку приложений этого телевизора. Телевизор запросит подтверждение.',
      'Allow access to this TV’s app list. The TV will ask you to confirm.'
    ],
    waiting: [
      'Ответьте на запрос сопряжения на экране телевизора.',
      'Respond to the pairing request on the TV.'
    ],
    pairedInfo: [
      'Можно открывать приложения с главного экрана.',
      'You can open apps from Home.'
    ],
    pair: ['Связать с телевизором', 'Pair with this TV'],
    later: ['Позже', 'Later'],
    cancelPair: ['Отменить сопряжение', 'Cancel pairing'],
    pairAgain: ['Сопрячь заново', 'Pair again'],
    retry: ['Попробовать снова', 'Try again'],
    probe: ['Проверить хранилище', 'Check storage'],
    storageWait: [
      'Приватное хранилище ещё не подтверждено. После проверки службы нажмите «Проверить хранилище».',
      'Private storage is awaiting verification. After the service check, select Check storage.'
    ],
    storageOff: [
      'Для сопряжения требуется доступное приватное хранилище службы.',
      'Pairing needs private storage in the service.'
    ],
    checking: ['Проверяем состояние службы…', 'Checking the service…'],
    startup: ['Фоновый запуск', 'Background startup'],
    off: ['Фоновый запуск выключен.', 'Background startup is off.'],
    pending: [
      'Ожидаем подтверждения фонового запуска от телевизора.',
      'Waiting for the TV to confirm background startup.'
    ],
    enabled: ['Фоновый запуск включён.', 'Background startup is enabled.'],
    stopped: ['Фоновый запуск остановлен.', 'Background startup is stopped.'],
    boot: [
      'В этом сеансе зарегистрирован запуск службы при загрузке.',
      'A service startup at boot was recorded in this session.'
    ],
    enableStartup: [
      'Запускать службу при включении ТВ',
      'Start the service when the TV turns on'
    ],
    stop: ['Остановить фоновый запуск', 'Stop background startup'],
    'denied': [
      'Служба не разрешила этот запрос.',
      'The service denied this request.'
    ],
    'invalid-request': [
      'Служба не приняла запрос.',
      'The service did not accept the request.'
    ],
    'storage-unavailable': [
      'Приватное хранилище службы недоступно.',
      'Private service storage is unavailable.'
    ],
    'storage-unverified': [
      'Приватное хранилище ещё не прошло проверку.',
      'Private storage has not passed verification yet.'
    ],
    'busy': [
      'Служба занята. Проверьте состояние ещё раз.',
      'The service is busy. Check its status again.'
    ],
    'cancelled': ['Сопряжение отменено.', 'Pairing was cancelled.'],
    'pairing-declined': [
      'Телевизор отклонил запрос на сопряжение.',
      'The TV declined the pairing request.'
    ],
    'pairing-timeout': [
      'Время ожидания сопряжения истекло. Проверьте запрос на экране телевизора.',
      'Pairing timed out. Check the prompt on the TV.'
    ],
    'saved-pairing-rejected': [
      'Телевизор отклонил сохранённое сопряжение. Выберите «Сопрячь заново» и подтвердите запрос.',
      'The TV rejected the saved pairing. Select Pair again and approve the new request.'
    ],
    'network-unavailable': [
      'Не удалось подключиться к этому телевизору.',
      'Could not connect to this TV.'
    ],
    'invalid-inventory': [
      'Не удалось получить список приложений.',
      'Could not read the TV’s app list.'
    ],
    'not-paired': [
      'Сначала выполните сопряжение с телевизором.',
      'Pair with this TV first.'
    ],
    'activity-cancel-unconfirmed': [
      'Служба остановлена. Телевизор ещё не подтвердил отмену фоновой задачи. Нажмите «Остановить фоновый запуск» ещё раз.',
      'The service has stopped. The TV has yet to confirm task cancellation. Select Stop background startup again.'
    ],
    'boot-clock-unavailable': [
      'Служба не смогла определить текущий сеанс работы телевизора.',
      'The service could not identify the current TV session.'
    ],
    'activity-unavailable': [
      'Телевизор не подтвердил фоновый запуск.',
      'The TV could not confirm background startup.'
    ],
    'unavailable': [
      'Служба не ответила. Проверьте состояние ещё раз.',
      'The service did not respond. Check its status again.'
    ]
  };
  function t(key) {
    return words[key][ru ? 0 : 1];
  }
  function el(id) {
    return document.getElementById(id);
  }
  function label(id, key) {
    el(id).textContent = t(key || id);
  }
  function show(id, on) {
    el(id).hidden = !on;
  }
  function visible(node) {
    return !!(node && node.offsetHeight && !node.disabled);
  }
  function focus(id) {
    var b = el(id);
    if (visible(b)) b.focus();
  }
  function rpc(uri, args, callback, timeout) {
    var bus,
      finished = false,
      timer = setTimeout(function () {
        finish(null);
      }, timeout || 8000);
    function finish(reply) {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (bus)
        try {
          bus.cancel();
        } catch (_) {}
      callback(reply || { returnValue: false, errorCode: 'unavailable' });
    }
    try {
      bus = new PalmServiceBridge();
      bus.onservicecallback = function (raw) {
        var reply;
        try {
          reply = JSON.parse(raw);
        } catch (_) {}
        finish(reply);
      };
      bus.call(uri, JSON.stringify(args));
    } catch (_) {
      finish(null);
    }
  }
  function call(method, args, cb, timeout) {
    rpc(service + method, args, cb, timeout);
  }
  var settings = /(?:^|[?&])settings=1(?:&|$)/.test(location.search);
  var repairRequested =
    settings &&
    /(?:^|[?&])reason=saved-pairing-rejected(?:&|$)/.test(location.search);
  var notice = repairRequested ? 'saved-pairing-rejected' : '';
  var state = null,
    pairing = false,
    changingStartup = '',
    checking = false,
    retryPair = false;
  var stateEpoch = 0,
    pairEpoch = 0,
    startupEpoch = 0,
    pollTimer,
    pollUntil = 0;

  function goHome(skipSetup) {
    if (skipSetup) {
      try {
        sessionStorage.setItem('cytv.home.skipSetup', '1');
      } catch (_) {}
    }
    location.replace('../index.html' + (skipSetup ? '?skipSetup=1' : ''));
  }

  function allowed() {
    return (
      !!state && state.storageReady === true && state.credentialsReady === true
    );
  }
  function knownState(r) {
    return (
      r.returnValue === true &&
      typeof r.paired === 'boolean' &&
      typeof r.pairing === 'boolean' &&
      typeof r.storageReady === 'boolean' &&
      typeof r.credentialsReady === 'boolean' &&
      ['off', 'pending', 'enabled', 'stopped'].indexOf(r.startup) >= 0
    );
  }
  function error(reply) {
    var code = reply && reply.errorCode;
    return typeof code === 'string' &&
      Object.prototype.hasOwnProperty.call(words, code) &&
      [
        'denied',
        'invalid-request',
        'storage-unavailable',
        'storage-unverified',
        'busy',
        'cancelled',
        'pairing-declined',
        'pairing-timeout',
        'saved-pairing-rejected',
        'network-unavailable',
        'invalid-inventory',
        'not-paired',
        'activity-unavailable',
        'activity-cancel-unconfirmed',
        'boot-clock-unavailable'
      ].indexOf(code) >= 0
      ? code
      : 'unavailable';
  }
  function render() {
    var paired = !!(state && state.paired),
      active = pairing || !!(state && state.pairing);
    document.documentElement.lang = ru ? 'ru' : 'en';
    label('title', settings ? 'settings' : 'setup');
    show('back', settings && !active);
    el('notice').textContent = notice ? t(notice) : '';
    label('pairHeading', paired ? 'paired' : 'connect');
    label('pairStatus', active ? 'waiting' : paired ? 'pairedInfo' : 'first');
    show('pair', !paired && !active && !retryPair);
    el('pair').disabled = !allowed() || checking;
    show('pairAgain', paired && !active && !retryPair);
    el('pairAgain').disabled = !allowed() || checking;
    show('retry', retryPair && !active && allowed());
    show('cancelPair', active);
    show('later', !settings && !active);
    el('storageStatus').textContent = allowed()
      ? ''
      : t(
          !state
            ? checking
              ? 'checking'
              : 'storageOff'
            : state.storageReady
              ? 'storageWait'
              : 'storageOff'
        );
    show('probe', !allowed() && !active);
    el('probe').disabled = checking;
    show('startupArea', settings && !!state);
    if (state) {
      el('startupStatus').textContent =
        t(state.startup) + (state.bootObserved === true ? ' ' + t('boot') : '');
      show(
        'enableStartup',
        !changingStartup &&
          (state.startup === 'off' || state.startup === 'stopped')
      );
      el('enableStartup').disabled =
        !state.storageReady || active || !!changingStartup;
      show(
        'stop',
        !!changingStartup ||
          state.startup === 'pending' ||
          state.startup === 'enabled' ||
          notice === 'activity-cancel-unconfirmed'
      );
      el('stop').disabled = changingStartup === 'disable';
    }
  }

  function focusAction() {
    var ids = [
      'cancelPair',
      'retry',
      'pair',
      'pairAgain',
      'probe',
      'back',
      'later'
    ];
    for (var i = 0; i < ids.length; i++) {
      if (visible(el(ids[i]))) {
        focus(ids[i]);
        return;
      }
    }
  }

  function poll() {
    clearTimeout(pollTimer);
    if (
      !state ||
      document.hidden ||
      (state.startup !== 'pending' && !state.pairing)
    )
      return;
    if (!pollUntil) pollUntil = Date.now() + (state.pairing ? 80000 : 45000);
    if (Date.now() >= pollUntil) {
      notice = 'unavailable';
      render();
      return;
    }
    pollTimer = setTimeout(function () {
      refresh(false);
    }, 2000);
  }
  function refresh(target) {
    var epoch = ++stateEpoch;
    checking = true;
    render();
    call('status', {}, function (r) {
      if (epoch !== stateEpoch) return;
      checking = false;
      if (!knownState(r)) {
        state = null;
        notice = error(r);
        render();
        if (target) focus('probe');
        return;
      }
      state = {
        paired: r.paired,
        pairing: r.pairing,
        storageReady: r.storageReady,
        credentialsReady: r.credentialsReady,
        startup: r.startup,
        bootObserved: r.bootObserved === true
      };
      if (!settings && state.paired && !state.pairing && allowed()) {
        goHome(false);
        return;
      }
      if (state.startup !== 'pending' && !state.pairing) pollUntil = 0;
      render();
      poll();
      if (
        target ||
        !visible(document.activeElement) ||
        document.activeElement === document.body
      )
        focusAction();
    });
  }
  function checkStorage() {
    if (checking) return;
    var epoch = ++stateEpoch;
    checking = true;
    notice = '';
    render();
    call('probe', {}, function (r) {
      if (epoch !== stateEpoch) return;
      checking = false;
      if (r.returnValue !== true) {
        notice = error(r);
        render();
        focus('probe');
        return;
      }
      refresh(true);
    });
  }
  function startPair() {
    if (!allowed() || pairing || (state && state.pairing)) return;
    clearTimeout(pollTimer);
    var epoch = ++pairEpoch;
    stateEpoch++;
    checking = false;
    pairing = true;
    retryPair = false;
    notice = '';
    render();
    focus('cancelPair');
    call(
      'pair',
      { confirm: true },
      function (r) {
        if (epoch !== pairEpoch) return;
        pairing = false;
        if (state) state.pairing = false;
        if (r.returnValue !== true || r.paired !== true) {
          notice = error(r);
          retryPair = true;
          render();
          focus('retry');
          return;
        }
        notice = '';
        goHome(false);
      },
      80000
    );
  }
  function cancel() {
    if (!pairing && !(state && state.pairing)) return;
    var epoch = ++pairEpoch;
    call('cancelPair', {}, function (r) {
      if (epoch !== pairEpoch) return;
      pairing = false;
      retryPair = false;
      if (state) state.pairing = false;
      notice = r.returnValue === true ? 'cancelled' : error(r);
      refresh(true);
    });
  }
  function startup(enable) {
    if (
      !state ||
      (enable &&
        (changingStartup || !state.storageReady || pairing || state.pairing))
    )
      return;
    if (!enable && changingStartup === 'disable') return;
    var epoch = ++startupEpoch;
    stateEpoch++;
    checking = false;
    if (!enable) {
      pairEpoch++;
      pairing = false;
    }
    clearTimeout(pollTimer);
    changingStartup = enable ? 'enable' : 'disable';
    notice = '';
    render();
    call(
      enable ? 'enable' : 'disable',
      enable ? { confirm: true } : {},
      function (r) {
        if (epoch !== startupEpoch) return;
        changingStartup = '';
        if (r.returnValue !== true) notice = error(r);
        else pollUntil = Date.now() + 45000;
        refresh(false);
      }
    );
  }
  el('back').onclick = function () {
    goHome(repairRequested || !allowed() || !state.paired);
  };
  el('later').onclick = function () {
    goHome(true);
  };
  el('pair').onclick =
    el('pairAgain').onclick =
    el('retry').onclick =
      startPair;
  el('cancelPair').onclick = cancel;
  el('probe').onclick = checkStorage;
  el('enableStartup').onclick = function () {
    startup(true);
  };
  el('stop').onclick = function () {
    startup(false);
  };
  [
    'back',
    'pair',
    'later',
    'cancelPair',
    'pairAgain',
    'retry',
    'probe',
    'enableStartup',
    'stop'
  ].forEach(function (id) {
    label(id);
  });
  label('startupHeading', 'startup');
  document.addEventListener('keydown', function (e) {
    var key = e.keyCode,
      active = document.activeElement;
    if (key === 27 || key === 461) {
      if (pairing || (state && state.pairing)) cancel();
      else if (settings) goHome(repairRequested || !allowed() || !state.paired);
      else return;
      e.preventDefault();
      return;
    }
    if (key === 13) {
      if (visible(active) && active.tagName === 'BUTTON') {
        e.preventDefault();
        if (!e.repeat) active.click();
      }
      return;
    }
    if ([37, 38, 39, 40].indexOf(key) < 0) return;
    var all = Array.prototype.filter.call(
      document.querySelectorAll('button'),
      visible
    );
    if (!all.length) return;
    e.preventDefault();
    if (all.indexOf(active) < 0) {
      all[0].focus();
      return;
    }
    var r = active.getBoundingClientRect(),
      h = key === 37 || key === 39,
      dir = key === 37 || key === 38 ? -1 : 1,
      best = null,
      distance = Infinity;
    all.forEach(function (b) {
      if (b === active) return;
      var t = b.getBoundingClientRect();
      var along = h
        ? ((t.left + t.right - r.left - r.right) * dir) / 2
        : ((t.top + t.bottom - r.top - r.bottom) * dir) / 2;
      var across = h
        ? Math.abs(t.top + t.bottom - r.top - r.bottom) / 2
        : Math.abs(t.left + t.right - r.left - r.right) / 2;
      if (along < 1) return;
      var score = along + across * 3;
      if (score < distance) {
        best = b;
        distance = score;
      }
    });
    if (best) best.focus();
  });
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) clearTimeout(pollTimer);
    else if (!pairing && !changingStartup) refresh(false);
  });
  document.addEventListener('webOSRelaunch', function () {
    if (!pairing && !changingStartup) refresh(false);
  });
  refresh(true);
})();
