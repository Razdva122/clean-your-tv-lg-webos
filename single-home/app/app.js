(function () {
  'use strict';
  var service = 'luna://io.github.razdva122.cytvhomepilot.service/';
  var appId = 'io.github.razdva122.cytvhomepilot';
  var ru = !/^en(?:-|$)/i.test(navigator.language || 'ru');
  var words = {
    home: ['Главный экран', 'Home'],
    settings: ['Настройки', 'Settings'],
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
    loadingApps: ['Получаем приложения…', 'Reading installed apps…'],
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
    apps: ['Приложения', 'Apps'],
    editLayout: ['Изменить список', 'Edit app list'],
    done: ['Готово', 'Done'],
    editHint: [
      'Выберите плитку, чтобы скрыть её с главного экрана.',
      'Select an app to hide its tile from Home.'
    ],
    empty: [
      'На главном экране пока нет приложений.',
      'There are no apps on Home yet.'
    ],
    restoreApps: [
      'Показать все установленные приложения',
      'Show all installed apps on Home'
    ],
    retryCatalog: ['Обновить список приложений', 'Refresh app list'],
    noApps: [
      'Телевизор вернул пустой список приложений.',
      'The TV returned an empty app list.'
    ],
    saveError: [
      'Не удалось сохранить выбор плиток.',
      'Could not save the selected tiles.'
    ],
    launchError: ['Не удалось открыть приложение.', 'Could not open the app.'],
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
      'Телевизор отклонил сохранённое сопряжение. В настройках выберите «Сопрячь заново» и подтвердите запрос.',
      'The TV rejected the saved pairing. Open Settings, select Pair again and approve the new request.'
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
  var state = null,
    page = 'home',
    editing = false,
    deferred = false;
  var pairing = false,
    changingStartup = '',
    checking = false,
    reading = false,
    retryPair = false;
  var stateEpoch = 0,
    pairEpoch = 0,
    startupEpoch = 0,
    catalogEpoch = 0,
    pollTimer,
    pollUntil = 0;
  var apps = [],
    selection = null,
    notice = '',
    failedCatalog = false;
  var layoutKey = 'pilot.home.layout.v1';
  try {
    var raw = localStorage.getItem(layoutKey);
    if (raw !== null) {
      var saved = JSON.parse(raw);
      selection = Array.isArray(saved) && saved.every(validId) ? saved : [];
    }
    deferred = localStorage.getItem('pilot.home.later') === '1';
  } catch (_) {
    selection = [];
    notice = 'saveError';
  }
  function validId(id) {
    return (
      typeof id === 'string' &&
      id.length <= 256 &&
      /^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$/.test(id) &&
      id !== appId
    );
  }
  function save(ids) {
    var text = JSON.stringify(ids);
    try {
      localStorage.setItem(layoutKey, text);
      if (localStorage.getItem(layoutKey) !== text) throw Error();
      selection = ids;
      return true;
    } catch (_) {
      notice = 'saveError';
      return false;
    }
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
    var settings = page === 'settings',
      paired = !!(state && state.paired),
      active = pairing || !!(state && state.pairing);
    var onboarding = !settings && !paired && !deferred;
    document.documentElement.lang = ru ? 'ru' : 'en';
    label('title', settings ? 'settings' : 'home');
    label('settings', settings ? 'back' : 'settings');
    el('notice').textContent = notice ? t(notice) : '';
    show('pairArea', settings || onboarding || active);
    label('pairHeading', paired ? 'paired' : 'connect');
    label('pairStatus', active ? 'waiting' : paired ? 'pairedInfo' : 'first');
    show('pair', !paired && !active && !retryPair);
    el('pair').disabled = !allowed() || checking;
    show('pairAgain', paired && !active && !retryPair);
    el('pairAgain').disabled = !allowed() || checking;
    show('retry', retryPair && !active && allowed());
    show('cancelPair', active);
    show('later', onboarding && !active);
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
    show('libraryArea', !settings && !onboarding);
    show(
      'libraryActions',
      paired && (settings || failedCatalog || !el('appGrid').children.length)
    );
    show('restoreApps', paired && !failedCatalog);
    el('restoreApps').disabled = reading;
    show('retryCatalog', paired);
    el('retryCatalog').disabled = reading;
    show(
      'editLayout',
      paired && (editing || el('appGrid').children.length > 0)
    );
    label('editLayout', editing ? 'done' : 'editLayout');
    el('gridHint').textContent = editing
      ? t('editHint')
      : reading
        ? t('loadingApps')
        : !el('appGrid').children.length
          ? t(paired && !apps.length && !failedCatalog ? 'noApps' : 'empty')
          : '';
    document.body.setAttribute('data-paired', String(paired));
    document.body.setAttribute(
      'data-startup',
      state ? state.startup : 'unknown'
    );
  }
  function drawGrid() {
    var grid = el('appGrid'),
      active = document.activeElement;
    var wasTile = grid.contains(active),
      focusedIndex = Array.prototype.indexOf.call(grid.children, active);
    var map = Object.create(null);
    apps.forEach(function (a) {
      map[a.id] = a;
    });
    var ids =
      selection === null
        ? apps.map(function (a) {
            return a.id;
          })
        : selection;
    grid.textContent = '';
    ids.forEach(function (id) {
      if (!map[id]) return;
      var tile = document.createElement('button');
      tile.setAttribute('data-app-id', id);
      tile.textContent = map[id].title;
      tile.onclick = function () {
        if (editing) {
          if (
            save(
              ids.filter(function (item) {
                return item !== id;
              })
            )
          )
            drawGrid();
          render();
          return;
        }
        rpc(
          'luna://com.webos.applicationManager/launch',
          { id: id },
          function (r) {
            if (r.returnValue !== true) {
              notice = 'launchError';
              render();
            }
          }
        );
      };
      grid.appendChild(tile);
    });
    if (wasTile) {
      var next =
        grid.children[Math.min(focusedIndex, grid.children.length - 1)];
      if (next) next.focus();
      else focus('editLayout');
    }
  }
  function readCatalog(restore) {
    if (!state || !state.paired) return;
    var epoch = ++catalogEpoch;
    reading = true;
    render();
    call(
      'catalog',
      {},
      function (r) {
        if (epoch !== catalogEpoch) return;
        reading = false;
        if (
          r.returnValue !== true ||
          !Array.isArray(r.apps) ||
          r.apps.length > 300
        ) {
          failedCatalog = true;
          notice = r.returnValue === true ? 'invalid-inventory' : error(r);
          render();
          return;
        }
        var seen = Object.create(null),
          next = [];
        for (var i = 0; i < r.apps.length; i++) {
          var a = r.apps[i];
          if (
            !a ||
            typeof a.title !== 'string' ||
            !a.title ||
            a.title.length > 256 ||
            typeof a.id !== 'string'
          ) {
            failedCatalog = true;
            notice = 'invalid-inventory';
            render();
            return;
          }
          if (validId(a.id) && !seen[a.id]) {
            seen[a.id] = true;
            next.push({ id: a.id, title: a.title });
          }
        }
        apps = next;
        failedCatalog = false;
        notice = '';
        if (apps.length && (selection === null || restore))
          save(
            apps.map(function (a) {
              return a.id;
            })
          );
        if (restore) {
          page = 'home';
          editing = false;
        }
        drawGrid();
        render();
        if (
          page === 'home' &&
          el('appGrid').children.length &&
          (restore || document.activeElement === document.body)
        )
          el('appGrid').children[0].focus();
      },
      16000
    );
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
  function refresh(loadGrid, target) {
    var epoch = ++stateEpoch,
      wasPaired = !!(state && state.paired);
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
      if (!state.paired) {
        catalogEpoch++;
        reading = false;
        failedCatalog = false;
        apps = [];
        drawGrid();
      }
      if (state.startup !== 'pending' && !state.pairing) pollUntil = 0;
      render();
      poll();
      if (state.paired && (loadGrid || !wasPaired)) readCatalog(false);
      if (target) {
        if (page === 'settings') focus('settings');
        else if (visible(el('pair'))) focus('pair');
        else if (visible(el('probe'))) focus('probe');
        else if (!el('appGrid').children.length) focus('settings');
      }
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
      refresh(false, true);
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
        page = 'home';
        editing = false;
        deferred = true;
        notice = '';
        refresh(true);
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
      refresh(false);
      render();
      focus('pair');
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
  el('settings').onclick = function () {
    page = page === 'settings' ? 'home' : 'settings';
    editing = false;
    render();
    focus('settings');
  };
  el('later').onclick = function () {
    deferred = true;
    try {
      localStorage.setItem('pilot.home.later', '1');
    } catch (_) {}
    render();
    focus('settings');
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
  el('editLayout').onclick = function () {
    editing = !editing;
    render();
    var first = el('appGrid').children[0];
    if (editing && first) first.focus();
    else focus('settings');
  };
  el('restoreApps').onclick = function () {
    readCatalog(true);
  };
  el('retryCatalog').onclick = function () {
    readCatalog(false);
  };
  var captions = [
    'pair',
    'later',
    'cancelPair',
    'pairAgain',
    'retry',
    'probe',
    'enableStartup',
    'stop',
    'restoreApps',
    'retryCatalog'
  ];
  captions.forEach(function (id) {
    label(id);
  });
  label('libraryHeading', 'apps');
  label('startupHeading', 'startup');
  function clock() {
    var d = new Date();
    el('clock').textContent =
      ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
  }
  clock();
  setInterval(clock, 30000);
  document.addEventListener('keydown', function (e) {
    var key = e.keyCode,
      active = document.activeElement;
    if (key === 27 || key === 461) {
      if (editing) {
        editing = false;
        render();
        focus('editLayout');
      } else if (page === 'settings') {
        page = 'home';
        render();
        focus('settings');
      } else if (pairing || (state && state.pairing)) {
        cancel();
      } else return;
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
    else if (!pairing && !changingStartup) refresh(true);
  });
  document.addEventListener('webOSRelaunch', function () {
    if (!pairing && !changingStartup) refresh(true);
  });
  refresh(true, true);
})();
