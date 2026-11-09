/* Desktop-only selector for reviewed showcase versions; never included in TV packages. */
(() => {
  const screen = document.getElementById('screen'),
    cards = document.getElementById('previewThemes'),
    status = document.getElementById('themeStatus'),
    filters = document.querySelectorAll('[data-theme-filter]'),
    filterStatus = document.getElementById('filterStatus');
  let data,
    desired = null,
    generation = 0;
  const packages = new Map();
  function filterThemes() {
    const active = Array.from(filters).filter(
      (button) => button.getAttribute('aria-pressed') === 'true'
    );
    let visible = 0;
    for (const button of cards.querySelectorAll('button')) {
      button.hidden = active.some(
        (filter) => button.dataset[filter.dataset.themeFilter] !== 'true'
      );
      if (!button.hidden) visible++;
    }
    filterStatus.hidden = visible !== 0;
    cards.scrollLeft = 0;
  }
  for (const button of filters)
    button.onclick = () => {
      button.setAttribute(
        'aria-pressed',
        String(button.getAttribute('aria-pressed') !== 'true')
      );
      filterThemes();
    };
  function selected(manager) {
    for (const button of cards.querySelectorAll('button'))
      button.setAttribute(
        'aria-pressed',
        String(button.dataset.theme === manager.current().id)
      );
  }
  function busy(value) {
    cards.setAttribute('aria-busy', String(value));
    for (const button of cards.querySelectorAll('button'))
      button.disabled = value;
    for (const button of filters) button.disabled = value || !data;
  }
  async function apply(item, frame, view) {
    const manager = frame.ThemeManager;
    let installed = (await manager.list()).find(
      (t) => t.id === item.id && (item.builtin || t.digest === item.digest)
    );
    let envelope;
    if (!installed) {
      envelope = packages.get(item.id);
      if (!envelope) {
        const response = await fetch('preview/' + data.packages[item.id]);
        if (!response.ok)
          throw Error('Theme download failed. Click the preview to retry.');
        envelope = await response.json();
      }
      if (view !== generation) return;
      installed = await manager.installEnvelope(envelope);
    }
    if (view !== generation) return;
    if (
      installed.id !== item.id ||
      (!item.builtin && installed.digest !== item.digest)
    )
      throw Error('Reviewed theme identity does not match.');
    if (envelope) packages.set(item.id, envelope);
    await manager.selectInstalled(installed);
    if (view !== generation) return;
    desired = item.id;
    selected(manager);
    status.textContent = '';
    // Selecting a theme blurs Home; return focus to resume its wallpaper video.
    frame.focus();
  }
  async function load() {
    const view = ++generation,
      frame = screen.contentWindow;
    busy(true);
    status.textContent = 'Loading themes…';
    try {
      // Let Home own startup: calling start() before its present callback hides Home.
      await new Promise((resolve, reject) => {
        const deadline = Date.now() + 12000;
        function ready() {
          if (view !== generation) return resolve();
          if (frame.RootLauncherRendered === true) return resolve();
          if (Date.now() > deadline)
            return reject(Error('Home did not finish loading.'));
          setTimeout(ready, 50);
        }
        ready();
      });
      if (view !== generation) return;
      if (!data) {
        const response = await fetch('preview/themes.json');
        if (!response.ok)
          throw Error('Theme showcase is unavailable. Reload to retry.');
        data = await response.json();
      }
      if (view !== generation) return;
      cards.replaceChildren();
      for (const item of data.themes) {
        const button = document.createElement('button');
        button.type = 'button';
        button.dataset.theme = item.id;
        button.dataset.hasVideo = String(!!item.hasVideo);
        button.dataset.has4k = String(!!item.has4k);
        button.setAttribute('aria-label', item.title);
        button.setAttribute('aria-pressed', 'false');
        const image = document.createElement('img');
        image.src = 'launcher/' + item.preview;
        image.alt = '';
        image.width = 160;
        image.height = 90;
        const title = document.createElement('strong');
        title.textContent = item.title;
        const version = document.createElement('small');
        version.textContent = item.builtin ? 'Built-in' : 'v' + item.version;
        const previewFrame = document.createElement('div');
        previewFrame.className = 'theme-preview-frame';
        previewFrame.append(image);
        const badges = document.createElement('span');
        badges.className = 'theme-media-badges';
        if (item.has4k) {
          const badge = document.createElement('span');
          badge.className = 'theme-media-badge';
          badge.textContent = '4K';
          badges.append(badge);
        }
        if (item.hasVideo) {
          const badge = document.createElement('span');
          badge.className = 'theme-media-badge theme-video-badge';
          badge.setAttribute('role', 'img');
          badge.setAttribute('aria-label', 'Video wallpaper');
          badges.append(badge);
        }
        previewFrame.append(badges);
        if (item.packageSize !== undefined)
          version.textContent +=
            ' · ' +
            Math.max(0.1, item.packageSize / 1000000).toFixed(1) +
            ' MB';
        button.append(previewFrame, title, version);
        cards.append(button);
        button.onclick = async () => {
          const current = ++generation;
          busy(true);
          status.textContent = 'Applying ' + item.title + '…';
          try {
            await apply(item, frame, current);
          } catch (error) {
            if (current === generation)
              status.textContent = 'Could not apply theme: ' + error.message;
          } finally {
            if (current === generation) {
              selected(frame.ThemeManager);
              busy(false);
            }
          }
        };
      }
      filterThemes();
      frame.document.addEventListener('home-theme-change', () => {
        if (view === generation || frame === screen.contentWindow)
          selected(frame.ThemeManager);
      });
      const item = data.themes.find((t) => t.id === desired);
      if (item && frame.ThemeManager.current().id !== desired)
        await apply(item, frame, view);
      else {
        selected(frame.ThemeManager);
        status.textContent = '';
      }
    } catch (error) {
      if (view === generation)
        status.textContent = 'Could not load themes: ' + error.message;
    } finally {
      if (view === generation) busy(false);
    }
  }
  for (const button of document.querySelectorAll('[data-edition]'))
    button.addEventListener('click', () => {
      if (button.getAttribute('aria-pressed') !== 'true') {
        generation++;
        busy(true);
        status.textContent = 'Loading themes…';
      }
    });
  screen.addEventListener('load', load);
})();
