import assert from 'node:assert/strict';
import './verify-articles.mjs';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parse } from '../../node_modules/parse5/dist/index.js';
import { updateReadmeCompatibility } from './update-readme-compatibility.mjs';
import { webosCategory } from '../src/lib/webos.mjs';
const root = fileURLToPath(new URL('../dist/', import.meta.url));
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
const pages = [
  '',
  'install/',
  'editions/',
  'compatibility/',
  'themes/',
  'help/'
];
function nodes(node) {
  return [node, ...(node.childNodes || []).flatMap(nodes)];
}
function attr(node, key) {
  return node.attrs?.find((a) => a.name === key)?.value;
}
const translations = JSON.parse(
  readFileSync(new URL('../src/lib/locales.json', import.meta.url), 'utf8')
);
assert.deepEqual(
  Object.keys(translations).sort(),
  [...locales].sort(),
  'locale registry'
);
const support = JSON.parse(
  readFileSync(new URL('../src/lib/support.json', import.meta.url), 'utf8')
);
assert.deepEqual(
  Object.keys(support).sort(),
  [...locales].sort(),
  'support locale registry'
);
const reports = JSON.parse(
  readFileSync(
    new URL('../../docs/compatibility-reports.json', import.meta.url),
    'utf8'
  )
).reports;
const visibleReports = reports.filter(
  (report) => report.showOnWebsite === true
);
const readme = readFileSync(
  new URL('../../README.md', import.meta.url),
  'utf8'
);
const conflictingVersion = '25; SDK 11.2.0';
for (const [reported, expected] of [
  [conflictingVersion, '26'],
  ['SDK 11.2.0', '26'],
  ['25; SDK99.0.0', '25'],
  ['4.5', '4.5-5'],
  [null, 'unknown']
]) {
  assert.equal(
    webosCategory(reported),
    expected,
    `webOS group for ${reported}`
  );
}
const fixtureReadme = updateReadmeCompatibility(readme, [
  {
    model: 'Fixture model',
    webos: conflictingVersion,
    edition: 'no-root',
    showOnWebsite: true
  }
]);
assert.match(
  fixtureReadme,
  /<summary>❔ webOS 26<\/summary>[^<]*\| Fixture model · No-root \| 25; SDK 11\.2\.0 \|/
);
assert(
  readme === updateReadmeCompatibility(readme, reports),
  'README compatibility block is stale. Run node website/scripts/update-readme-compatibility.mjs'
);
const compatibilityDoc = readFileSync(
  new URL('../../docs/COMPATIBILITY.md', import.meta.url),
  'utf8'
);
const reportBlock = compatibilityDoc.match(
  /<!-- compatibility-reports:start -->([\s\S]*?)<!-- compatibility-reports:end -->/
)?.[1];
assert(reportBlock, 'compatibility documentation report block');
const reportLines = reportBlock
  .split('\n')
  .filter((line) => line.startsWith('- '));
assert.equal(
  reportLines.length,
  visibleReports.length,
  'compatibility documentation model count'
);
for (const report of visibleReports) {
  const versions = [report.firmware, report.webos, report.release].filter(
    Boolean
  );
  assert(
    reportLines.some(
      (line) =>
        line.startsWith('- ' + report.model + ' —') &&
        versions.every((version) => line.includes(version))
    ),
    'compatibility documentation missing report ' + report.id
  );
}
function translated(value, reference, label) {
  if (typeof reference === 'string') {
    assert(
      typeof value === 'string' && value.trim().length,
      label + ' empty translation'
    );
  } else if (Array.isArray(reference)) {
    assert(Array.isArray(value), label + ' must be an array');
    assert.equal(
      value.length,
      reference.length,
      label + ' missing translated entries'
    );
    reference.forEach((item, index) =>
      translated(value[index], item, label + '[' + index + ']')
    );
  } else {
    assert(
      value && typeof value === 'object' && !Array.isArray(value),
      label + ' must be an object'
    );
    assert.deepEqual(
      Object.keys(value).sort(),
      Object.keys(reference).sort(),
      label + ' missing translation keys'
    );
    for (const key of Object.keys(reference))
      translated(value[key], reference[key], label + '.' + key);
  }
}
for (const lang of locales) {
  translated(translations[lang], translations.en, lang);
  translated(support[lang], support.en, lang + ' support');
  assert(
    support[lang].reportsTitle?.trim(),
    lang + ' missing device reports heading'
  );
  assert(
    support[lang].reportResults.partial?.trim(),
    lang + ' missing limited-operation result label'
  );
  assert.equal(
    translations[lang].nav.length,
    pages.length,
    lang + ' navigation'
  );
  assert.equal(translations[lang].features.length, 3, lang + ' features');
}
assert(
  existsSync(root + 'sitemap.xml'),
  'multilingual site must export a sitemap'
);
const sitemap = readFileSync(root + 'sitemap.xml', 'utf8');
for (const lang of locales)
  for (const page of pages) {
    const route = lang + '/' + page,
      html = readFileSync(root + route + 'index.html', 'utf8'),
      all = nodes(parse(html));
    assert.equal(
      attr(
        all.find((n) => n.tagName === 'html'),
        'lang'
      ),
      lang,
      route
    );
    assert.equal(
      all.filter((n) => n.tagName === 'h1').length,
      1,
      route + ' must have one H1'
    );
    const title = all.find((n) => n.tagName === 'title');
    assert(title?.childNodes[0]?.value.length > 10, route + ' title');
    assert(
      attr(
        all.find(
          (n) => n.tagName === 'meta' && attr(n, 'name') === 'description'
        ),
        'content'
      )?.length > 30,
      route + ' description'
    );
    assert.equal(
      attr(
        all.find((n) => n.tagName === 'link' && attr(n, 'rel') === 'canonical'),
        'href'
      ),
      base + route
    );
    const alts = all.filter(
      (n) => n.tagName === 'link' && attr(n, 'rel') === 'alternate'
    );
    for (const other of locales)
      assert(
        alts.some(
          (n) =>
            attr(n, 'hreflang') === other &&
            attr(n, 'href') === base + other + '/' + page
        ),
        route + ' alternate ' + other
      );
    const switches = all.filter(
      (n) => n.tagName === 'a' && attr(n, 'hreflang')
    );
    for (const other of locales)
      assert(
        switches.some(
          (n) =>
            attr(n, 'hreflang') === other &&
            new URL(attr(n, 'href'), base + route).href ===
              base + other + '/' + page
        ),
        route + ' language switch ' + other
      );
    assert(
      sitemap.includes('<loc>' + base + route + '</loc>'),
      route + ' in sitemap'
    );
    if (page === 'install/') {
      assert(
        !all.some((n) => attr(n, 'class')?.split(' ').includes('notice')),
        route + ' starts with the installation guide'
      );
      for (const name of [
        'windows',
        'macos-arm64',
        'macos-x64',
        'linux',
        'android'
      ]) {
        const expected = new URL('assets/downloads/' + name + '.svg', base)
          .pathname;
        assert(
          all.some((n) => n.tagName === 'img' && attr(n, 'src') === expected),
          route + ' local download button ' + name
        );
        assert(
          readFileSync(
            root + 'assets/downloads/' + name + '.svg',
            'utf8'
          ).includes('<svg'),
          route + ' SVG download asset ' + name
        );
      }
    }
    if (page === 'help/') {
      for (const n of all.filter((n) => n.tagName === 'a')) {
        const href = attr(n, 'href');
        const prefix =
          'https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/';
        if (href?.startsWith(prefix)) {
          const source = href.slice(prefix.length).split('#')[0];
          assert(
            existsSync(
              fileURLToPath(new URL('../../' + source, import.meta.url))
            ),
            route + ' missing source reference ' + source
          );
        }
      }
    }
    for (const n of all)
      for (const key of ['src', 'href']) {
        const value = attr(n, key);
        if (!value || /^(data:|mailto:)/.test(value)) continue;
        const url = new URL(value, base + route);
        if (!url.href.startsWith(base)) continue;
        let path = decodeURIComponent(
          url.pathname.slice(new URL(base).pathname.length)
        );
        if (path.endsWith('/')) path += 'index.html';
        assert(existsSync(root + path), route + ' broken ' + value);
        if (url.hash && path.endsWith('.html')) {
          const ids = nodes(parse(readFileSync(root + path, 'utf8'))).map((n) =>
            attr(n, 'id')
          );
          assert(
            ids.includes(decodeURIComponent(url.hash.slice(1))),
            route + ' missing anchor ' + value
          );
        }
      }
    if (page === 'help/') {
      for (const id of [
        'connection',
        'developer-mode',
        'home-button',
        'interrupted',
        'update-remove'
      ]) {
        assert(
          all.some((n) => n.tagName === 'section' && attr(n, 'id') === id),
          route + ' missing help topic ' + id
        );
      }
    }
    if (page === 'compatibility/') {
      const list = all.find(
        (n) => attr(n, 'class') === 'compatibility-reports'
      );
      assert.equal(
        Boolean(list),
        visibleReports.length > 0,
        route + ' device list visibility'
      );
      if (list) {
        const items = nodes(list).filter((n) => attr(n, 'data-report-id'));
        for (const [groupId, expectedReports] of [
          ['reported-series-c1', ['c1-65-root-issue418', 'c1-77-c12la-noroot']],
          ['reported-series-c2', ['c2-42-noroot', 'c2-reddit-noroot']],
          [
            'reported-series-c3',
            ['c3-65-noroot', 'c3-maintainer-root', 'c3-reddit-noroot']
          ],
          [
            'reported-series-nanocell',
            ['50nano756pa-noroot', 'nano80asa-noroot', '55nano81ana-noroot']
          ],
          ['reported-series-qned', ['qned75ura-noroot', '65qned80sra-noroot']],
          [
            'reported-series-um-un',
            ['43um7600plb-noroot', 'um7450pla-noroot', 'un7000-noroot']
          ],
          ['reported-series-uj-uk', ['49uj750v-noroot', 'uk6400plf-noroot']],
          [
            'reported-series-up-uq-ur',
            ['55up7000pua-noroot', 'uq7500-43-noroot', 'ur9100-noroot']
          ],
          ['reported-series-lb-lm', ['lb650v-32-noroot', 'lm6370psb-noroot']],
          ['reported-webos-3', ['49uj750v-noroot', 'uj6050-60-noroot']],
          ['reported-webos-4', ['sk8100-noroot']],
          ['reported-webos-4.5-5', ['um7450pla-noroot', '55um7450pla-noroot']],
          [
            'reported-webos-25',
            [
              'b3-noroot',
              'c2-42-noroot',
              'c2-reddit-noroot',
              'nano80asa-noroot'
            ]
          ],
          [
            'reported-webos-26',
            ['g3-83-noroot', 'c3-maintainer-root', 'c3-reddit-noroot']
          ]
        ]) {
          const group = all.find((n) => attr(n, 'id') === groupId);
          assert(group, route + ' missing compatibility group ' + groupId);
          const content = nodes(group);
          const details = group.parentNode;
          assert.equal(
            details.tagName,
            'details',
            route + ' disclosure ' + groupId
          );
          assert.equal(
            attr(details, 'open'),
            undefined,
            route + ' initially collapsed ' + groupId
          );
          const summary = details.childNodes.find(
            (n) => n.tagName === 'summary'
          );
          const count =
            summary &&
            nodes(summary).find((n) => attr(n, 'class') === 'group-count');
          assert(count, route + ' missing model count ' + groupId);
          const ids = new Set(content.map((n) => attr(n, 'data-report-id')));
          const links = new Set(content.map((n) => attr(n, 'href')));
          const groupReports = visibleReports.filter(
            ({ id }) => ids.has(id) || links.has('#reported-tv-' + id)
          );
          assert.equal(
            attr(details.parentNode, 'class')
              ?.split(/\s+/)
              .includes('confirmed'),
            groupReports.some(({ result }) => result === 'controls-tested'),
            route + ' group confirmation styling ' + groupId
          );
          const models = new Set(groupReports.map(({ model }) => model));
          assert(
            nodes(count).some(
              (n) =>
                n.value?.trim() ===
                new Intl.NumberFormat(lang).format(models.size)
            ),
            route + ' incorrect model count ' + groupId
          );
          for (const id of expectedReports.filter((id) =>
            visibleReports.some((report) => report.id === id)
          )) {
            assert(
              ids.has(id) || links.has('#reported-tv-' + id),
              route + ' missing ' + id + ' in ' + groupId
            );
          }
        }
        assert.equal(
          items.length,
          visibleReports.length,
          route + ' confirmed model count'
        );
        assert(
          nodes(list)
            .filter((n) => n.tagName === 'a')
            .every((n) => attr(n, 'href')?.startsWith('#reported-webos-')),
          route + ' device list must not show evidence links'
        );
        for (const report of visibleReports) {
          const item = items.find(
            (n) => attr(n, 'data-report-id') === report.id
          );
          assert(item, route + ' missing confirmed model ' + report.id);
          assert.equal(
            attr(item, 'class')?.split(/\s+/).includes('confirmed'),
            report.result === 'controls-tested',
            route + ' confirmation styling for ' + report.id
          );
          assert(
            nodes(item).some((n) => n.tagName === 'h4'),
            route + ' missing device card heading ' + report.id
          );
          const versionLinks = nodes(item).filter((n) => n.tagName === 'a');
          assert(versionLinks.length > 0, route + ' device card version link');
          for (const link of versionLinks) {
            const version = all.find(
              (n) => '#' + attr(n, 'id') === attr(link, 'href')
            );
            assert(
              version &&
                nodes(version).some(
                  (n) => attr(n, 'href') === '#reported-tv-' + report.id
                ),
              route + ' missing reciprocal link for ' + report.id
            );
          }
          const text = nodes(item)
            .filter((n) => n.nodeName === '#text')
            .map((n) => n.value)
            .join('');
          for (const value of [
            report.model,
            report.firmware,
            report.webos ?? support[lang].unknownWebos,
            report.release,
            support[lang].reportResults[report.result],
            support[lang].reportSources[report.evidenceKind]
          ].filter(Boolean))
            assert(
              text.includes(value),
              route + ' missing reported value ' + value
            );
          for (const source of report.sources)
            assert(
              !text.includes(source.url) &&
                (!source.date || !text.includes(source.date)),
              route + ' evidence must remain internal'
            );
        }
      }
      assert(
        html.includes('Node.js 0.10.15+'),
        route + ' released No-root runtime floor'
      );
    }
    if (page === 'editions/' || page === 'compatibility/') {
      const table = all.find((n) => n.tagName === 'table');
      assert(table, route + ' needs a requirements/comparison table');
      assert(
        nodes(table).some((n) => n.tagName === 'caption'),
        route + ' table caption'
      );
    }
    assert(!html.includes('__LIVE_RELOAD__'), route);
  }
for (const file of [
  'index.html',
  'launcher/index.html',
  'root-launcher/index.html',
  'preview/themes.json'
])
  assert(existsSync(root + 'demo/' + file), 'missing demo ' + file);
assert(
  readFileSync(root + 'demo/index.html', 'utf8').includes('launcher/index.html')
);
assert(
  readFileSync(root + 'index.html', 'utf8').includes('demo/'),
  'legacy demo entry'
);
assert(!sitemap.includes('/demo/'), 'demo is not a content landing page');
assert(!sitemap.includes('/launcher/'));
console.log(
  `PASS ${locales.length * pages.length} localized pages: metadata, alternates, navigation, sitemap, local resources and preserved demo`
);
