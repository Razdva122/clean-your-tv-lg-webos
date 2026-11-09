!(function () {
  'use strict';

  function tr(text, params) {
    return window.HomeI18n
      ? HomeI18n.t(text, params)
      : text.replace(/\{(\w+)\}/g, function (m, k) {
          return params && params[k] !== undefined ? params[k] : m;
        });
  }
  function sceneRect(element) {
    return window.HomeViewport
      ? HomeViewport.rect(element)
      : element.getBoundingClientRect();
  }
  function ht(markup) {
    return window.HomeI18n ? HomeI18n.html(markup) : markup;
  }
  window.RootLauncherRendered = false;
  // Shared layout, focus and remote-control state.
  var layoutState = window.HomeLayout
    ? HomeLayout.create(
        localStorage,
        CONFIG,
        window.RootProfileData || window.HomeData
      )
    : null;
  window.HomeLayoutState = layoutState;
  var GRID_LEFT = 112,
    GRID_WIDTH = 1696,
    FOCUS_SCALE = 1.1,
    FOCUS_PADDING = 12,
    ROW_GAP = 90,
    DOCK_PADDING = 28,
    DOCK_TOP = 680,
    columnCount = Math.max(1, Math.min(8, CONFIG.columns || 5)),
    columnWidth,
    CARD_WIDTH,
    CARD_HEIGHT,
    DOCK_HEIGHT,
    TILE_BASE = DOCK_TOP + DOCK_PADDING,
    HERO_OFFSET = 176,
    layoutPreset = 'dock-grid',
    layoutGeometry,
    ribbonStart = 0,
    ribbonWheelTime = 0;
  function updateGeometry(columns, preset, ribbon) {
    layoutPreset = preset || 'dock-grid';
    ribbonStart = 0;
    layoutGeometry = HomeLayout.geometry(
      layoutPreset,
      columns,
      ribbon,
      window.HomeWeather ? HomeWeather.reservation() : null
    );
    columnCount = columns;
    GRID_LEFT = layoutGeometry.left;
    GRID_WIDTH = layoutGeometry.width;
    columnWidth = layoutGeometry.columnWidth;
    CARD_WIDTH = layoutGeometry.cardWidth;
    CARD_HEIGHT = layoutGeometry.cardHeight;
    DOCK_TOP = layoutGeometry.dockTop;
    DOCK_PADDING = layoutGeometry.padding;
    TILE_BASE = layoutGeometry.top;
    ROW_GAP = layoutGeometry.rowGap;
    DOCK_HEIGHT = CARD_HEIGHT + DOCK_PADDING * 2;
    document
      .getElementById('homeSurface')
      .setAttribute('data-layout', layoutPreset);
    if (layoutGeometry.ribbon)
      document
        .getElementById('homeSurface')
        .setAttribute('data-ribbon', 'true');
    else document.getElementById('homeSurface').removeAttribute('data-ribbon');
    document
      .getElementById('homeSurface')
      .classList.toggle(
        'ctv-channel-multi',
        layoutPreset === 'channel-list' && columns > 1
      );
    document
      .getElementById('homeSurface')
      .classList.toggle(
        'ctv-channel-compact',
        layoutPreset === 'channel-list' && columns >= 5
      );
  }
  updateGeometry(columnCount);
  var toastTimer,
    KEY_OK = 13,
    KEY_BACK = 461,
    greetings = [
      [5, tr('Good night')],
      [12, tr('Good morning')],
      [17, tr('Good afternoon')],
      [22, tr('Good evening')],
      [24, tr('Good night')]
    ],
    weekdays = [
      'Sunday',
      'Monday',
      'Tuesday',
      'Wednesday',
      'Thursday',
      'Friday',
      'Saturday'
    ],
    months = [
      'January',
      'February',
      'March',
      'April',
      'May',
      'June',
      'July',
      'August',
      'September',
      'October',
      'November',
      'December'
    ],
    getElement = function (e) {
      return document.getElementById(e);
    },
    stage = getElement('stage'),
    tilesContainer = getElement('tiles'),
    focusGlass = getElement('glass'),
    heroTitle = getElement('hero'),
    ambientLayers = [getElement('ambientA'), getElement('ambientB')],
    ambientIndex = 0,
    ambientColor = null,
    ambientTimer = null,
    ambientBake = null,
    // Focus rest before the glow changes: longer than a browsing cadence of presses, so
    // the crossfade and bake never land on the next press (measured on an LG G1).
    AMBIENT_SETTLE = 800,
    // style.css's 600 ms .ambient fade plus a few frames, before the glow is baked.
    AMBIENT_FADE = 650,
    AMBIENT_BAKED = '#ambientBase{',
    topButtons = [
      getElement('btnInputs'),
      getElement('btnWifi'),
      getElement('btnSettings')
    ],
    inputsPanel = getElement('inputsPanel'),
    tiles = [],
    focusZone = 'grid',
    focusedTile = 0,
    focusedTopButton = 0,
    focusedInput = 0,
    inputRows = [],
    scrollOffset = 0,
    heroVisible = false,
    channelArtwork = null,
    focusGlassVisible = false,
    moveState = null,
    activeBridges = [];
  // Classic Inputs shelf: one row of TV sources between the header and the dock.
  // Whole 1080p pixels throughout: UHD panels upscale the graphics plane exactly 2x.
  var SHELF_TOP = 236,
    SHELF_WINDOW_TOP = 28,
    SHELF_TILE_WIDTH = 288,
    SHELF_TILE_HEIGHT = 162,
    // The focused tile grows instead of scaling, so its text stays sharp; its
    // 10px-framed picture is exactly 384x216.
    SHELF_FOCUS_WIDTH = 404,
    SHELF_FOCUS_HEIGHT = 236,
    SHELF_GAP = 24,
    SHELF_INSET = 16,
    // style.css's .input-tile transitions without transform; held while a FLIP is inverted.
    SHELF_FADES = 'background 160ms ease, opacity 200ms ease',
    INPUT_ICONS = {
      hdmi: 'M18,7V4c0,-1.1 -0.9,-2 -2,-2H8C6.9,2 6,2.9 6,4v3H5v6l3,6v3h8v-3l3,-6V7H18zM8,4h8v3h-2V5h-1v2h-2V5h-1v2H8V4z',
      tv: 'M21,6h-7.59l3.29,-3.29L16,2l-4,4l-4,-4l-0.71,0.71L10.59,6H3c-1.1,0 -2,0.89 -2,2v12c0,1.1 0.9,2 2,2h18c1.1,0 2,-0.89 2,-2V8C23,6.89 22.1,6 21,6zM21,20H3V8h18V20zM9,10v8l7,-4L9,10z',
      game: 'M15,7.5V2H9v5.5l3,3 3,-3zM7.5,9H2v6h5.5l3,-3 -3,-3zM9,16.5V22h6v-5.5l-3,-3 -3,3zM16.5,9l-3,3 3,3H22V9h-5.5z',
      stream:
        'M21,3H3c-1.1,0 -2,0.9 -2,2v3h2V5h18v14h-7v2h7c1.1,0 2,-0.9 2,-2V5c0,-1.1 -0.9,-2 -2,-2zM1,18v3h3c0,-1.66 -1.34,-3 -3,-3zM1,14v2c2.76,0 5,2.24 5,5h2c0,-3.87 -3.13,-7 -7,-7zM1,10v2c4.97,0 9,4.03 9,9h2c0,-6.08 -4.93,-11 -11,-11z',
      pc: 'M20,18c1.1,0 1.99,-0.9 1.99,-2L22,6c0,-1.1 -0.9,-2 -2,-2H4c-1.1,0 -2,0.9 -2,2v10c0,1.1 0.9,2 2,2H0v2h24v-2h-4zM4,6h16v10H4V6z'
    },
    inputSources = window.InputSources
      ? InputSources.create({
          root: !!document.querySelector('script[src="root-settings.js"]'),
          inventory: function () {
            return window.TV_APPS && TV_APPS.inputs;
          },
          call: callLuna
        })
      : null,
    shelf = getElement('inputShelf'),
    shelfTrack = getElement('inputShelfTrack'),
    shelfTiles = [],
    focusedShelf = 0,
    shelfOffset = 0,
    shelfLayout = null,
    // The input launched last from the shelf or dropdown, until focus moves elsewhere.
    returnInput = null,
    restoring = false,
    // Cleared while a system overlay or another app holds window focus.
    windowFocused = true,
    inputPreview = window.InputPreview
      ? InputPreview.create({
          onclaim: function () {
            if (window.HomeWallpaper) HomeWallpaper.suspend('input-preview');
          },
          onrelease: function () {
            if (window.HomeWallpaper) HomeWallpaper.resume('input-preview');
          },
          createMedia: function (uri) {
            return window.PREVIEW_INPUT_MEDIA
              ? window.PREVIEW_INPUT_MEDIA(uri)
              : InputPreview.createVideo(uri);
          },
          // The CARD owns the screen; preview still respects visibility and modal ownership.
          enabled: function () {
            return (
              layoutPreset === 'dock-grid' &&
              !document.hidden &&
              windowFocused &&
              !previewDialogOpen() &&
              window.HomeInputShelf.enabled() &&
              window.HomeInputShelf.previewEnabled()
            );
          },
          mount: function (media, input) {
            var tile = shelfTiles[focusedShelf];
            if (!tile || tile.input.appId !== input.appId) return false;
            media.className = 'input-preview ctv-input-preview';
            tile.el.insertBefore(media, tile.el.firstChild);
            return true;
          },
          onchange: function (input) {
            shelfTiles.forEach(function (tile) {
              setPartState(
                tile.el,
                'previewing',
                !!input && tile.input.appId === input.appId
              );
            });
          }
        })
      : null;
  // Retain service bridges until their replies arrive; subscriptions stay alive.
  function callLuna(uri, params, callback, timeout) {
    var bridge,
      timer,
      done = false;
    function finish(result) {
      if (done) return;
      if (!(params && params.subscribe)) {
        done = true;
        clearTimeout(timer);
        var index = activeBridges.indexOf(bridge);
        if (index >= 0) activeBridges.splice(index, 1);
        if (timeout && bridge)
          try {
            bridge.cancel();
          } catch (_) {}
      }
      callback && callback(result);
    }
    try {
      bridge = new PalmServiceBridge();
      bridge.onservicecallback = function (e) {
        var i;
        try {
          i = JSON.parse(e);
        } catch (e) {
          i = {
            returnValue: false
          };
        }
        finish(i);
      };
      activeBridges.push(bridge);
      if (timeout)
        timer = setTimeout(function () {
          finish({ returnValue: false });
        }, timeout);
      bridge.call(uri, JSON.stringify(params || {}));
    } catch (e) {
      finish({
        returnValue: false,
        errorText: String(e)
      });
    }
  }
  // Canonical Home owns one persistent CARD and has no transient controller.
  window.HomePresentationController = null;
  function launchApp(appId, title, params) {
    callLuna(
      'luna://com.webos.applicationManager/launch',
      {
        id: appId,
        params: params || {}
      },
      function (n) {
        false === n.returnValue &&
          showToast(
            tr("Can't open {app}", {
              app: title || appId
            })
          );
      }
    );
  }
  function showToast(message) {
    var toast = getElement('toast');
    toast.textContent = message;
    toast.classList.add('shown');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      toast.classList.remove('shown');
    }, 2200);
  }
  function launchFirst(candidates, index, label) {
    var candidate = candidates[index];
    if (!candidate) {
      showToast(
        tr("Can't open {app}", {
          app: label
        })
      );
      return;
    }
    callLuna(
      'luna://com.webos.applicationManager/launch',
      {
        id: candidate.id,
        params: candidate.params || {}
      },
      function (r) {
        if (false === r.returnValue) {
          launchFirst(candidates, index + 1, label);
        }
      }
    );
  }
  function openNetworkSettings() {
    launchFirst(
      [
        {
          id: 'com.webos.app.firstuse-overlay',
          params: {
            target: 'network'
          }
        },
        {
          id: 'com.palm.app.settings',
          params: {
            target: 'network'
          }
        },
        {
          id: 'com.palm.app.settings',
          params: {}
        }
      ],
      0,
      tr('Network settings')
    );
  }
  // App editing uses the existing grid positions and focus highlight.
  var library,
    hideButton,
    editHint,
    picker,
    pickerList,
    pickerStatus,
    pickerClose;
  var pickerOpen = false,
    pickerGeneration = 0,
    pickerIndex = 0,
    pickerButtons = [];
  var hideSelected = false,
    undoState = null,
    undoBar,
    undoButton,
    pointerTimer = null,
    pointerNavigation = true,
    suppressClick = false,
    // Held arrows repeat; taps glide the rows, held runs stay immediate.
    lastKeyRepeat = false,
    lastArrow = 0,
    lastArrowAt = 0,
    // Some remote paths send a held key as keydown/keyup pairs without `repeat`; presses
    // of the same arrow this close together count as held.
    REPEAT_GAP = 150,
    scrollGlideTimer = null,
    edgeBumpTimer = null;
  // A scrolling list can cross a stationary cursor and generate mouseover.
  // Remote input owns focus until the pointer actually moves or is clicked.
  function pointerInput() {
    pointerNavigation = true;
    lastKeyRepeat = false;
    getElement('homeSurface').classList.remove('ctv-remote-navigation');
  }
  document.addEventListener('mousemove', pointerInput, true);
  document.addEventListener(
    'keydown',
    function (event) {
      if ([13, 27, 37, 38, 39, 40, 461].indexOf(event.keyCode) >= 0)
        pointerNavigation = false;
      if ([37, 38, 39, 40].indexOf(event.keyCode) >= 0) {
        // The event's own clock: only ever compared with the previous arrow's.
        var surface = getElement('homeSurface'),
          at = event.timeStamp || Date.now();
        lastKeyRepeat =
          event.repeat === true ||
          (event.keyCode === lastArrow && at - lastArrowAt < REPEAT_GAP);
        lastArrow = event.keyCode;
        lastArrowAt = at;
        surface.classList.add('ctv-remote-navigation');
        // A held arrow cuts any running glide short, even if this step does not scroll.
        if (lastKeyRepeat) {
          clearTimeout(scrollGlideTimer);
          surface.classList.remove('ctv-scroll-glide');
        }
      }
    },
    true
  );
  // Glide and bump belong to the Classic layout, unthemed or with a theme that opts into
  // Classic motion (layout.motion); other layouts and themes stay immediate.
  function classicMotion() {
    var surface = getElement('homeSurface');
    return (
      layoutPreset === 'dock-grid' &&
      (!surface.classList.contains('ctv-theme-active') ||
        surface.classList.contains('ctv-classic-motion'))
    );
  }
  // Remote scrolling: a tap glides to the new row; a held arrow (or a repeat during a
  // glide) jumps straight there, so the list never chases an unfinished scroll.
  function setScroll(offset) {
    var surface = getElement('homeSurface'),
      target = 'translateY(' + -offset + 'px)';
    if (
      stage.style.transform !== target &&
      surface.classList.contains('ctv-remote-navigation')
    ) {
      clearTimeout(scrollGlideTimer);
      if (lastKeyRepeat || !classicMotion())
        surface.classList.remove('ctv-scroll-glide');
      else {
        surface.classList.add('ctv-scroll-glide');
        scrollGlideTimer = setTimeout(function () {
          surface.classList.remove('ctv-scroll-glide');
        }, 320);
      }
    }
    stage.style.webkitTransform = stage.style.transform = target;
    if (window.HomeWeather)
      HomeWeather.setScroll(offset, DOCK_TOP, layoutPreset);
  }
  // A fresh press that cannot move nudges the grid or shelf toward that direction.
  function edgeBump(direction) {
    var surface = getElement('homeSurface');
    if (lastKeyRepeat || moveState || !classicMotion()) return;
    clearTimeout(edgeBumpTimer);
    [
      'ctv-edge-bump',
      'bump-down',
      'bump-left',
      'bump-right',
      'bump-shelf-left',
      'bump-shelf-right'
    ].forEach(function (name) {
      surface.classList.remove(name);
    });
    surface.offsetWidth;
    surface.classList.add('ctv-edge-bump');
    surface.classList.add('bump-' + direction);
    edgeBumpTimer = setTimeout(function () {
      surface.classList.remove('ctv-edge-bump');
      surface.classList.remove('bump-' + direction);
    }, 200);
  }
  document.addEventListener('mousedown', pointerInput, true);
  function bindPointerFocus(element, action) {
    function hover() {
      if (pointerNavigation) action();
    }
    element.addEventListener('mouseover', hover);
    element.addEventListener('mousemove', hover);
  }
  function screenIds() {
    return tiles
      .filter(function (item) {
        return !item.add;
      })
      .map(function (item) {
        return item.app.id;
      });
  }
  function saveScreen(hidden) {
    try {
      library.save(screenIds(), hidden || library.hidden());
      return true;
    } catch (error) {
      showToast(tr("Couldn't save changes. Please try again."));
      return false;
    }
  }
  function rebuild(focusId) {
    tilesContainer.innerHTML = '';
    tiles = library.visible().map(createTile);
    if (library.showAddApp()) {
      var el = document.createElement('div');
      el.className = 'item add-app ctv-tile';
      el.setAttribute('role', 'button');
      el.setAttribute('aria-label', tr('Add app'));
      el.innerHTML = ht(
        '<div class="card ctv-card"><svg class="ctv-icon" viewBox="0 0 48 48" aria-hidden="true"><path d="M24 10v28M10 24h28"/></svg></div><div class="name ctv-label">Add app</div>'
      );
      var item = {
        add: true,
        app: {
          title: tr('Add app')
        },
        el: el,
        color: [100, 110, 125]
      };
      bindPointerFocus(el, function () {
        if (
          !moveState &&
          !pickerOpen &&
          !undoState &&
          (focusZone !== 'grid' || tiles[focusedTile] !== item)
        ) {
          focusTile(tiles.length - 1);
        }
      });
      el.addEventListener('click', function () {
        if (!moveState) {
          openPicker();
        }
      });
      tilesContainer.appendChild(el);
      tiles.push(item);
    }
    layoutTiles();
    tiles.forEach(function (tile) {
      tile.el.classList.add('shown');
    });
    focusZone = 'none';
    var nextFocus = 0;
    for (var i = 0; i < tiles.length; i++) {
      if (tiles[i].app.id === focusId) {
        nextFocus = i;
        break;
      }
    }
    focusTile(nextFocus);
  }
  function activateTile(item) {
    if (item.add) {
      openPicker();
    } else if (item.app.id === 'airplay') {
      callLuna(
        'luna://airplay.service/showAirplayPage',
        {},
        function (result) {
          if (!result || !result.returnValue) {
            launchApp(item.app.id, item.app.title);
          }
        },
        5000
      );
    } else {
      launchApp(item.app.id, item.app.title);
    }
  }
  function cancelHold() {
    clearTimeout(okHoldTimer);
    okHoldTimer = null;
    clearTimeout(pointerTimer);
    pointerTimer = null;
    okPressed = false;
    clearPressed();
  }
  function clearRibbonEditor() {
    if (moveState) {
      var arrows = moveState.item.el.querySelectorAll('.ribbon-edit-arrow');
      for (var i = 0; i < arrows.length; i++)
        arrows[i].parentNode.removeChild(arrows[i]);
    }
    document.body.classList.remove('ribbon-editing');
    if (hideButton.parentNode !== document.body)
      document.body.appendChild(hideButton);
    hideButton.style.left = '';
    hideButton.style.top = '';
    hideButton.style.webkitTransition = hideButton.style.transition = '';
    editHint.style.top = '';
  }
  function positionRibbonEditor() {
    if (!moveState || !layoutGeometry.ribbon) return;
    var ribbon = layoutGeometry.ribbon,
      item = moveState.item,
      scene = getElement('homeSurface');
    // Keep the control in logical scene coordinates at every graphics resolution.
    if (hideButton.parentNode !== scene) scene.appendChild(hideButton);
    if (!item.el.querySelector('.ribbon-edit-arrow')) {
      ['left', 'right'].forEach(function (side) {
        var arrow = document.createElement('span');
        arrow.className = 'ribbon-edit-arrow ribbon-edit-' + side;
        arrow.setAttribute('aria-hidden', 'true');
        arrow.innerHTML =
          '<svg viewBox="0 0 24 40" aria-hidden="true"><path d="' +
          (side === 'left' ? 'M16 4L6 20l10 16' : 'M8 4l10 16L8 36') +
          '"/></svg>';
        arrow.style.top = -(ribbon.focusLift + 32) / 2 - 20 + 'px';
        arrow.style.webkitTransform = arrow.style.transform =
          'skewX(' + -ribbon.skewDeg + 'deg)';
        item.el.appendChild(arrow);
      });
    }
    hideButton.style.webkitTransition = hideButton.style.transition =
      item.el.style.transition;
    var slant =
      -(ribbon.cardHeight + ribbon.focusLift + 32) *
      Math.tan((ribbon.skewDeg * Math.PI) / 180);
    hideButton.style.left =
      tileLeft(focusedTile) + CARD_WIDTH / 2 + slant + 'px';
    hideButton.style.top = TILE_BASE - ribbon.focusLift - 96 + 'px';
    editHint.style.top = TILE_BASE - ribbon.focusLift - 178 + 'px';
  }
  function beginMoving(item) {
    clearPressed();
    if (!item || item.add || moveState || pickerOpen || undoState) {
      return;
    }
    moveState = {
      item: item,
      snapshot: tiles.slice()
    };
    setPartState(item.el, 'moving', true);
    document.body.classList.add('editing');
    document.body.classList.toggle('ribbon-editing', !!layoutGeometry.ribbon);
    if (!layoutGeometry.ribbon)
      editHint.textContent = tr(
        '← ↑ ↓ → Move   ·   OK Place   ·   Back Cancel   ·   ↓ Below last row to hide'
      );
    hideButton.hidden = false;
    editHint.hidden = !!layoutGeometry.ribbon;
    hideButton.classList.remove('focused');
    hideSelected = false;
    focusTile(tiles.indexOf(item));
  }
  function pointerMove(item) {
    if (!moveState || item.add) {
      return;
    }
    hideSelected = false;
    hideButton.classList.remove('focused');
    moveTile(tiles.indexOf(item));
  }
  function bindHold(item) {
    item.el.addEventListener('mousedown', function (event) {
      if (event.button !== 0 || moveState || pickerOpen || undoState) {
        return;
      }
      focusTile(tiles.indexOf(item));
      setPressed(item.el, true);
      clearTimeout(pointerTimer);
      suppressClick = false;
      pointerTimer = setTimeout(function () {
        pointerTimer = null;
        suppressClick = true;
        beginMoving(item);
      }, 600);
    });
    item.el.addEventListener('mouseleave', function () {
      clearTimeout(pointerTimer);
      pointerTimer = null;
      setPressed(item.el, false);
    });
    item.el.addEventListener('mouseup', function () {
      setPressed(item.el, false);
    });
  }
  // Engine-only press feedback; not a theme state.
  function setPressed(element, pressed) {
    element && element.classList.toggle('pressed', pressed);
  }
  function clearPressed() {
    var pressed = document.querySelectorAll('.pressed');
    for (var index = 0; index < pressed.length; index++)
      pressed[index].classList.remove('pressed');
  }
  function tileClick(item) {
    if (suppressClick) {
      suppressClick = false;
      return;
    }
    if (pickerOpen || undoState) {
      return;
    }
    if (moveState) {
      pointerMove(item);
      finishMoving(true);
    } else {
      activateTile(item);
    }
  }
  function selectHide() {
    if (!moveState) {
      return;
    }
    hideSelected = true;
    hideButton.classList.add('focused');
    hideButton.focus();
  }
  function hideApp() {
    if (!moveState) {
      return;
    }
    var item = moveState.item,
      snapshot = moveState.snapshot.slice(),
      oldHidden = library.hidden();
    var previous = tiles.slice();
    tiles = tiles.filter(function (tile) {
      return tile !== item;
    });
    if (!saveScreen(oldHidden.concat(item.app.id))) {
      tiles = previous;
      return;
    }
    clearRibbonEditor();
    moveState = null;
    hideSelected = false;
    setPartState(item.el, 'moving', false);
    document.body.classList.remove('editing');
    hideButton.hidden = true;
    editHint.hidden = true;
    item.el.remove();
    layoutTiles();
    focusZone = 'none';
    focusTile(Math.min(focusedTile, tiles.length - 1));
    undoState = {
      ids: snapshot
        .filter(function (tile) {
          return !tile.add;
        })
        .map(function (tile) {
          return tile.app.id;
        }),
      hidden: oldHidden,
      id: item.app.id
    };
    undoBar.hidden = false;
    undoButton.focus();
  }
  function dismissUndo() {
    if (!undoState) {
      return;
    }
    undoState = null;
    undoBar.hidden = true;
    focusTile(focusedTile);
  }
  function undoHide() {
    if (!undoState) {
      return;
    }
    try {
      var id = undoState.id;
      library.save(undoState.ids, undoState.hidden);
      dismissUndo();
      rebuild(id);
    } catch (error) {
      showToast(tr("Couldn't restore app. Please try again."));
    }
  }
  function closePicker() {
    if (!pickerOpen) {
      return;
    }
    pickerOpen = false;
    pickerGeneration++;
    picker.hidden = true;
    cancelHold();
    focusZone = 'none';
    focusTile(library.showAddApp() ? tiles.length - 1 : focusedTile);
  }
  function focusPicker(index) {
    pickerIndex = Math.max(0, Math.min(index, pickerButtons.length - 1));
    pickerButtons[pickerIndex].focus();
    pickerButtons[pickerIndex].scrollIntoView({
      block: 'nearest'
    });
  }
  function renderPicker(apps) {
    pickerList.innerHTML = '';
    pickerButtons = [];
    apps.forEach(function (app) {
      var button = document.createElement('button');
      button.className = 'app-choice ctv-library-row';
      button.dataset.appId = app.id;
      var icon = document.createElement('img');
      icon.className = 'ctv-icon';
      icon.src = app.icon || '';
      icon.alt = '';
      icon.onerror = function () {
        icon.style.visibility = 'hidden';
      };
      var title = document.createElement('span');
      title.className = 'ctv-label';
      title.textContent = app.title;
      button.appendChild(icon);
      button.appendChild(title);
      button.addEventListener('focus', function () {
        pickerIndex = pickerButtons.indexOf(button);
        setPartState(button, 'focused', true);
      });
      button.addEventListener('blur', function () {
        setPartState(button, 'focused', false);
      });
      button.addEventListener('click', function () {
        try {
          library.add(app.id);
          closePicker();
          rebuild(app.id);
          if (!app.icon && window.ROOT_VERSION) refreshInstalledApps(app.id);
          showToast(
            tr('{app} added', {
              app: app.title
            })
          );
        } catch (error) {
          pickerStatus.textContent = tr(
            "Couldn't save changes. Please try again."
          );
        }
      });
      pickerList.appendChild(button);
      pickerButtons.push(button);
    });
    pickerButtons.push(pickerClose);
    focusPicker(0);
  }
  function openPicker() {
    if (moveState || pickerOpen) {
      return;
    }
    dismissUndo();
    cancelHold();
    pickerOpen = true;
    var generation = ++pickerGeneration;
    picker.hidden = false;
    pickerStatus.textContent = tr('Checking installed apps…');
    pickerList.innerHTML = '';
    pickerButtons = [pickerClose];
    focusPicker(0);
    setFocusZone('picker');
    AppLibrary.installed(function (apps) {
      if (!pickerOpen || generation !== pickerGeneration) {
        return;
      }
      if (apps !== null) {
        library.refresh(apps);
      }
      var choices = library.available();
      pickerStatus.textContent =
        apps === null
          ? tr('Showing the saved list. Could not refresh apps from the TV.')
          : choices.length
            ? tr('Choose an app to add to Home.')
            : tr('All installed apps are already on Home.');
      renderPicker(choices);
    }, visibleAppIds());
  }
  function visibleAppIds(first) {
    var ids = library.visible().map(function (app) {
      return app.id;
    });
    return first
      ? [first].concat(
          ids.filter(function (id) {
            return id !== first;
          })
        )
      : ids;
  }
  function refreshInstalledApps(first) {
    AppLibrary.installed(function (apps) {
      if (apps !== null) {
        library.refresh(apps);
        // Keep inventory updates, but let the next normal rebuild render them
        // when a menu, edit or button hold already owns the interaction.
        if (
          focusZone === 'grid' &&
          !moveState &&
          !pickerOpen &&
          !undoState &&
          !okHoldTimer &&
          !pointerTimer &&
          !document.hidden &&
          !(window.RenewalPanel && window.RenewalPanel.isOpen())
        ) {
          rebuild(tiles[focusedTile] && tiles[focusedTile].app.id);
        }
      }
    }, visibleAppIds(first));
  }
  function initializeApps() {
    library = AppLibrary.create(
      localStorage,
      (window.TV_APPS && TV_APPS.apps) || [],
      CONFIG
    );
    window.HomeAppControls = {
      refresh: function () {
        var button = getElement('homeShowAddApp');
        if (button)
          button.setAttribute('aria-checked', String(library.showAddApp()));
      },
      toggle: function () {
        var error = getElement('homeAppsError');
        try {
          library.setShowAddApp(!library.showAddApp());
          if (error) error.textContent = '';
          var id = tiles[focusedTile] && tiles[focusedTile].app.id;
          rebuild(id);
          window.HomeAppControls.refresh();
        } catch (_) {
          if (error)
            error.textContent = tr("Couldn't save changes. Please try again.");
        }
      },
      add: openPicker
    };
    hideButton = document.createElement('button');
    hideButton.id = 'hideApp';
    hideButton.hidden = true;
    hideButton.innerHTML = ht(
      '<svg class="hide-standard-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3l18 18M10 5.2c5.5-1 10 6.8 10 6.8a20 20 0 0 1-3 3M6 6C3.4 8 2 12 2 12s4 7 10 7c1.4 0 2.7-.4 4-1M9 9a4.2 4.2 0 0 0 6 6"/></svg><svg class="ribbon-delete-mark" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5l14 14M19 5L5 19"/></svg><span>Hide from Home</span>'
    );
    bindPointerFocus(hideButton, function () {
      if (!hideSelected) selectHide();
    });
    hideButton.addEventListener('click', hideApp);
    document.body.appendChild(hideButton);
    editHint = document.createElement('div');
    editHint.id = 'editHint';
    editHint.hidden = true;
    editHint.textContent = tr(
      '← ↑ ↓ → Move   ·   OK Place   ·   Back Cancel   ·   ↓ Below last row to hide'
    );
    document.body.appendChild(editHint);
    undoBar = document.createElement('div');
    undoBar.id = 'appUndo';
    undoBar.hidden = true;
    undoBar.setAttribute('role', 'status');
    var message = document.createElement('span');
    message.textContent = tr('App hidden. Restore it with Add app.');
    undoBar.appendChild(message);
    undoButton = document.createElement('button');
    undoButton.textContent = tr('Undo');
    undoButton.addEventListener('click', undoHide);
    undoBar.appendChild(undoButton);
    document.body.appendChild(undoBar);
    picker = document.createElement('section');
    picker.id = 'appPicker';
    picker.hidden = true;
    picker.setAttribute('role', 'dialog');
    picker.setAttribute('aria-modal', 'true');
    picker.setAttribute('aria-labelledby', 'appPickerTitle');
    picker.innerHTML = ht(
      '<div class="app-picker-card ctv-library-panel"><h2 id="appPickerTitle">Add app</h2><p id="appPickerStatus" role="status"></p><div id="appPickerList"></div><button id="appPickerClose" class="ctv-library-close">Back to Home</button></div>'
    );
    picker.className = 'ctv-library';
    getElement('homeSurface').appendChild(picker);
    pickerList = getElement('appPickerList');
    pickerStatus = getElement('appPickerStatus');
    pickerClose = getElement('appPickerClose');
    pickerClose.addEventListener('click', closePicker);
    pickerClose.addEventListener('focus', function () {
      pickerIndex = pickerButtons.indexOf(pickerClose);
      setPartState(pickerClose, 'focused', true);
    });
    pickerClose.addEventListener('blur', function () {
      setPartState(pickerClose, 'focused', false);
    });
    document.addEventListener('mouseup', function () {
      clearTimeout(pointerTimer);
      pointerTimer = null;
      setTimeout(function () {
        suppressClick = false;
      }, 0);
    });
    window.addEventListener('blur', cancelHold);
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) {
        cancelHold();
        if (moveState) {
          finishMoving(false);
        }
      }
    });
    document.addEventListener(
      'keydown',
      function (event) {
        var key = event.keyCode;
        if (pickerOpen) {
          event.preventDefault();
          event.stopImmediatePropagation();
          if (key === 27 || key === 461) {
            closePicker();
          } else if (key === 13 && !event.repeat) {
            pickerButtons[pickerIndex].click();
          } else if (key === 38 || key === 37) {
            focusPicker(pickerIndex - 1);
          } else if (key === 40 || key === 39) {
            focusPicker(pickerIndex + 1);
          } else if (key === 9) {
            focusPicker(
              (pickerIndex + (event.shiftKey ? -1 : 1) + pickerButtons.length) %
                pickerButtons.length
            );
          }
        } else if (undoState) {
          event.preventDefault();
          event.stopImmediatePropagation();
          if (key === 13 && !event.repeat) {
            undoHide();
          } else if (key === 27 || key === 461 || (key >= 37 && key <= 40)) {
            dismissUndo();
          }
        } else if (moveState && hideSelected) {
          event.preventDefault();
          event.stopImmediatePropagation();
          if (key === 13 && !event.repeat) {
            hideApp();
          } else if (key === 27 || key === 461) {
            finishMoving(false);
          } else if (key === (layoutGeometry.ribbon ? 40 : 38)) {
            hideSelected = false;
            hideButton.classList.remove('focused');
            hideButton.blur();
            focusTile(focusedTile);
          }
        }
      },
      true
    );
    document.addEventListener(
      'keyup',
      function (event) {
        if (pickerOpen || undoState || hideSelected) {
          cancelHold();
          event.stopImmediatePropagation();
        }
      },
      true
    );
    rebuild();
    refreshInstalledApps();
  }
  // Tile rendering, icon colors and grid geometry.
  function createTile(app) {
    var element = document.createElement('div');
    element.className = 'item ctv-tile';
    element.dataset.appId = app.id;
    element.setAttribute('role', 'button');
    element.setAttribute('aria-label', app.title);
    var card = document.createElement('div');
    card.className = 'card ctv-card';
    var image = document.createElement('img'),
      tile = {
        app: app,
        el: element,
        card: card,
        color: null
      };
    image.className = 'ctv-icon';
    image.onload = function () {
      image.style.display = '';
      card.classList.remove('missing-icon');
      card.removeAttribute('data-initial');
      !(function (e, t) {
        var n = null,
          a = null;
        try {
          var i = document.createElement('canvas');
          i.width = 12;
          i.height = 12;
          var o = i.getContext('2d');
          o.drawImage(t, 0, 0, 12, 12);
          n = o.getImageData(0, 0, 12, 12).data;
          a = (function (e) {
            var t = e.naturalWidth,
              n = e.naturalHeight,
              a = document.createElement('canvas');
            a.width = t;
            a.height = n;
            var i = a.getContext('2d');
            i.drawImage(e, 0, 0);
            var o = i.getImageData(2, 2, 1, 1).data;
            return o[3] > 200
              ? o
              : i.getImageData(2, Math.floor(n / 2), 1, 1).data;
          })(t);
        } catch (e) {}
        var r = null;
        a && a[3] > 200
          ? (e.card.style.background =
              'rgb(' + a[0] + ',' + a[1] + ',' + a[2] + ')')
          : (e.card.classList.add('glyph'),
            (e.card.style.background = tileBackground(e.app.iconColor)),
            (r =
              '#2c2c2e' === tileBackground(e.app.iconColor)
                ? null
                : parseHexColor(e.app.iconColor)));
        t.classList[a && a[3] <= 200 ? 'add' : 'remove']('is-glyph');
        t.classList[
          a && a[3] > 200 && a[0] >= 240 && a[1] >= 240 && a[2] >= 240
            ? 'add'
            : 'remove'
        ]('is-light');
        var iconLuma =
          a && a[3] > 200
            ? (a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722) / 255
            : -1;
        t.classList[iconLuma >= 0 && iconLuma < 0.25 ? 'add' : 'remove'](
          'is-dark'
        );
        t.classList[iconLuma >= 0.25 && iconLuma < 0.5 ? 'add' : 'remove'](
          'is-mid'
        );
        t.classList[iconLuma >= 0.5 ? 'add' : 'remove']('is-bright');
        t.classList[t.naturalWidth > t.naturalHeight * 1.5 ? 'add' : 'remove'](
          'is-wide'
        );
        e.brandBackground = e.card.style.background;
        if (layoutPreset === 'channel-list') e.card.style.background = '';
        e.color =
          r ||
          (n
            ? (function (e) {
                for (
                  var t = null, n = -1, a = [0, 0, 0], i = 0, o = 0;
                  o < e.length;
                  o += 4
                )
                  if (!(e[o + 3] < 128)) {
                    var r = [e[o], e[o + 1], e[o + 2]];
                    a[0] += r[0];
                    a[1] += r[1];
                    a[2] += r[2];
                    i++;
                    var s = rgbToHsv(r),
                      l = s[1] * Math.min(1, 1.4 * s[2]);
                    l > n && ((n = l), (t = r));
                  }
                if (!i) {
                  return [68, 68, 68];
                }
                if (n < 0.25) {
                  var c = rgbToHsv([a[0] / i, a[1] / i, a[2] / i]);
                  return ((c[2] = Math.max(c[2], 0.55)), hsvToRgb(c));
                }
                var u = rgbToHsv(t);
                return (
                  (u[1] = Math.min(1, 1.1 * u[1])),
                  (u[2] = Math.max(0.5, u[2])),
                  hsvToRgb(u)
                );
              })(n)
            : parseHexColor(e.app.iconColor));
        tiles[focusedTile] === e && updateAmbient(e.color);
      })(tile, image);
    };
    image.onerror = function () {
      card.style.background = '';
      tile.brandBackground = '';
      image.style.display = 'none';
      card.classList.add('missing-icon');
      card.setAttribute('data-initial', app.title.charAt(0));
    };
    image.src = app.icon || 'missing-icon';
    card.appendChild(image);
    element.appendChild(card);
    var label = document.createElement('div');
    return (
      (label.className = 'name ctv-label'),
      (label.textContent = app.title),
      element.appendChild(label),
      bindPointerFocus(element, function () {
        'inputs' === focusZone ||
          pickerOpen ||
          undoState ||
          (moveState
            ? pointerMove(tile)
            : (focusZone !== 'grid' || tiles[focusedTile] !== tile) &&
              focusTile(tiles.indexOf(tile)));
      }),
      element.addEventListener('click', function () {
        tileClick(tile);
      }),
      bindHold(tile),
      tilesContainer.appendChild(element),
      tile
    );
  }
  function ribbonSlot(index) {
    return (
      (((index - ribbonStart) % tiles.length) + tiles.length) % tiles.length
    );
  }
  function stepRibbon(direction) {
    if (
      direction < 0 &&
      ribbonSlot(focusedTile) === 0 &&
      layoutGeometry.ribbon &&
      layoutGeometry.ribbon.edgeNavigation === 'shortcuts'
    ) {
      focusTopButton(2);
      return;
    }
    var index = (focusedTile + direction + tiles.length) % tiles.length;
    if (tiles.length > columnCount && ribbonSlot(index) >= columnCount) {
      ribbonStart =
        direction < 0
          ? index
          : (index - columnCount + 1 + tiles.length) % tiles.length;
    }
    focusTile(index);
  }
  function rowFor(index) {
    return layoutPreset === 'scenic-grid' ? 0 : Math.floor(index / columnCount);
  }
  function tileLeft(index) {
    return (
      GRID_LEFT +
      (layoutPreset === 'scenic-grid'
        ? ribbonSlot(index)
        : index % columnCount) *
        columnWidth +
      (columnWidth - CARD_WIDTH) / 2
    );
  }
  function tileTop(index) {
    var row = rowFor(index);
    return (
      TILE_BASE +
      (CARD_HEIGHT + ROW_GAP) * row +
      (row > 0 ? layoutGeometry.rowExtra : 0)
    );
  }
  function layoutTiles() {
    tiles.forEach(function (e, t) {
      if (layoutPreset !== 'scenic-grid') tilesContainer.appendChild(e.el);
      else if (tilesContainer.children[t] !== e.el)
        tilesContainer.insertBefore(e.el, tilesContainer.children[t] || null);
      e.el.style.width = CARD_WIDTH + 'px';
      e.el.querySelector('.card').style.height = CARD_HEIGHT + 'px';
      if (e.card && typeof e.brandBackground === 'string')
        e.card.style.background =
          layoutPreset === 'channel-list' ? '' : e.brandBackground;
      var slot = layoutPreset === 'scenic-grid' ? ribbonSlot(t) : null;
      var previousSlot = Number(e.el.getAttribute('data-ribbon-slot'));
      e.el.style.webkitTransition = e.el.style.transition =
        slot === null
          ? ''
          : e.el.hasAttribute('data-ribbon-slot') &&
              Math.abs(previousSlot - slot) === 1 &&
              previousSlot <= columnCount &&
              slot <= columnCount
            ? 'left 160ms ease-out'
            : 'none';
      e.el.style.pointerEvents =
        slot !== null && slot >= columnCount ? 'none' : '';
      e.el.style.visibility =
        slot !== null && slot >= columnCount + (layoutGeometry.ribbon ? 1 : 0)
          ? 'hidden'
          : '';
      if (slot === null) e.el.removeAttribute('data-ribbon-slot');
      else e.el.setAttribute('data-ribbon-slot', slot);
      e.el.style.left = tileLeft(t) + 'px';
      e.el.style.top = tileTop(t) + 'px';
      e.el.classList.toggle('dock', layoutGeometry.dock && 0 === rowFor(t));
      e.el.setAttribute('data-channel', t < 9 ? '0' + (t + 1) : String(t + 1));
    });
    var dockBand = getElement('dockBand'),
      dockCount = Math.min(columnCount, tiles.length);
    dockBand.style.display =
      dockCount && layoutGeometry.dock ? 'block' : 'none';
    dockBand.style.left = tileLeft(0) - DOCK_PADDING + 'px';
    dockBand.style.top = DOCK_TOP + 'px';
    dockBand.style.width =
      (dockCount - 1) * columnWidth + CARD_WIDTH + DOCK_PADDING * 2 + 'px';
    dockBand.style.height = DOCK_HEIGHT + 'px';
  }
  if (layoutState)
    layoutState.onchange = function (state) {
      updateGeometry(state.columns, state.preset, state.ribbon);
      scrollOffset = 0;
      layoutTiles();
      renderShelf();
      'shelf' !== focusZone && focusTile(focusedTile);
      updateClock();
      window.HomeInputShelf && window.HomeInputShelf.refresh();
      var event = document.createEvent('Event');
      event.initEvent('home-layout-change', false, false);
      document.dispatchEvent(event);
    };
  function tileBackground(hex) {
    var rgb = parseHexColor(hex);
    if (!rgb) {
      return '#2c2c2e';
    }
    var hsv = rgbToHsv(rgb);
    return hsv[1] < 0.15 && (hsv[2] > 0.85 || hsv[2] < 0.1)
      ? '#2c2c2e'
      : 'rgb(' + rgb.join(',') + ')';
  }
  function parseHexColor(hex) {
    var match = /^#?([0-9a-f]{6})$/i.exec(hex || '');
    if (!match) {
      return null;
    }
    var value = parseInt(match[1], 16);
    return [(value >> 16) & 255, (value >> 8) & 255, 255 & value];
  }
  function rgbToHsv(rgb) {
    var red = rgb[0] / 255,
      green = rgb[1] / 255,
      blue = rgb[2] / 255,
      maximum = Math.max(red, green, blue),
      delta = maximum - Math.min(red, green, blue),
      hue = 0;
    return (
      delta &&
        ((hue =
          maximum === red
            ? ((green - blue) / delta) % 6
            : maximum === green
              ? (blue - red) / delta + 2
              : (red - green) / delta + 4),
        (hue *= 60) < 0 && (hue += 360)),
      [hue, maximum ? delta / maximum : 0, maximum]
    );
  }
  function hsvToRgb(hsv) {
    var hue = hsv[0],
      saturation = hsv[1],
      value = hsv[2],
      chroma = value * saturation,
      secondary = chroma * (1 - Math.abs(((hue / 60) % 2) - 1)),
      offset = value - chroma;
    return (
      hue < 60
        ? [chroma, secondary, 0]
        : hue < 120
          ? [secondary, chroma, 0]
          : hue < 180
            ? [0, chroma, secondary]
            : hue < 240
              ? [0, secondary, chroma]
              : hue < 300
                ? [secondary, 0, chroma]
                : [chroma, 0, secondary]
    ).map(function (e) {
      return Math.round(255 * (e + offset));
    });
  }
  // Focus follows both remote navigation and Magic Remote hover.
  function setPartState(element, state, enabled) {
    if (!element) return;
    element.classList.toggle(state, enabled);
    element.classList.toggle('is-' + state, enabled);
    var label = element.querySelector('.ctv-label');
    if (label) label.classList.toggle('is-' + state, enabled);
    var card = element.querySelector('.ctv-card');
    if (card) card.classList.toggle('is-' + state, enabled);
  }
  function focusTile(index) {
    if (!tiles.length) {
      focusGlassVisible = false;
      focusGlass.style.opacity = '0';
      scrollOffset = 0;
      stage.style.webkitTransform = stage.style.transform = 'translateY(0px)';
      clearTimeout(heroTitle.swap);
      heroVisible = false;
      heroTitle.style.opacity = '0';
      if (channelArtwork) channelArtwork.style.visibility = 'hidden';
      getElement('viewport').removeAttribute('data-position');
      heroTitle.removeAttribute('data-position');
      focusTopButton(0);
      return;
    }
    if (tiles.length) {
      index = Math.max(0, Math.min(index, tiles.length - 1));
      setFocusZone('grid');
      tiles[focusedTile] &&
        setPartState(tiles[focusedTile].el, 'focused', false);
      focusedTile = index;
      if (layoutPreset === 'scenic-grid') {
        ribbonStart = ribbonStart % tiles.length;
        if (ribbonSlot(index) >= Math.min(columnCount, tiles.length))
          ribbonStart = (index - columnCount + 1 + tiles.length) % tiles.length;
        layoutTiles();
      }
      setPartState(tiles[index].el, 'focused', true);
      var top = tileTop(index),
        row = rowFor(index);
      if (layoutPreset === 'scenic-grid') {
        var position = '← ' + (index + 1) + ' / ' + tiles.length + ' →';
        getElement('viewport').setAttribute('data-position', position);
        getElement('ribbonPosition').textContent = position;
      }
      var ceiling = layoutGeometry.scrollTop;
      var floor = moveState ? 850 : layoutGeometry.scrollBottom;
      if (layoutPreset === 'scenic-grid')
        scrollOffset = layoutGeometry.ribbon
          ? 0
          : top - (moveState ? 640 : TILE_BASE);
      else if (row === 0 && !moveState) scrollOffset = 0;
      else {
        if (top - scrollOffset + CARD_HEIGHT + 70 > floor)
          scrollOffset = top + CARD_HEIGHT + 70 - floor;
        if (top - scrollOffset - 24 < ceiling)
          scrollOffset = Math.max(0, top - 24 - ceiling);
      }
      setScroll(scrollOffset);
      var header = document.querySelector('header'),
        headerBottom = header.offsetTop + header.offsetHeight;
      document.body.classList.toggle(
        'scrolled',
        layoutPreset === 'dock-grid' &&
          DOCK_TOP - scrollOffset < headerBottom + 24
      );
      coverShelf(false);
      var glassWidth = FOCUS_SCALE * CARD_WIDTH + FOCUS_PADDING * 2,
        glassHeight = FOCUS_SCALE * CARD_HEIGHT + FOCUS_PADDING * 2,
        glassLeft = tileLeft(index) + CARD_WIDTH / 2 - glassWidth / 2,
        glassTop = top + CARD_HEIGHT / 2 - glassHeight / 2;
      focusGlass.style.width = glassWidth + 'px';
      focusGlass.style.height = glassHeight + 'px';
      var glassAt = 'translate(' + glassLeft + 'px,' + glassTop + 'px)';
      // Remote focus is immediate: the glass lands on the new card at card size, then
      // grows with it, so it never trails the card. A pointer keeps the glide.
      if (
        focusGlassVisible &&
        glassAt !== focusGlass.glassAt &&
        getElement('homeSurface').classList.contains('ctv-remote-navigation')
      ) {
        focusGlass.style.webkitTransition = focusGlass.style.transition =
          'none';
        focusGlass.style.webkitTransform = focusGlass.style.transform =
          glassAt +
          ' scale(' +
          (CARD_WIDTH + FOCUS_PADDING * 2) / glassWidth +
          ',' +
          (CARD_HEIGHT + FOCUS_PADDING * 2) / glassHeight +
          ')';
        focusGlass.offsetWidth;
        focusGlass.style.webkitTransition = focusGlass.style.transition = '';
      }
      focusGlass.glassAt = glassAt;
      focusGlass.style.webkitTransform = focusGlass.style.transform =
        glassAt + ' scale(1,1)';
      focusGlassVisible ||
        ((focusGlass.style.webkitTransition = focusGlass.style.transition =
          'none'),
        focusGlass.offsetWidth,
        (focusGlass.style.webkitTransition = focusGlass.style.transition = ''),
        (focusGlass.style.opacity = '1'),
        (focusGlassVisible = true));
      if (layoutPreset === 'channel-list') {
        if (!channelArtwork) {
          channelArtwork = document.createElement('img');
          channelArtwork.id = 'channelArtwork';
          channelArtwork.className = 'ctv-icon';
          channelArtwork.alt = '';
          channelArtwork.setAttribute('aria-hidden', 'true');
          channelArtwork.onload = function () {
            channelArtwork.style.visibility =
              channelArtwork.naturalWidth > 0 ? 'visible' : 'hidden';
          };
          channelArtwork.onerror = function () {
            channelArtwork.style.visibility = 'hidden';
          };
          getElement('homeSurface').appendChild(channelArtwork);
        }
        if (tiles[index].app.icon) {
          channelArtwork.style.visibility =
            channelArtwork.complete &&
            channelArtwork.naturalWidth > 0 &&
            channelArtwork.getAttribute('src') === tiles[index].app.icon
              ? 'visible'
              : 'hidden';
          if (channelArtwork.getAttribute('src') !== tiles[index].app.icon)
            channelArtwork.src = tiles[index].app.icon;
        } else {
          channelArtwork.style.visibility = 'hidden';
          channelArtwork.removeAttribute('src');
        }
        heroTitle.setAttribute(
          'data-position',
          index + 1 + ' / ' + tiles.length
        );
      }
      layoutPreset === 'channel-list' ||
      layoutPreset === 'scenic-grid' ||
      (layoutPreset === 'dock-grid' && 0 === row)
        ? (function (e) {
            var t = e.app.title,
              weatherRegion = window.HomeWeather && HomeWeather.reservation();
            heroTitle.style.fontSize =
              layoutPreset === 'scenic-grid' && t.length > 100
                ? t.length > 160
                  ? '20px'
                  : '26px'
                : '';
            heroTitle.style.top =
              (layoutPreset === 'channel-list'
                ? Math.max(
                    548,
                    weatherRegion && weatherRegion.format !== 'text'
                      ? weatherRegion.bottom + 36
                      : 0
                  )
                : layoutPreset === 'scenic-grid'
                  ? TILE_BASE - 142
                  : TILE_BASE - HERO_OFFSET) + 'px';
            if (
              layoutPreset === 'channel-list' ||
              layoutPreset === 'scenic-grid'
            ) {
              clearTimeout(heroTitle.swap);
              heroTitle.style.webkitTransition = heroTitle.style.transition =
                '';
              heroTitle.textContent = t;
              heroTitle.style.webkitTransform = heroTitle.style.transform =
                'none';
              heroTitle.style.opacity = '1';
              heroVisible = true;
            } else
              heroVisible
                ? heroTitle.textContent !== t &&
                  (clearTimeout(heroTitle.swap),
                  // Quick fade out, then the new title glides in with the focus motion.
                  (heroTitle.style.webkitTransition =
                    heroTitle.style.transition =
                      'opacity 100ms linear, transform 100ms linear'),
                  (heroTitle.style.opacity = '0'),
                  (heroTitle.style.webkitTransform = heroTitle.style.transform =
                    'translateX(-12px)'),
                  (heroTitle.swap = setTimeout(function () {
                    heroTitle.textContent = t;
                    heroTitle.style.webkitTransition =
                      heroTitle.style.transition = 'none';
                    heroTitle.style.webkitTransform =
                      heroTitle.style.transform = 'translateX(12px)';
                    heroTitle.offsetWidth;
                    heroTitle.style.webkitTransition =
                      heroTitle.style.transition = '';
                    heroTitle.style.webkitTransform =
                      heroTitle.style.transform = 'none';
                    heroTitle.style.opacity = '1';
                  }, 100)))
                : ((heroTitle.style.webkitTransition =
                    heroTitle.style.transition =
                      ''),
                  (heroTitle.textContent = t),
                  (heroTitle.style.webkitTransform = heroTitle.style.transform =
                    'none'),
                  (heroTitle.style.opacity = '1'),
                  (heroVisible = true));
            updateAmbient(e.color);
          })(tiles[index])
        : heroVisible &&
          ((heroVisible = false), (heroTitle.style.opacity = '0'));
      updateAmbient(tiles[index].color);
      positionRibbonEditor();
    }
  }
  // The glow follows once the focus rests, so its full-screen crossfade never competes
  // with focus motion for a 4K TV's GPU. Home then bakes the settled glow into a plain
  // (uncomposited) #ambientBase beneath the layers and hides both layers (style.css keeps
  // the layers for themes without Classic motion). The base is also .ctv-ambient, so a
  // theme's ambient rule (which outranks the trusted #ambientBase rule) styles it like the
  // layers, but only while it carries .baked; #homeSurface's background stays the wallpaper's.
  function updateAmbient(rgb, settled) {
    clearTimeout(ambientTimer);
    if (!rgb) return;
    if (!settled) {
      ambientTimer = setTimeout(function () {
        updateAmbient(rgb, true);
      }, AMBIENT_SETTLE);
      return;
    }
    var color = rgb.join(',');
    if (color === ambientColor) return;
    ambientColor = color;
    var current = ambientLayers[ambientIndex],
      nextLayer = ambientLayers[1 - ambientIndex];
    if (!getElement('ambientBase')) {
      var base = document.createElement('div');
      base.id = 'ambientBase';
      base.className = 'ambient-base ctv-ambient';
      current.parentNode.insertBefore(base, ambientLayers[0]);
    }
    var ambientSheet = getElement('ctv-ambient-style');
    if (!ambientSheet) {
      ambientSheet = document.createElement('style');
      ambientSheet.id = 'ctv-ambient-style';
      document.head.appendChild(ambientSheet);
    }
    function glow(value) {
      return (
        'background-image:radial-gradient(circle 1190px at 32% 42%, rgba(' +
        value +
        ',0.36) 0%, rgba(' +
        value +
        ',0.15) 50%, rgba(' +
        value +
        ',0) 100%);}'
      );
    }
    // A scoped author rule can override this trusted default; inline CSS could not.
    // The baked page glow goes away in the same frame its layer reappears.
    var rules = ambientSheet.textContent.split('\n').filter(function (rule) {
      return (
        rule &&
        rule.indexOf('#' + nextLayer.id + '{') !== 0 &&
        rule.indexOf(AMBIENT_BAKED) !== 0
      );
    });
    rules.push('#' + nextLayer.id + '{' + glow(color));
    ambientSheet.textContent = rules.join('\n');
    getElement('ambientBase').classList.remove('baked');
    if (current.classList.contains('baked')) {
      current.style.webkitTransition = current.style.transition = 'none';
      current.classList.remove('baked');
      getComputedStyle(current).opacity;
      current.style.webkitTransition = current.style.transition = '';
    }
    nextLayer.classList.remove('baked');
    nextLayer.style.opacity = '1';
    current.style.opacity = '0';
    ambientIndex = 1 - ambientIndex;
    clearTimeout(ambientBake);
    ambientBake = setTimeout(function () {
      ambientSheet.textContent = ambientSheet.textContent
        .split('\n')
        .filter(function (rule) {
          return rule && rule.indexOf(AMBIENT_BAKED) !== 0;
        })
        .concat(AMBIENT_BAKED + glow(color))
        .join('\n');
      nextLayer.classList.add('baked');
      getElement('ambientBase').classList.add('baked');
    }, AMBIENT_FADE);
  }
  function focusTopButton(index) {
    setFocusZone('top');
    document.body.classList.remove('scrolled');
    setPartState(topButtons[focusedTopButton], 'focused', false);
    focusedTopButton = Math.max(
      topButtons[0].hidden ? 1 : 0,
      Math.min(index, topButtons.length - 1)
    );
    setPartState(topButtons[focusedTopButton], 'focused', true);
  }
  function setFocusZone(zone) {
    // Some paths reset focusZone directly, so clear a shelf highlight and preview on every exit.
    if ('shelf' !== zone) {
      setPartState(
        shelfTiles[focusedShelf] && shelfTiles[focusedShelf].el,
        'focused',
        false
      );
      stopPreview();
      if (!restoring) returnInput = null;
    }
    focusZone !== zone &&
      ('top' === focusZone &&
        setPartState(topButtons[focusedTopButton], 'focused', false),
      'grid' === focusZone &&
        (tiles[focusedTile] &&
          setPartState(tiles[focusedTile].el, 'focused', false),
        (focusGlassVisible = false),
        (focusGlass.style.opacity = '0')),
      (focusZone = zone));
    if ('shelf' !== zone) layoutShelf();
  }
  function nearestTopButton(center) {
    var nearest = 0,
      distance = 1 / 0;
    topButtons.forEach(function (button, index) {
      if (button.hidden) return;
      var rect = sceneRect(button),
        offset = Math.abs(rect.left + rect.width / 2 - center);
      if (offset < distance) {
        distance = offset;
        nearest = index;
      }
    });
    return nearest;
  }
  function inputEntries() {
    var entries = inputSources ? inputSources.list() : [];
    if (CONFIG.liveTvApp)
      entries.push({
        appId: CONFIG.liveTvApp,
        label: tr('Live TV'),
        deviceName: null,
        connected: null,
        kind: 'tv',
        source: null
      });
    return entries;
  }
  function stopPreview() {
    inputPreview && inputPreview.stop();
  }
  // Dialogs share ownership regardless of how they opened (including manual Helper
  // relaunches and theme trials that deliberately resume ThemeRuntime). The hardware
  // video plane cannot be covered by the normal dialog backdrop.
  function previewDialogOpen() {
    var dialogs = document.querySelectorAll(
      '[role="dialog"], [role="alertdialog"]'
    );
    for (var index = 0; index < dialogs.length; index++) {
      if (dialogs[index].getClientRects().length) return true;
    }
    return false;
  }
  var previewDialogVisible = previewDialogOpen();
  new MutationObserver(function () {
    var open = previewDialogOpen();
    if (open === previewDialogVisible) return;
    previewDialogVisible = open;
    if (open) stopPreview();
    else if ('shelf' === focusZone && shelfTiles[focusedShelf] && inputPreview)
      inputPreview.focus(shelfTiles[focusedShelf].input);
  }).observe(document.body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['hidden', 'class', 'style', 'role']
  });
  // Launching hands the input to its own app; release the preview first. Returning to
  // Home lands back on this input's tile, so switching back is one press.
  function launchInput(input, element) {
    stopPreview();
    if (element) {
      setPressed(element, true);
      setTimeout(function () {
        setPressed(element, false);
      }, 160);
    }
    launchApp(input.appId, input.label);
    returnInput = input.appId;
  }
  function inputDetail(input) {
    return input.connected === false
      ? tr('Not connected')
      : input.deviceName || (input.connected === true ? tr('Connected') : '');
  }
  function shelfVisible() {
    return !!shelf && !shelf.hidden;
  }
  // Grow and push: while the shelf has focus, the focused tile is wider and the
  // tiles after it move right. Earlier tiles never move, so a pointer stays put.
  function shelfTileLeft(index) {
    return (
      SHELF_INSET +
      index * (SHELF_TILE_WIDTH + SHELF_GAP) +
      ('shelf' === focusZone && index > focusedShelf
        ? SHELF_FOCUS_WIDTH - SHELF_TILE_WIDTH
        : 0)
    );
  }
  function shelfTileWidth(index) {
    return 'shelf' === focusZone && index === focusedShelf
      ? SHELF_FOCUS_WIDTH
      : SHELF_TILE_WIDTH;
  }
  function shelfCenter(index) {
    return (
      GRID_LEFT -
      SHELF_INSET +
      shelfTileLeft(index) -
      shelfOffset +
      shelfTileWidth(index) / 2
    );
  }
  function nearestShelf(center) {
    var nearest = 0,
      distance = 1 / 0;
    shelfTiles.forEach(function (tile, index) {
      var offset = Math.abs(shelfCenter(index) - center);
      if (offset < distance) {
        distance = offset;
        nearest = index;
      }
    });
    return nearest;
  }
  function nearestDockTile(center) {
    var nearest = 0,
      distance = 1 / 0;
    for (var index = 0; index < Math.min(columnCount, tiles.length); index++) {
      var offset = Math.abs(tileLeft(index) + CARD_WIDTH / 2 - center);
      if (offset < distance) {
        distance = offset;
        nearest = index;
      }
    }
    return nearest;
  }
  function createShelfTile(input, index) {
    var element = document.createElement('div'),
      detail = inputDetail(input);
    element.className = 'input-tile ctv-input-tile';
    element.setAttribute('role', 'button');
    element.setAttribute(
      'aria-label',
      detail ? input.label + ', ' + detail : input.label
    );
    element.innerHTML =
      '<svg class="input-glyph" viewBox="0 0 24 24" aria-hidden="true"><path d="' +
      (INPUT_ICONS[input.kind] || INPUT_ICONS.hdmi) +
      '"/></svg><span class="input-dot" aria-hidden="true"></span>';
    var name = document.createElement('span');
    name.className = 'input-name';
    name.textContent = input.label;
    element.appendChild(name);
    var status = document.createElement('span');
    status.className = 'input-detail ctv-input-status';
    status.textContent = detail;
    element.appendChild(status);
    setPartState(element, 'connected', input.connected === true);
    setPartState(element, 'disconnected', input.connected === false);
    bindPointerFocus(element, function () {
      if (
        !moveState &&
        !pickerOpen &&
        !undoState &&
        'inputs' !== focusZone &&
        ('shelf' !== focusZone || focusedShelf !== index)
      )
        focusShelf(index);
    });
    element.addEventListener('click', function () {
      if (!moveState && !pickerOpen && !undoState) launchInput(input);
    });
    element.addEventListener('mousedown', function (event) {
      if (event.button === 0) setPressed(element, true);
    });
    element.addEventListener('mouseup', function () {
      setPressed(element, false);
    });
    element.addEventListener('mouseleave', function () {
      setPressed(element, false);
    });
    return { el: element, input: input };
  }
  // Rebuilds in place; focus follows the same source, or its old position if it left.
  // A running preview of the same source moves to the rebuilt tile in the same task,
  // so a CEC name or status update never blanks or restarts it.
  function renderShelf() {
    if (!shelf) return;
    var focusedId =
        shelfTiles[focusedShelf] && shelfTiles[focusedShelf].input.appId,
      enabled = window.HomeInputShelf && window.HomeInputShelf.enabled(),
      entries = enabled ? inputEntries() : [],
      next = Math.min(focusedShelf, Math.max(0, entries.length - 1));
    shelfTrack.innerHTML = '';
    shelfTiles = entries.map(createShelfTile);
    shelfTiles.forEach(function (tile, index) {
      shelfTrack.appendChild(tile.el);
      if (tile.input.appId === focusedId) next = index;
    });
    shelf.hidden = !shelfTiles.length;
    topButtons[0].hidden = !shelf.hidden;
    if (topButtons[0].hidden && focusZone === 'inputs') closeInputs();
    if (topButtons[0].hidden && focusZone === 'top' && focusedTopButton === 0)
      focusTopButton(1);
    shelf.setAttribute('aria-label', tr('Inputs'));
    shelf.style.left = GRID_LEFT - SHELF_INSET + 'px';
    shelf.style.top =
      (window.HomeWeather ? HomeWeather.shelfTop() : SHELF_TOP) + 'px';
    shelf.style.width = GRID_WIDTH + SHELF_INSET * 2 + 'px';
    focusedShelf = next;
    shelfLayout = null;
    if ('shelf' === focusZone && shelfTiles.length) {
      // Keeps a preview of the same eligible source (else stops it), then moves it in.
      focusShelf(focusedShelf, true);
      inputPreview && inputPreview.remount();
    } else if ('shelf' === focusZone) {
      stopPreview();
      focusTile(rowFor(focusedTile) === 0 ? focusedTile : 0);
    } else layoutShelf();
  }
  // Applies the grow-and-push geometry; skipped when nothing changed since the last pass.
  // Tiles snap to their final size (sharp text at rest) and a compositor-only transform
  // animates from where they were on screen, so growing never relayouts per frame.
  function layoutShelf() {
    if (!shelf) return;
    var key =
      ('shelf' === focusZone ? focusedShelf : -1) + ':' + shelfTiles.length;
    if (key === shelfLayout) return;
    var animate = shelfLayout !== null && !shelf.hidden;
    shelfLayout = key;
    // Measured against the track, so a shelf scroll in flight is not added twice.
    function boxes() {
      var origin = shelfTrack.getBoundingClientRect();
      return shelfTiles.map(function (tile) {
        var box = tile.el.getBoundingClientRect();
        return {
          x: box.left - origin.left + box.width / 2,
          y: box.top - origin.top + box.height / 2,
          width: box.width,
          height: box.height
        };
      });
    }
    var before = animate ? boxes() : null;
    shelfTiles.forEach(function (tile, index) {
      var grown = shelfTileWidth(index) === SHELF_FOCUS_WIDTH;
      // Everything but transform keeps style.css's transitions, so the focus fill still fades.
      tile.el.style.webkitTransition = tile.el.style.transition = SHELF_FADES;
      tile.el.style.webkitTransform = tile.el.style.transform = 'none';
      tile.el.style.left = shelfTileLeft(index) + 'px';
      tile.el.style.width = shelfTileWidth(index) + 'px';
      tile.el.style.height =
        (grown ? SHELF_FOCUS_HEIGHT : SHELF_TILE_HEIGHT) + 'px';
    });
    if (animate) {
      var after = boxes(),
        scale = shelfTrack.offsetWidth
          ? shelfTrack.getBoundingClientRect().width / shelfTrack.offsetWidth
          : 1;
      shelfTiles.forEach(function (tile, index) {
        var from = before[index],
          to = after[index];
        if (
          !to.width ||
          !to.height ||
          (Math.abs(from.x - to.x) < 0.5 &&
            Math.abs(from.y - to.y) < 0.5 &&
            Math.abs(from.width - to.width) < 0.5 &&
            Math.abs(from.height - to.height) < 0.5)
        )
          return;
        // Centre-based, so the default transform origin (also used by the press dip) works.
        tile.el.style.webkitTransform = tile.el.style.transform =
          'translate(' +
          (from.x - to.x) / scale +
          'px,' +
          (from.y - to.y) / scale +
          'px) scale(' +
          from.width / to.width +
          ',' +
          from.height / to.height +
          ')';
      });
      shelfTrack.offsetWidth;
    }
    shelfTiles.forEach(function (tile) {
      tile.el.style.webkitTransition = tile.el.style.transition = '';
      tile.el.style.webkitTransform = tile.el.style.transform = '';
    });
    scrollShelf();
  }
  // Whole-tile scrolling over variable widths: keep the first visible tile unless the
  // focused one would leave the window, and never scroll past the last tile.
  function scrollShelf() {
    var last = shelfTiles.length - 1,
      first = Math.round(shelfOffset / (SHELF_TILE_WIDTH + SHELF_GAP));
    function span(from, to) {
      return shelfTileLeft(to) + shelfTileWidth(to) - shelfTileLeft(from);
    }
    first = Math.max(0, Math.min(first, focusedShelf, last));
    while (first < focusedShelf && span(first, focusedShelf) > GRID_WIDTH)
      first++;
    while (first > 0 && span(first - 1, last) <= GRID_WIDTH) first--;
    shelfOffset = last < 0 ? 0 : shelfTileLeft(first) - SHELF_INSET;
    shelfTrack.style.webkitTransform = shelfTrack.style.transform =
      'translateX(' + -shelfOffset + 'px)';
    shelf.classList.toggle('overflow-left', first > 0);
    shelf.classList.toggle(
      'overflow-right',
      last >= 0 && span(first, last) > GRID_WIDTH
    );
  }
  // Lower rows scroll the shelf beneath the header, and the translucent Inputs
  // dropdown overlaps it; fade it in both cases rather than stack content.
  function coverShelf(covered) {
    if (!shelf) return;
    var header = document.querySelector('header');
    shelf.classList.toggle(
      'covered',
      covered ||
        (window.HomeWeather ? HomeWeather.shelfTop() : SHELF_TOP) +
          SHELF_WINDOW_TOP -
          scrollOffset <
          Math.max(
            header.offsetTop + header.offsetHeight,
            window.HomeWeather ? HomeWeather.bottom() : 0
          ) +
            16
    );
    // The video plane ignores the fade, so a covered shelf has no preview.
    if (shelf.classList.contains('covered')) stopPreview();
    // Classic fades the screen edges while more rows lie beyond them, so the grid reads
    // as one continuous list rather than a cut-off page.
    var viewport = getElement('viewport'),
      lastRow = tiles.length ? rowFor(tiles.length - 1) : 0;
    viewport.classList.toggle(
      'row-peek',
      layoutPreset === 'dock-grid' &&
        ('grid' === focusZone
          ? rowFor(focusedTile) < lastRow
          : scrollOffset === 0 && lastRow > 0)
    );
    viewport.classList.toggle(
      'row-above',
      layoutPreset === 'dock-grid' && scrollOffset > 0
    );
  }
  function refreshInputStatus() {
    if (inputSources && !document.hidden && windowFocused)
      inputSources.refresh();
  }
  function focusShelf(index, remount) {
    if (!shelfTiles.length) return;
    var changed = !remount && (focusZone !== 'shelf' || focusedShelf !== index);
    setFocusZone('shelf');
    setPartState(
      shelfTiles[focusedShelf] && shelfTiles[focusedShelf].el,
      'focused',
      false
    );
    focusedShelf = Math.max(0, Math.min(index, shelfTiles.length - 1));
    setPartState(shelfTiles[focusedShelf].el, 'focused', true);
    layoutShelf();
    scrollOffset = 0;
    setScroll(0);
    document.body.classList.remove('scrolled');
    coverShelf(false);
    clearTimeout(heroTitle.swap);
    heroVisible = false;
    heroTitle.style.opacity = '0';
    inputPreview && inputPreview.focus(shelfTiles[focusedShelf].input);
    if (changed) refreshInputStatus();
  }
  window.HomeInputShelf = {
    enabled: function () {
      return !!layoutState && layoutState.state().inputs === 'shelf';
    },
    previewEnabled: function () {
      return !!window.InputSources && InputSources.previewEnabled(localStorage);
    },
    // Only a theme with a shelf exposes the live-preview preference.
    refresh: function () {
      refreshInputStatus();
      var preview = getElement('homePreviewInputs');
      if (preview) {
        preview.setAttribute(
          'aria-checked',
          String(window.HomeInputShelf.previewEnabled())
        );
        preview.hidden = !window.HomeInputShelf.enabled();
      }
    },
    togglePreview: function () {
      var error = getElement('homeAppsError');
      try {
        InputSources.setPreviewEnabled(
          localStorage,
          !window.HomeInputShelf.previewEnabled()
        );
        if (error) error.textContent = '';
      } catch (_) {
        if (error)
          error.textContent = tr("Couldn't save changes. Please try again.");
      }
      stopPreview();
      if ('shelf' === focusZone && shelfTiles[focusedShelf] && inputPreview)
        inputPreview.focus(shelfTiles[focusedShelf].input);
      window.HomeInputShelf.refresh();
    }
  };
  // Classic breaks the date after the weekday, keeping the locale's own order.
  function classicDate(now) {
    var full = HomeI18n.formatDate(now),
      weekday = HomeI18n.formatDate(now, { weekday: 'long' }),
      at = weekday && weekday !== full ? full.indexOf(weekday) : -1,
      rest;
    if (at === 0) {
      rest = full.slice(weekday.length).replace(/^[\s,，、]+/, '');
      return rest ? weekday + '\n' + rest : full;
    }
    if (at > 0 && at + weekday.length === full.length) {
      rest = full.slice(0, at).replace(/[\s,，、]+$/, '');
      return rest ? rest + '\n' + weekday : full;
    }
    return full;
  }
  function updateClock() {
    var now = new Date(),
      hour = now.getHours();
    for (var idx = 0; idx < greetings.length; idx++)
      if (hour < greetings[idx][0]) {
        getElement('greeting').textContent = greetings[idx][1];
        break;
      }
    if (window.HomeI18n) {
      var time = HomeI18n.formatTime(now),
        period =
          layoutPreset === 'scenic-grid' ? time.match(/\s+(AM|PM)$/i) : null;
      getElement('clock').textContent = period
        ? time.slice(0, period.index)
        : time;
      getElement('ampm').textContent = period ? period[1] : '';
      getElement('date').textContent =
        layoutPreset === 'dock-grid'
          ? classicDate(now)
          : HomeI18n.formatDate(now);
    } else {
      getElement('clock').textContent =
        (hour % 12 || 12) + ':' + ('0' + now.getMinutes()).slice(-2);
      getElement('ampm').textContent = hour < 12 ? 'am' : 'pm';
      getElement('date').textContent =
        weekdays[now.getDay()] +
        '  ' +
        now.getDate() +
        ' ' +
        months[now.getMonth()];
    }
  }
  function fillInputsPanel() {
    inputsPanel.innerHTML = '';
    inputRows = [];
    inputEntries().forEach(function (input) {
      if (input.kind === 'tv' && inputRows.length) addInputSeparator();
      addInputRow(
        INPUT_ICONS[input.kind] || INPUT_ICONS.hdmi,
        input.label,
        input.appId,
        input.connected
      );
    });
    return inputRows.length;
  }
  function activateTopButton(index) {
    0 === index
      ? (function () {
          if (fillInputsPanel()) {
            var e = sceneRect(topButtons[0]);
            inputsPanel.style.left = e.left + 'px';
            inputsPanel.style.top = e.bottom + 20 + 'px';
            inputsPanel.style.minWidth = Math.max(e.width, 300) + 'px';
            inputsPanel.style.maxHeight = '';
            inputsPanel.style.overflowY = '';
            if (
              layoutGeometry.ribbon &&
              layoutGeometry.ribbon.shortcuts === 'bottom-left'
            ) {
              inputsPanel.style.maxHeight = Math.max(100, e.top - 32) + 'px';
              inputsPanel.style.overflowY = 'auto';
              inputsPanel.style.top =
                Math.max(16, e.top - inputsPanel.offsetHeight - 20) + 'px';
            }
            inputsPanel.classList.remove('hidden');
            coverShelf(true);
            setPartState(topButtons[focusedTopButton], 'focused', false);
            focusZone = 'inputs';
            focusInput(0);
          } else {
            showToast(tr('No inputs found'));
          }
        })()
      : 1 === index
        ? openNetworkSettings()
        : window.RenewalPanel.open();
  }
  function addInputSeparator() {
    var separator = document.createElement('div');
    separator.className = 'separator';
    inputsPanel.appendChild(separator);
  }
  function addInputRow(iconPath, label, appId, connected) {
    var element = document.createElement('div');
    element.className = 'inputRow ctv-input-row';
    element.innerHTML =
      ht('<svg viewBox="0 0 24 24"><path d="') + iconPath + '"/></svg>';
    element.appendChild(document.createTextNode(label));
    if (typeof connected === 'boolean') {
      var dot = document.createElement('span');
      dot.className = 'input-dot';
      dot.setAttribute('aria-hidden', 'true');
      element.appendChild(dot);
      setPartState(element, connected ? 'connected' : 'disconnected', true);
    }
    var index = inputRows.length;
    bindPointerFocus(element, function () {
      if (focusedInput !== index) focusInput(index);
    });
    element.addEventListener('click', function () {
      closeInputs();
      launchApp(appId, label);
      returnInput = appId;
    });
    element.appId = appId;
    element.label = label;
    inputRows.push(element);
    inputsPanel.appendChild(element);
  }
  function focusInput(index) {
    inputRows[focusedInput] &&
      setPartState(inputRows[focusedInput], 'focused', false);
    focusedInput = Math.max(0, Math.min(index, inputRows.length - 1));
    setPartState(inputRows[focusedInput], 'focused', true);
    if (
      layoutGeometry.ribbon &&
      layoutGeometry.ribbon.shortcuts === 'bottom-left' &&
      inputRows[focusedInput]
    ) {
      var row = inputRows[focusedInput];
      if (row.offsetTop < inputsPanel.scrollTop)
        inputsPanel.scrollTop = row.offsetTop;
      else if (
        row.offsetTop + row.offsetHeight >
        inputsPanel.scrollTop + inputsPanel.clientHeight
      )
        inputsPanel.scrollTop =
          row.offsetTop + row.offsetHeight - inputsPanel.clientHeight;
    }
  }
  function closeInputs() {
    inputsPanel.classList.add('hidden');
    coverShelf(false);
    focusZone = 'none';
    focusTopButton(0);
  }
  function moveTile(index) {
    index < 0 ||
      index >= screenIds().length ||
      index === focusedTile ||
      (tiles.splice(index, 0, tiles.splice(focusedTile, 1)[0]),
      (focusedTile = index),
      layoutTiles(),
      focusTile(index));
  }
  function finishMoving(commit) {
    var item = moveState.item;
    if (commit && !saveScreen()) {
      return;
    }
    if (!commit) {
      tiles = moveState.snapshot;
    }
    clearRibbonEditor();
    moveState = null;
    setPartState(item.el, 'moving', false);
    document.body.classList.remove('editing');
    hideSelected = false;
    hideButton.hidden = true;
    editHint.hidden = true;
    layoutTiles();
    focusTile(tiles.indexOf(item));
  }
  // Short OK launches on release; holding OK enters tile editing instead.
  var okPressed = false,
    okHoldTimer = null;
  function restoreFocus() {
    refreshInputStatus();
    cancelHold();
    closePicker();
    dismissUndo();
    moveState && finishMoving(false);
    updateClock();
    'inputs' === focusZone && inputsPanel.classList.add('hidden');
    topButtons.forEach(function (e) {
      setPartState(e, 'focused', false);
    });
    focusZone = 'none';
    var shelfIndex = -1;
    shelfTiles.forEach(function (tile, index) {
      if (returnInput && tile.input.appId === returnInput) shelfIndex = index;
    });
    restoring = true;
    try {
      shelfVisible() && shelfIndex >= 0
        ? focusShelf(shelfIndex)
        : focusTile(focusedTile);
    } finally {
      restoring = false;
    }
  }
  document.addEventListener('keyup', function (event) {
    if (window.RootLauncherRendered !== true) return;
    if (window.RenewalPanel && window.RenewalPanel.isOpen()) {
      okPressed = false;
      return;
    }
    if (event.keyCode === KEY_OK && ((okPressed = false), okHoldTimer)) {
      clearTimeout(okHoldTimer);
      okHoldTimer = null;
      clearPressed();
      var tile = tiles[focusedTile];
      'grid' === focusZone && tile && !moveState && activateTile(tile);
    }
  });
  document.addEventListener('keydown', function (event) {
    // Leave early Back/Home and key-up delivery to their native/recovery owners.
    if (window.RootLauncherRendered !== true) return;
    var key = event.keyCode;
    if (key !== KEY_OK && okHoldTimer) {
      cancelHold();
    }
    if (key === KEY_OK && okPressed) {
      event.preventDefault();
    } else {
      if ((key === KEY_OK && (okPressed = true), moveState)) {
        if (37 === key) {
          moveTile(
            layoutPreset === 'scenic-grid'
              ? (focusedTile - 1 + screenIds().length) % screenIds().length
              : focusedTile - 1
          );
        } else if (39 === key) {
          moveTile(
            layoutPreset === 'scenic-grid'
              ? (focusedTile + 1) % screenIds().length
              : focusedTile + 1
          );
        } else if (38 === key) {
          if (layoutGeometry.ribbon) selectHide();
          else if (layoutPreset !== 'scenic-grid')
            moveTile(focusedTile - columnCount);
        } else if (40 === key) {
          if (!layoutGeometry.ribbon) {
            if (rowFor(focusedTile) >= rowFor(screenIds().length - 1))
              selectHide();
            else
              moveTile(
                Math.min(focusedTile + columnCount, screenIds().length - 1)
              );
          }
        } else if (key === KEY_OK) {
          finishMoving(true);
        } else {
          if (key !== KEY_BACK && 27 !== key) {
            return;
          }
          finishMoving(false);
        }
      } else if ('inputs' === focusZone) {
        if (38 === key) {
          if (0 === focusedInput) {
            closeInputs();
          } else {
            focusInput(focusedInput - 1);
          }
        } else if (40 === key) {
          focusInput(focusedInput + 1);
        } else if (key === KEY_OK) {
          var input = inputRows[focusedInput];
          closeInputs();
          launchApp(input.appId, input.label);
          returnInput = input.appId;
        } else {
          if (key !== KEY_BACK && 27 !== key && 37 !== key && 39 !== key) {
            return;
          }
          closeInputs();
        }
      } else if ('shelf' === focusZone) {
        if (37 === key) {
          focusedShelf > 0
            ? focusShelf(focusedShelf - 1)
            : edgeBump('shelf-left');
        } else if (39 === key) {
          focusedShelf < shelfTiles.length - 1
            ? focusShelf(focusedShelf + 1)
            : edgeBump('shelf-right');
        } else if (38 === key) {
          focusTopButton(nearestTopButton(shelfCenter(focusedShelf)));
        } else if (40 === key) {
          focusTile(nearestDockTile(shelfCenter(focusedShelf)));
        } else if (key === KEY_OK) {
          launchInput(
            shelfTiles[focusedShelf].input,
            shelfTiles[focusedShelf].el
          );
        } else if (key === KEY_BACK || 27 === key) {
          focusTile(0 === rowFor(focusedTile) ? focusedTile : 0);
        } else {
          return;
        }
      } else if ('top' === focusZone) {
        if (layoutPreset === 'side-grid' && (38 === key || 40 === key)) {
          focusTopButton(focusedTopButton + (40 === key ? 1 : -1));
        } else if (layoutPreset === 'side-grid' && 39 === key) {
          focusTile(focusedTile);
        } else if (37 === key) {
          focusTopButton(focusedTopButton - 1);
        } else if (39 === key) {
          if (
            focusedTopButton === 2 &&
            layoutGeometry.ribbon &&
            layoutGeometry.ribbon.edgeNavigation === 'shortcuts'
          ) {
            focusTile(ribbonStart);
          } else focusTopButton(focusedTopButton + 1);
        } else if (40 === key) {
          if (shelfVisible()) {
            var buttonRect = sceneRect(topButtons[focusedTopButton]);
            focusShelf(nearestShelf(buttonRect.left + buttonRect.width / 2));
          } else focusTile(0 === rowFor(focusedTile) ? focusedTile : 0);
        } else if (key === KEY_OK) {
          activateTopButton(focusedTopButton);
        } else if (key !== KEY_BACK) {
          return;
        }
      } else {
        var column = focusedTile % columnCount,
          lastIndex = tiles.length - 1;
        if (37 === key) {
          if (layoutPreset === 'scenic-grid') stepRibbon(-1);
          else if (column > 0) focusTile(focusedTile - 1);
          else if (layoutPreset === 'side-grid')
            focusTopButton(focusedTopButton);
          else edgeBump('left');
        } else if (39 === key) {
          if (layoutPreset === 'scenic-grid') stepRibbon(1);
          else if (column < columnCount - 1 && focusedTile < lastIndex)
            focusTile(focusedTile + 1);
          else edgeBump('right');
        } else if (38 === key) {
          if (0 !== rowFor(focusedTile)) focusTile(focusedTile - columnCount);
          else if (shelfVisible())
            focusShelf(nearestShelf(tileLeft(focusedTile) + CARD_WIDTH / 2));
          else
            focusTopButton(
              nearestTopButton(tileLeft(focusedTile) + CARD_WIDTH / 2)
            );
        } else if (40 === key) {
          rowFor(focusedTile) < rowFor(lastIndex)
            ? focusTile(Math.min(focusedTile + columnCount, lastIndex))
            : edgeBump('down');
        } else if (key === KEY_OK) {
          setPressed(tiles[focusedTile] && tiles[focusedTile].el, true);
          okHoldTimer = setTimeout(function () {
            okHoldTimer = null;
            beginMoving(tiles[focusedTile]);
          }, 600);
        } else if (key !== KEY_BACK) {
          return;
        }
      }
      event.preventDefault();
    }
  });
  topButtons.forEach(function (e, t) {
    bindPointerFocus(e, function () {
      'inputs' !== focusZone &&
        !moveState &&
        !pickerOpen &&
        !undoState &&
        (focusZone !== 'top' || focusedTopButton !== t) &&
        focusTopButton(t);
    });
    e.addEventListener('click', function () {
      if (!moveState && !pickerOpen && !undoState) {
        activateTopButton(t);
      }
    });
  });
  getElement('viewport').addEventListener(
    'wheel',
    function (event) {
      if (
        layoutPreset !== 'scenic-grid' ||
        focusZone !== 'grid' ||
        moveState ||
        pickerOpen ||
        undoState ||
        (window.ThemeRuntime &&
          ThemeRuntime.isSuspended &&
          ThemeRuntime.isSuspended())
      )
        return;
      var delta =
        Math.abs(event.deltaX) > Math.abs(event.deltaY)
          ? event.deltaX
          : event.deltaY;
      if (!delta) return;
      event.preventDefault();
      if (ribbonWheelTime && event.timeStamp - ribbonWheelTime < 140) return;
      ribbonWheelTime = event.timeStamp;
      pointerNavigation = false;
      getElement('homeSurface').classList.add('ctv-remote-navigation');
      stepRibbon(delta > 0 ? 1 : -1);
    },
    false
  );
  document.addEventListener('webOSRelaunch', restoreFocus);
  document.addEventListener('visibilitychange', function () {
    if (window.ThemeRuntime) {
      // Retain validated styles/assets while hidden: the compositor may expose Home
      // before delivering the next visible/relaunch event. Dialog owners stay separate.
      if (!document.hidden) ThemeRuntime.resume('visibility');
    }
    document.hidden ? stopPreview() : restoreFocus();
  });
  // A system overlay can take window focus without hiding Home; resume the preview after it.
  window.addEventListener('blur', function () {
    windowFocused = false;
    stopPreview();
  });
  window.addEventListener('focus', function () {
    windowFocused = true;
    refreshInputStatus();
    if ('shelf' === focusZone && shelfTiles[focusedShelf] && inputPreview)
      inputPreview.focus(shelfTiles[focusedShelf].input);
  });
  initializeApps();
  layoutTiles();
  renderShelf();
  if (inputSources) {
    inputSources.onchange(function () {
      renderShelf();
      if ('inputs' === focusZone) {
        var focusedId =
            inputRows[focusedInput] && inputRows[focusedInput].appId,
          next = focusedInput;
        fillInputsPanel()
          ? (inputRows.forEach(function (row, index) {
              if (row.appId === focusedId) next = index;
            }),
            focusInput(next))
          : closeInputs();
      }
    });
    inputSources.start();
  }
  updateClock();
  setInterval(updateClock, 1e4);
  callLuna(
    'luna://com.palm.connectionmanager/getStatus',
    {
      subscribe: true
    },
    function (e) {
      if (false !== e.returnValue || e.wifi || e.wired) {
        var t = 'Wi-Fi';
        e.wired && 'connected' === e.wired.state
          ? (t = tr('Ethernet'))
          : e.wifi && 'connected' === e.wifi.state
            ? (t = e.wifi.ssid || 'Wi-Fi')
            : false === e.isInternetConnectionAvailable && (t = tr('Offline'));
        getElement('wifiLabel').textContent = t;
      }
    }
  );
  focusZone = 'none';
  focusTile(0);
  // Independent appearance restoration can run while the theme is prepared.
  // Presentation still waits for both, with decoder ownership already fenced.
  var personalAppearance = window.PersonalWallpaper
    ? PersonalWallpaper.start().catch(function () {})
    : Promise.resolve();
  function presentHome() {
    // The platform owns CARD foreground activation; expose only restored appearance.
    return personalAppearance.then(function () {
      tiles.forEach(function (tile) {
        tile.el.classList.add('shown');
      });
      getElement('homeSurface').classList.remove('ctv-starting');
      if (window.HomeName) HomeName.refresh();
    });
  }
  // Weather changes reserve layout space without resetting the user's app/row.
  document.addEventListener('home-weather-layout', function () {
    var state = layoutState.state();
    updateGeometry(state.columns, state.preset, state.ribbon);
    layoutTiles();
    renderShelf();
    if (focusZone === 'grid') focusTile(focusedTile);
    else setScroll(scrollOffset);
  });
  window.HomeUIReady = (
    window.ThemeManager
      ? ThemeManager.start(presentHome)
      : Promise.resolve().then(presentHome)
  ).then(function () {
    window.RootLauncherRendered = true;
    if (window.HomeWeather) HomeWeather.start();
  });
})();
