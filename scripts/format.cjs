// Only format versioned sources; leave untracked experiments and private files alone.
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const mode = process.argv[2];
if (!['--write', '--check'].includes(mode) || process.argv.length !== 3) {
  throw Error('Use npm run format or npm run format:check');
}
const files = execFileSync(
  'git',
  ['ls-files', '-z', '--', '*.js', '*.cjs', '*.mjs', '*.css', '*.html'],
  { cwd: root, encoding: 'utf8' }
)
  .split('\0')
  .filter(Boolean);
files.push('scripts/format.cjs');
try {
  execFileSync(
    process.execPath,
    [
      require.resolve('prettier/bin/prettier.cjs'),
      '--config',
      '.prettierrc.json',
      mode,
      ...files
    ],
    {
      cwd: root,
      stdio: 'inherit'
    }
  );
} catch (error) {
  process.exitCode = error.status || 1;
}
