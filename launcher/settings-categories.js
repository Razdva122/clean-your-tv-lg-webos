/* Shared settings navigation. Service actions remain owned by each edition. */
(function (root) {
  'use strict';
  var views = [];
  var labels = {
    cs: ['Vzhled', 'Pokročilé'],
    de: ['Darstellung', 'Erweitert'],
    es: ['Apariencia', 'Avanzado'],
    'pt-BR': ['Aparência', 'Avançado'],
    fr: ['Apparence', 'Avancé'],
    it: ['Aspetto', 'Avanzate'],
    ko: ['화면 꾸미기', '고급'],
    hi: ['दिखावट', 'उन्नत'],
    pl: ['Wygląd', 'Zaawansowane'],
    ru: ['Внешний вид', 'Дополнительно'],
    'zh-Hans': ['外观', '高级'],
    'zh-Hant': ['外觀', '進階']
  };
  function t(source) {
    if (source === 'Wallpapers' && root.HomeWallpaperPanel)
      return HomeWallpaperPanel.t(source);
    var language = root.HomeI18n && HomeI18n.language(),
      pair = labels[language];
    if (pair && source === 'Appearance') return pair[0];
    if (pair && source === 'Advanced') return pair[1];
    return root.HomeI18n ? HomeI18n.t(source) : source;
  }
  var paths = [
    'M3 11L12 3l9 8M5 10v11h14V10M9 21v-7h6v7',
    'M12 3a9 9 0 1 0 0 18h2a2 2 0 0 0 0-4h-1a2 2 0 0 1 0-4h4a4 4 0 0 0 4-4c0-4-5-6-9-6zM7 10h.01M10 6h.01M16 7h.01',
    'M3 4h18v16H3zM3 9h18M9 9v11M6 6.5h.01M9 6.5h.01',
    'M3 5h12M9 3v2M5 5c0 6 4 10 9 12M13 5c0 6-4 10-10 13M14 21l4-10 4 10M16 17h4',
    'M20 8a8 8 0 1 0 0 8M20 3v5h-5M12 8v5l3 2',
    'M4 5h16v12H4zM8 21h8M12 17v4',
    'M8 5L2 12l6 7M16 5l6 7-6 7M14 3l-4 18'
  ];
  var actionPaths = {
    tv: paths[5],
    notifications: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4',
    sound: 'M3 9h4l5-4v14l-5-4H3zM16 9a4 4 0 0 1 0 6M19 6a8 8 0 0 1 0 12'
  };
  function createIcon(shape) {
    var ns = 'http://www.w3.org/2000/svg',
      svg = document.createElementNS(ns, 'svg'),
      path = document.createElementNS(ns, 'path');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    path.setAttribute('d', shape);
    svg.appendChild(path);
    return svg;
  }
  function attach(panel, card, groups) {
    var nav = document.createElement('div'),
      workspace = document.createElement('div'),
      content = document.createElement('div');
    var heading = card.querySelector('.settings-heading'),
      footer = card.querySelector('.settings-footer'),
      tabs = [],
      panes = [],
      remembered = [],
      current = 0,
      updateTab;
    card.classList.add('settings-workspace');
    workspace.className = 'settings-columns';
    nav.className = 'settings-categories renewal-actions';
    nav.setAttribute('role', 'tablist');
    nav.setAttribute('aria-orientation', 'vertical');
    nav.setAttribute('aria-label', t('Home settings'));
    content.className = 'settings-content';
    workspace.appendChild(nav);
    workspace.appendChild(content);
    var more = document.createElement('span');
    more.className = 'settings-scroll-hint';
    more.textContent = '↓';
    more.setAttribute('aria-hidden', 'true');
    workspace.appendChild(more);
    function scrollHint() {
      more.style.left = Math.max(0, nav.offsetWidth - 30) + 'px';
      more.hidden = nav.scrollHeight <= nav.clientHeight + nav.scrollTop + 2;
    }
    nav.addEventListener('scroll', scrollHint);
    root.addEventListener('resize', scrollHint);
    card.insertBefore(workspace, heading.nextSibling);
    function actions() {
      return Array.prototype.filter.call(
        panes[current].querySelectorAll('button,input,[tabindex="0"]'),
        function (el) {
          return !el.disabled && !el.hidden && el.offsetHeight > 0;
        }
      );
    }
    function enter() {
      var list = actions();
      var target = remembered[current];
      if (list.indexOf(target) < 0)
        target = panes[current].querySelector(
          '#settingsLanguageChoices [aria-pressed="true"],.weather-enabled'
        );
      if (list.indexOf(target) < 0) target = list[0];
      if (target) target.focus();
    }
    function select(index) {
      if (current !== index && root.HomeThemePanel)
        HomeThemePanel.activate(false);
      current = index;
      tabs.forEach(function (tab, i) {
        tab.setAttribute('aria-selected', String(i === index));
        tab.tabIndex = i === index ? 0 : -1;
        panes[i].hidden = i !== index;
      });
      if (root.HomeThemePanel)
        HomeThemePanel.activate(groups[index].id === 'themes');
      if (root.HomeWallpaperPanel)
        HomeWallpaperPanel.activate(groups[index].id === 'wallpapers');
      scrollHint();
    }
    var weatherReady = root.HomeWeather
      ? root.HomeWeather.mountSettings(panel, card, groups)
      : null;
    groups.forEach(function (group, i) {
      var tab = document.createElement('button'),
        pane = document.createElement('section'),
        title = document.createElement('h3');
      tab.type = 'button';
      tab.setAttribute('role', 'tab');
      tab.setAttribute('data-category', group.id);
      tab.id = 'settings-tab-' + group.id;
      tab.setAttribute('aria-controls', 'settings-pane-' + group.id);
      tab.appendChild(
        createIcon(
          group.id === 'wallpapers'
            ? 'M3 3h18v18H3zM3 16l6-6 5 5 3-3 4 4M16 7h.01'
            : paths[
                [
                  'home',
                  'appearance',
                  'themes',
                  'language',
                  'updates',
                  'advanced',
                  'developer'
                ].indexOf(group.id)
              ]
        )
      );
      var text = document.createElement('span');
      text.textContent = t(group.label);
      tab.appendChild(text);
      if (group.id === 'updates') {
        updateTab = tab;
        var dot = document.createElement('span');
        dot.className = 'settings-update-dot';
        dot.setAttribute('aria-hidden', 'true');
        tab.appendChild(dot);
      }
      if (group.id === 'developer') {
        var summary = document.getElementById('renewalSummary');
        if (summary) tab.setAttribute('aria-describedby', summary.id);
      }
      pane.className = 'settings-pane renewal-actions';
      pane.id = 'settings-pane-' + group.id;
      pane.setAttribute('role', 'tabpanel');
      pane.setAttribute('aria-labelledby', tab.id);
      pane.addEventListener('focusin', function (e) {
        if (actions().indexOf(e.target) >= 0) remembered[i] = e.target;
      });
      title.textContent = t(group.label);
      pane.appendChild(title);
      if (
        group.id === 'language' &&
        root.HomeI18n &&
        HomeI18n.mountLanguagePicker
      )
        HomeI18n.mountLanguagePicker(pane);
      else
        group.elements.forEach(function (el, index) {
          if (!el) return;
          var shape = group.icons && actionPaths[group.icons[index]];
          if (shape) {
            var icon = createIcon(shape);
            icon.setAttribute('class', 'settings-action-icon');
            el.insertBefore(icon, el.firstChild);
          }
          pane.appendChild(el);
        });
      if (group.id === 'appearance') {
        [
          [
            'Columns',
            pane.querySelector('.home-columns-entry') ||
              pane.querySelector('.settings-layout')
          ],
          [
            'Applications',
            pane.querySelector('#homeAppSettings') ||
              pane.querySelector('#homeShowAddApp').parentNode
          ]
        ].forEach(function (section) {
          if (!section[1]) return;
          var label = document.createElement('h4');
          label.className = 'settings-subheading';
          label.textContent = t(section[0]);
          pane.insertBefore(label, section[1]);
        });
      }
      tab.addEventListener('focusin', function () {
        if (document.activeElement === tab) select(i);
      });
      tab.onclick = function () {
        select(i);
        tab.focus();
      };
      nav.appendChild(tab);
      content.appendChild(pane);
      tabs.push(tab);
      panes.push(pane);
    });
    // Empty grouping wrappers have no meaning once their controls move to categories.
    Array.prototype.forEach.call(card.children, function (el) {
      if (el !== heading && el !== workspace && el !== footer)
        el.style.display = 'none';
    });
    select(0);
    if (weatherReady) weatherReady();
    var view = {
      panel: panel,
      card: card,
      nav: nav,
      setUpdateAvailable: function (available) {
        if (!updateTab) return;
        updateTab.setAttribute('data-update-available', String(available));
        updateTab.setAttribute(
          'aria-label',
          t(
            available
              ? 'Software updates. Update available.'
              : 'Software updates'
          )
        );
      },
      open: function () {
        remembered = [];
        select(0);
        tabs[0].focus();
        setTimeout(scrollHint, 0);
      },
      key: function (e) {
        var key = e.keyCode,
          active = document.activeElement,
          inNav = nav.contains(active),
          list = actions();
        if (key === 27 || key === 461) {
          if (!inNav) {
            tabs[current].focus();
            return true;
          }
          return false;
        }
        var languageChoices = document.getElementById(
          'settingsLanguageChoices'
        );
        if (
          !inNav &&
          languageChoices &&
          languageChoices.contains(active) &&
          [37, 38, 39, 40].indexOf(key) >= 0
        ) {
          var languages = Array.prototype.slice.call(
              languageChoices.querySelectorAll('button')
            ),
            at = languages.indexOf(active);
          var columns =
              languages.slice(1).filter(function (button) {
                return button.offsetTop === languages[1].offsetTop;
              }).length || 1,
            next = at;
          if (key === 37) {
            if (at === 0 || (at - 1) % columns === 0) {
              tabs[current].focus();
              return true;
            }
            next = at - 1;
          }
          if (key === 39) {
            if (at > 0 && at % columns === 0) return true;
            next = at + 1;
          }
          if (key === 38) next = at <= columns ? 0 : at - columns;
          if (key === 40) next = at === 0 ? 1 : at + columns;
          if (next < languages.length) languages[next].focus();
          else footer.querySelector('button').focus();
          return true;
        }
        // Match arrows to actual rows, including compact Home and theme layouts.
        if (
          !inNav &&
          !footer.contains(active) &&
          [37, 38, 39, 40].indexOf(key) >= 0
        ) {
          var rect = active.getBoundingClientRect(),
            best = null,
            distance = Infinity;
          list.forEach(function (el) {
            if (el === active) return;
            var r = el.getBoundingClientRect(),
              vertical = key === 38 || key === 40;
            var overlap = vertical
              ? r.right > rect.left + 4 && r.left < rect.right - 4
              : r.bottom > rect.top + 4 && r.top < rect.bottom - 4;
            var delta =
              key === 37
                ? rect.left - r.right
                : key === 39
                  ? r.left - rect.right
                  : key === 38
                    ? rect.top - r.bottom
                    : r.top - rect.bottom;
            if (!overlap || delta < -2) return;
            var alignment = vertical
                ? Math.abs(r.left + r.width / 2 - rect.left - rect.width / 2)
                : Math.abs(r.top + r.height / 2 - rect.top - rect.height / 2),
              score = Math.max(0, delta) + alignment;
            if (score < distance) {
              distance = score;
              best = el;
            }
          });
          if (best) {
            best.focus();
            return true;
          }
          if (key === 37 || key === 38) {
            tabs[current].focus();
            return true;
          }
          if (key === 40) {
            footer.querySelector('button').focus();
            return true;
          }
          return true;
        }
        if (key === 37) {
          tabs[current].focus();
          return true;
        }
        if (key === 39) {
          if (inNav) enter();
          return true;
        }
        if (footer.contains(active) && (key === 38 || key === 40)) {
          if (key === 38 && list.length) list[list.length - 1].focus();
          else tabs[0].focus();
          return true;
        }
        if (inNav) {
          if (key === 38 || key === 40) {
            var menu = tabs.concat([footer.querySelector('button')]);
            menu[
              (current + (key === 38 ? -1 : 1) + menu.length) % menu.length
            ].focus();
            return true;
          }
          if (key === 13) {
            enter();
            return true;
          }
        } else if (key === 38 || key === 40) {
          var index = list.indexOf(active),
            targets = list.concat([footer.querySelector('button')]);
          targets[
            (index + (key === 38 ? -1 : 1) + targets.length) % targets.length
          ].focus();
          return true;
        }
        if (key === 9) {
          var all = tabs
              .concat(list)
              .concat(
                Array.prototype.slice.call(footer.querySelectorAll('button'))
              ),
            position = all.indexOf(active);
          all[
            (position + (e.shiftKey ? -1 : 1) + all.length) % all.length
          ].focus();
          return true;
        }
        // Native button activation works for both existing controls and the footer.
        if (key === 13) {
          if (!e.repeat && active && active.click) active.click();
          return true;
        }
        return false;
      }
    };
    views.push(view);
    return view;
  }
  document.addEventListener(
    'keydown',
    function (e) {
      if (root.HomeThemePanel && HomeThemePanel.handlesKey(e)) return;
      views.forEach(function (view) {
        if (
          view.panel.offsetHeight &&
          view.card.offsetHeight &&
          view.panel.contains(document.activeElement) &&
          view.key(e)
        ) {
          e.preventDefault();
          e.stopImmediatePropagation();
        }
      });
    },
    true
  );
  root.SettingsCategories = { attach: attach };
})(window);
