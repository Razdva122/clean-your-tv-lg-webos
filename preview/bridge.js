/* Browser-only webOS simulation. Injected by scripts/preview.py, never packaged. */
(function () {
  'use strict';
  window.CYTV_BROWSER_PREVIEW = true;
  window.PREVIEW_HOME_CONTEXT = 'empty';
  // The browser preview stays open when explicit recovery simulates leaving Home.
  window.close = function () {};
  var homeEnabled = true;
  var enabled = false, rootPhase = 'disabled';
  var firmwareBlocked = false, audioAutomatic = false, audioLast = null;
  var rootTransaction = 'preview-root-activation';
  var toastTimer;
  function message(text) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = 'Preview · ' + text;
    toast.classList.add('shown');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('shown'); }, 2400);
  }
  window.PalmServiceBridge = function () { this.timer = null; };
  window.PalmServiceBridge.prototype.cancel = function () { clearTimeout(this.timer); };
  window.PalmServiceBridge.prototype.call = function (uri, raw) {
    var bridge = this, payload = JSON.parse(raw || '{}');
    bridge.timer = setTimeout(function () {
      var result = {returnValue: false, errorText: 'Unavailable in browser preview'};
      if (uri === 'luna://org.webosbrew.hbchannel.service/getConfiguration') {
        result = {returnValue:true, root:true, blockUpdates:firmwareBlocked};
      } else if (uri === 'luna://org.webosbrew.hbchannel.service/setConfiguration') {
        if (Object.keys(payload).length === 1 && typeof payload.blockUpdates === 'boolean') {
          firmwareBlocked = payload.blockUpdates;
          result = {returnValue:true, blockUpdates:firmwareBlocked};
        }
      } else if (uri.indexOf('luna://com.cleanyourtv.system.updater.service/') === 0) {
        var systemMethod = uri.split('/').pop();
        if (systemMethod === 'restoreProfile' || systemMethod === 'status') result = {returnValue:true,result:null};
        else if (systemMethod === 'check') {
          var rootEdition = payload.edition === 'root';
          var names = rootEdition ? ['root','root-updater','root-infrastructure'] : ['home','helper','updater'];
          result = {returnValue:true,result:{edition:payload.edition,release:'v1.0.3',canInstall:false,
            reason:'Browser preview: no real updates are checked or installed.',notes:'Browser preview: no real updates are checked or installed.',
            components:names.map(function (name) { var version = name === 'home' ? '1.3.8' : name === 'helper' ? '0.6.18' : name === 'updater' || name === 'root-updater' ? '0.1.6' : window.ROOT_VERSION || '0.0.1'; return {name:name,installed:version,version:version}; })}};
        }
      } else if (uri === 'luna://com.webos.applicationManager/launch') {
        if (payload.id !== 'com.local.nativehome') {
          var app = (window.TV_APPS.apps || []).filter(function (a) { return a.id === payload.id; })[0];
          message(app ? app.title : payload.id === 'com.webos.app.firstuse-overlay' ? 'Network settings' : payload.id === 'com.palm.app.settings' ? 'TV settings' : payload.id);
        }
        result = {returnValue: true};
      } else if (uri.indexOf('luna://com.gathin.tvhome.renewal/') === 0 && ['homeStatus','setHomeControl','openLGHome'].indexOf(uri.split('/').pop()) >= 0) {
        var homeMethod=uri.split('/').pop();
        if(homeMethod==='setHomeControl')homeEnabled=payload.enabled;
        if(homeMethod==='openLGHome')message('LG Home · settings kept');
        if(['homeStatus','setHomeControl','openLGHome'].indexOf(homeMethod)>=0)result={returnValue:true,enabled:homeEnabled};
      } else if (uri === 'luna://com.local.nativehome.service/listApps' || uri === 'luna://com.cleanyourtv.root.preview.service/listApps' && payload.inputs !== true) {
        result = {returnValue:true, apps:(window.TV_APPS.apps || []).concat(window.TV_APPS.referenceApps ? [] : [{id:'preview.gallery', title:'Photo & Video', icon:'../preview/icons/browser.svg'}])};
      } else if (uri === 'luna://com.webos.service.eim/getAllInputStatus' || uri === 'luna://com.cleanyourtv.root.preview.service/listApps' && payload.inputs === true) {
        // Simulated live ports: captured inputs are connected, two spare ports are not.
        // window.PREVIEW_INPUT_STATUS overrides the device list; null simulates a denied call.
        var names = ['PlayStation 5', 'Apple TV'], captured = window.TV_APPS.inputs || [];
        var devices = captured.slice(0, 2).map(function (input, index) {
          return {id: 'HDMI_' + (index + 1), appId: input.appId, label: 'HDMI ' + (index + 1), connected: true, deviceName: names[index]};
        });
        for (var port = devices.length + 1; port <= 4; port++) devices.push({id: 'HDMI_' + port, appId: 'preview.hdmi' + port, label: 'HDMI ' + port, connected: false});
        if (window.PREVIEW_INPUT_STATUS !== undefined) devices = window.PREVIEW_INPUT_STATUS;
        result = devices ? {returnValue: true, devices: devices} : {returnValue: false, errorText: 'Denied method call'};
      } else if (uri === 'luna://com.palm.connectionmanager/getStatus') {
        result = {returnValue: true, isInternetConnectionAvailable: true, wifi: {state: 'connected', ssid: 'Demo Wi-Fi'}};
      } else if (uri === 'luna://com.webos.service.bus/signal/registerServerStatus') {
        result = {returnValue: true, connected: true};
      } else if (uri.indexOf('luna://com.cleanyourtv.root.preview.service/') === 0) {
        var rootMethod = uri.split('/').pop();
        if (rootMethod === 'status' && payload.presentation === 'context') {
          result = {returnValue:true,result:{content:window.PREVIEW_HOME_CONTEXT === 'content' ? true : window.PREVIEW_HOME_CONTEXT === 'empty' ? false : null}};
          if (bridge.onservicecallback) bridge.onservicecallback(JSON.stringify(result));
          return;
        }
        if (rootMethod === 'audioRecoveryStatus' || rootMethod === 'setAudioRecoveryEnabled') {
          if (rootMethod === 'setAudioRecoveryEnabled' && typeof payload.enabled === 'boolean') audioAutomatic = payload.enabled;
          result = {returnValue:true,enabled:audioAutomatic,observer:audioAutomatic,autoSupported:true,canRestart:true,canRestoreRoute:false,canRestoreSetting:false,needsRestore:false,mode:'earc',last:audioLast};
        } else if (rootMethod === 'recoverAudio') {
          audioLast = {result:'settings-restored'}; result = {returnValue:true,result:'settings-restored'};
        }
        if (rootMethod === 'enable') {
          rootPhase = 'active';
        } else if (rootMethod === 'restore') {
          rootPhase = 'disabled';
        }
        if (['status', 'enable', 'restore'].indexOf(rootMethod) >= 0) {
          var home = rootPhase === 'disabled' ? 'com.webos.app.home' : 'com.cleanyourtv.root.preview';
          var state = {intent: {phase: rootPhase}, journal: {transaction: rootTransaction},
            effective: {sam_home: home, profiles: {defaultApps: {categories: {home: home}}, idleApp: {appId: home}}}};
          result = {returnValue: true, result: {returnValue: true, result: rootMethod === 'restore' ? 'restored' : state}};
        }
      } else if (uri.indexOf('luna://com.cleanyourtv.root.updater.service/') === 0) {
        var updaterMethod = uri.split('/').pop();
        if (updaterMethod === 'restoreProfile' || updaterMethod === 'status') {
          result = {returnValue: true, result: null};
        } else if (updaterMethod === 'check') {
          var version = window.ROOT_VERSION || '0.0.1';
          result = {returnValue: true, result: {installed: {version: version}, canInstall: false,
            reason: 'current', candidate: {version: version,
              notes: 'Browser preview: no real updates are checked or installed.'}}};
        }
      } else if (uri.indexOf('luna://com.gathin.tvhome.renewal/') === 0) {
        var method = uri.split('/').pop();
        if (['status', 'enable', 'disable', 'check'].indexOf(method) >= 0) {
          if (method === 'enable') enabled = true;
          if (method === 'disable') enabled = false;
          result = {returnValue: true, state: {enabled: enabled, last: {status: 'healthy', remainingSeconds: 864000, checkedAt: Date.now()}}};
        }
      } else if (uri === 'luna://com.cleanyourtv.updater.service/check') {
        result = {returnValue: true, result: {home: '1.2.2', state: 'current', canInstall: false,
          candidate: {home: '1.2.2', notes: 'Browser preview: no real updates are checked or installed.'}}};
      } else if (uri === 'luna://com.cleanyourtv.updater.service/healthy') {
        result = {returnValue: true};
      }
      if (bridge.onservicecallback) bridge.onservicecallback(JSON.stringify(result));
    }, 30);
  };
  // Browsers cannot play webOS external inputs: stand in with a moving gradient that
  // "plays" shortly after it is mounted, like the TV's video pipeline.
  window.PREVIEW_INPUT_MEDIA = window.PREVIEW_INPUT_MEDIA || function (uri) {
    if (!document.getElementById('previewInputMediaStyle')) {
      var style = document.createElement('style');
      style.id = 'previewInputMediaStyle';
      style.textContent = '@keyframes preview-input-pan{from{background-position:0 0}to{background-position:-200% 0}}' +
        '.preview-input-media{background:linear-gradient(115deg,#1d3b8f,#7a2ca8,#d0452f,#1d3b8f);background-size:200% 100%;animation:preview-input-pan 6s linear infinite}' +
        '.preview-input-media span{position:absolute;top:8px;right:10px;font-size:14px;letter-spacing:.08em;color:rgba(255,255,255,.8)}';
      document.head.appendChild(style);
    }
    var media = document.createElement('div'), screen = document.createElement('div'), label = document.createElement('span');
    screen.className = 'preview-input-media';
    screen.hidden = true;
    screen.style.cssText = 'position:absolute;top:0;right:0;bottom:0;left:0';
    label.textContent = 'LIVE · ' + uri.replace('ext://', '').toUpperCase();
    screen.appendChild(label);
    media.appendChild(screen);
    setTimeout(function () { screen.dispatchEvent(new Event('playing')); screen.hidden = false; }, 300);
    return media;
  };
}());
