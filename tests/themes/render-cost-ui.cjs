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
        await page.evaluate(() => document.getElementById('homeSurface').classList.add('ctv-theme-active'));
        const themed = await glowState();
        assert.equal(themed.page, 'none', 'themes never see the baked glow');
        assert.deepEqual(themed.layers.filter(layer => layer.opacity === '1').map(layer => [layer.width, layer.height]), [[1920, 1080]], 'themes keep one full-size glow layer');
        await page.evaluate(() => document.getElementById('homeSurface').classList.remove('ctv-theme-active'));
        // open()'s `*` rule does not reach the edge fades' pseudo-elements; let them settle.
        await page.waitForTimeout(400);

        // The baked glow looks like the layer it replaced.
        const scaledShot = await page.screenshot();
        await page.evaluate(() => {
          const override = document.createElement('style');
          override.id = 'full-glow';
          override.textContent = '#homeSurface:not(.ctv-theme-active) #ambientBase{background-image:none!important}' +
            '#homeSurface:not(.ctv-theme-active) .ambient.baked{opacity:1!important}';
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
        assert(!/#homeSurface:not/.test(sweep.fading), 'the crossfade runs on the layers');
        assert(/#homeSurface:not/.test(sweep.settled) && sweep.settled !== sweep.start, 'the new glow is baked into the page');

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
