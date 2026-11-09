'use strict';
// Run real generated service closures with the same deterministic socket cases.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cp = require('node:child_process');
const { compile } = require('../../scripts/compile-helper.cjs');
const rootCompile = require('../../scripts/compile-root-node.cjs').compile;
function sources(directory, prefix = '') {
  return Object.fromEntries(
    fs
      .readdirSync(directory, { withFileTypes: true })
      .filter((entry) => entry.isFile())
      .map((entry) => [
        prefix + entry.name,
        fs.readFileSync(path.join(directory, entry.name), 'utf8')
      ])
  );
}
const output = fs.mkdtempSync(path.join(os.tmpdir(), 'weather-service-'));
try {
  const root = cp.spawnSync(
    process.env.PYTHON ||
      (process.platform === 'win32'
        ? '.venv-cytv/Scripts/python.exe'
        : '.venv-cytv/bin/python'),
    [
      '-c',
      `
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('root-edition').resolve()))
import build
from scripts.theme_receiver import inject
files={name:(build.SERVICE_SOURCE/name).read_bytes() for name in build.SERVICE_FILES}
files=inject(build.bundle_weather(build.bundle_c1_lease(build.bundle_presentation_context(files))),standalone=True)
print(json.dumps({name:raw.decode() for name,raw in files.items()}))
`
    ],
    { encoding: 'utf8' }
  );
  assert.equal(root.status, 0, root.stderr);
  const editions = {
    home: {
      appId: 'com.gathin.tvhome',
      files: compile({
        ...sources('renewal-service'),
        ...sources('theme-receiver', 'theme-receiver/'),
        'theme-receiver.js':
          "module.exports = require('./theme-receiver/register');\n"
      })
    },
    root: {
      appId: 'com.cleanyourtv.root.preview',
      files: rootCompile(JSON.parse(root.stdout))
    }
  };
  for (const [edition, { files }] of Object.entries(editions)) {
    for (const [name, code] of Object.entries(files)) {
      const target = path.join(output, edition, name);
      fs.mkdirSync(path.dirname(target), { recursive: true });
      fs.writeFileSync(target, code);
    }
  }
  for (const runtime of new Set(
    [
      process.execPath,
      process.env.NODE010,
      process.env.NODE01025,
      process.env.NODE012
    ].filter(Boolean)
  )) {
    for (const [edition, { appId }] of Object.entries(editions)) {
      const run = cp.spawnSync(
        runtime,
        [
          'tests/weather/service.cjs',
          path.join(output, edition, 'service.js'),
          appId,
          'entry'
        ],
        { encoding: 'utf8', timeout: 30000 }
      );
      assert.equal(
        run.status,
        0,
        runtime + ' ' + edition + '\n' + run.stdout + run.stderr
      );
      assert.match(run.stdout, /PASS trusted weather transport/);
      console.log('PASS generated weather ' + edition + ' on ' + runtime);
    }
  }
} finally {
  fs.rmSync(output, { recursive: true, force: true });
}
