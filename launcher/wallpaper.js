/* Trusted wallpaper plane. ThemeRuntime owns URLs; detach before it revokes them. */
(function (root) {
  'use strict';
  var doc = root.document, key = 'tvhome.wallpaper.preferences.v1', preferences = [], input = null, themeInput = null, personalInput = null, personalEnabled = false;
  var owners = Object.create(null), video = null, plane = null, shade = null, style = null;
  var generation = 0, timer = null, actual = 'image', quality = 'auto', dim = 0, notice = '';
  var capabilities = {uhd: null}, bridge = null;
  function emit() { doc.dispatchEvent(new root.CustomEvent('home-wallpaper-change')); }
  function blocked() { return !!doc.hidden || Object.keys(owners).length > 0; }
  function available() {
    var result = [], handles = input && input.videoHandles || {};
    ['4k', '1080p'].forEach(function (q) {
      if (input && input.manifest.wallpaperVideo && input.manifest.wallpaperVideo.variants.some(function (v) { return v.quality === q; }) && (typeof handles[q] === 'string' || input.videoLease)) result.push(q);
    });
    result.push('image'); return result;
  }
  function poster() {
    var m = input && input.manifest, id = m && m.defaults.wallpaperAssetId;
    return m && m.assets.filter(function (asset) { return asset.id === id; })[0];
  }
  function state() {
    var asset = poster(), m = input && input.manifest;
    return {source: personalEnabled && personalInput ? 'personal' : 'theme', origin: personalEnabled && personalInput ? personalInput.origin : null, themeId: m ? m.id : 'builtin:classic', title: m ? m.title : 'Classic', posterURL: asset && input.assetHandles && input.assetHandles[asset.id] || '', posterWidth: asset && asset.width || 0, posterHeight: asset && asset.height || 0, available: available(), paused: blocked() && available().length > 1 && quality !== 'image', actualQuality: actual, preferenceQuality: quality, dim: dim, notice: notice, capabilities: {uhd: capabilities.uhd}};
  }
  function classes(playing) {
    var surface = doc.getElementById('homeSurface'), method = playing ? 'add' : 'remove';
    if (surface) surface.classList[method]('ctv-wallpaper-playing');
    doc.documentElement.classList[method]('ctv-wallpaper-playing'); doc.body.classList[method]('ctv-wallpaper-playing');
    if (plane) plane.style.display = playing ? 'block' : 'none';
  }
  function detach() {
    generation++; if (timer !== null) root.clearTimeout(timer); timer = null;
    classes(false); actual = 'image';
    if (video) {
      var old = video; video = null;
      ['playing', 'error', 'stalled', 'waiting', 'timeupdate'].forEach(function (event) { old.removeEventListener(event, old._wallpaperListeners[event]); });
      try { old.pause(); old.removeAttribute('src'); old.load(); } catch (_) {}
      if (old.parentNode) old.parentNode.removeChild(old);
    }
  }
  function ensure() {
    if (plane) return;
    plane = doc.createElement('div'); plane.id = 'ctvWallpaper'; plane.setAttribute('aria-hidden', 'true');
    shade = doc.createElement('div'); shade.id = 'ctvWallpaperDim'; plane.appendChild(shade); doc.body.appendChild(plane);
    style = doc.createElement('style'); style.id = 'ctvWallpaperImage'; doc.body.appendChild(style);
  }
  function paintDim() {
    ensure(); shade.style.backgroundColor = 'rgba(0,0,0,' + dim + ')';
    var url = state().posterURL;
    style.textContent = !blocked() && url ? '#homeSurface.ctv-home{background-image:linear-gradient(rgba(0,0,0,' + dim + '),rgba(0,0,0,' + dim + ')),url("' + url.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/[\r\n]/g, '') + '")!important;}' : '';
  }
  function choose() {
    var choices = available();
    if (quality === 'image') return 'image';
    if (quality === '4k' && capabilities.uhd !== false && choices.indexOf('4k') >= 0) return '4k';
    if (quality === '4k') notice = '4K is unavailable. Using a compatible wallpaper.';
    if (quality === 'auto' && capabilities.uhd === true && choices.indexOf('4k') >= 0) return '4k';
    return choices.indexOf('1080p') >= 0 ? '1080p' : 'image';
  }
  function releaseLease() {
    if (input && input.videoLease && input.videoLease.release) {
      input.videoHandles = {};
      try { var pending = input.videoLease.release(); input.wallpaperRelease = Promise.resolve(pending).catch(function () {}); } catch (_) {}
    }
  }
  function play(q) {
    detach(); paintDim();
    if (!input || blocked() || q === 'image') { releaseLease(); emit(); return; }
    var token = generation, current = doc.createElement('video'), lastTime = -1; video = current;
    current.id = 'ctvWallpaperVideo'; current.muted = true; current.defaultMuted = true; current.volume = 0; current.loop = true; current.autoplay = true;
    current.setAttribute('muted', ''); current.setAttribute('playsinline', ''); current.preload = 'auto';
    function valid() { return generation === token && video === current; }
    function failed(reason) {
      if (!valid()) return;
      var next = q === '4k' && available().indexOf('1080p') >= 0 ? '1080p' : 'image';
      notice = q === '4k' ? '4K playback failed. Using ' + (next === 'image' ? 'the image.' : '1080p.') : 'Video playback failed. Using the image.';
      if (reason === 'dimensions') notice = 'Video dimensions do not match the theme. ' + notice;
      play(next);
    }
    function watchdog() { if (timer !== null) root.clearTimeout(timer); timer = root.setTimeout(failed, 10000); }
    current._wallpaperListeners = {
      playing: function () {
        if (!valid()) return;
        var expected = input.manifest.wallpaperVideo.variants.filter(function (v) { return v.quality === q; })[0];
        if (!expected || current.videoWidth <= 0 || current.videoHeight <= 0 || current.videoWidth !== expected.width || current.videoHeight !== expected.height) { failed('dimensions'); return; }
        actual = q; classes(true); watchdog(); emit();
      },
      error: failed,
      stalled: function () { if (valid() && timer === null) watchdog(); },
      waiting: function () { if (valid() && timer === null) watchdog(); },
      timeupdate: function () { if (valid() && current.currentTime !== lastTime) { lastTime = current.currentTime; watchdog(); } }
    };
    Object.keys(current._wallpaperListeners).forEach(function (event) { current.addEventListener(event, current._wallpaperListeners[event]); });
    plane.appendChild(current); current.src = input.videoHandles[q]; watchdog();
    try { var pending = current.play(); if (pending && pending.then) pending.then(function () {}, failed); } catch (_) { failed(); }
    emit();
  }
  function restart() {
    notice = ''; var q = choose();
    if (!input || !input.videoLease || blocked() || q === 'image') { play(q); return state(); }
    detach(); paintDim(); emit();
    var token = generation, active = input;
    function failed() { if (token !== generation || active !== input) return; notice = 'Video cache is unavailable. Using the image.'; play('image'); }
    try {
      input.videoLease.acquire().then(function (handles) {
        if (token !== generation || active !== input || blocked()) return;
        input.videoHandles = handles;
        if (!handles || typeof handles[q] !== 'string') { failed(); return; }
        play(q);
      }, failed);
    } catch (_) { failed(); }
    return state();
  }
  function read() {
    preferences = [];
    try { var saved = JSON.parse(root.localStorage.getItem(key)); if (Array.isArray(saved)) preferences = saved.slice(-32).filter(function (p) { return p && typeof p.id === 'string' && p.id.length <= 200 && ['auto', '4k', '1080p', 'image'].indexOf(p.quality) >= 0 && typeof p.dim === 'number' && isFinite(p.dim) && p.dim >= 0 && p.dim <= .85; }); } catch (_) {}
  }
  function save(remove) {
    if (!input) return;
    var id = input.manifest.id;
    preferences = preferences.filter(function (p) { return p.id !== id; });
    if (!remove) preferences.push({id: id, quality: quality, dim: dim});
    preferences = preferences.slice(-32);
    try { root.localStorage.setItem(key, JSON.stringify(preferences)); } catch (_) { notice = 'Wallpaper preferences could not be saved.'; }
  }
  function activate(next) {
    detach(); releaseLease(); input = next; read(); quality = 'auto'; dim = input ? input.manifest.defaults.dim : 0;
    preferences.forEach(function (p) { if (input && p.id === input.manifest.id) { quality = p.quality; dim = p.dim; } });
    return restart();
  }
  function configure(next) { themeInput = next; if (personalEnabled && personalInput) return state(); return activate(next); }
  function reset() { themeInput = null; if (personalEnabled && personalInput) return state(); return activate(null); }
  function setPersonal(next, enabled) {
    personalInput = next; personalEnabled = !!enabled && !!next;
    return activate(personalEnabled ? personalInput : themeInput);
  }
  function suspend(owner) { owners[owner || 'manual'] = true; detach(); releaseLease(); paintDim(); emit(); }
  function resume(owner) { var held = owners[owner || 'manual']; delete owners[owner || 'manual']; if (held && !blocked()) restart(); }
  function metadata(result) {
    var value = result && (result.uhd === undefined ? result.UHD : result.uhd), previous = capabilities.uhd;
    capabilities.uhd = value === true || value === 'true' ? true : value === false || value === 'false' ? false : null;
    if (input && quality === 'auto' && previous !== capabilities.uhd) restart(); else emit();
  }
  root.HomeWallpaper = {setPersonal: setPersonal, configure: configure, reset: reset, suspend: suspend, resume: resume, state: state,
    setQuality: function (q) { if (['auto', '4k', '1080p', 'image'].indexOf(q) < 0) throw Error('Invalid wallpaper quality'); quality = q; restart(); save(false); emit(); return state(); },
    setDim: function (value) { if (typeof value !== 'number' || !isFinite(value) || value < 0 || value > .85) throw Error('Invalid wallpaper dim'); dim = value; paintDim(); save(false); emit(); return state(); },
    resetPreferences: function () { save(true); quality = 'auto'; dim = input ? input.manifest.defaults.dim : 0; return restart(); }};
  doc.addEventListener('visibilitychange', function () { if (doc.hidden) suspend('visibility'); else resume('visibility'); });
  root.addEventListener && root.addEventListener('pagehide', function () { suspend('pagehide'); });
  root.addEventListener && root.addEventListener('pageshow', function () { resume('pagehide'); });
  try {
    if (root.webOS && root.webOS.deviceInfo) root.webOS.deviceInfo(metadata);
    else if (root.PalmServiceBridge) {
      bridge = new root.PalmServiceBridge(); bridge.onservicecallback = function (text) { try { metadata(JSON.parse(text)); } catch (_) {} bridge = null; };
      bridge.call('luna://com.webos.service.tv.systemproperty/getSystemInfo', JSON.stringify({keys: ['UHD']}));
    }
  } catch (_) {}
}(this));
