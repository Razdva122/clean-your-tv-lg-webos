// Removing a public part/state or changing Classic's geometry/appearance fails
// against the same real renderer before and after the CSS split.
const {
  assert,
  fs,
  path,
  chromium,
  root,
  stage,
  open,
  states
} = require('./browser.cjs');
const mode = process.argv[2];
const directory = process.argv[3] && path.resolve(process.argv[3]);
const capturing = mode === '--capture';
const comparing = mode === '--compare';
if ((capturing || comparing) && !directory)
  throw Error('Expected snapshot directory');

async function equivalentPixels(page, expected, actual) {
  // Headless gradient rasterization can round a handful of channels by one.
  // Reject every larger change, including text, geometry and palette changes.
  return page.evaluate(
    async (images) => {
      const load = (data) =>
        new Promise((resolve, reject) => {
          const image = new Image();
          image.onload = () => resolve(image);
          image.onerror = reject;
          image.src = 'data:image/png;base64,' + data;
        });
      const [a, b] = await Promise.all(images.map(load));
      if (a.width !== b.width || a.height !== b.height) return false;
      const pixels = (image) => {
        const canvas = document.createElement('canvas');
        canvas.width = image.width;
        canvas.height = image.height;
        const context = canvas.getContext('2d');
        context.drawImage(image, 0, 0);
        return context.getImageData(0, 0, image.width, image.height).data;
      };
      const left = pixels(a),
        right = pixels(b);
      let changed = 0;
      for (let i = 0; i < left.length; i += 4) {
        let different = false;
        for (let channel = 0; channel < 4; channel++) {
          const delta = Math.abs(left[i + channel] - right[i + channel]);
          if (delta > 1) return false;
          if (delta) different = true;
        }
        if (different && ++changed > 16) return false;
      }
      return true;
    },
    [expected.toString('base64'), actual.toString('base64')]
  );
}

async function checkParts(page, state) {
  for (const selector of [
    '.ctv-home',
    '.ctv-header',
    '.ctv-clock',
    '.ctv-date',
    '.ctv-greeting',
    '.ctv-hero',
    '.ctv-dock',
    '.ctv-card',
    '.ctv-icon',
    '.ctv-label',
    '.ctv-focus',
    '.ctv-inputs',
    '.ctv-shortcut',
    '.ctv-ambient'
  ]) {
    assert(await page.locator(selector).count(), 'public part: ' + selector);
  }
  assert(
    await page.locator('.add-app .ctv-card').count(),
    'Add uses public card'
  );
  if (['dock', 'grid', 'focused', 'add-app', 'reorder'].includes(state)) {
    assert.equal(await page.locator('.ctv-tile.is-focused').count(), 1);
    assert.equal(await page.locator('.ctv-card.is-focused').count(), 1);
  }
  if (state === 'reorder')
    assert.equal(await page.locator('.ctv-card.is-moving').count(), 1);
  if (state === 'library') {
    assert.equal(await page.locator('.ctv-home .ctv-library').count(), 1);
    assert.equal(await page.locator('.ctv-library-row.is-focused').count(), 1);
  }
  if (state === 'inputs')
    assert.equal(await page.locator('.ctv-input-row.is-focused').count(), 1);
  if (state === 'settings' || state === 'confirmation') {
    assert.equal(
      await page
        .locator(
          '.ctv-home #renewalPanel, .ctv-home .root-settings, .ctv-home #homeConfirmation'
        )
        .count(),
      0
    );
  }
}

(async () => {
  const site = process.env.THEME_BASELINE_SITE
    ? path.resolve(process.env.THEME_BASELINE_SITE)
    : stage();
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  try {
    if (capturing) fs.mkdirSync(directory, { recursive: true });
    for (const edition of ['launcher', 'root-launcher']) {
      for (const columns of [1, 4, 5, 8]) {
        const { page, errors } = await open(browser, site, edition, columns);
        try {
          await states(page, async (state) => {
            // Entry/hero timers are independent of CSS transitions; compare a
            // settled screen rather than a different point in a title swap.
            await page.waitForTimeout(650);
            if (!capturing) await checkParts(page, state);
            if (
              (capturing || comparing) &&
              !['settings', 'confirmation'].includes(state)
            ) {
              const name = edition + '-' + columns + '-' + state + '.png';
              const image = await page.screenshot({ animations: 'disabled' });
              if (capturing)
                fs.writeFileSync(path.join(directory, name), image);
              else {
                const expected = fs.readFileSync(path.join(directory, name));
                if (
                  !image.equals(expected) &&
                  !(await equivalentPixels(page, expected, image))
                ) {
                  fs.writeFileSync(
                    path.join(root, 'build/tests/themes', name),
                    image
                  );
                  assert.fail('Classic screenshot changed: ' + name);
                }
              }
            }
          });
          assert.deepEqual(errors, [], 'renderer errors');
          console.log(
            'PASS theme baseline: ' + edition + ', columns=' + columns
          );
        } finally {
          await page.close();
        }
      }
    }
  } finally {
    await browser.close();
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
