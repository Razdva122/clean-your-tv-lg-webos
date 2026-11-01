import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { parse } from "../../node_modules/parse5/dist/index.js";
const root = fileURLToPath(new URL("../dist/", import.meta.url));
const base = "https://razdva122.github.io/clean-your-tv-lg-webos/";
const locales = [
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
];
const pages = ["", "install/", "editions/", "compatibility/", "themes/"];
function nodes(node) {
  return [node, ...(node.childNodes || []).flatMap(nodes)];
}
function attr(node, key) {
  return node.attrs?.find((a) => a.name === key)?.value;
}
assert(
  existsSync(root + "sitemap.xml"),
  "multilingual site must export a sitemap",
);
const translations = JSON.parse(
  readFileSync(new URL("../src/lib/locales.json", import.meta.url), "utf8"),
);
assert.deepEqual(
  Object.keys(translations).sort(),
  [...locales].sort(),
  "locale registry",
);
for (const [lang, copy] of Object.entries(translations)) {
  assert.deepEqual(
    Object.keys(copy).sort(),
    Object.keys(translations.en).sort(),
    lang + " missing translation keys",
  );
  for (const value of Object.values(copy))
    for (const text of Array.isArray(value) ? value : [value])
      assert(
        typeof text === "string" && text.trim().length,
        lang + " empty translation",
      );
  assert.equal(copy.nav.length, pages.length, lang + " navigation");
  assert.equal(copy.features.length, 3, lang + " features");
}
const sitemap = readFileSync(root + "sitemap.xml", "utf8");
for (const lang of locales)
  for (const page of pages) {
    const route = lang + "/" + page,
      html = readFileSync(root + route + "index.html", "utf8"),
      all = nodes(parse(html));
    assert.equal(
      attr(
        all.find((n) => n.tagName === "html"),
        "lang",
      ),
      lang,
      route,
    );
    assert.equal(
      all.filter((n) => n.tagName === "h1").length,
      1,
      route + " must have one H1",
    );
    const title = all.find((n) => n.tagName === "title");
    assert(title?.childNodes[0]?.value.length > 10, route + " title");
    assert(
      attr(
        all.find(
          (n) => n.tagName === "meta" && attr(n, "name") === "description",
        ),
        "content",
      )?.length > 30,
      route + " description",
    );
    assert.equal(
      attr(
        all.find((n) => n.tagName === "link" && attr(n, "rel") === "canonical"),
        "href",
      ),
      base + route,
    );
    const alts = all.filter(
      (n) => n.tagName === "link" && attr(n, "rel") === "alternate",
    );
    for (const other of locales)
      assert(
        alts.some(
          (n) =>
            attr(n, "hreflang") === other &&
            attr(n, "href") === base + other + "/" + page,
        ),
        route + " alternate " + other,
      );
    const switches = all.filter(
      (n) => n.tagName === "a" && attr(n, "hreflang"),
    );
    for (const other of locales)
      assert(
        switches.some(
          (n) =>
            attr(n, "hreflang") === other &&
            new URL(attr(n, "href"), base + route).href ===
              base + other + "/" + page,
        ),
        route + " language switch " + other,
      );
    assert(
      sitemap.includes("<loc>" + base + route + "</loc>"),
      route + " in sitemap",
    );
    for (const n of all)
      for (const key of ["src", "href"]) {
        const value = attr(n, key);
        if (!value || /^(data:|mailto:|#)/.test(value)) continue;
        const url = new URL(value, base + route);
        if (!url.href.startsWith(base)) continue;
        let path = decodeURIComponent(
          url.pathname.slice(new URL(base).pathname.length),
        );
        if (path.endsWith("/")) path += "index.html";
        assert(existsSync(root + path), route + " broken " + value);
        if (url.hash && path.endsWith(".html")) {
          const ids = nodes(parse(readFileSync(root + path, "utf8"))).map((n) =>
            attr(n, "id"),
          );
          assert(
            ids.includes(decodeURIComponent(url.hash.slice(1))),
            route + " missing anchor " + value,
          );
        }
      }
    assert(!html.includes("__LIVE_RELOAD__"), route);
  }
for (const file of [
  "index.html",
  "launcher/index.html",
  "root-launcher/index.html",
  "preview/themes.json",
])
  assert(existsSync(root + "demo/" + file), "missing demo " + file);
assert(
  readFileSync(root + "demo/index.html", "utf8").includes(
    "launcher/index.html",
  ),
);
assert(
  readFileSync(root + "index.html", "utf8").includes("demo/"),
  "legacy demo entry",
);
assert(!sitemap.includes("/demo/"), "demo is not a content landing page");
assert(!sitemap.includes("/launcher/"));
console.log(
  `PASS ${locales.length * pages.length} localized pages: metadata, alternates, navigation, sitemap, local resources and preserved demo`,
);
