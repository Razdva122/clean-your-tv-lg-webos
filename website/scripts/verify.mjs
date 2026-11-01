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
const pages = [
  "",
  "install/",
  "editions/",
  "compatibility/",
  "themes/",
  "help/",
];
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
const support = JSON.parse(
  readFileSync(new URL("../src/lib/support.json", import.meta.url), "utf8"),
);
assert.deepEqual(
  Object.keys(support).sort(),
  [...locales].sort(),
  "support locale registry",
);
function translated(value, reference, label) {
  if (typeof reference === "string") {
    assert(
      typeof value === "string" && value.trim().length,
      label + " empty translation",
    );
  } else if (Array.isArray(reference)) {
    assert(Array.isArray(value), label + " must be an array");
    assert.equal(
      value.length,
      reference.length,
      label + " missing translated entries",
    );
    reference.forEach((item, index) =>
      translated(value[index], item, label + "[" + index + "]"),
    );
  } else {
    assert(
      value && typeof value === "object" && !Array.isArray(value),
      label + " must be an object",
    );
    assert.deepEqual(
      Object.keys(value).sort(),
      Object.keys(reference).sort(),
      label + " missing translation keys",
    );
    for (const key of Object.keys(reference))
      translated(value[key], reference[key], label + "." + key);
  }
}
for (const lang of locales) {
  translated(translations[lang], translations.en, lang);
  translated(support[lang], support.en, lang + " support");
  assert.equal(
    translations[lang].nav.length,
    pages.length,
    lang + " navigation",
  );
  assert.equal(translations[lang].features.length, 3, lang + " features");
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
    if (page === "help/") {
      for (const n of all.filter((n) => n.tagName === "a")) {
        const href = attr(n, "href");
        const prefix =
          "https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/";
        if (href?.startsWith(prefix)) {
          const source = href.slice(prefix.length).split("#")[0];
          assert(
            existsSync(
              fileURLToPath(new URL("../../" + source, import.meta.url)),
            ),
            route + " missing source reference " + source,
          );
        }
      }
    }
    for (const n of all)
      for (const key of ["src", "href"]) {
        const value = attr(n, key);
        if (!value || /^(data:|mailto:)/.test(value)) continue;
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
    if (page === "help/") {
      for (const id of [
        "connection",
        "developer-mode",
        "home-button",
        "interrupted",
        "update-remove",
      ]) {
        assert(
          all.some((n) => n.tagName === "section" && attr(n, "id") === id),
          route + " missing help topic " + id,
        );
      }
    }
    if (page === "editions/" || page === "compatibility/") {
      const table = all.find((n) => n.tagName === "table");
      assert(table, route + " needs a requirements/comparison table");
      assert(
        nodes(table).some((n) => n.tagName === "caption"),
        route + " table caption",
      );
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
