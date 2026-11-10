/* Trusted settings: poster URLs are borrowed from HomeWallpaper, never revoked here. */
(function (root) {
  'use strict';

  var panel,
    preview,
    title,
    sourceInfo,
    capability,
    actual,
    notice,
    inputWarning,
    inputWarningText,
    disableInputPreview,
    dimValue,
    qualityButtons = [],
    minus,
    plus,
    reset,
    preferences;
  function t(source) {
    var prefix = 'Video dimensions do not match the theme. ';
    if (source.indexOf(prefix) === 0)
      return (
        t('Video dimensions do not match the theme.') +
        ' ' +
        t(source.slice(prefix.length))
      );
    var language = root.HomeI18n && root.HomeI18n.language(),
      strings =
        root.HomeWallpaperLocales && root.HomeWallpaperLocales[language];
    return (
      (strings && strings[source]) ||
      (root.HomeI18n ? root.HomeI18n.t(source) : source)
    );
  }
  function node(tag, parent, id) {
    var el = document.createElement(tag);
    if (id) el.id = id;
    parent.appendChild(el);
    return el;
  }
  function state() {
    return root.HomeWallpaper && root.HomeWallpaper.state
      ? root.HomeWallpaper.state()
      : {};
  }
  function label(quality) {
    return t(
      quality === 'auto'
        ? 'Auto'
        : quality === 'image'
          ? 'Image'
          : quality === '4k'
            ? '4K'
            : '1080p'
    );
  }
  var personalControls,
    themeSource,
    mySource,
    receiveCYTV,
    phone,
    remove,
    connection,
    pinText,
    addressText,
    qr,
    pendingBox,
    pendingImage,
    applyButton,
    cancelButton,
    phoneWarning,
    statusText,
    receiverCancel;
  var receiver = null,
    requestSignal = null,
    receiverTimer = null,
    receiverGeneration = 0,
    active = false,
    lastRestoreError = '';
  function personal() {
    return root.PersonalWallpaper
      ? root.PersonalWallpaper.state()
      : {
          source: 'theme',
          installed: false,
          pending: null
        };
  }
  function stopReceiver() {
    receiverGeneration++;
    clearTimeout(receiverTimer);
    receiverTimer = null;
    if (requestSignal) {
      requestSignal.cancelled = true;
      if (requestSignal.cancel) requestSignal.cancel();
    }
    requestSignal = null;
    var old = receiver;
    receiver = null;
    if (old && root.ThemeReceiver) root.ThemeReceiver.stop(old.sessionId);
    if (connection) connection.hidden = true;
  }
  function invoke(method, value) {
    if (!root.PersonalWallpaper) return;
    try {
      Promise.resolve(root.PersonalWallpaper[method](value)).then(
        function () {
          statusText.textContent = '';
          refresh();
        },
        function (error) {
          statusText.textContent =
            error && error.code === 'storage-full'
              ? error.message
              : t('Could not change wallpaper settings.');
        }
      );
    } catch (_) {
      statusText.textContent = t('Could not change wallpaper settings.');
    }
  }
  function receive(fromPhone) {
    stopReceiver();
    var token = receiverGeneration,
      signal = {
        cancelled: false
      };
    requestSignal = signal;
    statusText.textContent = t('Waiting for upload…');
    function live() {
      return (
        token === receiverGeneration &&
        active &&
        !signal.cancelled &&
        !document.hidden
      );
    }
    function error(error) {
      if (!live()) return;
      stopReceiver();
      statusText.textContent =
        error && error.code === 'storage-full'
          ? error.message
          : t('Wallpaper receiver stopped. Try again.');
      refresh();
    }
    function poll() {
      if (!live() || !receiver) return;
      var session = receiver;
      if (Date.now() >= session.expiresAt) {
        error();
        return;
      }
      root.ThemeReceiver.status(session.sessionId, signal)
        .then(function (value) {
          if (!live()) return;
          if (value.state !== 'received') {
            receiverTimer = setTimeout(poll, 500);
            return;
          }
          return root.ThemeReceiver.read(session.sessionId, value.size, signal)
            .then(function (envelope) {
              if (!live()) throw Error('Cancelled');
              return root.PersonalWallpaper.receive(envelope, function () {
                return !live();
              });
            })
            .then(function () {
              if (!live()) return;
              stopReceiver();
              statusText.textContent = '';
              refresh();
              if (applyButton) applyButton.focus();
            });
        })
        .catch(error);
    }
    if (!root.ThemeReceiver) {
      error();
      return;
    }
    root.ThemeReceiver.start(signal, 'wallpaper').then(function (session) {
      if (!live()) {
        root.ThemeReceiver.stop(session.sessionId);
        return;
      }
      receiver = session;
      connection.hidden = false;
      addressText.textContent = fromPhone
        ? session.addresses
            .map(function (address) {
              return 'http://' + address + ':8879/wallpaper';
            })
            .join(' · ')
        : session.addresses.join(' · ');
      pinText.textContent = 'PIN: ' + session.pin;
      qr.hidden = !fromPhone;
      if (fromPhone && root.WallpaperQR)
        root.WallpaperQR.render(
          qr,
          'http://' +
            session.addresses[0] +
            ':8879/wallpaper#pin=' +
            session.pin
        );
      poll();
    }, error);
  }
  var builtinButtons = [];
  function mountPersonal() {
    if (!root.PersonalWallpaper) return;
    personalControls = node('div', panel, 'personalWallpaperControls');
    var sourceControls = node('div', panel, 'wallpaperSources');
    var sources = node('div', sourceControls);
    sources.className = 'wallpaper-quality';
    themeSource = button(sources, 'wallpaperSourceTheme', function () {
      invoke('select', 'theme');
    });
    mySource = button(sources, 'wallpaperSourcePersonal', function () {
      invoke('select', 'personal');
    });
    if (root.WallpaperLibrary) {
      var library = node('div', sourceControls, 'wallpaperBuiltins');
      var heading = node('h5', library);
      heading.textContent = t('Built-in wallpapers');
      root.WallpaperLibrary.list().forEach(function (item) {
        var el = button(
          library,
          'wallpaperBuiltin-' + item.id.slice(8),
          function () {
            stopReceiver();
            invoke('select', item.id);
          }
        );
        el.setAttribute('data-wallpaper-id', item.id);
        var name = node('strong', el);
        name.textContent = item.title;
        var credit = node('small', el);
        credit.textContent = '4K · ' + t('Video by') + ' ' + item.author;
        builtinButtons.push({
          button: el,
          credit: credit,
          item: item,
          heading: heading
        });
      });
    }
    panel.insertBefore(sourceControls, notice);
    sourceControls.insertBefore(personalControls, library || null);
    var uploads = node('div', personalControls);
    receiveCYTV = button(uploads, 'wallpaperCYTV', function () {
      receive(false);
    });
    phone = button(uploads, 'wallpaperPhone', function () {
      receive(true);
    });
    phoneWarning = node('p', personalControls, 'wallpaperPhoneWarning');
    statusText = node('p', personalControls, 'wallpaperStatus');
    statusText.setAttribute('aria-live', 'polite');
    connection = node('div', personalControls, 'wallpaperConnection');
    connection.hidden = true;
    qr = node('canvas', connection, 'wallpaperQR');
    qr.setAttribute('role', 'img');
    qr.setAttribute('aria-label', t('Upload from phone'));
    addressText = node('p', connection, 'wallpaperAddress');
    pinText = node('p', connection, 'wallpaperPIN');
    receiverCancel = button(connection, 'wallpaperReceiverCancel', function () {
      stopReceiver();
      statusText.textContent = '';
      refresh();
    });
    pendingBox = node('div', personalControls, 'wallpaperPending');
    pendingBox.hidden = true;
    pendingImage = node('img', pendingBox, 'wallpaperPendingPreview');
    pendingImage.alt = t('My wallpaper');
    applyButton = button(pendingBox, 'wallpaperApply', function () {
      stopReceiver();
      invoke('apply');
    });
    cancelButton = button(pendingBox, 'wallpaperCancel', function () {
      stopReceiver();
      invoke('cancel');
    });
    remove = button(personalControls, 'wallpaperRemove', function () {
      if (!root.HomeI18n || !root.HomeI18n.confirm) return;
      root.HomeI18n.confirm(
        {
          title: t('Remove personal wallpaper'),
          message: t(
            'Remove the saved wallpaper? Upload it again to use it later.'
          ),
          action: t('Remove personal wallpaper')
        },
        function () {
          stopReceiver();
          invoke('remove');
        }
      );
    });
  }
  function refreshPersonal() {
    if (!personalControls) return;
    var value = personal();
    if (value.error) {
      statusText.textContent = t(value.error);
      lastRestoreError = value.error;
    } else if (lastRestoreError) {
      statusText.textContent = '';
      lastRestoreError = '';
    }
    themeSource.textContent = t('Theme');
    mySource.textContent = t('My wallpaper');
    themeSource.setAttribute('aria-pressed', String(value.source === 'theme'));
    mySource.setAttribute('aria-pressed', String(value.source === 'personal'));
    mySource.disabled = !value.installed;
    remove.disabled = !value.installed;
    remove.textContent = t('Remove personal wallpaper');
    receiveCYTV.textContent = t('Receive from CYTV');
    phone.textContent = t('Upload from phone');
    phoneWarning.textContent = t(
      'Phone upload: ordinary image up to 1080p. Sharpness is limited by the TV interface. Use CYTV for native 4K video.'
    );
    builtinButtons.forEach(function (entry) {
      entry.button.setAttribute(
        'aria-pressed',
        String(value.source === 'builtin' && value.builtinId === entry.item.id)
      );
      entry.heading.textContent = t('Built-in wallpapers');
      entry.credit.textContent =
        '4K · ' + t('Video by') + ' ' + entry.item.author;
    });
    receiverCancel.textContent = t('Cancel');
    applyButton.textContent = t('Apply');
    cancelButton.textContent = t('Cancel');
    pendingBox.hidden = !value.pending;
    if (value.pending) {
      if (value.pending.storageBudget && !statusText.textContent)
        statusText.textContent = root.StorageBudget.format(
          value.pending.storageBudget
        );
      if (pendingImage.getAttribute('src') !== value.pending.posterURL)
        pendingImage.src = value.pending.posterURL;
    } else pendingImage.removeAttribute('src');
  }
  function refresh() {
    if (!panel) return;
    refreshPersonal();
    var focused = document.activeElement,
      wasInside = panel.contains(focused);
    var value = state(),
      available = value.available || [],
      hasPoster = !!value.posterURL,
      cap = value.capabilities || {},
      dim = typeof value.dim === 'number' ? value.dim : 0;
    preferences.hidden = !hasPoster;
    title.textContent =
      value.source === 'personal'
        ? t('My wallpaper')
        : value.title || 'Classic';
    sourceInfo.hidden = value.source !== 'personal' && !value.author;
    sourceInfo.textContent = value.author
      ? t('Video by') +
        ' ' +
        value.author +
        ' · ' +
        t(value.license) +
        ' · ' +
        value.posterWidth +
        ' × ' +
        value.posterHeight
      : value.source === 'personal'
        ? t(
            value.origin === 'phone'
              ? 'Uploaded from phone'
              : 'Uploaded from CYTV'
          ) +
          ' · ' +
          value.posterWidth +
          ' × ' +
          value.posterHeight
        : '';
    preview.hidden = !hasPoster;
    if (hasPoster) {
      if (preview.getAttribute('src') !== value.posterURL)
        preview.src = value.posterURL;
      preview.alt = t('Current theme wallpaper');
    } else preview.removeAttribute('src');
    capability.textContent =
      t('TV capability') +
      ': ' +
      t(
        cap.uhd === true
          ? '4K supported'
          : cap.uhd === false
            ? '4K not detected'
            : 'Unknown'
      );
    actual.textContent =
      t('Current mode') +
      ': ' +
      (hasPoster
        ? value.paused
          ? t('Paused while settings are open')
          : value.actualQuality
            ? label(value.actualQuality)
            : t('No wallpaper')
        : t('No wallpaper'));
    notice.textContent = !hasPoster
      ? t('This theme has no wallpaper.')
      : available.indexOf('4k') < 0 && available.indexOf('1080p') < 0
        ? t('This wallpaper has no video version.')
        : t(
            'Auto uses detected TV support. Playback may fall back to an image.'
          );
    if (value.notice) notice.textContent += ' ' + t(value.notice);
    qualityButtons.forEach(function (button) {
      var q = button.getAttribute('data-wallpaper-quality');
      button.textContent = label(q);
      button.disabled =
        !hasPoster ||
        (q !== 'auto' && available.indexOf(q) < 0) ||
        (q === '4k' && cap.uhd === false);
      button.setAttribute(
        'aria-pressed',
        String((value.preferenceQuality || 'auto') === q)
      );
    });
    var shelf = root.HomeInputShelf;
    inputWarning.hidden = !(
      hasPoster &&
      available.indexOf('4k') >= 0 &&
      (value.preferenceQuality === '4k' || value.actualQuality === '4k') &&
      shelf &&
      shelf.enabled() &&
      shelf.previewEnabled()
    );
    inputWarningText.textContent = t(
      'During HDMI previews, the 4K video wallpaper temporarily switches to a static 1080p image. Disable input previews to keep the wallpaper in 4K.'
    );
    disableInputPreview.textContent = t('Disable HDMI previews');
    dimValue.textContent = t('Dimming') + ': ' + Math.round(dim * 100) + '%';
    minus.textContent = t('Less dimming');
    plus.textContent = t('More dimming');
    reset.textContent = t('Reset to theme defaults');
    minus.disabled = !hasPoster || dim <= 0;
    plus.disabled = !hasPoster || dim >= 0.85;
    reset.disabled = !hasPoster;
    if (
      wasInside &&
      (focused.disabled ||
        (focused === disableInputPreview && inputWarning.hidden))
    ) {
      var target = hasPoster
        ? focused === plus
          ? minus
          : focused === minus
            ? plus
            : qualityButtons[0]
        : document.getElementById('settings-tab-wallpapers');
      if (target && !target.disabled) target.focus();
    }
  }
  function change(method, value) {
    if (!root.HomeWallpaper || !root.HomeWallpaper[method]) return;
    try {
      Promise.resolve(root.HomeWallpaper[method](value)).then(
        refresh,
        function () {
          notice.textContent = t('Could not change wallpaper settings.');
        }
      );
    } catch (_) {
      notice.textContent = t('Could not change wallpaper settings.');
    }
  }
  function button(parent, id, action) {
    var el = node('button', parent, id);
    el.type = 'button';
    el.onclick = action;
    return el;
  }
  function mount(host) {
    if (panel) {
      host.appendChild(panel);
      refresh();
      return;
    }
    panel = node('div', host, 'homeWallpaperPanel');
    var summary = node('div', panel);
    summary.className = 'wallpaper-summary';
    preview = node('img', summary, 'wallpaperPreview');
    var info = node('div', summary);
    info.className = 'wallpaper-info';
    title = node('h4', info, 'wallpaperTitle');
    sourceInfo = node('p', info, 'wallpaperSourceInfo');
    capability = node('p', info, 'wallpaperCapability');
    actual = node('p', info, 'wallpaperActual');
    notice = node('p', panel, 'wallpaperNotice');
    notice.setAttribute('aria-live', 'polite');
    preferences = node('div', panel, 'wallpaperPreferences');
    var qualities = node('div', preferences);
    qualities.className = 'wallpaper-quality';
    qualities.setAttribute('role', 'group');
    qualities.setAttribute('aria-label', t('Wallpaper quality'));
    ['auto', '4k', '1080p', 'image'].forEach(function (q) {
      var el = button(qualities, null, function () {
        change('setQuality', q);
      });
      el.setAttribute('data-wallpaper-quality', q);
      qualityButtons.push(el);
    });
    inputWarning = node('div', preferences, 'wallpaperInputPreviewWarning');
    inputWarning.hidden = true;
    inputWarningText = node(
      'p',
      inputWarning,
      'wallpaperInputPreviewWarningText'
    );
    inputWarningText.setAttribute('aria-live', 'polite');
    disableInputPreview = button(
      inputWarning,
      'wallpaperDisableInputPreview',
      function () {
        if (!root.HomeInputShelf || !root.HomeInputShelf.previewEnabled())
          return;
        root.HomeInputShelf.togglePreview();
        refresh();
        if (root.HomeInputShelf.previewEnabled())
          notice.textContent = t('Could not change wallpaper settings.');
        else qualityButtons[1].focus();
      }
    );
    disableInputPreview.setAttribute(
      'aria-describedby',
      'wallpaperInputPreviewWarningText'
    );
    var dim = node('div', preferences);
    dim.className = 'wallpaper-dim';
    dimValue = node('p', dim, 'wallpaperDimValue');
    minus = button(dim, 'wallpaperDimMinus', function () {
      change(
        'setDim',
        Math.max(0, Math.round(((state().dim || 0) - 0.05) * 100) / 100)
      );
    });
    plus = button(dim, 'wallpaperDimPlus', function () {
      change(
        'setDim',
        Math.min(0.85, Math.round(((state().dim || 0) + 0.05) * 100) / 100)
      );
    });
    reset = button(preferences, 'wallpaperReset', function () {
      change('resetPreferences');
    });
    mountPersonal();
    refresh();
  }
  document.addEventListener('home-wallpaper-change', refresh);
  document.addEventListener('home-layout-change', refresh);
  function deactivate() {
    active = false;
    stopReceiver();
    if (statusText) statusText.textContent = '';
  }
  document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
      stopReceiver();
      if (statusText) statusText.textContent = '';
    }
  });
  root.addEventListener('pagehide', function () {
    stopReceiver();
  });
  root.HomeWallpaperPanel = {
    mount: mount,
    refresh: refresh,
    t: t,
    activate: function (value) {
      active = !!value;
      if (!value) deactivate();
      else refresh();
    },
    unmount: deactivate
  };
})(window);
