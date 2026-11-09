/* Trusted appearance lifecycle. Transport and persistent trials are separate. */
(function (root) {
  'use strict';
  var owners = Object.create(null),
    heldSheet = null,
    wasEnabled = false,
    accepted = null;
  function suspended() {
    return Object.keys(owners).length > 0;
  }
  function sheet() {
    return root.document.getElementById('ctv-theme-style');
  }
  function surfaceState(active) {
    var surface = root.document.getElementById('homeSurface');
    if (surface)
      surface.classList[active ? 'add' : 'remove']('ctv-theme-suspended');
  }
  function suspend(owner) {
    if (!suspended()) {
      heldSheet = sheet();
      wasEnabled = !!heldSheet && !heldSheet.disabled;
      if (wasEnabled) heldSheet.disabled = true;
      surfaceState(wasEnabled);
    }
    owners[owner || 'manual'] = true;
    if (root.HomePresentationController)
      root.HomePresentationController.suspend('theme:' + (owner || 'manual'));
    // Dialogs isolate theme styles, but the independent wallpaper keeps playing.
    // Its own visibility/focus and input-preview owners release the decoder.
  }
  function resume(owner) {
    delete owners[owner || 'manual'];
    if (root.HomePresentationController)
      root.HomePresentationController.resume('theme:' + (owner || 'manual'));

    if (suspended()) return;
    if (heldSheet && wasEnabled) heldSheet.disabled = false;
    heldSheet = null;
    wasEnabled = false;
    surfaceState(false);
  }
  function fail(code, field) {
    var error = new Error(code + ': invalid ' + field);
    error.code = code;
    error.field = field;
    throw error;
  }
  function release(previous, next) {
    if (!previous || !root.URL || !root.URL.revokeObjectURL) return;
    Object.keys(previous).forEach(function (key) {
      var value = previous[key];
      if (
        typeof value === 'string' &&
        value.indexOf('blob:') === 0 &&
        (!next ||
          Object.keys(next).every(function (k) {
            return next[k] !== value;
          }))
      )
        root.URL.revokeObjectURL(value);
    });
  }
  function apply(input) {
    var policy = root.ThemePolicy;
    if (!policy) fail('api-unsupported', 'ThemePolicy');
    var manifest = policy.validateManifest(input.manifest),
      rules = policy.validateRules(input.rules);
    policy.validateMotion(manifest, rules);
    var weatherRules = rules.rules.some(function (rule) {
      return rule.selector.some(function (s) {
        return s.part === 'weather' || s.part.indexOf('weather-') === 0;
      });
    });
    if (
      weatherRules &&
      manifest.requires.capabilities.indexOf('weather-v1') < 0
    )
      fail('api-unsupported', 'weather-v1');
    if (
      manifest.layout.weather &&
      (!root.HomeWeather || root.HomeWeather.supportsThemes !== true)
    )
      fail('api-unsupported', 'weather renderer');
    var modernIcons =
      manifest.requires.capabilities.indexOf('modern-icon-css-v1') >= 0;
    var hasIconEffects = rules.rules.some(function (rule) {
      return rule.declarations.some(function (d) {
        return (
          d.property === 'filter' ||
          d.property === 'mix-blend-mode' ||
          d.property === 'isolation' ||
          d.property === 'transform' ||
          d.property === 'overflow'
        );
      });
    });
    if (hasIconEffects && !modernIcons)
      fail('api-unsupported', 'icon CSS capability');
    if (
      modernIcons &&
      (!root.CSS ||
        !root.CSS.supports ||
        !root.CSS.supports('isolation', 'isolate') ||
        !root.CSS.supports('mix-blend-mode', 'screen') ||
        !root.CSS.supports('filter', 'grayscale(1) invert(1) brightness(1.3)'))
    )
      fail('api-unsupported', 'modern icon CSS');
    if (
      rules.rules.some(function (rule) {
        return rule.declarations.some(function (d) {
          return d.property === 'transform';
        });
      }) &&
      (manifest.layout.preset !== 'scenic-grid' ||
        manifest.layout.columns > 5 ||
        manifest.layout.allowColumnOverride !== false)
    )
      fail(
        'layout-invalid',
        'icon scale requires fixed scenic-grid with at most five columns'
      );
    /* Trusted layouts currently implement only the Classic scale values. */
    if (
      manifest.layout.spacingScale !== 1 ||
      manifest.layout.textScale !== 1 ||
      manifest.layout.focusScale !== 1.1
    )
      fail('layout-invalid', 'unsupported scale preset');
    if (
      manifest.layout.preset !== 'dock-grid' &&
      (!root.HomeLayoutState || !root.HomeLayoutState.setThemeLayout)
    )
      fail('layout-invalid', 'unsupported renderer preset');
    if (
      manifest.layout.inputs !== undefined &&
      (!root.HomeLayoutState ||
        root.HomeLayoutState.supportsInputPlacement !== true)
    )
      fail('layout-invalid', 'unsupported input placement');
    if (
      manifest.layout.ribbon &&
      (!root.HomeLayoutState ||
        root.HomeLayoutState.supportsRibbonOptions !== true)
    )
      fail('layout-invalid', 'unsupported ribbon options');
    if (
      manifest.layout.allowColumnOverride === false &&
      (!root.HomeLayoutState ||
        root.HomeLayoutState.supportsColumnPolicy !== true)
    )
      fail('layout-invalid', 'unsupported column policy');
    var handles = input.assetHandles || {},
      overrides = input.overrides || {},
      own = Object.prototype.hasOwnProperty;
    Object.keys(overrides).forEach(function (key) {
      if (['accent', 'dim', 'wallpaperAssetId'].indexOf(key) < 0)
        fail('manifest-invalid', 'overrides');
    });
    var accent = own.call(overrides, 'accent')
      ? overrides.accent
      : manifest.defaults.accent;
    var dim = own.call(overrides, 'dim')
      ? overrides.dim
      : manifest.defaults.dim;
    var wallpaper = own.call(overrides, 'wallpaperAssetId')
      ? overrides.wallpaperAssetId
      : manifest.defaults.wallpaperAssetId;
    if (typeof accent !== 'string' || !/^#[a-fA-F0-9]{6}$/.test(accent))
      fail('manifest-invalid', 'accent');
    if (typeof dim !== 'number' || !isFinite(dim) || dim < 0 || dim > 0.85)
      fail('manifest-invalid', 'dim');
    var css = policy.compileRules(rules, handles);
    function appendCss(text) {
      if (text.length > policy.limits.emittedCssBytes - css.length)
        fail('css-budget', 'emitted CSS bytes');
      css += text;
    }
    if (wallpaper !== null) {
      if (
        !manifest.assets.some(function (asset) {
          return asset.id === wallpaper;
        })
      )
        fail('asset-invalid', 'wallpaperAssetId');
      var wallpaperBundle = {
        schemaVersion: 1,
        rules: [
          {
            selector: [{ part: 'home', states: [] }],
            declarations: [
              {
                property: 'background-image',
                value: { type: 'asset', id: wallpaper }
              }
            ]
          }
        ]
      };
      var wallpaperCss = policy.compileRules(wallpaperBundle, handles);
      appendCss(
        '\n' +
          wallpaperCss.replace(
            'background-image:',
            'background-image:linear-gradient(rgba(0,0,0,' +
              dim +
              '),rgba(0,0,0,' +
              dim +
              ')),'
          )
      );
    }
    /* A trusted minimum remains visible even against higher-specificity author states.
       Author CSS cannot emit !important; this narrow engine-owned border may. */
    var scaleFocus =
      modernIcons &&
      manifest.layout.preset === 'scenic-grid' &&
      rules.rules.some(function (rule) {
        return (
          rule.selector.length === 1 &&
          rule.selector[0].part === 'card' &&
          rule.selector[0].states.length === 1 &&
          rule.selector[0].states[0] === 'focused' &&
          rule.declarations.some(function (d) {
            return d.property === 'border-width' && d.value.value === 0;
          }) &&
          rule.declarations.some(function (d) {
            return d.property === 'border-style' && d.value.value === 'none';
          })
        );
      });
    var hiddenHero = rules.rules.some(function (rule) {
      return (
        rule.selector.length === 1 &&
        rule.selector[0].part === 'hero' &&
        rule.selector[0].states.length === 0 &&
        rule.declarations.some(function (d) {
          return d.property === 'color' && d.value.rgba[3] === 0;
        })
      );
    });
    if (scaleFocus) {
      appendCss(
        '\n#homeSurface.ctv-home .ctv-card.is-focused{border:0!important;transform:scale(1.1)!important;}'
      );
      // A visible hero already names the selected app; keep the fallback only when hidden.
      if (hiddenHero)
        appendCss(
          '\n#homeSurface.ctv-home .ctv-label.is-focused{color:#fff!important;opacity:1!important;text-shadow:0 1px 6px #000!important;}'
        );
    } else
      appendCss(
        '\n#homeSurface.ctv-home .ctv-card.is-focused{border-color:' +
          accent +
          '!important;border-style:solid!important;border-width:' +
          (manifest.layout.preset === 'scenic-grid' ? '3' : '2') +
          'px!important;}'
      );
    if (modernIcons || manifest.layout.ribbon)
      rules.rules.forEach(function (rule) {
        var part = rule.selector[rule.selector.length - 1].part;
        if (
          part !== 'card' &&
          (!modernIcons ||
            (part !== 'clock' && part !== 'date' && part !== 'icon'))
        )
          return;
        rule.declarations.forEach(function (d) {
          if (
            !(part === 'card' && d.property === 'background-color') &&
            !(
              (part === 'clock' || part === 'date') &&
              d.property === 'font-size'
            ) &&
            !(part === 'icon' && d.property === 'transform')
          )
            return;
          var background = policy.compileRules(
            {
              schemaVersion: 1,
              rules: [{ selector: rule.selector, declarations: [d] }]
            },
            handles
          );
          appendCss('\n' + background.replace(/;\}$/, '!important;}'));
        });
      });
    if (manifest.layout.datePlacement === 'below-clock') {
      appendCss(
        '\n#homeSurface.ctv-home #timeRow{flex-wrap:wrap;}#homeSurface.ctv-home #timeRow .divider{display:none;}#homeSurface.ctv-home #date{width:100%;margin:16px 0 0;white-space:normal;line-height:1.4;}'
      );
    }
    if (manifest.layout.ribbon) {
      var r = manifest.layout.ribbon,
        prefix = '#homeSurface.ctv-home[data-ribbon="true"] ';
      function ribbonRule(selector, declarations) {
        appendCss('\n' + prefix + selector + '{' + declarations + '}');
      }
      ribbonRule('#viewport', 'top:0;bottom:0;overflow:hidden;');
      ribbonRule('#stage', 'top:0;');
      ribbonRule('.ctv-position', 'display:none!important;');
      // Transform the hit target itself: browser pointer hit-testing follows its slanted shape.
      ribbonRule(
        '.item',
        'height:' +
          r.cardHeight +
          'px;padding-bottom:0;border-radius:0;transform:skewX(' +
          r.skewDeg +
          'deg)!important;transform-origin:center bottom;'
      );
      ribbonRule('.item .card', 'transform:none!important;transition:none;');
      ribbonRule(
        '.item.focused .card',
        'height:' +
          (r.cardHeight + r.focusLift) +
          'px!important;top:-' +
          r.focusLift +
          'px;border:3px solid ' +
          accent +
          '!important;transform:none!important;'
      );
      ribbonRule(
        '.item.moving .card',
        'animation:none;top:-' + (r.focusLift + 32) + 'px;'
      );
      ribbonRule(
        '.item .card img',
        'width:' +
          r.iconScale * 100 +
          '%;height:' +
          r.cardHeight * r.iconScale +
          'px;left:' +
          (1 - r.iconScale) * 50 +
          '%;top:' +
          (r.cardHeight * (1 - r.iconScale)) / 2 +
          'px;'
      );
      ribbonRule(
        '.add-app svg',
        'width:' + 64 * r.iconScale + 'px;height:' + 64 * r.iconScale + 'px;'
      );
      ribbonRule(
        '.item .ctv-icon',
        'transform:skewX(' + -r.skewDeg + 'deg)!important;'
      );
      ribbonRule(
        '.item .name',
        'transform:skewX(' +
          -r.skewDeg +
          'deg)!important;transition:none!important;'
      );
      if (r.labels === 'focused-above') {
        ribbonRule('#hero', 'display:none!important;');
        ribbonRule('.item .name', 'display:none!important;');
        ribbonRule(
          '.item.focused .name',
          'display:block!important;position:absolute;left:0;right:0;bottom:' +
            (r.cardHeight + r.focusLift + 20) +
            'px;margin:0 -40px;height:auto;max-height:96px;line-height:32px;white-space:normal;overflow:hidden;opacity:1!important;color:#fff!important;text-shadow:0 2px 8px #000;transform-origin:center bottom;transform:translateX(' +
            Math.tan((r.skewDeg * Math.PI) / 180) * 20 +
            'px) skewX(' +
            -r.skewDeg +
            'deg)!important;'
        );
      } else
        ribbonRule(
          '.item .name',
          'position:absolute;top:' +
            (r.cardHeight + 16) +
            'px;left:0;right:0;margin:0 -32px;line-height:32px;height:32px;'
        );
      if (!r.showClock) ribbonRule('#timeRow', 'display:none!important;');
      if (r.shortcuts === 'bottom-left') {
        ribbonRule(
          'header',
          'top:0;bottom:0;left:0;right:0;pointer-events:none;'
        );
        ribbonRule('#timeRow', 'position:absolute;top:104px;left:112px;');
        ribbonRule(
          '#topButtons',
          'position:absolute;left:28px;right:auto;top:auto;bottom:28px;margin:0;pointer-events:auto;'
        );
        ribbonRule(
          '#topButtons .pill',
          'width:68px;height:68px;padding:0;margin:0 8px 0 0;justify-content:center;font-size:0;'
        );
        ribbonRule('#topButtons .pill svg', 'width:32px;height:32px;margin:0;');
        if (
          manifest.id === 'builtin:ribbon' ||
          manifest.layout.presentation === 'overlay'
        ) {
          // Built-in Ribbon keeps its continuous lane in the ordinary CARD Home.
          var shortcutWidth =
            r.left +
            Math.abs(
              Math.tan((r.skewDeg * Math.PI) / 180) *
                (r.cardHeight + r.focusLift)
            );
          ribbonRule(
            '#topButtons',
            'left:0;bottom:' +
              r.bottom +
              'px;width:' +
              shortcutWidth +
              'px;height:' +
              r.cardHeight +
              'px;align-items:center;justify-content:center;'
          );
          ribbonRule(
            '#topButtons::before',
            'content:"";position:absolute;left:-64px;top:0;bottom:0;width:' +
              (shortcutWidth + 64) +
              'px;box-sizing:border-box;border:0;background:#20242b;transform:skewX(' +
              r.skewDeg +
              'deg);transform-origin:center bottom;pointer-events:none;'
          );
          ribbonRule(
            '#topButtons .pill',
            'position:relative;width:60px;height:60px;margin:0 4px;padding:0;background:transparent;border:3px solid transparent;transform:none;'
          );
          ribbonRule(
            '#topButtons .pill.focused',
            'background:#303238;border-color:#fff;'
          );
          ribbonRule('#topButtons .pill svg', 'width:30px;height:30px;');
        }
      }
    }
    // Runtime rules do not pass through PostCSS. Old WebKit only understands
    // prefixed forms; keep the normal declarations and charge both to the budget.
    var style =
      root.document.documentElement && root.document.documentElement.style;
    if (style && !('transform' in style) && 'webkitTransform' in style) {
      css = css.replace(
        /(^|[;{])\s*(transform(?:-origin)?|transition|animation|justify-content):([^;}]+)/g,
        '$1-webkit-$2:$3;$2:$3'
      );
      if (css.length > policy.limits.emittedCssBytes)
        fail('css-budget', 'emitted CSS bytes');
    }
    /* All untrusted input is checked before either geometry or styles are changed. */
    if (root.HomeLayoutState && root.HomeLayoutState.setThemeLayout)
      root.HomeLayoutState.setThemeLayout(manifest.layout);
    else if (root.HomeLayoutState && root.HomeLayoutState.setThemeColumns)
      root.HomeLayoutState.setThemeColumns(manifest.layout.columns);
    var current = sheet(),
      previous = accepted;
    if (!current) {
      current = root.document.createElement('style');
      current.id = 'ctv-theme-style';
      current.disabled = true;
      root.document.head.appendChild(current);
    }
    current.disabled = true;
    current.textContent = css;
    current.disabled = suspended();
    if (suspended()) {
      heldSheet = current;
      wasEnabled = true;
      surfaceState(true);
    } else surfaceState(false);
    var ownedHandles = Object.create(null);
    Object.keys(handles).forEach(function (key) {
      ownedHandles[key] = handles[key];
    });
    var videoHandles = Object.create(null);
    Object.keys(input.videoHandles || {}).forEach(function (key) {
      videoHandles[key] = input.videoHandles[key];
    });
    if (root.HomeWallpaper)
      root.HomeWallpaper.configure({
        manifest: manifest,
        assetHandles: ownedHandles,
        videoHandles: videoHandles,
        videoLease: input.videoLease
      });
    accepted = {
      themeId: manifest.id,
      themeVersion: manifest.themeVersion,
      handles: ownedHandles,
      videoHandles: videoHandles,
      videoLease: input.videoLease,
      weather: manifest.layout.weather || null,
      weatherRules: rules.rules
        .filter(function (rule) {
          return (
            rule.selector.length === 1 &&
            ['home', 'clock'].indexOf(rule.selector[0].part) >= 0 &&
            rule.selector[0].states.length === 0
          );
        })
        .map(function (rule) {
          return {
            selector: [{ part: 'weather', states: [] }],
            declarations: rule.declarations.filter(function (d) {
              return (
                ['font-family', 'color', 'text-shadow'].indexOf(d.property) >= 0
              );
            })
          };
        })
        .concat(
          rules.rules.filter(function (rule) {
            return rule.selector.some(function (s) {
              return s.part === 'weather' || s.part.indexOf('weather-') === 0;
            });
          })
        )
    };
    var surface = root.document.getElementById('homeSurface');
    if (surface) {
      surface.classList.add('ctv-theme-active');
      surface.classList[
        manifest.layout.motion === 'classic' ? 'add' : 'remove'
      ]('ctv-classic-motion');
    }
    release(previous && previous.handles, ownedHandles);
    if (root.HomePresentationController)
      root.HomePresentationController.setTheme(manifest.layout);
    release(previous && previous.videoHandles, videoHandles);
    if (
      previous &&
      previous.videoLease &&
      previous.videoLease !== input.videoLease
    )
      previous.videoLease.dispose();

    return { themeId: manifest.id, themeVersion: manifest.themeVersion };
  }
  function reset() {
    var current = sheet(),
      previous = accepted;
    if (root.HomeWallpaper) root.HomeWallpaper.reset();
    if (root.HomeLayoutState && root.HomeLayoutState.setThemeLayout)
      root.HomeLayoutState.setThemeLayout({
        preset: 'dock-grid',
        columns: 5,
        spacingScale: 1,
        textScale: 1,
        focusScale: 1.1
      });
    else if (root.HomeLayoutState && root.HomeLayoutState.setThemeColumns)
      root.HomeLayoutState.setThemeColumns(5);
    if (current && current.parentNode) current.parentNode.removeChild(current);
    accepted = null;
    heldSheet = null;
    wasEnabled = false;
    surfaceState(false);
    var surface = root.document.getElementById('homeSurface');
    if (surface) {
      surface.classList.remove('ctv-theme-active');
      surface.classList.remove('ctv-classic-motion');
    }
    release(previous && previous.handles, null);
    if (root.HomePresentationController)
      root.HomePresentationController.setTheme(null);
    release(previous && previous.videoHandles, null);
    if (previous && previous.videoLease) previous.videoLease.dispose();

    return { themeId: 'builtin:classic', themeVersion: null };
  }
  root.ThemeRuntime = {
    isSuspended: suspended,
    apply: apply,
    suspend: suspend,
    resume: resume,
    reset: reset,
    weather: function () {
      return accepted
        ? {
            options: accepted.weather,
            css: root.ThemePolicy.compileRules(
              { schemaVersion: 1, rules: accepted.weatherRules },
              accepted.handles
            )
          }
        : { options: null, css: '' };
    }
  };
})(this);
