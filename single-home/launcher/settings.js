/* Standard product settings backed by this app's local preferences. */
(function (root) {
  'use strict';
  var panel, categories, previous;
  function button(parent, id, label, action, toggle) {
    var b = document.createElement('button');
    b.type = 'button';
    b.id = id;
    b.textContent = HomeI18n.t(label);
    b.onclick = action;
    if (toggle) {
      b.className = 'home-routing-switch';
      b.setAttribute('role', 'switch');
    }
    if (parent) parent.appendChild(b);
    return b;
  }
  function container(name) {
    var el = document.createElement('div');
    el.className = name || '';
    return el;
  }
  function isOpen() {
    return !!panel && !panel.classList.contains('hidden');
  }
  function close() {
    root.HomeThemePanel.unmount();
    root.HomeWallpaperPanel.unmount();
    panel.classList.add('hidden');
    root.ThemeRuntime.resume('settings');
    if (previous && previous.focus) previous.focus();
  }
  function build() {
    panel = document.createElement('section');
    panel.id = 'renewalPanel';
    panel.className = 'hidden';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-modal', 'true');
    panel.setAttribute('aria-labelledby', 'pilotSettingsTitle');
    var card = container('renewal-card settings-main'),
      heading = container('settings-heading'),
      title = document.createElement('h2'),
      footer = container('settings-footer'),
      row = container('renewal-actions');
    title.id = 'pilotSettingsTitle';
    title.textContent = HomeI18n.t('Home settings');
    heading.appendChild(title);
    card.appendChild(heading);
    button(row, 'renewalClose', 'Back to Home', close);
    footer.appendChild(row);
    card.appendChild(footer);
    panel.appendChild(card);
    document.body.appendChild(panel);

    var pairing = button(
      null,
      'pilotSetup',
      'TV pairing and background startup',
      function () {
        location.replace('setup/index.html?settings=1');
      }
    );
    if (HomeI18n.language() === 'ru')
      pairing.textContent = 'Сопряжение с телевизором и фоновый запуск';
    var columns = container('renewal-actions settings-layout');
    button(columns, 'homeColumns', 'Columns', function () {
      root.HomeLayoutPanel.open();
    });
    var apps = container('renewal-actions settings-layout');
    apps.id = 'homeAppSettings';
    button(
      apps,
      'homeUsageSort',
      'Sort by most used',
      function () {
        root.HomeAppControls.toggle(true);
      },
      true
    );
    button(
      apps,
      'homeShowAddApp',
      'Show Add app tile',
      function () {
        root.HomeAppControls.toggle();
      },
      true
    );
    button(apps, 'homeAddApp', 'Add app', function () {
      close();
      root.HomeAppControls.add();
    });
    button(apps, 'homeEditTiles', 'Edit tiles', function () {
      close();
      root.HomeAppControls.edit();
    });
    var error = document.createElement('p');
    error.id = 'homeAppsError';
    error.setAttribute('role', 'alert');
    apps.appendChild(error);
    var themes = container();
    root.HomeThemePanel.mount(themes);
    var wallpapers = container();
    root.HomeWallpaperPanel.mount(wallpapers);
    categories = SettingsCategories.attach(panel, card, [
      { id: 'home', label: 'Your Home screen', elements: [pairing] },
      { id: 'appearance', label: 'Appearance', elements: [columns, apps] },
      { id: 'themes', label: 'Themes', elements: [themes] },
      { id: 'wallpapers', label: 'Wallpapers', elements: [wallpapers] },
      { id: 'language', label: 'Language', elements: [] }
    ]);
  }
  // Categories handles its own navigation in capture. Back from the category
  // list closes settings. Other keys must not move tiles underneath the dialog.
  document.addEventListener(
    'keydown',
    function (event) {
      if (!isOpen() || !panel.contains(document.activeElement)) return;
      if ([9, 13, 27, 37, 38, 39, 40, 461].indexOf(event.keyCode) < 0) return;
      if (event.keyCode === 27 || event.keyCode === 461) close();
      event.preventDefault();
      event.stopImmediatePropagation();
    },
    true
  );
  root.RenewalPanel = {
    isOpen: isOpen,
    open: function () {
      if (!panel) build();
      if (isOpen()) return;
      previous = document.activeElement;
      root.HomeAppControls.refresh();
      root.HomeLayoutPanel.refreshAvailability();
      root.ThemeRuntime.suspend('settings');
      panel.classList.remove('hidden');
      categories.open();
    }
  };
})(window);
