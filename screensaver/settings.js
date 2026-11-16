(function (root, factory) {
  var settings = factory();
  if (typeof module === 'object' && module.exports) module.exports = settings;
  else root.CYTVScreensaverSettings = settings;
})(this, function () {
  'use strict';

  var backgrounds = [
    {
      id: 'alpine-photo',
      mode: 'photo',
      label: 'Alpine lake',
      file: 'backgrounds/alpine-photo.jpg'
    },
    {
      id: 'ribbon-photo',
      mode: 'photo',
      label: 'Ribbon',
      file: 'backgrounds/ribbon-photo.jpg'
    },
    {
      id: 'alpine-video',
      mode: 'video',
      label: 'Alpine lake (still)',
      file: 'backgrounds/alpine-video.mp4',
      hdFile: 'backgrounds/alpine-video-1080p.mp4'
    },
    {
      id: 'ribbon-video',
      mode: 'video',
      label: 'Ribbon',
      file: 'backgrounds/ribbon-video.mp4',
      hdFile: 'backgrounds/ribbon-video-1080p.mp4'
    }
  ];

  function background(mode, id) {
    for (var i = 0; i < backgrounds.length; i++) {
      var item = backgrounds[i];
      if (item.mode === mode && item.id === id) return item;
    }
    return null;
  }

  function personal(mode, id) {
    return (mode === 'photo' || mode === 'video') && id === 'personal-' + mode;
  }

  function personalMediaUrl(mode, url) {
    if (typeof url !== 'string') return false;
    var match =
      /^http:\/\/127\.0\.0\.1:([1-9][0-9]{0,4})\/[a-f0-9]{32}\/(4k\.mp4|1080p\.mp4|photo\.(?:jpg|png))$/.exec(
        url
      );
    if (!match || match[0] !== url || Number(match[1]) > 65535) return false;
    return mode === 'photo' || mode === 'video';
  }

  var qualities = ['auto', '4k', '1080p', 'image'];

  function clockPresentation(value) {
    if (
      !value ||
      typeof value !== 'object' ||
      Array.isArray(value) ||
      Object.keys(value).sort().join(',') !== 'hour12,locale' ||
      typeof value.locale !== 'string' ||
      !/^[a-z]{2,3}(?:-[A-Z][a-z]{3}|-[A-Z]{2})?$/.test(value.locale) ||
      typeof value.hour12 !== 'boolean'
    )
      return null;
    return { locale: value.locale, hour12: value.hour12 };
  }

  function normalize(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) input = {};
    function own(name) {
      return Object.prototype.hasOwnProperty.call(input, name)
        ? input[name]
        : undefined;
    }
    var idle = own('idleTimeoutMs');
    if (typeof idle !== 'number' || !isFinite(idle)) idle = 60000;
    idle = Math.max(30000, Math.min(1800000, Math.round(idle)));
    var asset = own('assetId');
    if (typeof asset !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(asset))
      asset = '';
    var mode = own('mode');
    if (mode !== 'photo' && mode !== 'video' && mode !== 'clock')
      mode = 'ambient';
    var settings = {
      enabled: own('enabled') === true,
      scope: personal(mode, asset) ? 'cytv' : 'global',
      mode: mode,
      assetId: asset,
      clockOverlay: own('clockOverlay') !== false,
      quality: qualities.indexOf(own('quality')) >= 0 ? own('quality') : 'auto',
      idleTimeoutMs: idle
    };
    var clock = clockPresentation(own('clock'));
    if (clock) settings.clock = clock;
    return settings;
  }

  // Home uses its own idle timer in either mode. Other apps require a
  // verified LG trigger and an asset the owner can serve without Home.
  function canActivate(input, capabilities) {
    var settings = normalize(input);
    var caps = capabilities || {};
    if (!settings.enabled || caps.popupSupported !== true) return false;
    if (
      (settings.mode === 'photo' || settings.mode === 'video') &&
      !settings.assetId
    )
      return false;
    return (
      caps.inAppEligible === true ||
      (settings.scope === 'global' &&
        caps.globalTriggerVerified === true &&
        caps.globalEligible === true)
    );
  }

  return {
    normalize: normalize,
    clockPresentation: clockPresentation,
    qualities: qualities,
    canActivate: canActivate,
    backgrounds: backgrounds,
    background: background,
    personal: personal,
    personalMediaUrl: personalMediaUrl
  };
});
