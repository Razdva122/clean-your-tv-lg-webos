'use strict';
// This source runs only in a phone worker, never in the TV's Node runtime.
function decodePhoto() {
  self.onmessage = function (event) {
    var file = event.data;
    if (!file || !file.size || file.size > 32 * 1024 * 1024) {
      self.postMessage({ error: true });
      self.close();
      return;
    }
    var images = [];
    function release() {
      images.forEach(function (image) {
        image.free();
      });
      images = [];
    }
    function fail() {
      release();
      self.postMessage({ error: true });
      self.close();
    }
    var reader = new FileReader();
    reader.onerror = fail;
    reader.onload = function () {
      try {
        Promise.resolve(libheif()).then(function (module) {
          try {
            images = new module.HeifDecoder().decode(
              new Uint8Array(reader.result)
            );
            var image =
              images.filter(function (item) {
                return item.is_primary();
              })[0] || images[0];
            if (!image) return fail();
            var width = image.get_width(),
              height = image.get_height();
            if (width < 16 || height < 9 || width * height > 50000000)
              return fail();
            image.display(
              {
                width: width,
                height: height,
                data: new Uint8ClampedArray(width * height * 4)
              },
              function (result) {
                if (!result) return fail();
                release();
                self.postMessage(
                  { width: width, height: height, rgba: result.data.buffer },
                  [result.data.buffer]
                );
                self.close();
              }
            );
          } catch (_) {
            fail();
          }
        }, fail);
      } catch (_) {
        fail();
      }
    };
    reader.readAsArrayBuffer(file);
  };
}
module.exports = function () {
  return (
    require('fs').readFileSync(
      __dirname + '/vendor/heic/libheif-bundle.txt',
      'utf8'
    ) +
    '\n;(' +
    decodePhoto.toString() +
    ')();'
  );
};

module.exports.license = function () {
  return (
    require('fs').readFileSync(__dirname + '/vendor/heic/LICENSE.txt', 'utf8') +
    '\n\n' +
    require('fs').readFileSync(__dirname + '/vendor/heic/README.md', 'utf8')
  );
};
