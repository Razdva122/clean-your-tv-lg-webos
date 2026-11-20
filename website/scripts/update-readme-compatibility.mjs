import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { webosCategory } from '../src/lib/webos.mjs';

const block =
  /(?<=<!-- compatibility:readme -->\n)[\s\S]*?(?=<!-- \/compatibility:readme -->)/;
const readmePath = new URL('../../README.md', import.meta.url);
const catalogPath = new URL(
  '../../docs/compatibility-reports.json',
  import.meta.url
);
const verified = (report) => report.result === 'controls-tested';

function cell(value) {
  return (value ?? 'Not reported').replace(/[&<>\\[\]\x60*_|\r\n]/g, (char) =>
    char === '\r' || char === '\n' ? ' ' : '&#' + char.charCodeAt(0) + ';'
  );
}

export function updateReadmeCompatibility(readme, reports) {
  if (!block.test(readme))
    throw new Error('README compatibility markers are missing');
  const groups = new Map();
  for (const report of reports.filter(
    ({ showOnWebsite }) => showOnWebsite === true
  )) {
    const category = webosCategory(report.webos);
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(report);
  }

  const groupOrder = [...groups].sort(([a], [b]) =>
    a.localeCompare(b, 'en', { numeric: true })
  );
  const sections = groupOrder.map(([category, entries]) => {
    const title =
      category === 'unknown'
        ? 'Version not reported'
        : 'webOS ' + category.replace('-', '–');
    const groupStatus = entries.some(verified) ? '✅' : '❔';
    const rows = entries
      .sort(
        (a, b) =>
          Number(verified(b)) - Number(verified(a)) ||
          a.model.localeCompare(b.model, 'en', { numeric: true })
      )
      .map((report) => {
        const edition = { root: 'Root', 'no-root': 'No-root' }[report.edition];
        return (
          '| ' +
          [
            verified(report) ? '✅' : '❔',
            cell(report.model) + (edition ? ' · ' + edition : ''),
            cell(report.webos)
          ].join(' | ') +
          ' |'
        );
      });
    return [
      '<details>',
      '<summary>' + groupStatus + ' ' + title + '</summary>',
      '',
      '| Home | TV · Edition | Reported webOS |',
      '| :---: | --- | --- |',
      ...rows,
      '',
      '</details>'
    ].join('\n');
  });
  const contents = [
    '<details>',
    '<summary>TV test results by webOS</summary>',
    '',
    '✅ Home button verified · ❔ Partial or unconfirmed',
    '',
    ...sections.flatMap((section) => [section, '']),
    '[Test details and sources](docs/COMPATIBILITY.md#user-reported-working-tvs)',
    '',
    '</details>',
    ''
  ].join('\n');
  return readme.replace(block, () => contents);
}

if (
  process.argv[1] &&
  import.meta.url === pathToFileURL(process.argv[1]).href
) {
  const readme = readFileSync(readmePath, 'utf8');
  const { reports } = JSON.parse(readFileSync(catalogPath, 'utf8'));
  const updated = updateReadmeCompatibility(readme, reports);
  if (updated !== readme) writeFileSync(readmePath, updated);
}
