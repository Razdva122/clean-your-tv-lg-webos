/* Trusted settings: poster URLs are borrowed from HomeWallpaper, never revoked here. */
(function (root) {
  'use strict';

  var panel,
    preview,
    mediaBadges,
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
    preferences,
    fullscreen,
    closePreview,
    clearFocusPreview;
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
  function renderBadges(element, mode, qualities, width, height) {
    var labels = mode ? [t(mode === 'video' ? 'Video' : 'Photo')] : [];
    if (mode) {
      if (
        qualities.indexOf('4k') >= 0 ||
        (mode === 'photo' && width >= 3840 && height >= 2160)
      )
        labels.push(label('4k'));
      if (
        qualities.indexOf('1080p') >= 0 ||
        (mode === 'photo' && width === 1920 && height === 1080)
      )
        labels.push(label('1080p'));
    }
    if (element.getAttribute('data-labels') === labels.join('\n')) return;
    element.setAttribute('data-labels', labels.join('\n'));
    element.textContent = '';
    labels.forEach(function (value) {
      node('span', element).textContent = value;
    });
  }
  function mediaCard(button, title, mode, media) {
    button.classList.add('wallpaper-media-card');
    if (!button.mediaCard) {
      button.textContent = '';
      var image = node('img', button);
      image.alt = '';
      image.hidden = true;
      var name = node('strong', button);
      var badges = node('span', button);
      badges.className = 'wallpaper-media-badges';
      button.mediaCard = { image: image, name: name, badges: badges };
    }
    var card = button.mediaCard;
    card.name.textContent = title;
    card.image.hidden = !media || !media.url;
    if (card.image.hidden) card.image.removeAttribute('src');
    else if (card.image.getAttribute('src') !== media.url)
      card.image.src = media.url;
    renderBadges(
      card.badges,
      mode,
      media ? media.qualities : [],
      media && media.width,
      media && media.height
    );
  }
  function releaseCard(button) {
    if (!button) return;
    button.mediaEpoch = (button.mediaEpoch || 0) + 1;
    if (!button.mediaUrl) return;
    button.mediaCard.image.hidden = true;
    button.mediaCard.image.removeAttribute('src');
    root.URL.revokeObjectURL(button.mediaUrl);
    button.mediaUrl = '';
  }
  function savedCard(button, title, mode) {
    if (!button.mediaCard) mediaCard(button, title, mode);
    if (!root.PersonalWallpaper || !root.PersonalWallpaper.previewMedia) return;
    var epoch = (button.mediaEpoch || 0) + 1;
    button.mediaEpoch = epoch;
    return root.PersonalWallpaper.previewMedia(mode)
      .then(function (media) {
        if (button.mediaEpoch !== epoch) {
          if (media) root.URL.revokeObjectURL(media.url);
          return;
        }
        if (button.mediaUrl) root.URL.revokeObjectURL(button.mediaUrl);
        button.mediaUrl = media && media.url;
        mediaCard(button, title, mode, media);
      })
      .catch(function () {});
  }
  function backgroundLayout(parent) {
    var layout = node('div', parent);
    layout.className = 'background-layout';
    var left = node('div', layout);
    left.className = 'background-preview';
    var right = node('div', layout);
    right.className = 'background-library';
    return { left: left, right: right };
  }
  function libraryTabs(parent, builtin, saved, initial) {
    var tabs = node('div', parent);
    tabs.className = 'background-tabs wallpaper-quality';
    tabs.setAttribute('role', 'group');
    tabs.setAttribute('aria-label', t('Background source'));
    var panes = [builtin, saved];
    var buttons = ['Built-in', 'My files'].map(function (name, index) {
      var choice = button(tabs, null, function () {
        select(index);
      });
      choice.setAttribute(
        'data-background-tab',
        index === 0 ? 'built-in' : 'my-files'
      );
      choice.textContent = t(name);
      return choice;
    });
    panes.forEach(function (pane) {
      parent.appendChild(pane);
    });
    function select(index) {
      panes.forEach(function (pane, i) {
        pane.hidden = index !== i;
        buttons[i].setAttribute('aria-pressed', String(index === i));
      });
    }
    select(initial || 0);
    return select;
  }
  function disclosure(parent, content, name) {
    var control = button(parent, null, function () {
      content.hidden = !content.hidden;
      control.setAttribute('aria-expanded', String(!content.hidden));
    });
    control.textContent = t(name);
    control.setAttribute('aria-expanded', 'false');
    control.setAttribute('data-background-upload', '');
    content.hidden = true;
    parent.appendChild(content);
  }
  function focusPreview(gallery, summary) {
    var overlay = node('div', summary);
    overlay.className = 'background-focus-preview';
    overlay.hidden = true;
    overlay.setAttribute('aria-hidden', 'true');
    var image = node('img', overlay);
    image.alt = '';
    var title = node('strong', overlay);
    gallery.addEventListener('focusin', function (event) {
      var card = event.target.mediaCard;
      if (
        !card ||
        card.image.hidden ||
        event.target.getAttribute('aria-pressed') === 'true'
      )
        return;
      image.src = card.image.src;
      title.textContent = card.name.textContent;
      overlay.hidden = false;
    });
    gallery.addEventListener('focusout', function (event) {
      if (!event.target.mediaCard) return;
      overlay.hidden = true;
      image.removeAttribute('src');
    });
    return function () {
      overlay.hidden = true;
      image.removeAttribute('src');
    };
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
  var sharedButtons = {};
  var sharedHeading = null;
  function refreshSharedMedia() {
    if (!sharedHeading || !root.PersonalWallpaper.listMedia) return;
    root.PersonalWallpaper.listMedia().then(
      function (result) {
        sharedHeading.hidden = result.photo || result.video;
        sharedButtons.photo.hidden = !result.photo;
        sharedButtons.video.hidden = !result.video;
        ['photo', 'video'].forEach(function (mode) {
          if (result[mode] && active)
            savedCard(sharedButtons[mode], savedLabel(mode), mode);
          else releaseCard(sharedButtons[mode]);
        });
      },
      function () {
        sharedHeading.hidden =
          sharedButtons.photo.hidden =
          sharedButtons.video.hidden =
            true;
      }
    );
  }
  function savedLabel(mode) {
    return t(mode === 'photo' ? 'My photo' : 'My video');
  }
  function mountPersonal(destination) {
    if (!root.PersonalWallpaper) return;
    var sourceControls = node('div', destination, 'wallpaperSources');
    var builtinPane = node('div', sourceControls);
    var myPane = node('div', sourceControls);
    var sources = node('div', builtinPane);
    sources.className = 'background-source-action';
    var savedSource = node('div', myPane);
    savedSource.className = 'background-source-action';
    themeSource = button(sources, 'wallpaperSourceTheme', function () {
      invoke('select', 'theme');
    });
    mySource = button(savedSource, 'wallpaperSourcePersonal', function () {
      invoke('select', 'personal');
    });
    if (root.WallpaperLibrary) {
      var library = node('div', builtinPane, 'wallpaperBuiltins');
      var gallery = node('div', library);
      gallery.className = 'wallpaper-media-gallery';
      root.WallpaperLibrary.list().forEach(function (item) {
        var el = button(
          gallery,
          'wallpaperBuiltin-' + item.id.slice(8),
          function () {
            stopReceiver();
            invoke('select', item.id);
          }
        );
        el.setAttribute('data-wallpaper-id', item.id);
        mediaCard(el, item.title, 'video', {
          url: 'wallpapers/ribbon-preview.jpg',
          qualities: ['4k', '1080p']
        });
        var credit = node('small', el);
        credit.textContent = t('Video by') + ' ' + item.author;
        builtinButtons.push({
          button: el,
          credit: credit,
          item: item
        });
      });
    }
    libraryTabs(sourceControls, builtinPane, myPane);
    if (root.PersonalWallpaper.selectMedia) {
      var shared = node('div', myPane);
      shared.className = 'wallpaper-media-gallery';
      sharedHeading = node('p', myPane);
      sharedHeading.className = 'background-empty';
      sharedHeading.textContent = t('No saved files');
      ['photo', 'video'].forEach(function (mode) {
        sharedButtons[mode] = button(
          shared,
          'wallpaperSaved-' + mode,
          function () {
            invoke('selectMedia', mode);
          }
        );
        mediaCard(sharedButtons[mode], savedLabel(mode), mode);
        sharedButtons[mode].hidden = true;
      });
      refreshSharedMedia();
    }
    personalControls = node('div', destination, 'personalWallpaperControls');
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
    if (root.PilotHome) personalControls.hidden = true;
    else disclosure(destination, personalControls, 'Add a file');
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
    if (sharedHeading) {
      sharedHeading.textContent = t('No saved files');
    }
    themeSource.setAttribute('aria-pressed', String(value.source === 'theme'));
    mySource.setAttribute('aria-pressed', String(value.source === 'personal'));
    mySource.disabled = !value.installed;
    mySource.hidden = !value.installed;
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

      entry.credit.textContent = t('Video by') + ' ' + entry.item.author;
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
    fullscreen.disabled = !hasPoster;
    fullscreen.textContent = t('Full screen');
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
    renderBadges(
      mediaBadges,
      hasPoster &&
        ((value.source === 'personal' && personal().mediaKind) ||
          (available.indexOf('4k') >= 0 || available.indexOf('1080p') >= 0
            ? 'video'
            : 'photo')),
      available,
      value.posterWidth,
      value.posterHeight
    );
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
      button.textContent =
        q === 'image' &&
        (available.indexOf('4k') >= 0 || available.indexOf('1080p') >= 0) &&
        personal().mediaKind !== 'photo'
          ? t('Still frame')
          : label(q);
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
  function showFullscreen() {
    var poster = state().posterURL;
    if (!poster || closePreview) return;
    var dialog = node('div', document.body);
    dialog.className = 'wallpaper-fullscreen';
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-label', t('Wallpaper preview'));
    var image = node('img', dialog);
    image.alt = '';
    image.src = poster;
    var back = button(dialog, null, function () {
      closePreview(true);
    });
    back.textContent = t('Close preview');
    var settings = panel.parentElement;
    while (settings && settings.getAttribute('role') !== 'dialog')
      settings = settings.parentElement;
    var wasHidden = settings && settings.getAttribute('aria-hidden');
    function key(event) {
      if ([8, 13, 27, 32, 461].indexOf(event.keyCode) >= 0) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closePreview(true);
      } else if ([9, 37, 38, 39, 40].indexOf(event.keyCode) >= 0) {
        event.preventDefault();
        event.stopImmediatePropagation();
      }
    }
    closePreview = function (focus) {
      root.removeEventListener('keydown', key, true);
      document.body.classList.remove('ctv-wallpaper-fullscreen');
      dialog.parentNode.removeChild(dialog);
      if (settings) {
        if (wasHidden === null) settings.removeAttribute('aria-hidden');
        else settings.setAttribute('aria-hidden', wasHidden);
      }
      closePreview = null;
      if (focus) fullscreen.focus();
    };
    if (settings) settings.setAttribute('aria-hidden', 'true');
    document.body.classList.add('ctv-wallpaper-fullscreen');
    root.addEventListener('keydown', key, true);
    back.focus();
  }
  function mount(host) {
    if (panel) {
      host.appendChild(panel);
      refresh();
      return;
    }
    panel = node('div', host, 'homeWallpaperPanel');
    var layout = backgroundLayout(panel);
    var summary = node('div', layout.left);
    summary.className = 'wallpaper-summary';
    preview = node('img', summary, 'wallpaperPreview');
    preview.className = 'wallpaper-preview-image';
    var info = node('div', summary);
    info.className = 'wallpaper-info';
    title = node('h4', info, 'wallpaperTitle');
    mediaBadges = node('div', info);
    mediaBadges.className = 'wallpaper-media-badges';
    sourceInfo = node('p', info, 'wallpaperSourceInfo');
    capability = node('p', info, 'wallpaperCapability');
    actual = node('p', info, 'wallpaperActual');
    notice = node('p', layout.left, 'wallpaperNotice');
    notice.setAttribute('aria-live', 'polite');
    preferences = node('div', layout.left, 'wallpaperPreferences');
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
    fullscreen = button(layout.left, 'wallpaperFullscreen', showFullscreen);
    layout.left.insertBefore(fullscreen, preferences);
    var details = node('div', panel);
    details.className = 'background-options';
    inputWarning = node('div', details, 'wallpaperInputPreviewWarning');
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
    var dim = node('div', details);
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
    reset = button(details, 'wallpaperReset', function () {
      change('resetPreferences');
    });
    var mediaDetails = node('div', panel);
    mediaDetails.className = 'background-media-details';
    [sourceInfo, capability, actual, notice].forEach(function (line) {
      mediaDetails.appendChild(line);
    });
    mountPersonal(layout.right);
    clearFocusPreview = focusPreview(layout.right, summary);
    panel.addEventListener('click', clearFocusPreview);
    refresh();
  }
  document.addEventListener('home-wallpaper-change', refresh);
  document.addEventListener('home-wallpaper-change', refreshSharedMedia);
  document.addEventListener('home-layout-change', refresh);
  function deactivate() {
    active = false;
    if (closePreview) closePreview(false);
    if (clearFocusPreview) clearFocusPreview();
    releaseCard(sharedButtons.photo);
    releaseCard(sharedButtons.video);
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
    if (closePreview) closePreview(false);
    stopReceiver();
  });
  root.HomeWallpaperPanel = {
    mount: mount,
    refresh: refresh,
    t: t,
    qualityLabel: label,
    renderBadges: renderBadges,
    backgroundLayout: backgroundLayout,
    libraryTabs: libraryTabs,
    disclosure: disclosure,
    focusPreview: focusPreview,
    mediaCard: mediaCard,
    savedCard: savedCard,
    releaseCard: releaseCard,
    activate: function (value) {
      active = !!value;
      if (!value) deactivate();
      else {
        refresh();
        refreshSharedMedia();
      }
    },
    unmount: deactivate
  };
})(window);
