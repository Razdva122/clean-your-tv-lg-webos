// Rendering budget measured on a 4K webOS TV: the settled glow is baked into the page
// and only crossfades at rest, every Classic tile and the stage are their own layers,
// and input tiles grow without per-frame layout.
const {assert, chromium, stage, open} = require('./browser.cjs');

(async () => {
  const site = stage(), browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const edition of ['launcher', 'root-launcher']) {
      const {page, errors} = await open(browser, site, edition);
      try {
        await page.evaluate(() => {
          window.key = (code, repeat) => {
            document.dispatchEvent(new KeyboardEvent('keydown', {keyCode: code, which: code, repeat: !!repeat, bubbles: true, cancelable: true}));
            document.dispatchEvent(new KeyboardEvent('keyup', {keyCode: code, which: code, bubbles: true}));
          };
          window.glow = () => (document.getElementById('ctv-ambient-style') || {}).textContent || '';
        });
        assert.equal(await page.locator('#stage').evaluate(el => getComputedStyle(el).willChange), 'transform', 'the stage is its own layer');
        assert.deepEqual([...new Set(await page.locator('#tiles .item, .ctv-input-tile').evaluateAll(els => els.map(el => getComputedStyle(el).willChange)))], ['transform'],
          'every Classic tile is its own layer');

        // Settled Classic glow: baked into the page background, no full-screen layers.
        await page.waitForTimeout(1600);
        const glowState = () => page.evaluate(() => ({
          page: getComputedStyle(document.getElementById('ambientBase')).backgroundImage,
          wallpaper: getComputedStyle(document.getElementById('homeSurface')).backgroundImage,
          layers: Array.from(document.querySelectorAll('.ambient')).map(el => ({opacity: getComputedStyle(el).opacity, width: el.offsetWidth, height: el.offsetHeight})),
        }));
        const baked = await glowState();
        assert.match(baked.page, /\b1190px at 32% 42%/, 'the settled glow is painted by the plain base element');
        assert.equal(baked.wallpaper, 'none', 'the Home background stays the theme wallpaper slot');
        assert.deepEqual(baked.layers.map(layer => layer.opacity), ['0', '0'], 'no glow layer is drawn at rest');
        // Themes bake too, and a theme's ambient rule styles the base like the layers.
        await page.evaluate(() => {
          document.getElementById('homeSurface').classList.add('ctv-theme-active');
          const style = document.createElement('style');
          style.id = 'theme-ambient';
          style.textContent = '#homeSurface.ctv-home .ctv-ambient{background-image:linear-gradient(0deg, transparent 0%, transparent 100%)}';
          document.head.appendChild(style);
        });
        const themed = await glowState();
        assert.match(themed.page, /^linear-gradient/, 'a theme ambient rule overrides the baked glow on the base');
        assert.deepEqual(themed.layers.map(layer => layer.opacity), ['0', '0'], 'themes draw no glow layer at rest either');
        await page.evaluate(() => { document.getElementById('theme-ambient').remove(); document.getElementById('homeSurface').classList.remove('ctv-theme-active'); });
        // open()'s `*` rule does not reach the edge fades' pseudo-elements; let them settle.
        await page.waitForTimeout(400);

        // The baked glow looks like the layer it replaced.
        const scaledShot = await page.screenshot();
        await page.evaluate(() => {
          const override = document.createElement('style');
          override.id = 'full-glow';
          override.textContent = '#homeSurface #ambientBase{background-image:none!important}' +
            '#homeSurface .ambient.baked{opacity:1!important}';
          document.head.appendChild(override);
        });
        const fullShot = await page.screenshot();
        await page.evaluate(() => document.getElementById('full-glow').remove());
        const diff = await page.evaluate(async ([a, b]) => {
          const load = data => new Promise(resolve => { const image = new Image(); image.onload = () => resolve(image); image.src = 'data:image/png;base64,' + data; });
          const pixels = image => { const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height; const context = canvas.getContext('2d'); context.drawImage(image, 0, 0); return context.getImageData(0, 0, image.width, image.height).data; };
          const [first, second] = (await Promise.all([load(a), load(b)])).map(pixels);
          let sum = 0, max = 0, count = 0;
          for (let i = 0; i < first.length; i += 4) for (let c = 0; c < 3; c++) { const d = Math.abs(first[i + c] - second[i + c]); sum += d; max = Math.max(max, d); count++; }
          return {mean: sum / count, max};
        }, [scaledShot.toString('base64'), fullShot.toString('base64')]);
        assert(diff.mean < 1.5 && diff.max < 8, 'the baked glow matches the glow layer: ' + JSON.stringify(diff));

        // Browsing at a press every 500 ms leaves the glow alone; it crossfades once the
        // focus rests for 800 ms, then bakes.
        const sweep = await page.evaluate(() => new Promise(resolve => {
          const start = glow(), seen = [];
          let step = 0;
          (function next() {
            if (step++ < 3) { key(39, false); seen.push(glow()); setTimeout(() => { seen.push(glow()); next(); }, 500); return; }
            setTimeout(() => {
              seen.push(glow());
              setTimeout(() => {
                const fading = glow();
                setTimeout(() => resolve({start, seen, fading, settled: glow()}), 800);
              }, 400);
            }, 200);
          }());
        }));
        assert(sweep.seen.every(value => value === sweep.start), 'focus motion never changes the glow');
        assert.notEqual(sweep.fading, sweep.start, 'the glow follows once the focus rests');
        const bakedRule = sheet => sheet.split('\n').filter(rule => rule.indexOf('#ambientBase{') === 0)[0] || '';
        assert.equal(bakedRule(sweep.fading), '', 'the crossfade runs on the layers, with no baked rule');
        assert(bakedRule(sweep.settled) && bakedRule(sweep.settled) !== bakedRule(sweep.start), 'the new glow is baked into the page');

        // Growing an input relayouts once per press, not on every frame of the motion.
        await page.evaluate(() => Array.from(document.querySelectorAll('style')).filter(style => /transition: none !important/.test(style.textContent)).forEach(style => style.remove()));
        await page.evaluate(() => key(38, false));
        assert.equal(await page.locator('.ctv-input-tile.is-focused').count(), 1, 'the shelf has focus');
        await page.waitForTimeout(400);
        const cdp = await page.context().newCDPSession(page);
        await cdp.send('Performance.enable');
        const layouts = async () => (await cdp.send('Performance.getMetrics')).metrics.find(metric => metric.name === 'LayoutCount').value;
        const before = await layouts();
        await page.evaluate(() => key(39, false));
        await page.waitForTimeout(400);
        const count = await layouts() - before;
        assert(count <= 4, 'one shelf press costs at most 4 layouts: ' + count);
        assert.deepEqual(errors, [], 'renderer errors');
        console.log('PASS rendering budget: baked glow, tile and stage layers, FLIP inputs: ' + edition);
      } finally { await page.close(); }
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
