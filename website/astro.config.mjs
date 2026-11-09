import { defineConfig } from 'astro/config';
import { unified } from '@astrojs/markdown-remark';
const base = '/clean-your-tv-lg-webos/';
// Source-guide URLs remain useful on GitHub; rewrite only the website rendering.
function documentationLinks() {
  return function walk(node) {
    if (node.type === 'link' || node.type === 'image') {
      const url = node.url;
      if (url && !/^(?:[a-z][a-z\d+.-]*:|\/|#)/i.test(url)) {
        const target = new URL(
          url,
          'https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/i18n/'
        );
        const match = target.pathname.match(
          /\/docs\/i18n\/(en|de|es|pt-BR|fr|it|ko|hi|pl|ru|cs|zh-Hans|zh-Hant)\.md$/
        );
        const downloadImage =
          node.type === 'image' &&
          target.pathname.match(
            /\/assets\/brand\/downloads\/(windows|macos-arm64|macos-x64|linux|android)\.svg$/
          );
        node.url = downloadImage
          ? base + 'assets/downloads/' + downloadImage[1] + '.svg'
          : match
            ? base + match[1] + '/install/' + target.hash
            : target.href;
      }
    }
    node.children?.forEach(walk);
  };
}
export default defineConfig({
  site: 'https://razdva122.github.io',
  base,
  trailingSlash: 'always',
  output: 'static',
  markdown: { processor: unified({ remarkPlugins: [documentationLinks] }) },
  i18n: {
    defaultLocale: 'en',
    locales: [
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
    ],
    routing: { prefixDefaultLocale: true }
  },
  vite: {
    server: { fs: { allow: ['..'] } },
    plugins: [
      {
        name: 'demo-directory-index',
        configureServer(server) {
          // Astro serves public files verbatim, but does not resolve public directory indexes.
          // GitHub Pages does; keep the existing clean demo URL identical in local preview.
          server.middlewares.use((request, _response, next) => {
            const pathname = request.url?.split('?')[0];
            if (pathname === base + 'demo/' || pathname === '/demo/') {
              request.url = request.url.replace('/demo/', '/demo/index.html');
            }
            next();
          });
        }
      }
    ]
  }
});
