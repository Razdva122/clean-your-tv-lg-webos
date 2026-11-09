'use strict';
// Self-contained LAN page; hash is the shared ThemeData SHA-256 algorithm.
function phone() {
  'use strict';
  function hash(input) {
    var a = new Uint8Array(input),
      len = a.length,
      bytes = new Uint8Array(((len + 9 + 63) >> 6) << 6);
    bytes.set(a);
    bytes[len] = 128;
    var v = new DataView(bytes.buffer);
    v.setUint32(bytes.length - 8, Math.floor(len / 536870912));
    v.setUint32(bytes.length - 4, (len * 8) >>> 0);
    var h = [
      1779033703, 3144134277, 1013904242, 2773480762, 1359893119, 2600822924,
      528734635, 1541459225
    ];
    var k = [
      1116352408, 1899447441, 3049323471, 3921009573, 961987163, 1508970993,
      2453635748, 2870763221, 3624381080, 310598401, 607225278, 1426881987,
      1925078388, 2162078206, 2614888103, 3248222580, 3835390401, 4022224774,
      264347078, 604807628, 770255983, 1249150122, 1555081692, 1996064986,
      2554220882, 2821834349, 2952996808, 3210313671, 3336571891, 3584528711,
      113926993, 338241895, 666307205, 773529912, 1294757372, 1396182291,
      1695183700, 1986661051, 2177026350, 2456956037, 2730485921, 2820302411,
      3259730800, 3345764771, 3516065817, 3600352804, 4094571909, 275423344,
      430227734, 506948616, 659060556, 883997877, 958139571, 1322822218,
      1537002063, 1747873779, 1955562222, 2024104815, 2227730452, 2361852424,
      2428436474, 2756734187, 3204031479, 3329325298
    ];
    function r(x, n) {
      return (x >>> n) | (x << (32 - n));
    }
    var w = new Int32Array(64);
    for (var offset = 0; offset < bytes.length; offset += 64) {
      var i;
      for (i = 0; i < 16; i++) w[i] = v.getInt32(offset + i * 4);
      for (i = 16; i < 64; i++) {
        var x = w[i - 15],
          y = w[i - 2];
        w[i] =
          ((r(x, 7) ^ r(x, 18) ^ (x >>> 3)) +
            w[i - 16] +
            (r(y, 17) ^ r(y, 19) ^ (y >>> 10)) +
            w[i - 7]) |
          0;
      }
      var aa = h[0],
        b = h[1],
        c = h[2],
        d = h[3],
        e = h[4],
        f = h[5],
        g = h[6],
        hh = h[7];
      for (i = 0; i < 64; i++) {
        var t1 =
            (hh +
              (r(e, 6) ^ r(e, 11) ^ r(e, 25)) +
              ((e & f) ^ (~e & g)) +
              k[i] +
              w[i]) |
            0,
          t2 =
            ((r(aa, 2) ^ r(aa, 13) ^ r(aa, 22)) +
              ((aa & b) ^ (aa & c) ^ (b & c))) |
            0;
        hh = g;
        g = f;
        f = e;
        e = (d + t1) | 0;
        d = c;
        c = b;
        b = aa;
        aa = (t1 + t2) | 0;
      }
      [aa, b, c, d, e, f, g, hh].forEach(function (n, index) {
        h[index] = (h[index] + n) | 0;
      });
    }
    return h
      .map(function (n) {
        return ('00000000' + (n >>> 0).toString(16)).slice(-8);
      })
      .join('');
  }

  var ru = /^ru\b/i.test(navigator.language),
    texts = ru
      ? {
          title: 'Обои для телевизора',
          intro:
            'Выберите JPG, PNG или HEIC с iPhone. Кадрируйте фото и отправьте на телевизор в вашей сети.',
          file: 'Фото JPG / PNG / HEIC',
          pin: 'PIN на телевизоре',
          zoom: 'Масштаб',
          x: 'По горизонтали',
          y: 'По вертикали',
          ack: 'Я понимаю ограничение качества',
          send: 'Отправить на телевизор',
          cancel: 'Отмена',
          ready: 'Фото готово. Проверьте кадр и подтвердите предупреждение.',
          sending: 'Отправка… ',
          received: 'Получено телевизором. Выберите «Применить» на телевизоре.',
          error:
            'Не удалось отправить. Проверьте PIN и заново откройте приём на телевизоре.',
          invalid:
            'Выберите исправный JPG, PNG или HEIC (до 32 МиБ, до 50 миллионов пикселей). Видео не поддерживается.',
          heicUnsupported:
            'Не удалось открыть HEIC в этом браузере. Откройте страницу в Safari 17 или новее на iPhone либо выберите JPG или PNG.',
          stopped: 'Отменено. Заново откройте приём на телевизоре.'
        }
      : {
          title: 'TV wallpaper',
          intro:
            'Choose JPG, PNG or an iPhone HEIC photo, crop your photo, then send to the TV on your local network.',
          file: 'JPG / PNG / HEIC photo',
          pin: 'PIN shown on TV',
          zoom: 'Zoom',
          x: 'Horizontal position',
          y: 'Vertical position',
          ack: 'I understand the quality limit',
          send: 'Send to TV',
          cancel: 'Cancel',
          ready: 'Photo ready. Check the crop and acknowledge the warning.',
          sending: 'Sending… ',
          received: 'Received by TV. Choose Apply on your TV.',
          error:
            'Could not send. Check the PIN and reopen receiving on your TV.',
          invalid:
            'Choose a valid JPG, PNG or HEIC (up to 32 MiB, 50 million pixels). Video is unsupported.',
          heicUnsupported:
            'Could not open this HEIC photo. Open this page in Safari 17 or newer on your iPhone, or choose JPG or PNG.',
          stopped: 'Cancelled. Reopen receiving on your TV.'
        };
  var warnings = {
    cs: 'Telefon odesílá běžný obrázek do 1080p. Ostrost omezuje rozlišení rozhraní TV. Pro nativní 4K video použijte CYTV na počítači.',
    hi: 'फ़ोन से अधिकतम 1080p की साधारण तस्वीर भेजी जाती है। स्पष्टता टीवी इंटरफ़ेस के रिज़ॉल्यूशन से सीमित है। मूल 4K वीडियो के लिए कंप्यूटर पर CYTV इस्तेमाल करें।',
    en: 'Phone upload is an ordinary image up to 1080p. Actual sharpness is limited by the TV UI resolution. Use CYTV on a computer for the native 4K video layer.',
    ru: 'С телефона загружается обычное изображение до 1080p. Чёткость ограничена разрешением интерфейса ТВ. Для нативного видеослоя 4K используйте CYTV на компьютере.',
    de: 'Vom Telefon wird ein normales Bild bis 1080p geladen. Die Schärfe ist durch die TV-Oberfläche begrenzt. Für die native 4K-Videoebene CYTV am Computer verwenden.',
    es: 'El teléfono envía una imagen normal de hasta 1080p. La nitidez depende de la resolución de la interfaz del TV. Use CYTV en un ordenador para vídeo 4K nativo.',
    fr: 'Le téléphone envoie une image classique jusqu’à 1080p. La netteté dépend de la résolution de l’interface TV. Utilisez CYTV sur ordinateur pour la couche vidéo 4K native.',
    it: 'Il telefono invia una normale immagine fino a 1080p. La nitidezza dipende dalla risoluzione dell’interfaccia TV. Usare CYTV sul computer per il video 4K nativo.',
    pt: 'O telefone envia uma imagem normal até 1080p. A nitidez é limitada pela resolução da interface da TV. Use CYTV no computador para vídeo 4K nativo.',
    uk: 'З телефона завантажується звичайне зображення до 1080p. Чіткість обмежена роздільністю інтерфейсу ТВ. Для нативного відеошару 4K використовуйте CYTV на комп’ютері.',
    pl: 'Telefon wysyła zwykły obraz do 1080p. Ostrość ogranicza rozdzielczość interfejsu TV. Do natywnej warstwy wideo 4K użyj CYTV na komputerze.',
    tr: 'Telefon en fazla 1080p normal görüntü gönderir. Keskinlik TV arayüz çözünürlüğüyle sınırlıdır. Yerel 4K video katmanı için bilgisayarda CYTV kullanın.',
    zh: '手机上传的是最高 1080p 的普通图片。实际清晰度受电视界面分辨率限制。如需原生 4K 视频层，请使用电脑上的 CYTV。',
    ko: '휴대폰 업로드는 최대 1080p 일반 이미지입니다. 선명도는 TV UI 해상도로 제한됩니다. 네이티브 4K 비디오 레이어는 컴퓨터의 CYTV를 사용하세요.'
  };
  document.documentElement.lang = ru ? 'ru' : 'en';
  document.title = texts.title;
  function el(id) {
    return document.getElementById(id);
  }
  Object.keys(texts).forEach(function (id) {
    var target =
      el(id + 'Label') ||
      document.querySelector('label[for="' + id + '"]') ||
      el(id);
    if (target) target.textContent = texts[id];
  });
  el('warning').textContent = /^zh-(TW|HK|Hant)/i.test(navigator.language)
    ? '手機上傳的是最高 1080p 的一般圖片。實際清晰度受電視介面解析度限制。如需原生 4K 影片層，請使用電腦上的 CYTV。'
    : warnings[navigator.language.split('-')[0]] || warnings.en;
  var fragment = /(?:^#|&)pin=(\d{6})(?:&|$)/.exec(location.hash);
  if (fragment) el('pin').value = fragment[1];
  fragment = null;
  history.replaceState(null, '', location.pathname);
  var image = null,
    url = null,
    xhr = null,
    serial = 0,
    busy = false,
    canvas = el('preview'),
    ctx = canvas.getContext('2d');
  function controls() {
    el('send').disabled =
      busy || !image || !el('ack').checked || !/^\d{6}$/.test(el('pin').value);
    ['zoom', 'x', 'y'].forEach(function (id) {
      el(id).disabled = busy || !image;
    });
    el('file').disabled = busy;
    el('pin').disabled = busy;
    el('ack').disabled = busy;
  }
  function drop() {
    serial++;
    image = null;
    if (url) URL.revokeObjectURL(url);
    url = null;
    el('file').value = '';
    el('pin').value = '';
    el('ack').checked = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    controls();
  }
  function draw() {
    if (!image) return;
    var w = Math.min(image.width, (image.height * 16) / 9) / +el('zoom').value,
      h = (w * 9) / 16;
    var scale = Math.min(1, 1920 / w, 1080 / h);
    canvas.width = Math.max(16, Math.floor((w * scale) / 16) * 16);
    canvas.height = (canvas.width * 9) / 16;
    ctx.drawImage(
      image,
      ((image.width - w) * +el('x').value) / 100,
      ((image.height - h) * +el('y').value) / 100,
      w,
      h,
      0,
      0,
      canvas.width,
      canvas.height
    );
  }
  ['zoom', 'x', 'y'].forEach(function (id) {
    el(id).oninput = draw;
  });
  el('pin').oninput = el('ack').onchange = controls;
  el('file').onchange = function () {
    var token = ++serial,
      file = this.files[0];
    image = null;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    el('status').textContent = '';
    el('ack').checked = false;
    controls();
    if (url) URL.revokeObjectURL(url);
    url = null;
    if (!file) return;
    if (!file.size || file.size > 32 * 1024 * 1024) {
      el('status').textContent = texts.invalid;
      return;
    }
    var reader = new FileReader();
    reader.onload = function () {
      if (token !== serial) return;
      var bytes = new Uint8Array(reader.result),
        png =
          bytes[0] === 137 &&
          bytes[1] === 80 &&
          bytes[2] === 78 &&
          bytes[3] === 71,
        jpeg = bytes[0] === 255 && bytes[1] === 216,
        heic = false;
      // MIME and filename may be empty or generic in iPhone's Files picker.
      // Accept only actual JPEG/PNG bytes or a bounded HEIF file-type box.
      if (
        bytes.length >= 16 &&
        String.fromCharCode.apply(null, bytes.subarray(4, 8)) === 'ftyp'
      ) {
        var boxSize = new DataView(reader.result).getUint32(0);
        if (
          boxSize >= 16 &&
          boxSize <= file.size &&
          boxSize <= bytes.length &&
          boxSize % 4 === 0
        ) {
          for (var at = 8; at + 4 <= boxSize; at += 4) {
            if (at === 12) continue; // Minor version, not a compatible brand.
            var brand = String.fromCharCode.apply(
              null,
              bytes.subarray(at, at + 4)
            );
            if (
              [
                'heic',
                'heix',
                'hevc',
                'hevx',
                'heim',
                'heis',
                'hevm',
                'hevs',
                'mif1',
                'msf1'
              ].indexOf(brand) >= 0
            )
              heic = true;
          }
        }
      }
      if (!png && !jpeg && !heic) {
        el('status').textContent = texts.invalid;
        return;
      }
      url = URL.createObjectURL(
        new Blob([file], {
          type: png ? 'image/png' : jpeg ? 'image/jpeg' : 'image/heic'
        })
      );
      var next = new Image();
      next.onload = function () {
        if (token !== serial) return;
        if (
          next.width * next.height > 50000000 ||
          next.width < 16 ||
          next.height < 9
        ) {
          el('status').textContent = texts.invalid;
          URL.revokeObjectURL(url);
          url = null;
          return;
        }
        image = next;
        el('zoom').value = 1;
        el('x').value = el('y').value = 50;
        draw();
        el('status').textContent = texts.ready;
        controls();
      };
      next.onerror = function () {
        if (token === serial) {
          el('status').textContent = heic
            ? texts.heicUnsupported
            : texts.invalid;
          URL.revokeObjectURL(url);
          url = null;
        }
      };
      next.src = url;
    };
    reader.onerror = function () {
      if (token === serial) el('status').textContent = texts.invalid;
    };
    reader.readAsArrayBuffer(file.slice(0, 4096));
  };
  el('send').onclick = function () {
    if (el('send').disabled) return;
    busy = true;
    controls();
    el('status').textContent = texts.sending;
    var token = serial,
      pin = el('pin').value,
      quality = 0.9;
    function encode() {
      canvas.toBlob(
        function (blob) {
          if (token !== serial) return;
          if (!blob) {
            fail();
            return;
          }
          if (blob.size > 2 * 1024 * 1024) {
            quality -= 0.15;
            if (quality < 0.25) {
              fail();
              return;
            }
            encode();
            return;
          }
          var reader = new FileReader();
          reader.onload = function () {
            if (token !== serial) return;
            var bytes = new Uint8Array(reader.result),
              raw = '';
            for (var at = 0; at < bytes.length; at += 8192)
              raw += String.fromCharCode.apply(
                null,
                bytes.subarray(at, at + 8192)
              );
            var payload = {
              schemaVersion: 1,
              kind: 'wallpaper',
              source: 'phone',
              image: {
                mediaType: 'image/jpeg',
                width: canvas.width,
                height: canvas.height,
                size: bytes.length,
                sha256: hash(bytes),
                data: btoa(raw)
              },
              variants: []
            };
            xhr = new XMLHttpRequest();
            xhr.open('POST', '/v1/wallpaper');
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-CYTV-PIN', pin);
            xhr.timeout = 20000;
            xhr.upload.onprogress = function (e) {
              if (e.lengthComputable)
                el('status').textContent =
                  texts.sending + Math.round((e.loaded / e.total) * 100) + '%';
            };
            xhr.onload = function () {
              var ok = xhr.status === 202;
              xhr = null;
              pin = '';
              busy = false;
              drop();
              el('status').textContent = ok ? texts.received : texts.error;
            };
            xhr.onerror = xhr.ontimeout = fail;
            xhr.send(JSON.stringify(payload));
          };
          reader.readAsArrayBuffer(blob);
        },
        'image/jpeg',
        quality
      );
    }
    function fail() {
      xhr = null;
      pin = '';
      busy = false;
      drop();
      el('status').textContent = texts.error;
    }
    encode();
  };
  function cancel() {
    if (xhr) {
      xhr.abort();
      xhr = null;
    }
    busy = false;
    drop();
    el('status').textContent = texts.stopped;
  }
  setTimeout(cancel, Math.max(0, Number('CYTV_SESSION_EXPIRES') - Date.now()));
  el('cancel').onclick = cancel;
  window.addEventListener('pagehide', cancel);
  controls();
}

module.exports =
  '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>TV wallpaper</title><style>*{box-sizing:border-box}body{margin:0;background:#101820;color:#f5f7fa;font:16px/1.5 system-ui,sans-serif}main{max-width:560px;padding:24px 20px 40px;margin:auto}h1{font-size:28px;line-height:1.2}p{margin:16px 0}label{display:block;margin:16px 0 6px}input,button{font:inherit;min-height:48px}input[type=file]{width:100%;padding:8px 0}input[type=range]{width:100%}input[type=text]{width:100%;padding:10px;border:1px solid #8fa6b6;border-radius:6px;background:#182934;color:inherit}canvas{display:block;width:100%;height:auto;aspect-ratio:16/9;background:#000;margin:20px 0}button{padding:10px 16px;border:0;border-radius:6px;cursor:pointer;background:#65d1cb;color:#0e2629;margin:8px 8px 0 0}button:disabled{opacity:.5;cursor:default}#warning{border-left:4px solid #e6b85e;padding:12px;background:#24303a}#ack{width:24px;height:24px;min-height:24px;vertical-align:middle;margin-right:10px}#status{min-height:48px}:focus-visible{outline:3px solid #e6b85e;outline-offset:3px}</style><main><h1 id="title"></h1><p id="intro"></p><label for="pin" id="pinLabel">PIN</label><input id="pin" type="text" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" autocomplete="off"><label for="file" id="fileLabel">JPG / PNG / HEIC</label><input id="file" type="file" accept="image/jpeg,image/png,image/heic,image/heif,image/heic-sequence,image/heif-sequence,.heic,.heif"><canvas id="preview" width="320" height="180" aria-label="16:9 crop preview"></canvas><label for="zoom">Zoom</label><input id="zoom" type="range" min="1" max="3" step=".05" value="1" disabled><label for="x">Horizontal position</label><input id="x" type="range" min="0" max="100" value="50" disabled><label for="y">Vertical position</label><input id="y" type="range" min="0" max="100" value="50" disabled><p id="warning"></p><label><input id="ack" type="checkbox"><span id="ackLabel"></span></label><button id="send" disabled></button><button id="cancel"></button><p id="status" role="status" aria-live="polite"></p></main><script>' +
  '(' +
  phone.toString() +
  ')();</script></html>';
