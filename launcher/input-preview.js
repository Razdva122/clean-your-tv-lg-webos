/* One focused external-input video after a dwell. Element mute is requested; firmware may ignore it. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.InputPreview = factory();
})(this, function () {
  'use strict';
  // webOS draws the input on a hardware video plane: transforms apply, rounded clipping and opacity do not.
  function createVideo(uri) {
    var wrapper = document.createElement('div'),
      video = document.createElement('video'),
      source = document.createElement('source');
    video.setAttribute('autoplay', '');
    video.setAttribute('muted', '');
    video.muted = true;
    source.setAttribute('type', 'service/webos-external');
    source.setAttribute('src', uri);
    video.appendChild(source);
    wrapper.appendChild(video);
    return wrapper;
  }
  // The release order that left no picture or sound behind on hardware.
  function release(media) {
    var video =
      media.tagName === 'VIDEO'
        ? media
        : media.querySelector && media.querySelector('video');
    try {
      if (video) {
        video.pause();
        var source = video.querySelector('source');
        if (source) source.removeAttribute('src');
        video.removeAttribute('src');
        video.load();
      }
    } catch (_) {}
    if (media.parentNode) media.parentNode.removeChild(media);
  }
  function create(options) {
    options = options || {};
    var delay = options.delay === undefined ? 800 : options.delay,
      timeout = options.timeout === undefined ? 4000 : options.timeout,
      cooldown = options.cooldown === undefined ? 60000 : options.cooldown,
      now =
        options.now ||
        function () {
          return Date.now();
        },
      createMedia = options.createMedia || createVideo,
      mount = options.mount || function () {},
      enabled =
        options.enabled ||
        function () {
          return true;
        },
      onchange = options.onchange || function () {},
      onclaim = options.onclaim || function () {},
      onrelease = options.onrelease || function () {},
      failed = Object.create(null),
      wanted = null,
      dwell = null,
      active = null;
    function eligible(input) {
      return (
        !!input &&
        typeof input.source === 'string' &&
        input.connected !== false &&
        !!enabled() &&
        !(
          failed[input.source] !== undefined &&
          now() - failed[input.source] < cooldown
        )
      );
    }
    function end() {
      if (!active) return;
      var preview = active;
      active = null;
      clearTimeout(preview.timer);
      release(preview.media);
      if (preview.playing) onchange(null);
      onrelease();
    }
    function fail(preview) {
      if (active !== preview) return;
      failed[preview.uri] = now();
      end();
    }
    function begin() {
      dwell = null;
      if (!eligible(wanted)) return;
      var input = wanted,
        media;
      onclaim();
      try {
        media = createMedia(input.source);
      } catch (_) {
        failed[input.source] = now();
        onrelease();
        return;
      }
      var preview = {
        input: input,
        uri: input.source,
        media: media,
        playing: false
      };
      active = preview;
      // Media events do not bubble; capture sees them on any wrapper.
      media.addEventListener(
        'playing',
        function () {
          if (active !== preview || preview.playing) return;
          preview.playing = true;
          clearTimeout(preview.timer);
          onchange(input, media);
        },
        true
      );
      media.addEventListener(
        'error',
        function () {
          fail(preview);
        },
        true
      );
      preview.timer = setTimeout(function () {
        fail(preview);
      }, timeout);
      // No tile to show it in (focus moved on): not a playback failure, so no cooldown.
      if (mount(media, input) === false) end();
    }
    function stop() {
      wanted = null;
      clearTimeout(dwell);
      dwell = null;
      end();
    }
    return {
      // A repeated focus on the same live source keeps the running preview or dwell.
      focus: function (input) {
        if (
          input &&
          wanted &&
          input.source === wanted.source &&
          eligible(input) &&
          (dwell || active)
        ) {
          wanted = input;
          return;
        }
        stop();
        if (!eligible(input)) return;
        wanted = input;
        dwell = setTimeout(begin, delay);
      },
      stop: stop,
      // Moves the running preview into a rebuilt tile; call in the same task as the
      // rebuild so the detached media element never pauses.
      remount: function () {
        if (!active) return;
        if (mount(active.media, active.input) === false) {
          end();
          return;
        }
        if (active.playing) onchange(active.input, active.media);
      },
      playing: function () {
        return !!(active && active.playing);
      }
    };
  }
  return { create: create, createVideo: createVideo, release: release };
});
