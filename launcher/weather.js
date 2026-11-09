/* Home-owned weather renderer and settings. Shared by Root and No-root. */
(function (root) {
  'use strict';
  const formats = root.WeatherData.formats,
    store = root.WeatherData.create({
      language: root.HomeI18n.language(),
      metRequest: root.HomeWeatherTransport.met
    }),
    doc = root.document;
  let options = store.state(),
    element,
    previewSheet,
    region = null,
    last = null,
    started = false,
    busy = false,
    queued = false,
    headerFont = 'sans-serif',
    headerColor = '#fff',
    pageHidden = false;
  function t(key, params) {
    return root.HomeI18n.t('Weather / ' + key, params);
  }
  function lang() {
    return root.HomeI18n.language();
  }
  function number(value) {
    try {
      return value.toLocaleString(lang(), { maximumFractionDigits: 1 });
    } catch (_) {
      return String(value);
    }
  }
  function percent(value) {
    try {
      if (root.Intl)
        return new Intl.NumberFormat(lang(), {
          style: 'percent',
          maximumFractionDigits: 0
        }).format(value);
    } catch (_) {}
    return number(Math.round(value * 100)) + '%';
  }
  function weekday(date) {
    const value = new Date(date + 'T12:00:00Z');
    try {
      if (root.Intl)
        return value.toLocaleDateString(lang(), {
          weekday: 'short',
          timeZone: 'UTC'
        });
    } catch (_) {}
    return root.HomeI18n.t(
      [
        'Sunday',
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday'
      ][value.getUTCDay()]
    );
  }
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () {
      queued = false;
      render();
    });
  }
  function storeState() {
    const state = store.state();
    state.searchResults = state.results;
    return state;
  }
  function escape(value) {
    return String(value ?? '').replace(
      /[&<>"']/g,
      (c) =>
        ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;'
        })[c]
    );
  }
  function dayLabel(day, index, w) {
    const today = new Date(Date.now() + (w.offset || 0) * 1000)
      .toISOString()
      .slice(0, 10);
    if (day.date === today) return t('Today');
    const tomorrow = new Date(today + 'T12:00:00Z');
    tomorrow.setUTCDate(tomorrow.getUTCDate() + 1);
    if (day.date === tomorrow.toISOString().slice(0, 10)) return t('Tomorrow');
    return weekday(day.date);
  }
  function condition(code, day) {
    return root.WeatherData.condition(code, day);
  }
  var iconSequence = 0;
  function img(c, style) {
    if (!c.icon) return '<span aria-hidden="true">—</span>';
    if (style === 'monochrome' && root.WeatherIcons[c.icon]) {
      var prefix = 'weatherIcon' + ++iconSequence + '_';
      return root.WeatherIcons[c.icon]
        .replace(
          '<svg ',
          '<svg class="ctv-weather-icon" role="img" aria-label="' +
            escape(t(c.label)) +
            '" '
        )
        .replace(/id="/g, 'id="' + prefix)
        .replace(/url\(#/g, 'url(#' + prefix)
        .replace(/href="#/g, 'href="#' + prefix);
    }
    return (
      '<img class="ctv-weather-icon" alt="' +
      escape(t(c.label)) +
      '" src="weather-icons/' +
      style +
      '-' +
      c.icon +
      '.svg">'
    );
  }
  function temp(v) {
    if (!Number.isFinite(v)) return '—';
    if (options.units === 'imperial') v = (v * 9) / 5 + 32;
    v = Math.round(v);
    return (
      (v < 0 ? '−' + number(-v) : v > 0 ? '+' + number(v) : number(0)) + '°'
    );
  }
  function content(format, iconStyle, w = store.state().data) {
    if (!w) return '';
    const c = condition(w.code, w.isDay),
      first = w.days[0],
      range = first
        ? '↑ ' + temp(first.high) + ' &nbsp; ↓ ' + temp(first.low)
        : '';
    if (format === 'text')
      return (
        '<div class="weather-line">' +
        img(c, iconStyle) +
        '<span class="weather-temp ctv-weather-temp">' +
        temp(w.temp) +
        '</span><span>' +
        t(c.label) +
        '</span><span class="weather-secondary ctv-weather-secondary">' +
        range +
        '</span></div>'
      );
    let html =
      '<div class="weather-header"><div><div class="weather-city">' +
      escape(w.city || t('Yekaterinburg')) +
      '</div><div class="weather-temp ctv-weather-temp">' +
      temp(w.temp) +
      '</div>' +
      (w.feels !== null
        ? '<div class="weather-secondary ctv-weather-secondary weather-feels">' +
          t('Feels like {value}', { value: temp(w.feels) }) +
          '</div>'
        : '') +
      '</div><div class="weather-condition ctv-weather-condition">' +
      img(c, iconStyle) +
      '<span>' +
      t(c.label) +
      '</span><span class="weather-secondary ctv-weather-secondary">' +
      range +
      '</span></div></div>';
    if (format === 'details') {
      const metrics = [];
      if (w.wind !== null)
        metrics.push([
          'Wind',
          number(
            Math.round(w.wind * (options.units === 'imperial' ? 2.236936 : 1))
          ) +
            ' ' +
            t(options.units === 'imperial' ? 'mph' : 'm/s')
        ]);
      if (w.precip !== null)
        metrics.push(['Precipitation', percent(w.precip / 100)]);
      if (w.humidity !== null)
        metrics.push(['Humidity', percent(w.humidity / 100)]);
      if (metrics.length)
        html +=
          '<div class="weather-rule"></div><div class="weather-metrics">' +
          metrics
            .map(
              (m) =>
                '<div><span>' +
                t(m[0]) +
                '</span><strong>' +
                m[1] +
                '</strong></div>'
            )
            .join('') +
          '</div>';
    }
    if (format === 'forecast') {
      const low = Math.min(...w.days.map((d) => d.low)),
        high = Math.max(...w.days.map((d) => d.high)),
        span = high - low;
      html +=
        '<div class="weather-rule"></div>' +
        (!w.days.length
          ? t('No forecast')
          : w.days
              .map(
                (d, index) =>
                  '<div class="weather-row"><span class="ctv-weather-day">' +
                  dayLabel(d, index, w) +
                  '</span>' +
                  img(condition(d.code), iconStyle) +
                  '<span class="weather-secondary ctv-weather-secondary weather-low">' +
                  temp(d.low) +
                  '</span><span class="weather-track ctv-weather-track"><span class="ctv-weather-bar" style="left:' +
                  (span ? ((d.low - low) / span) * 100 : 0) +
                  '%;width:' +
                  (span ? ((d.high - d.low) / span) * 100 : 100) +
                  '%"></span></span><span class="weather-high">' +
                  temp(d.high) +
                  '</span></div>'
              )
              .join(''));
    }
    return html;
  }

  function fitLabels(container) {
    const range = doc.createRange(),
      renderedScale =
        container.getBoundingClientRect().width / container.offsetWidth || 1;
    function textWidth(label) {
      // Measure the rendered glyphs, including locale-specific font fallback.
      range.selectNodeContents(label);
      return Math.ceil(range.getBoundingClientRect().width / renderedScale);
    }
    let width = 138,
      tempWidth = 58;
    Array.prototype.forEach.call(
      container.querySelectorAll('.weather-row>span:first-child'),
      function (label) {
        width = Math.max(width, textWidth(label));
      }
    );
    Array.prototype.forEach.call(
      container.querySelectorAll('.weather-low,.weather-high'),
      function (label) {
        tempWidth = Math.max(tempWidth, textWidth(label));
      }
    );
    Array.prototype.forEach.call(
      container.querySelectorAll('.weather-row'),
      function (row) {
        const label = row.children[0],
          low = row.children[2],
          track = row.children[3],
          high = row.children[4];
        label.style.width = width + 'px';
        low.style.width = high.style.width = tempWidth + 'px';
        track.style.width =
          Math.max(
            40,
            container.clientWidth -
              width -
              tempWidth * 2 -
              52 -
              48 -
              parseFloat(getComputedStyle(container).paddingLeft) * 2
          ) + 'px';
      }
    );
  }
  function appearance() {
    const value = root.ThemeRuntime.weather();
    return {
      options: root.ThemePolicy.normalizeWeather(
        value.options || { padding: 0, icons: 'monochrome' }
      ),
      css: value.css
    };
  }
  function paint(target, format, data, preview) {
    const a = appearance(),
      w = a.options;
    target.innerHTML = content(format, w.icons, data);
    target.setAttribute('data-format', format);
    if (!doc.getElementById('weatherDefaults')) {
      const defaults = doc.createElement('style');
      defaults.id = 'weatherDefaults';
      doc.head.appendChild(defaults);
    }
    doc.getElementById('weatherDefaults').textContent =
      '#homeWeather,#weatherPreviewSurface .home-weather{font-family:' +
      headerFont +
      ';color:' +
      headerColor +
      '}';
    target.style.padding = format === 'text' ? '0' : w.padding + 'px';
    if (preview) {
      if (!previewSheet) {
        previewSheet = doc.createElement('style');
        previewSheet.id = 'weatherPreviewStyle';
        doc.head.appendChild(previewSheet);
      }
      previewSheet.textContent = a.css.replace(
        /#homeSurface\.ctv-home/g,
        '#weatherPreviewSurface'
      );
    }
  }
  function position(node) {
    let left = 0,
      top = 0;
    while (node && node.id !== 'homeSurface') {
      left += node.offsetLeft;
      top += node.offsetTop;
      node = node.offsetParent;
    }
    return {
      left: left,
      top: top,
      bottom: top + (arguments[0]?.offsetHeight || 0)
    };
  }
  function render() {
    if (!started || busy || !root.HomeLayoutState) return;
    busy = true;
    try {
      store.setLanguage(lang());
      options = store.state();
      const state = root.HomeLayoutState.state(),
        a = appearance(),
        supported = state.ribbon ? [] : a.options.formats;
      store.setAllowed(
        supported.length > 0 && !pageHidden && doc.visibilityState !== 'hidden'
      );
      const effective =
        supported.indexOf(options.preferred) >= 0
          ? options.preferred
          : supported.indexOf('text') >= 0
            ? 'text'
            : supported[0];
      const old = JSON.stringify(region);
      region = null;
      if (!element) {
        element = doc.createElement('section');
        element.id = 'homeWeather';
        element.className = 'home-weather ctv-weather';
        doc.getElementById('homeSurface').appendChild(element);
      }
      const show = options.enabled && !!effective && !!options.data;
      element.hidden = !show;
      doc
        .getElementById('homeSurface')
        .classList.toggle(
          'weather-reserves-right',
          show && effective !== 'text' && state.preset === 'scenic-grid'
        );
      doc
        .getElementById('homeSurface')
        .classList.toggle(
          'weather-replaces-artwork',
          show && effective !== 'text' && state.preset === 'channel-list'
        );
      if (!root.ThemeRuntime.isSuspended()) {
        const clock = getComputedStyle(doc.getElementById('clock'));
        headerFont = clock.fontFamily;
        headerColor = clock.color;
      }
      const hero = doc.getElementById('hero');
      hero.style.maxWidth = '';
      hero.style.whiteSpace = '';
      if (show) {
        paint(element, effective, options.data, false);
        const header = position(doc.querySelector('#homeSurface>header')),
          time = position(doc.getElementById('timeRow')),
          buttons = position(doc.getElementById('topButtons')),
          scale = a.options.scale;
        const width = effective === 'text' ? 920 : 660;
        let left =
            effective === 'text' ? header.left : 1920 - 112 - width * scale,
          top = effective === 'text' ? time.bottom + 20 : buttons.bottom + 26;
        if (state.preset === 'side-grid') {
          left = effective === 'text' ? 560 : 1920 - 112 - width * scale;
          top = effective === 'text' ? 100 : 72;
        }
        element.style.width = width + 'px';
        element.style.left = left + 'px';
        element.style.top = top + 'px';
        element.style.transform = 'scale(' + scale + ')';
        element.style.webkitTransform = element.style.transform;
        fitLabels(element);
        const bottom = top + element.offsetHeight * scale;
        region = {
          bottom: bottom,
          format: effective,
          shelfTop:
            effective === 'text' && state.inputs === 'shelf'
              ? Math.max(236, Math.ceil(bottom + 38))
              : 236
        };
        element.setAttribute(
          'aria-label',
          t('Weather: {city}', {
            city: options.data.city || t('Yekaterinburg')
          })
        );
        if (!previewSheet) {
          previewSheet = doc.createElement('style');
          previewSheet.id = 'weatherPreviewStyle';
          doc.head.appendChild(previewSheet);
        }
        if (state.preset === 'dock-grid' || state.preset === 'scenic-grid') {
          hero.style.maxWidth =
            effective === 'text'
              ? ''
              : Math.max(300, left - position(hero).left - 48) + 'px';
          hero.style.whiteSpace = effective === 'text' ? '' : 'normal';
        }
      }
      last = { supported: supported, effective: show ? effective : null };
      refreshSettings();
      if (old !== JSON.stringify(region)) {
        const event = doc.createEvent('Event');
        event.initEvent('home-weather-layout', false, false);
        doc.dispatchEvent(event);
      }
    } finally {
      busy = false;
    }
  }
  const formatLabels = {
    text: 'Compact',
    current: 'Now',
    details: 'In detail',
    forecast: '4 days'
  };
  const sourceNames = { 'met-no': 'MET Norway', 'open-meteo': 'Open-Meteo' };
  let settingsHost, cityDialog, cityReturn, sourcesDialog, sourcesButton;
  function choose(format, on) {
    const value = {};
    if (format) value.preferred = format;
    if (on !== undefined) value.enabled = on;
    store.setPreferences(value);
  }
  function refreshSettings() {
    if (!settingsHost || !last) return;
    options = store.state();
    const supported = last.supported;
    settingsHost.querySelector('.weather-options').hidden = !options.enabled;
    settingsHost.classList.toggle('weather-is-off', !options.enabled);
    settingsHost.classList.toggle('weather-unsupported', !supported.length);
    if (!options.enabled && cityDialog && !cityDialog.hidden) closeCity();
    refreshLocationSettings();
    settingsHost.querySelector('.weather-provider-label').textContent =
      t('Weather source');
    settingsHost
      .querySelectorAll('[data-weather-provider]')
      .forEach((button) => {
        const provider = button.dataset.weatherProvider;
        button.textContent =
          provider === 'auto' ? t('Auto') : sourceNames[provider];
        button.setAttribute(
          'aria-pressed',
          String(options.provider === provider)
        );
      });
    settingsHost.querySelector('.weather-actual-source').textContent =
      options.source && sourceNames[options.source]
        ? t('Source: {source}', { source: sourceNames[options.source] })
        : t(
            options.status === 'error'
              ? 'Weather unavailable. Try again.'
              : 'No source data yet'
          );
    settingsHost.querySelector('.weather-units-label').textContent = t('Units');
    settingsHost.querySelectorAll('[data-weather-unit]').forEach((b) => {
      b.setAttribute(
        'aria-pressed',
        String(options.units === b.dataset.weatherUnit)
      );
      b.textContent =
        b.dataset.weatherUnit === 'metric'
          ? '°C · ' + t('m/s')
          : '°F · ' + t('mph');
    });
    const tab = document.querySelector('[data-category="weather"]');
    if (tab) tab.querySelector('span').textContent = t('Weather');
    const heading = document.querySelector('#settings-pane-weather>h3');
    if (heading) {
      const title = heading.querySelector('.weather-settings-title');
      if (title) title.textContent = t('Weather');
      else heading.textContent = t('Weather');
    }
    if (sourcesButton) sourcesButton.textContent = 'ⓘ ' + t('Data sources');
    settingsHost.querySelector('.weather-enabled>span').textContent =
      t('Weather on Home');
    settingsHost
      .querySelector('.weather-enabled')
      .setAttribute('aria-label', t('Weather on Home'));
    settingsHost
      .querySelectorAll('[data-weather-choice]')
      .forEach(
        (b) =>
          (b.querySelector('.weather-format-title').textContent = t(
            formatLabels[b.dataset.weatherChoice]
          ))
      );
    const toggle = settingsHost.querySelector('.weather-enabled');
    toggle.disabled = false;
    toggle.setAttribute('aria-checked', String(options.enabled));
    toggle.querySelector('.weather-switch-state').textContent = options.enabled
      ? t('On')
      : t('Off');
    settingsHost.querySelector('.weather-formats-label').textContent =
      t('Format');
    settingsHost.querySelector('.weather-settings-note').hidden =
      supported.length === 4;
    settingsHost.querySelector('.weather-settings-note').textContent =
      !supported.length
        ? t('Weather is unavailable in Ribbon. Choose another composition.')
        : supported.length === 1
          ? t('This theme supports only the compact format.')
          : t('Choose a format. Its appearance follows your theme.');
    settingsHost.querySelectorAll('[data-weather-choice]').forEach((button) => {
      const format = button.dataset.weatherChoice;
      button.hidden = !supported.includes(format);
      button.setAttribute(
        'aria-pressed',
        String((last.effective || options.preferred) === format)
      );
    });
    const format =
      last.effective ||
      (supported.includes(options.preferred)
        ? options.preferred
        : supported[0]);
    settingsHost.querySelector('.weather-live-preview').hidden =
      !format || !options.enabled;
    const liveData = storeState().data;
    settingsHost.querySelector('.weather-live-title').textContent = format
      ? t(formatLabels[format]) + (liveData ? '' : ' · ' + t('Example'))
      : '';
    settingsHost.querySelector('.weather-live-preview').hidden =
      !format || !options.enabled;
    if (format) {
      const preview = settingsHost.querySelector('.weather-preview');
      paint(preview, format, liveData || root.WeatherData.example(), true);
      preview.style.width = format === 'text' ? '920px' : '660px';
      preview.style.transform = 'none';
      fitLabels(preview);
      const area = settingsHost.querySelector('.weather-preview-window');
      let width = 660;
      if (format === 'text') {
        const line = preview.querySelector('.weather-line');
        width =
          [...line.children].reduce(
            (sum, child) => sum + child.getBoundingClientRect().width,
            0
          ) +
          20 * (line.children.length - 1);
        preview.style.width = width + 'px';
      }
      const scale = Math.min(
        1,
        (area.clientWidth - 8) / width,
        (area.clientHeight - 8) / preview.offsetHeight
      );
      preview.style.transform = 'scale(' + Math.max(0.1, scale) + ')';
      preview.style.left =
        Math.max(0, (area.clientWidth - width * scale) / 2) + 'px';
      preview.style.top =
        Math.max(0, (area.clientHeight - preview.offsetHeight * scale) / 2) +
        'px';
    }
  }
  function mountSettings(panel, card, groups) {
    settingsHost = document.createElement('div');
    settingsHost.className = 'weather-settings';
    settingsHost.innerHTML =
      '<div class="weather-left"><button type="button" class="weather-enabled" role="switch" aria-checked="true"><span></span><span class="weather-switch-value" aria-hidden="true"><span class="weather-switch-state"></span><span class="weather-switch-track"><span></span></span></span></button><div class="weather-options"><button type="button" class="weather-city-summary"><span class="weather-city-heading"><span class="weather-city-label"></span><span class="weather-city-mode"></span></span><span class="weather-city-value"></span><span class="weather-city-chevron" aria-hidden="true">›</span></button><div class="weather-units"><span class="weather-units-label"></span><div><button type="button" data-weather-unit="metric" aria-pressed="true"></button><button type="button" data-weather-unit="imperial" aria-pressed="false"></button></div></div><div class="weather-formats-label"></div><div class="weather-format-grid">' +
      formats
        .map(
          (format) =>
            '<button type="button" class="weather-format-choice" data-weather-choice="' +
            format +
            '" aria-pressed="false"><span class="weather-format-title"></span><span class="weather-choice-state" aria-hidden="true">✓</span></button>'
        )
        .join('') +
      '</div><p class="weather-settings-note"></p></div></div><div class="weather-right"><div class="weather-provider" role="group" aria-labelledby="weather-provider-label"><div id="weather-provider-label" class="weather-provider-label"></div><div class="weather-provider-choices"><button type="button" data-weather-provider="auto"></button><button type="button" data-weather-provider="met-no"></button><button type="button" data-weather-provider="open-meteo"></button></div><div class="weather-actual-source" role="status"></div></div><div class="weather-live-preview"><div class="weather-live-title"></div><div class="weather-preview-window" aria-hidden="true"><div id="weatherPreviewSurface" class="weather-preview-surface ctv-home"><div id="weatherPreview" class="weather-preview home-weather ctv-weather"></div></div></div></div></div>';
    settingsHost
      .querySelectorAll('[data-weather-provider]')
      .forEach((button) => {
        button.onclick = () =>
          store.setPreferences({ provider: button.dataset.weatherProvider });
      });
    settingsHost.querySelector('.weather-city-summary').onclick = openCity;
    mountCity();
    settingsHost.querySelector('.weather-enabled').onclick = () =>
      choose(null, !options.enabled);
    settingsHost
      .querySelectorAll('[data-weather-choice]')
      .forEach(
        (button) =>
          (button.onclick = () => choose(button.dataset.weatherChoice))
      );
    settingsHost.querySelectorAll('[data-weather-unit]').forEach(
      (b) =>
        (b.onclick = () => {
          store.setPreferences({ units: b.dataset.weatherUnit });
        })
    );
    groups.splice(
      groups.findIndex((group) => group.id === 'wallpapers') + 1,
      0,
      { id: 'weather', label: t('Weather'), elements: [settingsHost] }
    );
    return function () {
      mountSources(card);
      const icon = card.querySelector('[data-category="weather"] path');
      if (icon)
        icon.setAttribute(
          'd',
          'M7 18a5 5 0 1 1 1-10 6 6 0 0 1 11 3 4 4 0 0 1-1 8H7'
        );
      const tab = card.querySelector('[data-category="weather"]');
      tab.addEventListener('focusin', schedule);
      tab.addEventListener('click', schedule);
      refreshSettings();
    };
  }
  function mountSources(card) {
    const heading = card.querySelector('#settings-pane-weather>h3');
    heading.classList.add('weather-settings-heading');
    heading.textContent = '';
    const title = doc.createElement('span');
    title.className = 'weather-settings-title';
    title.textContent = t('Weather');
    sourcesButton = doc.createElement('button');
    sourcesButton.type = 'button';
    sourcesButton.className = 'weather-sources-button';
    sourcesButton.textContent = 'ⓘ ' + t('Data sources');
    heading.appendChild(title);
    heading.appendChild(sourcesButton);
    sourcesDialog = doc.createElement('section');
    sourcesDialog.className = 'weather-city-dialog weather-sources-dialog';
    sourcesDialog.hidden = true;
    sourcesDialog.setAttribute('role', 'dialog');
    sourcesDialog.setAttribute('aria-modal', 'true');
    sourcesDialog.setAttribute('aria-labelledby', 'weather-sources-title');
    doc.body.appendChild(sourcesDialog);
    function close() {
      sourcesDialog.hidden = true;
      if (sourcesButton.offsetHeight) sourcesButton.focus();
    }
    sourcesButton.onclick = function () {
      sourcesDialog.innerHTML =
        '<div class="weather-city-card"><h2 id="weather-sources-title">' +
        escape(t('Data sources')) +
        '</h2><dl>' +
        '<dt>' +
        escape(t('Forecast')) +
        '</dt><dd><a href="https://www.met.no/" target="_blank" rel="noopener">MET Norway</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a> · <a href="https://api.met.no/doc/TermsOfService" target="_blank" rel="noopener">' +
        escape(t('Terms of service')) +
        '</a><br><a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a></dd>' +
        '<dt>' +
        escape(t('Location')) +
        '</dt><dd><a href="https://www.geonames.org/" target="_blank" rel="noopener">GeoNames</a> · Open-Meteo · CC BY 4.0</dd>' +
        '<dt>' +
        escape(t('Automatic')) +
        '</dt><dd><a href="https://www.geojs.io/" target="_blank" rel="noopener">GeoJS</a></dd>' +
        '<dt>' +
        escape(t('Icons')) +
        '</dt><dd><a href="https://github.com/basmilius/meteocons" target="_blank" rel="noopener">Meteocons — Bas Milius</a> · MIT</dd></dl>' +
        '<p>' +
        escape(t('Values are rounded and converted to your selected units.')) +
        ' ' +
        escape(t('Daily ranges summarize forecast points.')) +
        '</p><button type="button" class="weather-sources-close">' +
        escape(t('Back')) +
        '</button></div>';
      sourcesDialog.querySelector('button').onclick = close;
      sourcesDialog.hidden = false;
      sourcesDialog.querySelector('button').focus();
    };
    root.addEventListener(
      'keydown',
      function (event) {
        if (
          sourcesDialog.hidden ||
          ![9, 13, 27, 37, 38, 39, 40, 461].includes(event.keyCode)
        )
          return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const list = [...sourcesDialog.querySelectorAll('a,button')],
          at = list.indexOf(doc.activeElement),
          key = event.keyCode;
        if (key === 27 || key === 461) close();
        else if (key === 13) {
          if (!event.repeat && doc.activeElement) doc.activeElement.click();
        } else
          list[
            (at +
              (key === 37 || key === 38 || (key === 9 && event.shiftKey)
                ? -1
                : 1) +
              list.length) %
              list.length
          ].focus();
      },
      true
    );
  }
  let previousResults = '';
  function placeLabel(location) {
    if (!location) return '';
    const country = location.country || '';
    return [...new Set([location.name, country].filter(Boolean))].join(' · ');
  }
  function refreshLocationSettings() {
    const state = storeState(),
      host = cityDialog;
    if (!host) return;
    const cityValue = state.location
      ? placeLabel(state.location)
      : state.mode === 'auto'
        ? t(state.status === 'locating' ? 'Finding city…' : 'Not determined')
        : t('Choose city');
    settingsHost.querySelector('.weather-city-label').textContent =
      t('Location');
    settingsHost.querySelector('.weather-city-mode').textContent = t(
      state.mode === 'auto' ? 'Automatic' : 'Manual'
    );
    settingsHost.querySelector('.weather-city-value').textContent = cityValue;
    host.querySelector('h2').textContent = t('Location');
    host.querySelector('.weather-city-back').textContent = t('Back');
    host.querySelectorAll('[data-location-mode]').forEach((b) => {
      b.textContent = t(
        b.dataset.locationMode === 'auto' ? 'Automatic' : 'Manual'
      );
      b.setAttribute(
        'aria-pressed',
        String(state.mode === b.dataset.locationMode)
      );
    });
    host.querySelector('.weather-location-help').hidden = state.mode !== 'auto';
    host.querySelector('.weather-location-help').textContent = t(
      'Approximate city by IP. VPN can change the result.'
    );
    const detected = host.querySelector('.weather-detected-city');
    detected.hidden = state.mode !== 'auto';
    detected.textContent = cityValue;
    host.querySelector('.weather-city-search').hidden = state.mode !== 'manual';
    host.querySelector('.weather-search-status').hidden =
      state.mode !== 'manual';
    host.querySelector('.weather-city-results').hidden =
      state.mode !== 'manual';
    const input = host.querySelector('input');
    input.placeholder = t('City name');
    input.setAttribute('aria-label', t('City name'));
    host.querySelector('.weather-search-button').textContent = t('Search');
    host.querySelector('.weather-search-button').disabled =
      state.searchStatus === 'loading';
    const searchLabels = {
      loading: 'Searching…',
      short: 'Enter at least 2 characters.',
      empty: 'No cities found.',
      error: 'Search unavailable. Try again.'
    };
    host.querySelector('.weather-search-status').textContent = searchLabels[
      state.searchStatus
    ]
      ? t(searchLabels[state.searchStatus])
      : '';
    const identity = JSON.stringify(state.searchResults);
    if (identity !== previousResults) {
      previousResults = identity;
      const results = host.querySelector('.weather-city-results');
      results.replaceChildren();
      for (const city of state.searchResults) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = [city.name, city.admin1, city.country]
          .filter(Boolean)
          .join(' · ');
        button.onclick = () => {
          store.select(city.id);
          closeCity();
        };
        results.appendChild(button);
      }
    }
  }
  function mountCity() {
    if (cityDialog) return;
    cityDialog = document.createElement('div');
    cityDialog.className = 'weather-city-dialog';
    cityDialog.hidden = true;
    cityDialog.setAttribute('role', 'dialog');
    cityDialog.setAttribute('aria-modal', 'true');
    cityDialog.setAttribute('aria-labelledby', 'weather-city-title');
    cityDialog.innerHTML =
      '<div class="weather-city-card"><div class="weather-city-header"><h2 id="weather-city-title"></h2><button type="button" class="weather-city-back"></button></div><div class="weather-location-modes"><button type="button" data-location-mode="auto"></button><button type="button" data-location-mode="manual"></button></div><p class="weather-location-help"></p><p class="weather-detected-city"></p><div class="weather-city-search"><input type="text" maxlength="100" autocomplete="off"><button type="button" class="weather-search-button"></button></div><div class="weather-search-status" role="status"></div><div class="weather-city-results"></div></div>';
    document.body.appendChild(cityDialog);
    cityDialog.querySelector('.weather-city-back').onclick = closeCity;
    cityDialog.querySelectorAll('[data-location-mode]').forEach(
      (b) =>
        (b.onclick = () => {
          store.setMode(b.dataset.locationMode);
          refreshLocationSettings();
          if (b.dataset.locationMode === 'manual')
            cityDialog.querySelector('input').focus();
        })
    );
    cityDialog.querySelector('.weather-search-button').onclick = () =>
      store.search(cityDialog.querySelector('input').value);
    window.addEventListener(
      'keydown',
      (event) => {
        if (cityDialog.hidden) return;
        const key = event.keyCode,
          active = document.activeElement;
        if (![9, 13, 27, 37, 38, 39, 40, 461].includes(key)) {
          event.stopPropagation();
          return;
        }
        event.stopImmediatePropagation();
        if ((key === 37 || key === 39) && active.tagName === 'INPUT') return;
        event.preventDefault();
        if (key === 27 || key === 461) {
          closeCity();
          return;
        }
        if (key === 13) {
          if (!event.repeat) {
            if (active.tagName === 'INPUT')
              cityDialog.querySelector('.weather-search-button').click();
            else active.click();
          }
          return;
        }
        const list = [...cityDialog.querySelectorAll('button,input')].filter(
            (e) => !e.disabled && e.offsetHeight > 0
          ),
          index = list.indexOf(active);
        if (key === 9) {
          list[
            (index + (event.shiftKey ? -1 : 1) + list.length) % list.length
          ].focus();
          return;
        }
        const r = active.getBoundingClientRect();
        let best = null,
          distance = Infinity;
        for (const button of list) {
          if (button === active) continue;
          const b = button.getBoundingClientRect(),
            vertical = key === 38 || key === 40,
            delta =
              key === 37
                ? r.left - b.right
                : key === 39
                  ? b.left - r.right
                  : key === 38
                    ? r.top - b.bottom
                    : b.top - r.bottom;
          const overlap = vertical
            ? b.right > r.left && b.left < r.right
            : b.bottom > r.top && b.top < r.bottom;
          if (delta < -2 || !overlap) continue;
          const alignment = vertical
              ? Math.abs(b.left + b.width / 2 - r.left - r.width / 2)
              : Math.abs(b.top + b.height / 2 - r.top - r.height / 2),
            score = Math.max(0, delta) + alignment;
          if (score < distance) {
            distance = score;
            best = button;
          }
        }
        if (best) best.focus();
      },
      true
    );
    window.addEventListener(
      'keydown',
      (event) => {
        if (
          !cityDialog.hidden ||
          !settingsHost.contains(document.activeElement) ||
          !settingsHost.offsetHeight
        )
          return;
        const key = event.keyCode;
        if (![37, 38, 39, 40].includes(key)) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const active = document.activeElement,
          units = [...settingsHost.querySelectorAll('[data-weather-unit]')],
          providers = [
            ...settingsHost.querySelectorAll('[data-weather-provider]')
          ],
          tab = document.querySelector('[data-category="weather"]');
        if (key === 37 || key === 39) {
          if (key === 39 && active.classList.contains('weather-enabled')) {
            (
              providers.find(
                (b) => b.getAttribute('aria-pressed') === 'true'
              ) || providers[0]
            ).focus();
            return;
          }
          const row = providers.includes(active) ? providers : units,
            index = row.indexOf(active);
          if (index >= 0 && row[index + (key === 37 ? -1 : 1)])
            row[index + (key === 37 ? -1 : 1)].focus();
          else if (key === 37) {
            if (providers.includes(active))
              settingsHost.querySelector('.weather-enabled').focus();
            else tab.focus();
          }
          return;
        }
        const groups = [
          [settingsHost.querySelector('.weather-enabled')],
          providers,
          [settingsHost.querySelector('.weather-city-summary')],
          units,
          ...[...settingsHost.querySelectorAll('[data-weather-choice]')].map(
            (b) => [b]
          )
        ].filter((row) => row.some((e) => e.offsetHeight > 0));
        const index = groups.findIndex((row) => row.includes(active)),
          next = groups[index + (key === 38 ? -1 : 1)];
        if (next) {
          const target =
            next.find((b) => b.getAttribute('aria-pressed') === 'true') ||
            next[0];
          target.focus();
        } else if (key === 38) sourcesButton.focus();
        else
          settingsHost
            .closest('.settings-workspace')
            .querySelector('.settings-footer button')
            .focus();
      },
      true
    );
  }
  function openCity() {
    cityReturn = settingsHost.querySelector('.weather-city-summary');
    refreshLocationSettings();
    cityDialog.hidden = false;
    cityDialog
      .querySelector('[data-location-mode="' + storeState().mode + '"]')
      .focus();
  }
  function closeCity() {
    if (!cityDialog) return;
    cityDialog.hidden = true;
    if (cityReturn?.offsetHeight) cityReturn.focus();
  }
  function openSettings() {
    const panel = root.RenewalPanel || root.RootSettings;
    if (panel?.open) panel.open();
    else document.getElementById('btnSettings').click();
    document.querySelector('[data-category="weather"]')?.click();
  }

  store.onChange(schedule);
  doc.addEventListener('home-theme-change', schedule);
  root.addEventListener('resize', schedule);
  doc.addEventListener('visibilitychange', function () {
    if (doc.visibilityState !== 'hidden') pageHidden = false;
    if (started) render();
  });
  root.addEventListener('pagehide', function () {
    pageHidden = true;
    store.setAllowed(false);
  });
  root.addEventListener('pageshow', function () {
    pageHidden = false;
    if (started) render();
  });
  root.HomeWeather = {
    supportsThemes: true,
    store: store,
    mountSettings: mountSettings,
    start: function () {
      if (started) return;
      started = true;
      render();
      store.start();
      setInterval(function () {
        if (doc.visibilityState !== 'hidden') store.refresh();
      }, 60000);
    },
    reservation: function () {
      return region;
    },
    shelfTop: function () {
      return region ? region.shelfTop : 236;
    },
    bottom: function () {
      return region ? region.bottom : 0;
    },
    setScroll: function (offset, dock, preset) {
      if (!element) return;
      const hide = !!region && offset > 0 && dock - offset < region.bottom + 24;
      doc.body.classList.toggle('weather-scrolled', hide);
    },
    render: render
  };
})(window);
