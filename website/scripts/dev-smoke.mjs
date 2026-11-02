import assert from "node:assert/strict";
import { dev } from "astro";
import { createRequire } from "node:module";
const require = createRequire(new URL("../../package.json", import.meta.url));
const { chromium } = require("playwright");
const server = await dev({
  root: new URL("../", import.meta.url),
  server: { host: "127.0.0.1", port: 0 },
  logLevel: "error",
});
let browser;
try {
  const address = `http://127.0.0.1:${server.address.port}/clean-your-tv-lg-webos/demo/`;
  const response = await fetch(address);
  assert.equal(
    response.status,
    200,
    "Astro dev must serve the same /demo/ URL linked by the website",
  );
  browser = await chromium.launch({
    headless: true,
    channel: process.env.BROWSER_CHANNEL || "chrome",
  });
  const page = await browser.newPage();
  await page.goto(address);
  await page.frameLocator("#screen").locator("#tiles .focused").waitFor();
  for (const edition of ["Root Edition", "No-root Edition"]) {
    await page.getByRole("button", { name: edition, exact: true }).click();
    await page.locator('#previewThemes[aria-busy="false"]').waitFor();
    await page.getByRole("button", { name: "Liquid Glass", exact: true }).click();
    await page.waitForFunction(
      () =>
        document.getElementById("screen").contentWindow.ThemeManager?.current()
          .title === "Liquid Glass",
    );
  }
  console.log(
    "PASS real Astro dev /demo/ route, both editions and inline themes",
  );
} finally {
  await browser?.close();
  await server.stop();
}
