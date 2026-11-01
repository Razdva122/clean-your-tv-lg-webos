import { defineConfig } from "astro/config";
import { unified } from "@astrojs/markdown-remark";
const base = "/clean-your-tv-lg-webos/";
// Source-guide URLs remain useful on GitHub; rewrite only the website rendering.
function documentationLinks() {
  return function walk(node) {
    if (node.type === "link" || node.type === "image") {
      const url = node.url;
      if (url && !/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(url)) {
        const target = new URL(
          url,
          "https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/i18n/",
        );
        const match = target.pathname.match(
          /\/docs\/i18n\/(en|de|es|pt-BR|fr|it|ko|hi|pl|ru|zh-Hans|zh-Hant)\.md$/,
        );
        node.url = match
          ? base + match[1] + "/install/" + target.hash
          : target.href;
      }
    }
    node.children?.forEach(walk);
  };
}
export default defineConfig({
  site: "https://razdva122.github.io",
  base,
  trailingSlash: "always",
  output: "static",
  markdown: { processor: unified({ remarkPlugins: [documentationLinks] }) },
  i18n: {
    defaultLocale: "en",
    locales: [
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
    ],
    routing: { prefixDefaultLocale: true },
  },
  vite: { server: { fs: { allow: [".."] } } },
});
