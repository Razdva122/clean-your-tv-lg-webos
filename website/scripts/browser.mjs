import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync, mkdirSync } from "node:fs";
import { resolve, extname, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(new URL("../../package.json", import.meta.url));
const { chromium } = require("playwright");
const dist = fileURLToPath(new URL("../dist/", import.meta.url));
const base = "/clean-your-tv-lg-webos/";
const server = createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (!url.pathname.startsWith(base)) {
    res.writeHead(404).end();
    return;
  }
  let file = resolve(dist, decodeURIComponent(url.pathname.slice(base.length)));
  if (file !== resolve(dist) && !file.startsWith(resolve(dist) + sep)) {
    res.writeHead(404).end();
    return;
  }
  if (existsSync(file) && statSync(file).isDirectory()) file += "/index.html";
  if (!existsSync(file)) {
    res.writeHead(404).end();
    return;
  }
  res.setHeader(
    "Content-Type",
    {
      ".css": "text/css",
      ".js": "application/javascript",
      ".json": "application/json",
      ".svg": "image/svg+xml",
      ".jpg": "image/jpeg",
      ".png": "image/png",
      ".ttf": "font/ttf",
      ".xml": "application/xml",
    }[extname(file)] || "text/html",
  );
  res.end(readFileSync(file));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const host = "http://127.0.0.1:" + server.address().port;
const browser = await chromium.launch({
  headless: true,
  channel: process.env.BROWSER_CHANNEL || "chrome",
});
const errors = [];
const shots = process.env.WEBSITE_SCREENSHOTS;
if (shots) mkdirSync(shots, { recursive: true });
try {
  // Crawlable content and navigation must work with JavaScript disabled.
  const staticPage = await browser.newPage({
    javaScriptEnabled: false,
    viewport: { width: 1440, height: 1000 },
  });
  for (const lang of [
    "en",
    "de",
    "es",
    "pt-BR",
    "fr",
    "it",
    "ko",
    "hi",
    "pl",
    "ru",
    "zh-Hans",
    "zh-Hant",
  ]) {
    for (const section of [
      "",
      "install/",
      "editions/",
      "compatibility/",
      "themes/",
    ]) {
      const response = await staticPage.goto(
        host + base + lang + "/" + section,
      );
      assert.equal(response.status(), 200);
      assert.equal(await staticPage.locator("h1").count(), 1);
      await staticPage.locator("h1").waitFor({ state: "visible" });
    }
  }
  await staticPage.goto(host + base + "ru/install/");
  await staticPage.locator(".languages summary").focus();
  await staticPage.keyboard.press("Enter");
  await staticPage.locator('.languages a[hreflang="de"]').click();
  assert.equal(new URL(staticPage.url()).pathname, base + "de/install/");
  await staticPage.close();
  const page = await browser.newPage();
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("response", (r) => {
    if (r.url().startsWith(host) && r.status() >= 400)
      errors.push(`${r.status()} ${r.url()}`);
  });
  await page.route(/^https:/, (r) => r.abort());
  for (const [lang, width] of [
    ["en", 1440],
    ["ru", 390],
    ["de", 360],
    ["hi", 390],
    ["zh-Hans", 390],
    ["zh-Hant", 390],
    ["ko", 390],
  ]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const section of ["", "install/"]) {
      await page.goto(host + base + lang + "/" + section);
      await page.locator("img").first().waitFor({ state: "visible" });
      assert(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
        `${lang}/${section} horizontal overflow at ${width}`,
      );
      // Load below-the-fold lazy images before judging resources or full-page QA.
      for (const img of await page.locator("img").all()) {
        await img.scrollIntoViewIfNeeded();
        await img.evaluate((image) => image.decode());
      }
      await page.evaluate(() => scrollTo(0, 0));
      if (shots && (!section || lang === "ru"))
        await page.screenshot({
          path: resolve(
            shots,
            `${lang}-${section ? "install" : "home"}-${width}.png`,
          ),
          fullPage: true,
        });
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(host + base + "#root");
  await page.waitForURL("**/demo/#root");
  const frame = page.frameLocator("#screen");
  await frame.locator("#tiles .focused").waitFor();
  assert.equal(
    await page.locator("#screen").getAttribute("src"),
    "root-launcher/index.html",
  );
  for (const edition of ["No-root Edition", "Root Edition"]) {
    await page.getByRole("button", { name: edition, exact: true }).click();
    await frame.locator("#tiles .focused").waitFor();
    await page.locator('#previewThemes[aria-busy="false"]').waitFor();
    await page.getByRole("button", { name: "Alpine", exact: true }).click();
    await page.waitForFunction(
      () =>
        document.getElementById("screen").contentWindow.ThemeManager?.current()
          .title === "Alpine",
    );
  }
  assert.deepEqual(errors, []);
  console.log(
    "PASS 60 pages without JavaScript; keyboard language switching; mobile layouts; legacy fragment routing; offline Root/No-root theme demo",
  );
} finally {
  await browser.close();
  await new Promise((r) => server.close(r));
}
