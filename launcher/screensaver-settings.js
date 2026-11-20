/* Shared settings and local Home-only inactivity. Edition services own authority. */
(function (root) {
  'use strict';
  var doc = root.document;
  var config = root.CYTVScreensaverSettings;
  if (!config) return;
  var state = config.normalize();
  var known = false;
  var available = false;
  var busy = false;
  var requestEpoch = 0;
  var statusPending = false;
  var statusRetry = null;
  var statusRetries = 0;
  var helperStarting = false;
  var helperStopped = false;
  var statusUnconfirmed = false;
  var helperLaunchFailed = false;
  var host = null;
  var started = false;
  var localFocused = true;
  var contextActive = false;
  var stopped = false;
  var handoff = null;
  var actionPending = null;
  var activityTimer = null;
  var activityBusy = false;
  var activityAcknowledged = null;
  var idle = null;
  var idleDelay = null;
  var pendingOffer = null;
  var handoffTimer = null;
  var observer = null;
  var activeMedia = null;
  var pendingMedia = null;
  var wallpaperHeld = null;
  var mediaRelease = Promise.resolve();
  var settingsActive = false;
  var mediaPreview = null;
  var mediaPreviewKey = '';
  var mediaPreviewEpoch = 0;
  var qualitySummary;
  var clearGalleryFocus;
  var selectGallery;
  var receiver = null;
  var receiverSignal = null;
  var receiverTimer = null;
  var receiverEpoch = 0;
  var clockPreferencesReady = false;
  var clockSyncQueued = false;
  var delays = [30000, 60000, 300000, 900000, 1800000];

  if (root.HomeI18n && root.HomeI18n.add)
    root.HomeI18n.add({
      ru: {
        'Screensaver': 'Заставка',
        'Full screen': 'На весь экран',
        'Built-in backgrounds': 'Встроенные фоны',
        'Saved media': 'Общая медиатека',
        'Background quality': 'Качество фона',
        'Video': 'Видео',
        'Enable screensaver': 'Включить заставку',
        'On': 'Вкл.',
        'Off': 'Выкл.',
        'Personal backgrounds appear only on CYTV Home.':
          'Личные фоны показываются только на главном экране CYTV.',
        'Turn on the screensaver to edit its settings.':
          'Включите заставку, чтобы изменить её настройки.',
        'Show clock': 'Показывать часы',
        'Show clock and date': 'Показывать часы и дату',
        'Use the standard screensaver': 'Выбрать стандартную заставку',
        'Preview screensaver': 'Предпросмотр',
        'Start on Home after': 'Запуск на Home через',
        'Background': 'Фон',
        'Clock': 'Часы',
        'Ambient glow': 'Мягкое свечение',
        'Photo': 'Фото',
        '4K video': 'Видео 4K',
        'Scene': 'Сюжет',
        'My photo': 'Моё фото',
        'My video': 'Моё видео',
        'Add photo': 'Добавить фото',
        'Replace photo': 'Заменить фото',
        'Add video': 'Добавить видео',
        'Replace video': 'Заменить видео',
        'Send a prepared photo or video from Clean Your TV on your computer.':
          'Отправьте подготовленное фото или видео из Clean Your TV на компьютере.',
        'Waiting for upload…': 'Ожидание загрузки…',
        'Cancel import': 'Отменить загрузку',
        'Could not import screensaver media.':
          'Не удалось загрузить фон заставки.',
        'Alpine lake': 'Альпийское озеро',
        'Alpine lake (still)': 'Альпийское озеро (статично)',
        'Ribbon': 'Лента',
        '30 seconds': '30 секунд',
        '30 sec': '30 сек.',
        '1 minute': '1 минута',
        '5 minutes': '5 минут',
        '15 minutes': '15 минут',
        '30 minutes': '30 минут',
        '1 min': '1 мин.',
        '5 min': '5 мин.',
        '15 min': '15 мин.',
        '30 min': '30 мин.',
        'Checking screensaver availability…': 'Проверка доступности заставки…',
        'Screensaver is unavailable on this TV.':
          'Заставка недоступна на этом телевизоре.',
        'Could not save screensaver settings.':
          'Не удалось сохранить настройки заставки.',
        'Screensaver preview is unavailable right now.':
          'Предпросмотр заставки сейчас недоступен.'
      }
    });
  function t(value) {
    return root.HomeI18n ? root.HomeI18n.t(value) : value;
  }
  function now() {
    return root.performance.now();
  }
  function rootEdition() {
    return (
      root.ROOT_VERSION || doc.querySelector('script[src="root-settings.js"]')
    );
  }
  function service() {
    return (
      'luna://' +
      (rootEdition()
        ? 'com.cleanyourtv.root.preview.service'
        : 'com.gathin.tvhome.renewal') +
      '/'
    );
  }
  function rpc(method, payload, callback) {
    var deadline = now() + 5000;
    function request() {
      var bridge,
        done = false;
      var timer = root.setTimeout(
        function () {
          finish(null);
        },
        Math.max(0, deadline - now())
      );
      function finish(reply) {
        if (done) return;
        done = true;
        root.clearTimeout(timer);
        if (bridge)
          try {
            bridge.cancel();
          } catch (_) {}
        var channelBusy = !!(
          reply &&
          reply.returnValue === false &&
          reply.errorText === 'Home control busy'
        );
        // BUSY is returned before the Helper channel accepts the request.
        // An unanswered request may already have reached the Helper.
        if (
          channelBusy &&
          (method === 'screensaverStatus' ||
            method === 'screensaverConfigure') &&
          now() + 200 < deadline
        ) {
          root.setTimeout(request, 200);
          return;
        }
        callback(
          reply && reply.returnValue === true ? reply : null,
          channelBusy
        );
      }
      try {
        bridge = new root.PalmServiceBridge();
        bridge.onservicecallback = function (raw) {
          try {
            if (typeof raw !== 'string' || raw.length > 16384)
              return finish(null);
            finish(JSON.parse(raw));
          } catch (_) {
            finish(null);
          }
        };
        bridge.call(service() + method, JSON.stringify(payload || {}));
      } catch (_) {
        finish(null);
      }
    }
    request();
  }
  function supportedChoice() {
    return (
      state.mode === 'ambient' ||
      state.mode === 'clock' ||
      !!config.background(state.mode, state.assetId) ||
      (config.personal(state.mode, state.assetId) && personal()[state.mode])
    );
  }
  function personal() {
    return root.ScreensaverPersonal ? root.ScreensaverPersonal.state() : {};
  }
  function clearMediaPreview() {
    mediaPreviewEpoch++;
    if (mediaPreview && mediaPreview.url)
      root.URL.revokeObjectURL(mediaPreview.url);
    mediaPreview = null;
    mediaPreviewKey = '';
  }
  function refreshMediaPreview() {
    var key =
      settingsActive && state.assetId === 'personal-' + state.mode
        ? state.assetId
        : '';
    if (key === mediaPreviewKey) return;
    clearMediaPreview();
    if (!key || !root.ScreensaverPersonal || !root.ScreensaverPersonal.preview)
      return;
    mediaPreviewKey = key;
    var epoch = mediaPreviewEpoch;
    root.ScreensaverPersonal.preview(state.mode).then(
      function (value) {
        if (epoch !== mediaPreviewEpoch) {
          if (value) root.URL.revokeObjectURL(value.url);
          return;
        }
        mediaPreview = value;
        renderQuality();
      },
      function () {}
    );
  }
  function wallpaperUhd() {
    var wallpaper =
      root.HomeWallpaper &&
      root.HomeWallpaper.state &&
      root.HomeWallpaper.state();
    return wallpaper && wallpaper.capabilities && wallpaper.capabilities.uhd;
  }
  function renderQuality() {
    if (!qualitySummary) return;
    refreshMediaPreview();
    var asset = config.background(state.mode, state.assetId);
    var media = mediaPreview;
    var personal = state.assetId === 'personal-' + state.mode;
    var url = asset
      ? 'wallpapers/' + asset.id.split('-')[0] + '-preview.jpg'
      : media && media.url;
    var qualities =
      asset && asset.mode === 'video'
        ? ['4k', '1080p']
        : media
          ? media.qualities
          : [];
    var portrait = qualitySummary.image;
    if (url) {
      if (portrait.getAttribute('src') !== url) portrait.src = url;
    } else portrait.removeAttribute('src');
    portrait.hidden = !url;
    var ambient = state.mode === 'ambient';
    qualitySummary.clock.hidden = !ambient && state.mode !== 'clock';
    qualitySummary.clock.classList.toggle('screensaver-glow', ambient);
    var showClock = state.mode === 'clock' || (ambient && state.clockOverlay);
    qualitySummary.time.hidden = !showClock;
    qualitySummary.date.hidden = !showClock || !ambient;
    if (showClock) {
      var time = new Date();
      var locale = root.HomeI18n;
      qualitySummary.time.textContent =
        locale && locale.formatTime
          ? locale.formatTime(time)
          : ('0' + time.getHours()).slice(-2) +
            ':' +
            ('0' + time.getMinutes()).slice(-2);
      if (ambient)
        qualitySummary.date.textContent =
          locale && locale.formatDate
            ? locale.formatDate(time)
            : time.toLocaleDateString(doc.documentElement.lang || undefined, {
                weekday: 'long',
                month: 'long',
                day: 'numeric'
              });
    }
    qualitySummary.heading.textContent = t(
      asset
        ? asset.label
        : personal
          ? state.mode === 'video'
            ? 'My video'
            : 'My photo'
          : ambient
            ? 'Ambient glow'
            : 'Clock'
    );
    if (root.HomeWallpaperPanel) {
      root.HomeWallpaperPanel.renderBadges(
        qualitySummary.badges,
        (asset || personal) && state.mode,
        qualities,
        asset ? 3840 : media && media.width,
        asset ? 2160 : media && media.height
      );
    }
    qualitySummary.controls.hidden = ambient || state.mode === 'clock';
    var uhd = wallpaperUhd();
    qualitySummary.buttons.forEach(function (choice, i) {
      var quality = config.qualities[i];
      choice.disabled =
        !canEdit() ||
        !url ||
        (quality === '4k' && uhd === false) ||
        (quality !== 'auto' &&
          quality !== 'image' &&
          qualities.indexOf(quality) < 0);
      if (quality === 'image')
        choice.textContent =
          state.mode === 'video' && root.HomeWallpaperPanel
            ? root.HomeWallpaperPanel.t('Still frame')
            : root.HomeWallpaperPanel
              ? root.HomeWallpaperPanel.qualityLabel(quality)
              : t('Image');
      choice.setAttribute('aria-pressed', String(state.quality === quality));
    });
  }
  function refreshMedia() {
    if (!root.ScreensaverPersonal) return;
    root.ScreensaverPersonal.start().then(
      function () {
        render();
        if (settingsActive && host && root.HomeWallpaperPanel) {
          ['photo', 'video'].forEach(function (mode) {
            var card = host.querySelector('#screensaverPersonal-' + mode);
            if (personal()[mode])
              root.HomeWallpaperPanel.savedCard(
                card,
                t(mode === 'photo' ? 'My photo' : 'My video'),
                mode
              );
            else root.HomeWallpaperPanel.releaseCard(card);
          });
        }
        tick();
      },
      function () {}
    );
  }
  function releaseMedia() {
    var old = activeMedia,
      pending = pendingMedia,
      wallpaper = wallpaperHeld;
    activeMedia = null;
    pendingMedia = null;
    wallpaperHeld = null;
    mediaRelease = mediaRelease
      .catch(function () {})
      .then(function () {
        return pending
          ? pending.then(
              function (lease) {
                return lease ? lease.dispose() : null;
              },
              function () {}
            )
          : null;
      })
      .catch(function () {})
      .then(function () {
        return old ? old.dispose() : null;
      })
      .catch(function () {})
      .then(function () {
        if (!wallpaper) return;
        return Promise.resolve(wallpaper.release)
          .catch(function () {})
          .then(function () {
            wallpaper.owner.resume('screensaver');
          });
      })
      .catch(function () {});
    return mediaRelease;
  }
  function canSuspendWallpaper() {
    return (
      root.HomeWallpaper &&
      typeof root.HomeWallpaper.suspend === 'function' &&
      typeof root.HomeWallpaper.resume === 'function'
    );
  }
  function canEdit() {
    return known && available && state.enabled;
  }
  function running() {
    return canEdit() && supportedChoice();
  }
  function status(message) {
    if (host)
      host.querySelector('.screensaver-status').textContent = t(message);
  }
  function render() {
    if (!host) return;
    var focused = doc.activeElement;
    var enabled = host.querySelector('#screensaverEnabled');
    var editable = canEdit();
    var startHelper = host.querySelector('#screensaverStartHelper');
    var retry = host.querySelector('#screensaverStatusRetry');
    startHelper.hidden =
      rootEdition() ||
      available ||
      !(
        helperStopped === true ||
        (statusUnconfirmed && helperStopped === null)
      );
    startHelper.disabled = startHelper.hidden || helperStarting;
    retry.hidden =
      rootEdition() ||
      !statusUnconfirmed ||
      available ||
      helperStopped ||
      helperStarting;
    retry.disabled = retry.hidden;
    retry.parentNode.hidden = startHelper.hidden && retry.hidden;
    enabled.setAttribute('aria-checked', String(state.enabled));
    enabled.textContent =
      t('Screensaver') + ': ' + t(state.enabled ? 'On' : 'Off');
    enabled.disabled = !known || !available;
    var ownMedia = config.personal(state.mode, state.assetId);
    host.querySelector('#screensaverPersonalHint').hidden =
      !editable || !ownMedia;
    if (!editable && receiverSignal) stopReceiver();
    var libraryControls = host.querySelectorAll(
      '[data-background-tab],[data-background-upload],#screensaverReceiverCancel'
    );
    for (var b = 0; b < libraryControls.length; b++)
      libraryControls[b].disabled = !editable;
    var overlay = host.querySelector('#screensaverClockOverlay');
    overlay.textContent = t(
      state.mode === 'ambient' ? 'Show clock and date' : 'Show clock'
    );
    overlay.setAttribute(
      'aria-checked',
      String(state.mode === 'clock' || state.clockOverlay)
    );
    overlay.disabled = !editable;
    var defaults = host.querySelector('#screensaverLocal');
    defaults.hidden = supportedChoice();
    defaults.disabled = !editable;
    var formats = host.querySelector('.background-formats');
    formats.hidden = !config.background(state.mode, state.assetId);
    var modes = formats.querySelectorAll('[data-background-mode]');
    for (var j = 0; j < modes.length; j++) {
      modes[j].setAttribute(
        'aria-pressed',
        String(modes[j].getAttribute('data-background-mode') === state.mode)
      );
      modes[j].disabled = !editable;
    }
    var scenes = host.querySelectorAll('[data-background-scene]');
    for (var k = 0; k < scenes.length; k++) {
      scenes[k].disabled = !editable;
      scenes[k].setAttribute(
        'aria-pressed',
        String(
          scenes[k].getAttribute('data-background-scene') ===
            state.assetId.split('-')[0]
        )
      );
    }
    host.querySelector('#screensaverAmbientCard').disabled = !editable;
    host
      .querySelector('#screensaverAmbientCard')
      .setAttribute('aria-pressed', String(state.mode === 'ambient'));
    host.querySelector('#screensaverSavedEmpty').hidden = !!(
      personal().photo || personal().video
    );
    ['photo', 'video'].forEach(function (mode) {
      var choice = host.querySelector('#screensaverPersonal-' + mode);
      choice.hidden = !personal()[mode];
      choice.disabled = !editable;
      choice.setAttribute(
        'aria-pressed',
        String(state.assetId === 'personal-' + mode)
      );
      var add = host.querySelector('#screensaverImport-' + mode);
      add.textContent = t((personal()[mode] ? 'Replace ' : 'Add ') + mode);
      add.disabled =
        !editable || !root.ScreensaverPersonal || !root.ThemeReceiver;
    });
    host.querySelector('#screensaverDelay').textContent =
      t('Start on Home after') +
      (delays.indexOf(state.idleTimeoutMs) < 0
        ? ' · ' + Math.round(state.idleTimeoutMs / 1000) + ' s'
        : '');
    var choices = host.querySelectorAll('[data-screensaver-delay]');
    for (var i = 0; i < choices.length; i++) {
      choices[i].setAttribute(
        'aria-pressed',
        String(state.idleTimeoutMs === delays[i])
      );
      choices[i].disabled = !editable;
    }
    renderQuality();
    host.querySelector('#screensaverPreview').disabled = busy || !running();
    host.setAttribute('aria-busy', String(busy));
    status(
      !known
        ? 'Checking screensaver availability…'
        : !available
          ? helperStarting
            ? 'Starting Helper…'
            : helperLaunchFailed
              ? 'Could not start Home Helper.'
              : helperStopped
                ? 'Home Helper is stopped.'
                : statusUnconfirmed && !rootEdition()
                  ? 'Could not check screensaver availability.'
                  : 'Screensaver is unavailable on this TV.'
          : !state.enabled
            ? 'Turn on the screensaver to edit its settings.'
            : ''
    );
    if (
      settingsActive &&
      host.contains(focused) &&
      (focused.disabled || focused.hidden)
    ) {
      if (clearGalleryFocus) clearGalleryFocus();
      if (!enabled.disabled) enabled.focus();
      else if (!startHelper.hidden && !startHelper.disabled)
        startHelper.focus();
      else if (!retry.hidden) retry.focus();
      else host.querySelector('.screensaver-status').focus();
    }
  }
  function accepted(reply) {
    if (
      !reply ||
      typeof reply.available !== 'boolean' ||
      !reply.state ||
      typeof reply.state !== 'object' ||
      Array.isArray(reply.state)
    )
      return false;
    state = config.normalize(reply.state);
    known = true;
    available = reply.available;
    return true;
  }
  function retryStatus(recheck) {
    if (
      (!rootEdition() && !helperStarting) ||
      !settingsActive ||
      statusRetry !== null ||
      statusRetries >= 3 ||
      doc.hidden ||
      !visible(host)
    )
      return;
    statusRetries++;
    statusRetry = root.setTimeout(function () {
      statusRetry = null;
      if (
        settingsActive &&
        (recheck || !available) &&
        !doc.hidden &&
        visible(host)
      )
        refresh();
    }, 1000);
  }
  function refresh() {
    if (busy || statusPending) return;
    var epoch = ++requestEpoch;
    statusPending = true;
    rpc('screensaverStatus', {}, function (reply, channelBusy) {
      statusPending = false;
      if (epoch !== requestEpoch) return;
      statusUnconfirmed = !accepted(reply);
      if (statusUnconfirmed) {
        if (channelBusy && known && !helperStarting) return;
        known = true;
        available = false;
      }
      if (available) {
        statusRetries = 0;
        helperStarting = helperStopped = helperLaunchFailed = false;
      } else {
        retryStatus();
        if (helperStarting && statusRetry === null) helperStarting = false;
        if (
          !rootEdition() &&
          !helperStarting &&
          settingsActive &&
          root.HomeHelper
        ) {
          root.HomeHelper.checkStopped(function (stopped) {
            if (epoch !== requestEpoch || !settingsActive) return;
            helperStopped = stopped;
            render();
          });
        }
      }
      render();
      tick();
      syncClock();
    });
  }
  function clockPresentation() {
    var locale = root.HomeI18n;
    return clockPreferencesReady && locale && locale.clockPresentation
      ? locale.clockPresentation()
      : null;
  }
  function syncClock() {
    var clock = clockPresentation();
    if (!clock || !known || !available) return;
    // Configuring the clock would stop a preview or idle activation in progress.
    if (busy || handoff || statusPending) {
      clockSyncQueued = true;
      return;
    }
    clockSyncQueued = false;
    if (
      state.clock &&
      state.clock.locale === clock.locale &&
      state.clock.hour12 === clock.hour12
    )
      return;
    configure({}, true);
  }
  function configure(changes, clockSync) {
    if (
      busy ||
      !known ||
      !available ||
      (!clockSync && !canEdit() && typeof changes.enabled !== 'boolean')
    )
      return;
    var desired = config.normalize(state);
    Object.keys(changes).forEach(function (key) {
      desired[key] = changes[key];
    });
    desired = config.normalize(desired);
    var clock = clockPresentation();
    if (clock) desired.clock = clock;
    var epoch = ++requestEpoch;
    busy = true;
    render();
    rpc('screensaverConfigure', desired, function (reply) {
      if (epoch !== requestEpoch) return;
      busy = false;
      var ok = accepted(reply);
      render();
      if (!ok && !clockSync) status('Could not save screensaver settings.');
      if (!ok || !available) retryStatus(true);
      contextActive = false;
      releaseMedia();
      handoff = null;
      actionPending = null;
      if (idle) idle.destroy();
      idle = null;
      tick();
    });
  }
  function visible(element) {
    return !!element && element.getClientRects().length > 0;
  }
  function localContext(allowSettings) {
    if (
      !started ||
      doc.hidden ||
      !localFocused ||
      !doc.hasFocus() ||
      doc.body.classList.contains('editing')
    )
      return false;
    var dialogs = doc.querySelectorAll('[role="dialog"],[role="alertdialog"]');
    for (var i = 0; i < dialogs.length; i++) {
      if (!visible(dialogs[i])) continue;
      if (
        allowSettings &&
        (dialogs[i].id === 'renewalPanel' ||
          dialogs[i].classList.contains('root-settings'))
      )
        continue;
      return false;
    }
    var previews = doc.querySelectorAll('.ctv-input-preview,.input-preview');
    for (var j = 0; j < previews.length; j++)
      if (visible(previews[j])) return false;
    // Do not infer paused playback from Home's foreground ID. Until an owned
    // media adapter explicitly grants eligibility, any playing video blocks it.
    var media = doc.querySelectorAll('video,audio');
    for (var k = 0; k < media.length; k++)
      if (
        !media[k].paused &&
        !media[k].ended &&
        !(media[k].id === 'ctvWallpaperVideo' && canSuspendWallpaper())
      )
        return false;
    return true;
  }
  function stopLocal() {
    contextActive = false;
    root.clearTimeout(activityTimer);
    activityTimer = null;
    root.clearTimeout(pendingOffer);
    pendingOffer = null;
    activityAcknowledged = null;
    if (stopped || handoff || !known || !state.enabled) return;
    stopped = true;
    releaseMedia();
    if (state.scope !== 'global') rpc('screensaverStop', {}, function () {});
  }
  function activity() {
    if (!running() || !localContext(false) || handoff) return;
    stopped = false;
    activityAcknowledged = null;
    root.clearTimeout(pendingOffer);
    pendingOffer = null;
    if (activityTimer !== null || activityBusy) return;
    activityTimer = root.setTimeout(function () {
      activityTimer = null;
      if (!idle || !running() || !localContext(false) || handoff) return;
      var current = idle,
        epoch = current.status().epoch;
      activityBusy = true;
      rpc('screensaverActivity', {}, function (reply) {
        activityBusy = false;
        if (idle !== current || !running() || !localContext(false) || handoff)
          return;
        if (current.status().epoch !== epoch) return activity();
        if (reply) activityAcknowledged = now();
      });
    }, 100);
  }
  function becameIdle(event) {
    if (!idle || activityAcknowledged === null) return;
    var current = idle;
    // The service measures idle from receipt. Start only after a complete
    // interval since its last acknowledgement, including transport latency.
    var wait =
      Math.max(0, activityAcknowledged + state.idleTimeoutMs - now()) + 20;
    pendingOffer = root.setTimeout(function () {
      pendingOffer = null;
      if (idle === current && current.status().epoch === event.epoch)
        offer(false);
    }, wait);
  }
  function activationSettings() {
    var settings = Object.assign({}, state);
    delete settings.clock;
    return JSON.stringify(settings);
  }
  function offer(preview) {
    if (actionPending || handoff || !running() || !localContext(preview))
      return;
    var attempt = {
        config: activationSettings(),
        preparing: true,
        preview: preview
      },
      selected = state.mode;
    handoff = attempt;
    actionPending = attempt;
    function current() {
      return handoff === attempt;
    }
    function failed() {
      if (!current()) return;
      handoff = null;
      actionPending = null;
      root.clearTimeout(handoffTimer);
      releaseMedia();
      if (preview) status('Screensaver preview is unavailable right now.');
    }
    function expired() {
      if (!current() || !localContext(preview)) return;
      failed();
      stopped = true;
      rpc('screensaverStop', {}, function () {});
    }
    root.clearTimeout(handoffTimer);
    handoffTimer = root.setTimeout(expired, 120000);
    var prepare = mediaRelease
      .then(function () {
        if (!current()) throw Error('Cancelled');
        if (!canSuspendWallpaper()) return;
        wallpaperHeld = { owner: root.HomeWallpaper, release: null };
        wallpaperHeld.release = root.HomeWallpaper.suspend('screensaver');
        return wallpaperHeld.release;
      })
      .then(function () {
        if (!current()) throw Error('Cancelled');
        return state.assetId === 'personal-' + selected
          ? root.ScreensaverPersonal.prepare(
              selected,
              function () {
                return !current();
              },
              state.quality,
              wallpaperUhd()
            )
          : null;
      });
    pendingMedia = prepare;
    prepare.then(
      function (lease) {
        if (pendingMedia === prepare) pendingMedia = null;
        if (
          !current() ||
          !running() ||
          !localContext(preview) ||
          attempt.config !== activationSettings()
        ) {
          if (lease) lease.dispose();
          failed();
          return;
        }
        activeMedia = lease;
        attempt.preparing = false;
        root.clearTimeout(handoffTimer);
        handoffTimer = root.setTimeout(expired, 10000);
        rpc(
          preview ? 'screensaverPreview' : 'screensaverEligible',
          lease ? { mediaUrl: lease.mediaUrl } : {},
          function (reply) {
            if (!current()) return;
            actionPending = null;
            if (!reply || reply.started !== true) failed();
          }
        );
      },
      function () {
        if (pendingMedia === prepare) pendingMedia = null;
        failed();
      }
    );
  }
  function tick() {
    if (!started) return;
    if (clockSyncQueued && !busy && !handoff) syncClock();
    if (receiverSignal && (!settingsActive || !visible(host))) stopReceiver();
    if (!root.CYTVScreensaverIdle) return;
    if (!running()) {
      if (idle) idle.destroy();
      idle = null;
      return stopLocal();
    }
    if (!idle || idleDelay !== state.idleTimeoutMs) {
      if (idle) idle.destroy();
      idleDelay = state.idleTimeoutMs;
      idle = root.CYTVScreensaverIdle({
        window: root,
        document: doc,
        idleMs: idleDelay,
        isEligible: function () {
          return running() && !handoff && localContext(false);
        },
        onActivity: activity,
        onInput: function () {
          if (
            !handoff ||
            !handoff.preparing ||
            handoff.preview ||
            !localContext(false)
          )
            return;
          handoff = null;
          actionPending = null;
          root.clearTimeout(handoffTimer);
          releaseMedia();
        },
        onIdle: becameIdle
      });
      idle.enable();
    }
    if (!localContext(false)) {
      if (contextActive) idle.refresh();
      return stopLocal();
    }
    if (handoff) return;
    if (!contextActive) {
      contextActive = true;
      idle.refresh();
    }
  }
  function focus() {
    localFocused = true;
    releaseMedia();
    handoff = null;
    actionPending = null;
    root.clearTimeout(handoffTimer);
    contextActive = false;
    if (idle) idle.refresh();
    refresh();
  }
  function cancelPreparing() {
    if (!handoff || !handoff.preparing) return;
    handoff = null;
    actionPending = null;
    root.clearTimeout(handoffTimer);
    releaseMedia();
  }
  function start() {
    if (started) return;
    started = true;
    root.addEventListener('blur', function () {
      localFocused = false;
      stopReceiver();
      cancelPreparing();
      stopLocal();
    });
    root.addEventListener('focus', focus);
    doc.addEventListener('visibilitychange', function () {
      if (doc.hidden) {
        stopReceiver();
        cancelPreparing();
        stopLocal();
      } else focus();
    });
    root.addEventListener('pagehide', function () {
      handoff = null;
      clearMediaPreview();
      stopReceiver();
      releaseMedia();
      stopLocal();
      root.clearInterval(observer);
      root.clearTimeout(handoffTimer);
      if (idle) idle.destroy();
      idle = null;
      started = false;
    });
    observer = root.setInterval(tick, 1000);
    var locale = root.HomeI18n;
    function preferencesReady() {
      clockPreferencesReady = true;
      syncClock();
    }
    if (locale && locale.ready) locale.ready(preferencesReady);
    else preferencesReady();
    doc.addEventListener('home-helper-start-requested', function () {
      if (rootEdition() || !settingsActive) return;
      helperStarting = true;
      helperLaunchFailed = false;
      statusRetries = 0;
      refresh();
    });
    doc.addEventListener('home-clock-format-change', function () {
      renderQuality();
      syncClock();
    });
    doc.addEventListener('home-wallpaper-change', refreshMedia);
    doc.addEventListener('home-screensaver-media-change', function () {
      clearMediaPreview();
      refreshMedia();
    });
    refreshMedia();
    refresh();
  }
  function stopReceiver() {
    receiverEpoch++;
    root.clearTimeout(receiverTimer);
    receiverTimer = null;
    if (receiverSignal) receiverSignal.cancelled = true;
    receiverSignal = null;
    var old = receiver;
    receiver = null;
    if (old) root.ThemeReceiver.stop(old.sessionId);
    if (host) {
      host.querySelector('#screensaverReceiver').hidden = true;
      host.querySelector('#screensaverReceiverPin').textContent = '';
      host.querySelector('#screensaverReceiverAddress').textContent = '';
    }
  }
  function receive(mode) {
    if (
      !canEdit() ||
      !settingsActive ||
      !root.ScreensaverPersonal ||
      !root.ThemeReceiver
    )
      return;
    stopReceiver();
    var epoch = receiverEpoch,
      signal = { cancelled: false };
    receiverSignal = signal;
    status('Waiting for upload…');
    function live() {
      return (
        canEdit() &&
        settingsActive &&
        visible(host) &&
        !doc.hidden &&
        !signal.cancelled &&
        epoch === receiverEpoch
      );
    }
    function fail(error) {
      if (!live()) return;
      stopReceiver();
      status(
        error && error.code === 'storage-full'
          ? error.message
          : 'Could not import screensaver media.'
      );
    }
    function poll() {
      if (!live() || !receiver) return;
      if (Date.now() >= receiver.expiresAt) return fail();
      root.ThemeReceiver.status(receiver.sessionId, signal)
        .then(function (reply) {
          if (!live()) return;
          if (reply.state !== 'received') {
            receiverTimer = root.setTimeout(poll, 500);
            return;
          }
          return root.ThemeReceiver.read(receiver.sessionId, reply.size, signal)
            .then(function (envelope) {
              if (!live()) throw Error('Cancelled');
              return root.ScreensaverPersonal.receive(
                mode,
                envelope,
                function () {
                  return !live();
                }
              );
            })
            .then(function () {
              if (!live()) return;
              stopReceiver();
              if (selectGallery) selectGallery(1);
              configure({
                mode: mode,
                assetId: 'personal-' + mode
              });
              render();
            });
        })
        .catch(fail);
    }
    root.ThemeReceiver.start(signal, 'wallpaper').then(function (session) {
      if (!live()) {
        root.ThemeReceiver.stop(session.sessionId);
        return;
      }
      receiver = session;
      host.querySelector('#screensaverReceiver').hidden = false;
      host.querySelector('#screensaverReceiverPin').textContent =
        'PIN: ' + session.pin;
      host.querySelector('#screensaverReceiverAddress').textContent =
        session.addresses.join(' · ');
      poll();
    }, fail);
  }
  function button(parent, id, label) {
    var value = doc.createElement('button');
    value.type = 'button';
    value.id = id;
    value.textContent = t(label);
    parent.appendChild(value);
    return value;
  }
  function mountSettings(panel, card, groups) {
    host = doc.createElement('div');
    host.className = 'screensaver-settings';
    var panelUi = root.HomeWallpaperPanel;
    var header = doc.createElement('div');
    header.className = 'screensaver-header';
    host.appendChild(header);
    var toggle = button(header, 'screensaverEnabled', 'Enable screensaver');
    toggle.setAttribute('role', 'switch');
    toggle.setAttribute('aria-label', t('Screensaver'));
    toggle.onclick = function () {
      configure({ enabled: !state.enabled });
    };
    var overlay = button(header, 'screensaverClockOverlay', 'Show clock');
    overlay.setAttribute('role', 'switch');
    overlay.onclick = function () {
      if (state.mode === 'clock')
        configure({ mode: 'ambient', assetId: '', clockOverlay: false });
      else configure({ clockOverlay: !state.clockOverlay });
    };

    var fallback = button(
      header,
      'screensaverLocal',
      'Use the standard screensaver'
    );
    fallback.onclick = function () {
      configure({ mode: 'ambient', assetId: '' });
    };

    var output = doc.createElement('p');
    output.id = 'screensaverStatus';
    output.className = 'screensaver-status';
    output.setAttribute('role', 'status');
    output.tabIndex = -1;
    toggle.setAttribute('aria-describedby', output.id);
    host.appendChild(output);
    var recovery = doc.createElement('div');
    recovery.className = 'renewal-actions';
    recovery.hidden = true;
    host.appendChild(recovery);
    var startHelper = button(
      recovery,
      'screensaverStartHelper',
      'Start Helper'
    );
    startHelper.onclick = function () {
      root.HomeHelper.confirmStart(
        function () {
          if (!settingsActive || helperStarting) return false;
          helperStarting = true;
          helperLaunchFailed = false;
          render();
        },
        function (accepted) {
          if (accepted) return;
          helperStarting = false;
          helperLaunchFailed = true;
          render();
        }
      );
    };
    var retry = button(recovery, 'screensaverStatusRetry', 'Try again');
    retry.onclick = refresh;

    var layout = panelUi.backgroundLayout(host);
    var options = doc.createElement('div');
    options.className = 'screensaver-options';

    var summary = doc.createElement('div');
    summary.className = 'wallpaper-summary';
    var picture = doc.createElement('img');
    picture.className = 'wallpaper-preview-image';
    picture.alt = '';
    picture.hidden = true;
    summary.appendChild(picture);
    var clock = doc.createElement('div');
    clock.className = 'wallpaper-preview-image screensaver-clock-preview';
    clock.hidden = true;
    var time = doc.createElement('span');
    var date = doc.createElement('span');
    date.className = 'screensaver-preview-date';
    clock.appendChild(time);
    clock.appendChild(date);
    summary.appendChild(clock);
    var info = doc.createElement('div');
    info.className = 'wallpaper-info';
    var heading = doc.createElement('h4');
    var badges = doc.createElement('div');
    badges.className = 'wallpaper-media-badges';
    info.appendChild(heading);
    info.appendChild(badges);
    summary.appendChild(info);
    layout.left.appendChild(summary);
    var qualityControls = doc.createElement('div');
    qualityControls.className = 'wallpaper-quality';
    qualityControls.setAttribute('role', 'group');
    qualityControls.setAttribute('aria-label', t('Background quality'));
    var qualityLabels = ['Auto', '4K', '1080p', 'Image'];
    qualitySummary = {
      image: picture,
      clock: clock,
      time: time,
      date: date,
      heading: heading,
      badges: badges,
      controls: qualityControls,
      buttons: config.qualities.map(function (quality, i) {
        var item = button(
          qualityControls,
          'screensaverQuality-' + quality,
          qualityLabels[i]
        );
        if (root.HomeWallpaperPanel)
          item.textContent = root.HomeWallpaperPanel.qualityLabel(quality);
        item.onclick = function () {
          if (state.quality !== quality) configure({ quality: quality });
        };
        return item;
      })
    };
    layout.left.appendChild(qualityControls);

    var formats = doc.createElement('div');
    formats.className = 'background-formats wallpaper-quality';
    formats.setAttribute('role', 'group');
    formats.setAttribute('aria-label', t('Background'));
    [
      ['photo', 'Photo'],
      ['video', 'Video']
    ].forEach(function (format) {
      var mode = format[0];
      var choice = button(formats, 'screensaverBackground-' + mode, format[1]);
      choice.setAttribute('data-background-mode', mode);
      choice.onclick = function () {
        var next = config.background(
          mode,
          state.assetId.split('-')[0] + '-' + mode
        );
        if (next) configure({ mode: mode, assetId: next.id });
      };
    });
    layout.left.insertBefore(formats, qualityControls);
    var builtinPane = doc.createElement('div');
    var saved = doc.createElement('div');
    saved.id = 'screensaverSaved';
    selectGallery = panelUi.libraryTabs(layout.right, builtinPane, saved);
    var scenes = doc.createElement('div');
    scenes.id = 'screensaverScenes';
    scenes.className = 'wallpaper-media-gallery';
    scenes.setAttribute('role', 'group');
    scenes.setAttribute('aria-label', t('Built-in backgrounds'));
    var ambientCard = button(scenes, 'screensaverAmbientCard', 'Ambient glow');
    panelUi.mediaCard(ambientCard, t('Ambient glow'), '');
    var glow = doc.createElement('span');
    glow.setAttribute('aria-hidden', 'true');
    glow.className = 'screensaver-glow-thumbnail screensaver-glow';
    ambientCard.insertBefore(glow, ambientCard.firstChild);
    ambientCard.onclick = function () {
      configure({ mode: 'ambient', assetId: '' });
    };
    config.backgrounds.forEach(function (asset) {
      if (asset.mode !== 'photo') return;
      var scene = asset.id.split('-')[0];
      var choice = button(scenes, 'screensaverScene-' + scene, asset.label);
      choice.setAttribute('data-background-scene', scene);
      panelUi.mediaCard(choice, t(asset.label), '', {
        url: 'wallpapers/' + scene + '-preview.jpg',
        qualities: []
      });
      choice.onclick = function () {
        var mode = state.mode === 'photo' ? 'photo' : 'video';
        configure({ mode: mode, assetId: scene + '-' + mode });
      };
    });
    builtinPane.appendChild(scenes);
    var empty = doc.createElement('p');
    empty.id = 'screensaverSavedEmpty';
    empty.className = 'background-empty';
    empty.textContent = panelUi.t('No saved files');
    saved.appendChild(empty);
    var savedCards = doc.createElement('div');
    savedCards.className = 'wallpaper-media-gallery';
    saved.appendChild(savedCards);
    ['photo', 'video'].forEach(function (mode) {
      var label = mode === 'photo' ? 'My photo' : 'My video';
      var choice = button(savedCards, 'screensaverPersonal-' + mode, label);
      if (root.HomeWallpaperPanel)
        root.HomeWallpaperPanel.mediaCard(choice, t(label), mode);
      choice.onclick = function () {
        if (personal()[mode])
          configure({ mode: mode, assetId: 'personal-' + mode });
      };
    });
    clearGalleryFocus = panelUi.focusPreview(layout.right, summary);
    layout.right.addEventListener('click', clearGalleryFocus);

    var imports = doc.createElement('div');
    imports.className = 'screensaver-choices';
    ['photo', 'video'].forEach(function (mode) {
      button(imports, 'screensaverImport-' + mode, 'Add ' + mode).onclick =
        function () {
          receive(mode);
        };
    });

    var connection = doc.createElement('div');
    connection.id = 'screensaverReceiver';
    connection.className = 'screensaver-receiver';
    connection.hidden = true;
    ['screensaverReceiverPin', 'screensaverReceiverAddress'].forEach(
      function (id) {
        var line = doc.createElement('p');
        line.id = id;
        connection.appendChild(line);
      }
    );
    var instructions = doc.createElement('p');
    instructions.textContent = t(
      'Send a prepared photo or video from Clean Your TV on your computer.'
    );
    connection.appendChild(instructions);
    button(connection, 'screensaverReceiverCancel', 'Cancel import').onclick =
      function () {
        stopReceiver();
        status('');
      };
    imports.appendChild(connection);
    panelUi.disclosure(layout.right, imports, 'Add a file');

    var timing = doc.createElement('div');
    timing.className = 'screensaver-timing';
    var label = doc.createElement('p');
    label.id = 'screensaverDelay';
    label.textContent = t('Start on Home after');
    timing.appendChild(label);
    var choices = doc.createElement('div');
    choices.className = 'screensaver-choices screensaver-delay-choices';
    choices.setAttribute('role', 'group');
    choices.setAttribute('aria-labelledby', label.id);
    ['30 seconds', '1 minute', '5 minutes', '15 minutes', '30 minutes'].forEach(
      function (name, i) {
        var short = ['30 sec', '1 min', '5 min', '15 min', '30 min'][i];
        var choice = button(choices, 'screensaverDelay-' + delays[i], short);
        choice.setAttribute('aria-label', t(name));
        choice.setAttribute('data-screensaver-delay', '');
        choice.onclick = function () {
          if (state.idleTimeoutMs !== delays[i])
            configure({ idleTimeoutMs: delays[i] });
        };
      }
    );
    timing.appendChild(choices);
    var personalHint = doc.createElement('p');
    personalHint.id = 'screensaverPersonalHint';
    personalHint.className = 'screensaver-personal-hint';
    personalHint.textContent = t(
      'Personal backgrounds appear only on CYTV Home.'
    );
    timing.appendChild(personalHint);
    options.appendChild(timing);

    var previewAction = button(
      layout.left,
      'screensaverPreview',
      'Full screen'
    );
    previewAction.onclick = function () {
      if (!busy) offer(true);
    };
    var previewActions = doc.createElement('div');
    previewActions.className = 'background-preview-actions';
    layout.left.insertBefore(previewActions, formats);
    previewActions.appendChild(previewAction);
    previewActions.appendChild(formats);
    layout.left.appendChild(options);
    var wallpapers = groups.findIndex(function (group) {
      return group.id === 'wallpapers';
    });
    groups.splice(wallpapers < 0 ? groups.length : wallpapers + 1, 0, {
      id: 'screensaver',
      label: t('Screensaver'),
      elements: [host]
    });
    render();
  }
  root.HomeScreensaver = {
    start: start,
    mountSettings: mountSettings,
    activate: function (active) {
      if (active && !settingsActive) statusRetries = 0;
      settingsActive = active;
      if (active) {
        refreshMedia();
        refresh();
      } else {
        if (statusRetry !== null) root.clearTimeout(statusRetry);
        statusRetry = null;
        helperStarting = false;
        clearMediaPreview();
        if (clearGalleryFocus) clearGalleryFocus();
        if (host && root.HomeWallpaperPanel) {
          root.HomeWallpaperPanel.releaseCard(
            host.querySelector('#screensaverPersonal-photo')
          );
          root.HomeWallpaperPanel.releaseCard(
            host.querySelector('#screensaverPersonal-video')
          );
        }
        stopReceiver();
      }
    }
  };
})(window);
