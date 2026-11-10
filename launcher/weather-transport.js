/* Fixed MET Norway LS2 transport. Network policy belongs to the service. */
(function (root) {
  'use strict';
  let sequence = 0;
  root.HomeWeatherTransport = {
    met: function (place) {
      const service = root.ROOT_VERSION
          ? 'com.cleanyourtv.root.preview.service'
          : 'com.gathin.tvhome.renewal',
        id =
          'weather-' +
          Date.now().toString(36) +
          '-' +
          (++sequence).toString(36);
      let bridge,
        timer,
        settled = false,
        rejectRequest;
      function finish(error, forecast) {
        if (settled) return;
        settled = true;
        root.clearTimeout(timer);
        if (bridge) bridge.onservicecallback = function () {};
        if (error) rejectRequest(error);
        else resolveRequest(forecast);
      }
      let resolveRequest;
      function cancel() {
        if (settled) return;
        finish(new Error('Weather request cancelled'));
        if (!bridge) return;
        try {
          bridge.cancel();
        } catch (_) {}
        try {
          const cancellation = new root.PalmServiceBridge();
          cancellation.onservicecallback = function () {};
          cancellation.call(
            'luna://' + service + '/weatherForecastCancel',
            JSON.stringify({ id: id })
          );
        } catch (_) {}
      }
      const promise = new root.Promise(function (resolve, reject) {
        resolveRequest = resolve;
        rejectRequest = reject;
        try {
          if (!root.PalmServiceBridge)
            throw new Error('Weather bridge unavailable');
          bridge = new root.PalmServiceBridge();
          bridge.onservicecallback = function (raw) {
            if (settled) return;
            try {
              const reply = JSON.parse(raw);
              if (
                !reply ||
                reply.returnValue !== true ||
                !reply.forecast ||
                typeof reply.forecast !== 'object' ||
                Array.isArray(reply.forecast)
              )
                throw new Error('Weather response unavailable');
              finish(null, reply.forecast);
            } catch (_) {
              finish(new Error('Weather response unavailable'));
            }
          };
          // The service has a 12-second deadline; allow delivery before cancelling.
          timer = root.setTimeout(cancel, 15000);
          bridge.call(
            'luna://' + service + '/weatherForecast',
            JSON.stringify({
              id: id,
              latitude: place.latitude,
              longitude: place.longitude
            })
          );
        } catch (_) {
          finish(new Error('Weather bridge unavailable'));
        }
      });
      return { promise: promise, cancel: cancel };
    }
  };
})(window);
