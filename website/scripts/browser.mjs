import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFileSync, existsSync, statSync, mkdirSync } from 'node:fs';
import { resolve, extname, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
const require = createRequire(new URL('../../package.json', import.meta.url));
const { chromium } = require('playwright');
const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const base = '/clean-your-tv-lg-webos/';
const server = createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (!url.pathname.startsWith(base)) {
    res.writeHead(404).end();
    return;
  }
  let file = resolve(dist, decodeURIComponent(url.pathname.slice(base.length)));
  if (file !== resolve(dist) && !file.startsWith(resolve(dist) + sep)) {
    res.writeHead(404).end();
    return;
  }
  if (existsSync(file) && statSync(file).isDirectory()) file += '/index.html';
  if (!existsSync(file)) {
    res.writeHead(404).end();
    return;
  }
  res.setHeader(
    'Content-Type',
    {
      '.css': 'text/css',
      '.js': 'application/javascript',
      '.json': 'application/json',
      '.svg': 'image/svg+xml',
      '.jpg': 'image/jpeg',
      '.png': 'image/png',
      '.webp': 'image/webp',
      '.woff2': 'font/woff2',
      '.ttf': 'font/ttf',
      '.xml': 'application/xml'
    }[extname(file)] || 'text/html'
  );
  res.end(readFileSync(file));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const host = 'http://127.0.0.1:' + server.address().port;
let browser;
const errors = [];
const shots = process.env.WEBSITE_SCREENSHOTS;
if (shots) mkdirSync(shots, { recursive: true });
try {
  browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || 'chrome'
  });
  // The landing page shows captures; the full renderer stays on /demo/.
  const showcase = await browser.newPage();
  showcase.on('pageerror', (error) => errors.push(error.message));
  const requests = [];
  showcase.on('request', (request) => requests.push(request.url()));
  await showcase.goto(host + base + 'ru/');
  assert.equal(await showcase.getByRole('radio').count(), 3);
  await showcase
    .locator('[data-poster="liquid-glass"]')
    .waitFor({ state: 'visible' });
  await showcase.getByRole('radio', { name: 'Classic', exact: true }).check();
  await showcase
    .locator('[data-poster="classic"]')
    .waitFor({ state: 'visible' });
  assert.match(
    await showcase.locator('[data-poster="classic"]').getAttribute('src'),
    /classic\.webp$/
  );
  await showcase.locator('.preview-toggle').click();
  assert.equal(
    await showcase.locator('[data-showcase]').getAttribute('data-paused'),
    'true'
  );
  assert.match(
    await showcase.locator('[data-poster="classic"]').getAttribute('src'),
    /classic-still\.webp$/
  );
  await showcase.getByRole('radio', { name: 'Ribbon', exact: true }).check();
  assert.match(
    await showcase.locator('[data-poster="ribbon"]').getAttribute('src'),
    /ribbon-still\.webp$/
  );
  await showcase.locator('.preview-toggle').click();
  assert.match(
    await showcase.locator('[data-poster="ribbon"]').getAttribute('src'),
    /ribbon\.webp$/
  );
  assert.equal(await showcase.locator('iframe').count(), 0);
  assert.equal(
    requests.some((url) => url.includes('/demo/')),
    false,
    'landing loads no TV renderer'
  );
  assert.equal(
    await showcase.locator('[data-open-demo]').getAttribute('href'),
    base + 'demo/'
  );
  await showcase.close();
  const reduced = await browser.newPage({ reducedMotion: 'reduce' });
  const reducedRequests = [];
  reduced.on('request', (r) => reducedRequests.push(r.url()));
  await reduced.goto(host + base + 'en/');
  assert.equal(
    await reduced.locator('[data-showcase]').getAttribute('data-paused'),
    'true'
  );
  assert.equal(
    reducedRequests.some((url) =>
      /\/(?:classic|liquid-glass|ribbon)(?:-small)?\.webp$/.test(url)
    ),
    false,
    'reduced motion loads only stills'
  );
  await reduced.close();
  const failedPreview = await browser.newPage();
  await failedPreview.route('**/liquid-glass.webp', (request) =>
    request.abort()
  );
  await failedPreview.goto(host + base + 'en/');
  await failedPreview.waitForFunction(
    () => document.querySelector('[data-showcase]').dataset.paused === 'true'
  );
  assert.match(
    await failedPreview
      .locator('[data-poster="liquid-glass"]')
      .getAttribute('src'),
    /-still\.webp$/
  );
  await failedPreview
    .locator('[data-poster="liquid-glass"]')
    .evaluate((image) => image.decode());
  await failedPreview.close();
  const staticShowcase = await browser.newPage({ javaScriptEnabled: false });
  await staticShowcase.goto(host + base + 'ru/');
  await staticShowcase
    .getByRole('radio', { name: 'Liquid Glass', exact: true })
    .check();
  await staticShowcase
    .locator('[data-poster="liquid-glass"]')
    .waitFor({ state: 'visible' });
  assert.equal(
    await staticShowcase.locator('.preview-toggle').isVisible(),
    false
  );
  assert.equal(
    await staticShowcase.locator('[data-open-demo]').getAttribute('href'),
    base + 'demo/'
  );
  await staticShowcase.close();
  // The actual preview must fit its frame, even when overflow-x is clipped.
  const responsive = await browser.newPage({ reducedMotion: 'reduce' });
  const languages = [
    'en',
    'de',
    'es',
    'pt-BR',
    'fr',
    'it',
    'ko',
    'hi',
    'pl',
    'ru',
    'cs',
    'zh-Hans',
    'zh-Hant'
  ];
  const previewWidths = new Map();
  for (const lang of languages) {
    for (const [width, height] of [
      [320, 700],
      [390, 844],
      [768, 1024],
      [820, 1180],
      [1024, 768],
      [1340, 746],
      [1440, 900],
      [1440, 600]
    ]) {
      await responsive.setViewportSize({ width, height });
      await responsive.goto(host + base + lang + '/');
      await responsive.evaluate(() => document.fonts.ready);
      const failures = await responsive.evaluate(() => {
        const issues = [];
        for (const section of document.querySelectorAll('main > section')) {
          const box = section.getBoundingClientRect();
          for (const item of section.querySelectorAll(
            'h1,h2,h3,p,a,img,.showcase-screen'
          )) {
            if (!item.checkVisibility()) continue;
            const rect = item.getBoundingClientRect();
            if (
              rect.right > innerWidth + 2 ||
              rect.left < -2 ||
              rect.bottom > box.bottom + 2
            )
              issues.push([
                section.id || 'hero',
                item.tagName,
                Math.round(rect.right),
                Math.round(rect.bottom - box.bottom)
              ]);
          }
        }
        const stage = document
          .querySelector('.showcase-stage')
          .getBoundingClientRect();
        for (const control of document.querySelectorAll(
          '.hero .btn-row, .theme-picker'
        )) {
          if (control.getBoundingClientRect().bottom > stage.top + 1)
            issues.push(['hero', 'preview covers controls']);
        }
        return issues;
      });
      assert.deepEqual(
        failures,
        [],
        `${lang} at ${width}×${height}: preview/content crosses its frame or section`
      );
      const { width: previewWidth, height: previewHeight } = await responsive
        .locator('.showcase-stage')
        .boundingBox();
      const viewport = `${width}×${height}`;
      assert.ok(
        previewWidth >= Math.min(width - 48, 560) &&
          Math.abs(previewWidth / previewHeight - 16 / 9) < 0.01,
        `${lang} at ${viewport}: expected a usable 16:9 preview, got ${previewWidth}×${previewHeight}`
      );
      if (!previewWidths.has(viewport))
        previewWidths.set(viewport, previewWidth);
      assert.equal(
        previewWidth,
        previewWidths.get(viewport),
        `${lang} at ${viewport}: translated copy changes the preview width`
      );
      if (shots && lang === 'ru')
        await responsive.screenshot({
          path: resolve(shots, `ru-layout-${width}-${height}.png`),
          fullPage: true
        });
    }
  }
  await responsive.close();
  // Each visitor starts with fresh storage; regional browser tags map to site locales.
  for (const [languages, expected] of [
    [['ru-RU', 'en-US'], 'ru'],
    [['xx', 'de-AT'], 'de'],
    [['pt-PT'], 'pt-BR'],
    [['zh-TW'], 'zh-Hant'],
    [['zh-HK'], 'zh-Hant'],
    [['zh-Hant-CN'], 'zh-Hant'],
    [['zh-CN'], 'zh-Hans'],
    [['zh-Hans-TW'], 'zh-Hans'],
    [['zh'], 'zh-Hans'],
    [['en-GB', 'ru'], 'en'],
    [['xx'], 'en'],
    [[], 'en']
  ]) {
    const context = await browser.newContext();
    await context.addInitScript((values) => {
      Object.defineProperty(navigator, 'languages', { get: () => values });
      Object.defineProperty(navigator, 'language', {
        get: () => values[0] || ''
      });
    }, languages);
    const visitor = await context.newPage();
    visitor.on('pageerror', (e) => errors.push(e.message));
    await visitor.goto(host + base + '?from=test#content');
    await visitor.waitForURL(host + base + expected + '/?from=test#content');
    assert.equal(await visitor.locator('html').getAttribute('lang'), expected);
    await context.close();
  }
  const context = await browser.newContext({ locale: 'ru-RU' });
  const visitor = await context.newPage();
  visitor.on('pageerror', (e) => errors.push(e.message));
  await visitor.goto(host + base + 'de/install/');
  assert.equal(new URL(visitor.url()).pathname, base + 'de/install/');
  await visitor.locator('.languages summary').click();
  await visitor.locator('.languages a[hreflang="fr"]').click();
  await visitor.waitForURL('**/fr/install/');
  await visitor.goto(host + base);
  await visitor.waitForURL('**/fr/');
  // An explicit URL takes priority without overwriting the manual preference.
  await visitor.goto(host + base + 'en/help/');
  assert.equal(new URL(visitor.url()).pathname, base + 'en/help/');
  await visitor.goto(host + base);
  await visitor.waitForURL('**/fr/');
  await context.close();
  const blockedContext = await browser.newContext({ locale: 'ru-RU' });
  await blockedContext.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      get() {
        throw new DOMException('Storage blocked', 'SecurityError');
      }
    });
  });
  const blocked = await blockedContext.newPage();
  blocked.on('pageerror', (e) => errors.push(e.message));
  await blocked.goto(host + base);
  await blocked.waitForURL('**/ru/');
  await blocked.locator('.languages summary').click();
  await blocked.locator('.languages a[hreflang="en"]').click();
  await blocked.waitForURL('**/en/');
  await blockedContext.close();
  // Crawlable content and navigation must work with JavaScript disabled.
  const staticPage = await browser.newPage({
    javaScriptEnabled: false,
    viewport: { width: 1440, height: 1000 }
  });
  for (const lang of [
    'en',
    'de',
    'es',
    'pt-BR',
    'fr',
    'it',
    'ko',
    'hi',
    'pl',
    'ru',
    'cs',
    'zh-Hans',
    'zh-Hant'
  ]) {
    for (const section of [
      '',
      'install/',
      'editions/',
      'compatibility/',
      'themes/',
      'help/'
    ]) {
      const response = await staticPage.goto(
        host + base + lang + '/' + section
      );
      assert.equal(response.status(), 200);
      assert.equal(await staticPage.locator('h1').count(), 1);
      await staticPage.locator('h1').waitFor({ state: 'visible' });
    }
  }
  await staticPage.goto(host + base + 'ru/install/');
  await staticPage.locator('.languages summary').focus();
  await staticPage.keyboard.press('Enter');
  await staticPage.locator('.languages a[hreflang="cs"]').click();
  assert.equal(new URL(staticPage.url()).pathname, base + 'cs/install/');
  await staticPage.goto(host + base + 'ru/help/');
  for (const id of [
    'connection',
    'developer-mode',
    'home-button',
    'interrupted',
    'update-remove'
  ]) {
    await staticPage.locator('.topic-links a[href="#' + id + '"]').click();
    assert.equal(new URL(staticPage.url()).hash, '#' + id);
    await staticPage.locator('#' + id + ' h2').waitFor({ state: 'visible' });
  }
  await staticPage.locator('.languages summary').click();
  await staticPage.locator('.languages a[hreflang="cs"]').click();
  assert.equal(new URL(staticPage.url()).pathname, base + 'cs/help/');
  // The compact header must keep every destination reachable without JavaScript.
  await staticPage.setViewportSize({ width: 320, height: 812 });
  await staticPage.goto(host + base + 'ru/');
  await staticPage.locator('.mobile-menu summary').focus();
  await staticPage.keyboard.press('Enter');
  await staticPage
    .locator('.mobile-menu a[href="' + base + 'ru/help/"]')
    .click();
  assert.equal(new URL(staticPage.url()).pathname, base + 'ru/help/');
  await staticPage.close();
  // Article discovery, translation links and text remain usable without JavaScript.
  const articleContext = await browser.newContext({ javaScriptEnabled: false });
  const articlePage = await articleContext.newPage();
  // The reading index must also be usable on phones without JavaScript.
  await articlePage.setViewportSize({ width: 390, height: 844 });
  await articlePage.goto(host + base + 'ru/articles/root-vs-no-root/');
  const mobileContents = articlePage.locator('.mobile-toc');
  assert.equal(
    await mobileContents.count(),
    1,
    'article has a mobile table of contents'
  );
  assert.equal(
    await mobileContents.getAttribute('open'),
    null,
    'mobile contents start collapsed'
  );
  await mobileContents.locator('summary').click();
  const firstSection = mobileContents.locator('a').first();
  const sectionHash = await firstSection.getAttribute('href');
  await firstSection.click();
  assert.equal(
    decodeURIComponent(new URL(articlePage.url()).hash),
    sectionHash
  );
  await articlePage.locator(sectionHash).waitFor({ state: 'visible' });
  const topics = [
    'change-lg-webos-home-screen',
    'lg-tv-home-screen-ads',
    'root-vs-no-root',
    'lg-developer-mode'
  ];
  for (const lang of [
    'en',
    'de',
    'es',
    'pt-BR',
    'fr',
    'it',
    'ko',
    'hi',
    'pl',
    'ru',
    'cs',
    'zh-Hans',
    'zh-Hant'
  ]) {
    await articlePage.setViewportSize({ width: 1440, height: 1000 });
    for (const topic of ['', ...topics]) {
      const response = await articlePage.goto(
        host + base + lang + '/articles/' + (topic ? topic + '/' : '')
      );
      assert.equal(response.status(), 200);
      await articlePage.locator('h1').waitFor({ state: 'visible' });
      assert(
        await articlePage.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1
        ),
        lang + '/' + topic + ' article desktop overflow'
      );
      await articlePage.setViewportSize({ width: 320, height: 812 });
      assert(
        await articlePage.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1
        ),
        lang + '/' + topic + ' article mobile overflow'
      );
      if (shots && lang === 'ru')
        await articlePage.screenshot({
          path: resolve(shots, 'ru-article-' + (topic || 'index') + '-320.png'),
          fullPage: true
        });
      await articlePage.setViewportSize({ width: 1440, height: 1000 });
    }
  }
  await articlePage.goto(host + base + 'ru/articles/root-vs-no-root/');
  await articlePage.locator('.languages summary').click();
  await articlePage.locator('.languages a[hreflang="zh-Hant"]').click();
  assert.equal(
    new URL(articlePage.url()).pathname,
    base + 'zh-Hant/articles/root-vs-no-root/'
  );
  await articlePage.setViewportSize({ width: 320, height: 812 });
  await articlePage.locator('.mobile-menu summary').focus();
  await articlePage.keyboard.press('Enter');
  await articlePage
    .locator('.mobile-menu a[href="' + base + 'zh-Hant/articles/"]')
    .click();
  await articlePage.locator('.article-list h2 a').first().click();
  assert.equal(
    new URL(articlePage.url()).pathname,
    base + 'zh-Hant/articles/change-lg-webos-home-screen/'
  );
  await articleContext.close();
  const page = await browser.newPage();
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('response', (r) => {
    if (r.url().startsWith(host) && r.status() >= 400)
      errors.push(`${r.status()} ${r.url()}`);
  });
  await page.route(/^https:/, (r) => r.abort());
  for (const [lang, width] of [
    ['en', 1440],
    ['ru', 390],
    ['cs', 320],
    ['cs', 1440],
    ['de', 320],
    ['de', 360],
    ['hi', 390],
    ['zh-Hans', 390],
    ['zh-Hant', 390],
    ['ko', 390]
  ]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const section of [
      '',
      'install/',
      'editions/',
      'compatibility/',
      'help/'
    ]) {
      await page.goto(host + base + lang + '/' + section);
      if (lang === 'de')
        await page.addStyleTag({
          content:
            ':root { font-family: Verdana, sans-serif; --font-body: Verdana, sans-serif; --font-display: Verdana, sans-serif; }'
        });
      await page.locator('img').first().waitFor({ state: 'visible' });
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1
        ),
        `${lang}/${section} horizontal overflow at ${width}: ${JSON.stringify(await page.locator('body *').evaluateAll((nodes) => nodes.filter((n) => n.getBoundingClientRect().right > innerWidth + 1).map((n) => ({ tag: n.tagName, class: n.className, text: n.textContent?.slice(0, 80), width: n.getBoundingClientRect().width }))))}`
      );
      if (section === 'editions/' || section === 'compatibility/') {
        const table = page.locator('.comparison-scroll');
        if (await table.evaluate((n) => n.scrollWidth > n.clientWidth)) {
          await table.focus();
          await page.keyboard.press('ArrowRight');
          await page.waitForFunction(
            () => document.querySelector('.comparison-scroll').scrollLeft > 0
          );
          await table.evaluate((n) => (n.scrollLeft = 0));
        }
      }
      // Load below-the-fold lazy images before judging resources or full-page QA.
      for (const img of await page.locator('img').all()) {
        if (await img.isVisible()) await img.scrollIntoViewIfNeeded();
        await img.evaluate((image) => image.decode());
      }
      await page.evaluate(() => scrollTo(0, 0));
      if (shots && (!section || lang === 'ru'))
        await page.screenshot({
          path: resolve(
            shots,
            `${lang}-${section ? section.replace('/', '') : 'home'}-${width}.png`
          ),
          fullPage: true
        });
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(host + base + '#root');
  await page.waitForURL('**/demo/#root');
  const frame = page.frameLocator('#screen');
  await frame.locator('#tiles .focused').waitFor();
  assert.equal(
    await page.locator('#screen').getAttribute('src'),
    'root-launcher/index.html'
  );
  for (const edition of ['No-root Edition', 'Root Edition']) {
    await page.getByRole('button', { name: edition, exact: true }).click();
    await frame.locator('#tiles .focused').waitFor();
    await page.locator('#previewThemes[aria-busy="false"]').waitFor();
    assert.equal(
      await frame
        .locator('#tiles .item[data-app-id]')
        .first()
        .getAttribute('data-app-id'),
      'com.beb.plxnative'
    );
    const cards = page.locator('#previewThemes img');
    await cards.last().waitFor({ state: 'attached' });
    await page.waitForFunction(() =>
      [...document.querySelectorAll('#previewThemes img')].every(
        (card) =>
          card.src.includes('/preview/theme-cards/') && card.naturalWidth > 0
      )
    );
    await page
      .getByRole('button', { name: 'Liquid Glass', exact: true })
      .click();
    await page.waitForFunction(
      () =>
        document.getElementById('screen').contentWindow.ThemeManager?.current()
          .title === 'Liquid Glass'
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    'PASS browser language selection; remembered manual choice; explicit locale URLs; blocked storage; 143 localized pages without JavaScript; article desktop/mobile layouts and topic-preserving translations; keyboard navigation; help deep links; mobile tables/layouts; legacy fragment routing; offline Root/No-root theme demo'
  );
} finally {
  await browser?.close();
  await new Promise((r) => server.close(r));
}
