/* Trusted appearance lifecycle. Transport and persistent trials are separate. */
(function (root) {
  'use strict';
  var owners = Object.create(null), heldSheet = null, wasEnabled = false, accepted = null;
  function suspended() { return Object.keys(owners).length > 0; }
  function sheet() { return root.document.getElementById('ctv-theme-style'); }
  function surfaceState(active) {
    var surface = root.document.getElementById('homeSurface');
    if (surface) surface.classList[active ? 'add' : 'remove']('ctv-theme-suspended');
  }
  function suspend(owner) {
    if (!suspended()) {
      heldSheet = sheet(); wasEnabled = !!heldSheet && !heldSheet.disabled;
      if (wasEnabled) heldSheet.disabled = true;
      surfaceState(wasEnabled);
    }
    owners[owner || 'manual'] = true;
  }
  function resume(owner) {
    delete owners[owner || 'manual'];
    if (suspended()) return;
    if (heldSheet && wasEnabled) heldSheet.disabled = false;
    heldSheet = null; wasEnabled = false; surfaceState(false);
  }
  function fail(code, field) { var error = new Error(code + ': invalid ' + field); error.code = code; error.field = field; throw error; }
  function release(previous, next) {
    if (!previous || !root.URL || !root.URL.revokeObjectURL) return;
    Object.keys(previous).forEach(function (key) {
      var value = previous[key];
      if (typeof value === 'string' && value.indexOf('blob:') === 0 && (!next || Object.keys(next).every(function (k) { return next[k] !== value; }))) root.URL.revokeObjectURL(value);
    });
  }
  function apply(input) {
    var policy = root.ThemePolicy;
    if (!policy) fail('api-unsupported', 'ThemePolicy');
    var manifest = policy.validateManifest(input.manifest), rules = policy.validateRules(input.rules);
    var modernIcons = manifest.requires.capabilities.indexOf('modern-icon-css-v1') >= 0;
    var hasIconEffects = rules.rules.some(function (rule) { return rule.declarations.some(function (d) { return d.property === 'filter' || d.property === 'mix-blend-mode' || d.property === 'isolation' || d.property === 'transform' || d.property === 'overflow'; }); });
    if (hasIconEffects && !modernIcons) fail('api-unsupported', 'icon CSS capability');
    if (modernIcons && (!root.CSS || !root.CSS.supports || !root.CSS.supports('isolation', 'isolate') || !root.CSS.supports('mix-blend-mode', 'screen') || !root.CSS.supports('filter', 'grayscale(1) invert(1) brightness(1.3)'))) fail('api-unsupported', 'modern icon CSS');
    if (rules.rules.some(function (rule) { return rule.declarations.some(function (d) { return d.property === 'transform'; }); }) && (manifest.layout.preset !== 'scenic-grid' || manifest.layout.columns > 5 || manifest.layout.allowColumnOverride !== false)) fail('layout-invalid', 'icon scale requires fixed scenic-grid with at most five columns');
    /* Trusted layouts currently implement only the Classic scale values. */
    if (manifest.layout.spacingScale !== 1 || manifest.layout.textScale !== 1 || manifest.layout.focusScale !== 1.1) fail('layout-invalid', 'unsupported scale preset');
    if (manifest.layout.preset !== 'dock-grid' && (!root.HomeLayoutState || !root.HomeLayoutState.setThemeLayout)) fail('layout-invalid', 'unsupported renderer preset');
    if (manifest.layout.ribbon && (!root.HomeLayoutState || root.HomeLayoutState.supportsRibbonOptions !== true)) fail('layout-invalid', 'unsupported ribbon options');
    if (manifest.layout.allowColumnOverride === false && (!root.HomeLayoutState || root.HomeLayoutState.supportsColumnPolicy !== true)) fail('layout-invalid', 'unsupported column policy');
    var handles = input.assetHandles || {}, overrides = input.overrides || {}, own = Object.prototype.hasOwnProperty;
    Object.keys(overrides).forEach(function (key) { if (['accent', 'dim', 'wallpaperAssetId'].indexOf(key) < 0) fail('manifest-invalid', 'overrides'); });
    var accent = own.call(overrides, 'accent') ? overrides.accent : manifest.defaults.accent;
    var dim = own.call(overrides, 'dim') ? overrides.dim : manifest.defaults.dim;
    var wallpaper = own.call(overrides, 'wallpaperAssetId') ? overrides.wallpaperAssetId : manifest.defaults.wallpaperAssetId;
    if (typeof accent !== 'string' || !/^#[a-fA-F0-9]{6}$/.test(accent)) fail('manifest-invalid', 'accent');
    if (typeof dim !== 'number' || !isFinite(dim) || dim < 0 || dim > .85) fail('manifest-invalid', 'dim');
    var css = policy.compileRules(rules, handles);
    function appendCss(text) {
      if (text.length > policy.limits.emittedCssBytes - css.length) fail('css-budget', 'emitted CSS bytes');
      css += text;
    }
    if (wallpaper !== null) {
      if (!manifest.assets.some(function (asset) { return asset.id === wallpaper; })) fail('asset-invalid', 'wallpaperAssetId');
      var wallpaperBundle = {schemaVersion: 1, rules: [{selector: [{part: 'home', states: []}], declarations: [{property: 'background-image', value: {type: 'asset', id: wallpaper}}]}]};
      var wallpaperCss = policy.compileRules(wallpaperBundle, handles);
      appendCss('\n' + wallpaperCss.replace('background-image:', 'background-image:linear-gradient(rgba(0,0,0,' + dim + '),rgba(0,0,0,' + dim + ')),'));
    }
    /* A trusted minimum remains visible even against higher-specificity author states.
       Author CSS cannot emit !important; this narrow engine-owned border may. */
    var scaleFocus = modernIcons && manifest.layout.preset === 'scenic-grid' && rules.rules.some(function (rule) {
      return rule.selector.length === 1 && rule.selector[0].part === 'card' && rule.selector[0].states.length === 1 && rule.selector[0].states[0] === 'focused' &&
        rule.declarations.some(function (d) { return d.property === 'border-width' && d.value.value === 0; }) &&
        rule.declarations.some(function (d) { return d.property === 'border-style' && d.value.value === 'none'; });
    });
    var hiddenHero = rules.rules.some(function (rule) {
      return rule.selector.length === 1 && rule.selector[0].part === 'hero' && rule.selector[0].states.length === 0 &&
        rule.declarations.some(function (d) { return d.property === 'color' && d.value.rgba[3] === 0; });
    });
    if (scaleFocus) {
      appendCss('\n#homeSurface.ctv-home .ctv-card.is-focused{border:0!important;transform:scale(1.1)!important;}');
      // A visible hero already names the selected app; keep the fallback only when hidden.
      if (hiddenHero) appendCss('\n#homeSurface.ctv-home .ctv-label.is-focused{color:#fff!important;opacity:1!important;text-shadow:0 1px 6px #000!important;}');
    }
    else appendCss('\n#homeSurface.ctv-home .ctv-card.is-focused{border-color:' + accent + '!important;border-style:solid!important;border-width:' + (manifest.layout.preset === 'scenic-grid' ? '3' : '2') + 'px!important;}');
    if (modernIcons) rules.rules.forEach(function (rule) {
      var part = rule.selector[rule.selector.length - 1].part;
      if (part !== 'card' && part !== 'clock' && part !== 'date' && part !== 'icon') return;
      rule.declarations.forEach(function (d) {
        if (!(part === 'card' && d.property === 'background-color') && !((part === 'clock' || part === 'date') && d.property === 'font-size') && !(part === 'icon' && d.property === 'transform')) return;
        var background = policy.compileRules({schemaVersion: 1, rules: [{selector: rule.selector, declarations: [d]}]}, handles);
        appendCss('\n' + background.replace(/;\}$/, '!important;}'));
      });
    });
    if (manifest.layout.ribbon) {
      var r = manifest.layout.ribbon, prefix = '#homeSurface.ctv-home[data-ribbon="true"] ';
      function ribbonRule(selector, declarations) { appendCss('\n' + prefix + selector + '{' + declarations + '}'); }
      ribbonRule('#viewport', 'top:0;bottom:0;overflow:hidden;');
      ribbonRule('#stage', 'top:0;');
      ribbonRule('.ctv-position', 'display:none!important;');
      // Transform the hit target itself: browser pointer hit-testing follows its slanted shape.
      ribbonRule('.item', 'height:' + r.cardHeight + 'px;padding-bottom:0;border-radius:0;transform:skewX(' + r.skewDeg + 'deg)!important;transform-origin:center bottom;');
      ribbonRule('.item .card', 'transform:none!important;transition:none;');
      ribbonRule('.item.focused .card', 'height:' + (r.cardHeight + r.focusLift) + 'px!important;top:-' + r.focusLift + 'px;border:3px solid ' + accent + '!important;transform:none!important;');
      ribbonRule('.item.moving .card', 'animation:none;');
      ribbonRule('.item .card img', 'width:' + (r.iconScale * 100) + '%;height:' + (r.cardHeight * r.iconScale) + 'px;left:' + ((1 - r.iconScale) * 50) + '%;top:' + (r.cardHeight * (1 - r.iconScale) / 2) + 'px;');
      ribbonRule('.add-app svg', 'width:' + (64 * r.iconScale) + 'px;height:' + (64 * r.iconScale) + 'px;');
      ribbonRule('.item .ctv-icon', 'transform:skewX(' + (-r.skewDeg) + 'deg)!important;');
      ribbonRule('.item .name', 'transform:skewX(' + (-r.skewDeg) + 'deg)!important;');
      if (r.labels === 'focused-above') {
        ribbonRule('#hero', 'display:none!important;');
        ribbonRule('.item .name', 'display:none!important;');
        ribbonRule('.item.focused .name', 'display:block!important;position:absolute;left:0;right:0;bottom:' + (r.cardHeight + r.focusLift + 20) + 'px;margin:0 -40px;height:auto;max-height:96px;line-height:32px;white-space:normal;overflow:hidden;opacity:1!important;color:#fff!important;text-shadow:0 2px 8px #000;');
      }
      else ribbonRule('.item .name', 'position:absolute;top:' + (r.cardHeight + 16) + 'px;left:0;right:0;margin:0 -32px;line-height:32px;height:32px;');
      if (!r.showClock) ribbonRule('#timeRow', 'display:none!important;');
      if (r.shortcuts === 'bottom-left') {
        ribbonRule('header', 'top:0;bottom:0;left:0;right:0;pointer-events:none;');
        ribbonRule('#timeRow', 'position:absolute;top:104px;left:112px;');
        ribbonRule('#topButtons', 'position:absolute;left:28px;right:auto;top:auto;bottom:28px;margin:0;pointer-events:auto;');
        ribbonRule('#topButtons .pill', 'width:72px;height:72px;padding:0;margin:0 12px 0 0;justify-content:center;font-size:0;');
        ribbonRule('#topButtons .pill svg', 'width:32px;height:32px;margin:0;');
      }
    }
    /* All untrusted input is checked before either geometry or styles are changed. */
    if (root.HomeLayoutState && root.HomeLayoutState.setThemeLayout) root.HomeLayoutState.setThemeLayout(manifest.layout);
    else if (root.HomeLayoutState && root.HomeLayoutState.setThemeColumns) root.HomeLayoutState.setThemeColumns(manifest.layout.columns);
    var current = sheet(), previous = accepted;
    if (!current) { current = root.document.createElement('style'); current.id = 'ctv-theme-style'; current.disabled = true; root.document.head.appendChild(current); }
    current.disabled = true; current.textContent = css;
    current.disabled = suspended();
    if (suspended()) { heldSheet = current; wasEnabled = true; surfaceState(true); }
    else surfaceState(false);
    var ownedHandles = Object.create(null);
    Object.keys(handles).forEach(function (key) { ownedHandles[key] = handles[key]; });
    accepted = {themeId: manifest.id, themeVersion: manifest.themeVersion, handles: ownedHandles};
    var surface = root.document.getElementById('homeSurface');
    if (surface) surface.classList.add('ctv-theme-active');
    release(previous && previous.handles, ownedHandles);
    return {themeId: manifest.id, themeVersion: manifest.themeVersion};
  }
  function reset() {
    var current = sheet(), previous = accepted;
    if (root.HomeLayoutState && root.HomeLayoutState.setThemeLayout) root.HomeLayoutState.setThemeLayout({preset: 'dock-grid', columns: 5, spacingScale: 1, textScale: 1, focusScale: 1.1});
    else if (root.HomeLayoutState && root.HomeLayoutState.setThemeColumns) root.HomeLayoutState.setThemeColumns(5);
    if (current && current.parentNode) current.parentNode.removeChild(current);
    accepted = null; heldSheet = null; wasEnabled = false; surfaceState(false);
    var surface = root.document.getElementById('homeSurface');
    if (surface) surface.classList.remove('ctv-theme-active');
    release(previous && previous.handles, null);
    return {themeId: 'builtin:classic', themeVersion: null};
  }
  root.ThemeRuntime = {isSuspended: suspended, apply: apply, suspend: suspend, resume: resume, reset: reset};
}(this));
