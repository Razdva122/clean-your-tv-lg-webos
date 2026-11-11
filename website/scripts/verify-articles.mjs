import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parse } from '../../node_modules/parse5/dist/index.js';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const base = 'https://razdva122.github.io/clean-your-tv-lg-webos/';
const locales = [
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
const topics = [
  'change-lg-webos-home-screen',
  'lg-tv-home-screen-ads',
  'root-vs-no-root',
  'lg-developer-mode'
];
const nodes = (node) => [node, ...(node.childNodes || []).flatMap(nodes)];
const attr = (node, key) => node.attrs?.find((a) => a.name === key)?.value;
const text = (node) =>
  nodes(node)
    .filter((n) => n.nodeName === '#text')
    .map((n) => n.value)
    .join('');
const sitemap = readFileSync(dist + 'sitemap.xml', 'utf8');
const sitemapNodes = nodes(parse(sitemap));
const locations = sitemapNodes.filter((n) => n.tagName === 'loc').map(text);
assert.equal(new Set(locations).size, locations.length, 'unique sitemap URLs');
const titles = new Set();
const descriptions = new Set();
for (const lang of locales) {
  for (const topic of ['', ...topics]) {
    const path = `${lang}/articles/${topic ? topic + '/' : ''}`;
    assert(
      existsSync(dist + path + 'index.html'),
      'missing article route ' + path
    );
    const all = nodes(parse(readFileSync(dist + path + 'index.html', 'utf8')));
    const canonical = base + path;
    assert.equal(
      attr(
        all.find((n) => n.tagName === 'html'),
        'lang'
      ),
      lang
    );
    const h1 = all.filter((n) => n.tagName === 'h1');
    assert.equal(h1.length, 1, path + ' single H1');
    const title = text(all.find((n) => n.tagName === 'title'));
    assert(title.includes(text(h1[0])), path + ' article-specific title');
    assert(!titles.has(title), path + ' unique title');
    titles.add(title);
    const description = attr(
      all.find(
        (n) => n.tagName === 'meta' && attr(n, 'name') === 'description'
      ),
      'content'
    );
    assert(description?.length > 30, path + ' description');
    assert(!descriptions.has(description), path + ' unique description');
    descriptions.add(description);
    assert.equal(
      attr(
        all.find((n) => n.tagName === 'link' && attr(n, 'rel') === 'canonical'),
        'href'
      ),
      canonical
    );
    assert.equal(
      attr(
        all.find(
          (n) => n.tagName === 'meta' && attr(n, 'property') === 'og:url'
        ),
        'content'
      ),
      canonical
    );
    assert(
      !all.some(
        (n) =>
          n.tagName === 'meta' &&
          attr(n, 'name') === 'robots' &&
          /noindex|nosnippet/.test(attr(n, 'content'))
      ),
      path + ' indexable'
    );
    assert(locations.includes(canonical), path + ' in sitemap');
    for (const other of locales) {
      const href = `${base}${other}/articles/${topic ? topic + '/' : ''}`;
      assert(
        all.some(
          (n) =>
            n.tagName === 'link' &&
            attr(n, 'hreflang') === other &&
            attr(n, 'href') === href
        ),
        path + ' alternate ' + other
      );
      assert(
        all.some(
          (n) =>
            n.tagName === 'a' &&
            attr(n, 'hreflang') === other &&
            new URL(attr(n, 'href'), base).href === href
        ),
        path + ' language switch retains topic ' + other
      );
      assert(
        sitemap.includes(`hreflang="${other}" href="${href}"`),
        path + ' sitemap alternate ' + other
      );
    }
    assert(
      all.some(
        (n) =>
          n.tagName === 'link' &&
          attr(n, 'hreflang') === 'x-default' &&
          attr(n, 'href') === `${base}en/articles/${topic ? topic + '/' : ''}`
      ),
      path + ' default alternate'
    );
    const graph = all
      .filter(
        (n) =>
          n.tagName === 'script' && attr(n, 'type') === 'application/ld+json'
      )
      .flatMap((n) => JSON.parse(text(n))['@graph']);
    const breadcrumb = graph.find((n) => n['@type'] === 'BreadcrumbList');
    assert(breadcrumb, path + ' breadcrumb schema');
    const crumbs = all.find(
      (n) => n.tagName === 'nav' && attr(n, 'class') === 'breadcrumbs'
    );
    assert(crumbs, path + ' visible breadcrumbs');
    assert.deepEqual(
      breadcrumb.itemListElement.map((n) => n.name),
      nodes(crumbs)
        .filter((n) => n.tagName === 'li')
        .map(text)
    );
    assert.equal(breadcrumb.itemListElement.at(-1).item, canonical);
    if (topic) {
      const article = graph.find((n) => n['@type'] === 'Article');
      assert(article, path + ' Article schema');
      assert.equal(article.headline, text(h1[0]));
      assert.equal(article.description, description);
      assert.equal(article.inLanguage, lang);
      assert.equal(article.mainEntityOfPage, canonical);
      assert.equal(
        attr(
          all.find(
            (n) => n.tagName === 'meta' && attr(n, 'property') === 'og:type'
          ),
          'content'
        ),
        'article'
      );
      assert.equal(
        attr(
          all.find((n) => n.tagName === 'time'),
          'datetime'
        ),
        article.dateModified
      );
      assert.equal(article.author.name, 'Clean Your TV');
      assert(
        all.some(
          (n) =>
            n.tagName === 'a' &&
            attr(n, 'href') === article.author.url &&
            text(n) === article.author.name
        ),
        path + ' visible project attribution'
      );
      const articleNode = all.find((n) => n.tagName === 'article');
      assert(
        nodes(articleNode).filter((n) => n.tagName === 'h2').length >= 4,
        path + ' full article sections'
      );
      assert(
        nodes(articleNode).some(
          (n) => n.tagName === 'a' && attr(n, 'href')?.startsWith('https://')
        ),
        path + ' source links'
      );
    } else {
      for (const slug of topics)
        assert(
          all.some(
            (n) =>
              n.tagName === 'a' &&
              new URL(attr(n, 'href'), base).href === canonical + slug + '/'
          ),
          path + ' links to ' + slug
        );
    }
    for (const n of all.filter(
      (n) => n.tagName === 'a' || n.tagName === 'link'
    )) {
      const href = attr(n, 'href');
      if (!href) continue;
      const url = new URL(href, canonical);
      if (!url.href.startsWith(base)) continue;
      let target = decodeURIComponent(
        url.pathname.slice(new URL(base).pathname.length)
      );
      if (target.endsWith('/')) target += 'index.html';
      assert(existsSync(dist + target), path + ' broken link ' + href);
      if (url.hash && target.endsWith('.html'))
        assert(
          nodes(parse(readFileSync(dist + target, 'utf8'))).some(
            (node) => attr(node, 'id') === decodeURIComponent(url.hash.slice(1))
          ),
          path + ' broken anchor ' + href
        );
    }
  }
  const home = nodes(parse(readFileSync(dist + lang + '/index.html', 'utf8')));
  assert(
    home.some(
      (n) =>
        n.tagName === 'a' &&
        new URL(attr(n, 'href'), base).href === base + lang + '/articles/'
    ),
    lang + ' articles discoverable from home'
  );
}
console.log(
  'PASS 52 articles and 13 indexes: rendered content, unique metadata, reciprocal language routes, schema, sitemap and links'
);
