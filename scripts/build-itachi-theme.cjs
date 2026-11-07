'use strict';
// Build with the separately maintained toolkit; never fetch or execute a theme repository.
const fs = require('node:fs'),
  path = require('node:path'),
  cp = require('node:child_process');
const root = path.resolve(__dirname, '..'),
  args = process.argv.slice(2);
function option(name, fallback) {
  const i = args.indexOf(name);
  return path.resolve(i < 0 ? fallback : args[i + 1]);
}
const toolkit = option(
  '--toolkit',
  path.join(root, '../clean-your-tv-lg-theme')
);
const runtime = option(
  '--runtime',
  path.join(root, 'build/itachi-css-runtime')
);
const out = option(
  '--out',
  path.join(
    root,
    'build/itachi-theme-' +
      JSON.parse(fs.readFileSync(path.join(root, 'themes/itachi/theme.json')))
        .themeVersion
  )
);
// Capture the fixed TV canvas first. Resizing the viewport crops/reflows its UI.
async function capturePreview(page) {
  const viewport = page.viewportSize();
  if (!viewport || viewport.width !== 1920 || viewport.height !== 1080)
    throw Error('Itachi preview requires the full 1920x1080 viewport');
  const full = await page.screenshot({ animations: 'disabled' });
  const jpeg = await page.evaluate(async (base64) => {
    const image = new Image();
    image.src = 'data:image/png;base64,' + base64;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = 960;
    canvas.height = 540;
    canvas.getContext('2d').drawImage(image, 0, 0, 960, 540);
    return canvas.toDataURL('image/jpeg', 0.85).split(',')[1];
  }, full.toString('base64'));
  return Buffer.from(jpeg, 'base64');
}
module.exports = { capturePreview };
if (require.main === module)
  (async () => {
    const tools = require(path.join(toolkit, 'lib/toolkit.cjs')),
      rt = tools.runtime(runtime);
    const commit = cp
      .execFileSync('git', ['rev-parse', 'HEAD'], {
        cwd: root,
        encoding: 'utf8'
      })
      .trim();
    await tools.build(path.join(root, 'themes/itachi'), rt, {
      out,
      repository: 'https://github.com/razdva122/clean-your-tv-lg-webos',
      commit
    });
    fs.copyFileSync(
      path.join(root, 'themes/itachi/README.md'),
      path.join(out, 'README.md')
    );
    console.log(out);
  })().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
