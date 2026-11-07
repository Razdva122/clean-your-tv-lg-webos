const fs = require('node:fs');
const { compile } = require('./compile-tv-web.cjs');
(async () => {
  for (const directory of [
    'launcher',
    'root-edition/ui',
    'updater-app',
    'homebrew/app'
  ]) {
    const files = {};
    for (const entry of fs.readdirSync(directory)) {
      if (/\.(js|css|html)$/.test(entry))
        files[entry] = fs.readFileSync(directory + '/' + entry, 'utf8');
    }
    await compile(files);
    console.log('PASS TV web compatibility:', directory);
  }
})().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
