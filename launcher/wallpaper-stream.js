/* One verified local fragment is appended on a continuous timeline. No seek at loop boundaries. */
(function (root) {
  'use strict';
  var last = { mode: 'native' };
  function create(video, variant, onFailure) {
    var spec =
      root.WallpaperLibrary && root.WallpaperLibrary.streamFor(variant);
    last = { mode: 'native' };
    if (
      !spec ||
      !root.MediaSource ||
      !root.MediaSource.isTypeSupported(spec.mime)
    )
      return null;
    var media = new root.MediaSource(),
      url = root.URL.createObjectURL(media),
      buffer = null,
      bytes = null,
      timer = null,
      disposed = false,
      removedThrough = 0,
      signal = { cancelled: false };
    var status = {
      mode: 'loading',
      appends: 0,
      bufferAheadSeconds: 0,
      bufferSpanSeconds: 0
    };
    last = status;
    function dispose() {
      if (disposed) return;
      disposed = true;
      signal.cancelled = true;
      if (signal.cancel) signal.cancel();
      if (timer !== null) root.clearInterval(timer);
      timer = null;
      bytes = null;
      buffer = null;
      status.mode = 'closed';
      root.URL.revokeObjectURL(url);
    }
    function fail() {
      if (disposed) return;
      dispose();
      status.mode = 'failed';
      onFailure();
    }
    function pump() {
      if (
        disposed ||
        !buffer ||
        !bytes ||
        buffer.updating ||
        media.readyState !== 'open' ||
        video.error
      )
        return;
      try {
        var n = buffer.buffered.length,
          end = n ? buffer.buffered.end(n - 1) : 0,
          start = n ? buffer.buffered.start(0) : 0;
        status.bufferAheadSeconds = Math.max(0, end - video.currentTime);
        status.bufferSpanSeconds = end - start;
        // Retain a complete previous cycle: removing through a GOP may otherwise overtake playback.
        var cut =
          Math.floor(video.currentTime / spec.seconds) * spec.seconds -
          spec.seconds;
        if (cut > removedThrough && n && cut > start) {
          removedThrough = cut;
          buffer.remove(0, cut);
          return;
        }
        if (end - video.currentTime < spec.seconds) {
          buffer.appendBuffer(bytes);
          status.appends++;
        }
      } catch (_) {
        fail();
      }
    }
    media.addEventListener('sourceopen', function () {
      if (disposed) return;
      try {
        buffer = media.addSourceBuffer(spec.mime);
        buffer.mode = 'sequence';
        media.duration = Infinity;
        buffer.addEventListener('updateend', pump);
        buffer.addEventListener('error', fail);
        root.ThemeData.request(spec.url, spec.size, true, signal)
          .then(function (value) {
            if (disposed) return;
            if (
              value.byteLength !== spec.size ||
              root.ThemeData.hash(value) !== spec.sha256
            )
              throw Error('Stream integrity mismatch');
            bytes = value;
            status.mode = 'mse';
            timer = root.setInterval(pump, 250);
            pump();
          })
          .catch(function () {
            if (!disposed) fail();
          });
      } catch (_) {
        fail();
      }
    });
    media.addEventListener('sourceclose', dispose);
    return { url: url, dispose: dispose };
  }
  root.WallpaperStream = {
    create: create,
    state: function () {
      return Object.assign({}, last);
    }
  };
})(window);
