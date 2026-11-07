#!/usr/bin/env node
'use strict';
const args = process.argv.slice(2),
  action = args[0],
  variant = args[1],
  root = args[2] || '/var/luna-service2-dev';
if (
  !['plan', 'apply', 'remove'].includes(action) ||
  !['lab', 'production'].includes(variant) ||
  args.length > 3
)
  throw Error(
    'Usage: update-permissions.cjs plan|apply|remove lab|production [LS2 root]'
  );
const setup = require('./lib/update-permissions.cjs'),
  options = { variant, root };
if (action === 'plan')
  console.log(JSON.stringify(setup.plan(options), null, 2));
else {
  if (process.platform !== 'linux' || !process.getuid || process.getuid() !== 0)
    throw Error('apply/remove require root on the TV');
  const ctl = ['/usr/bin/ls-control', '/usr/sbin/ls-control'].find((p) =>
    require('fs').existsSync(p)
  );
  if (!ctl) throw Error('ls-control unavailable');
  options.refresh = () =>
    require('child_process').execFileSync(ctl, ['scan-services'], {
      timeout: 15000,
      stdio: 'pipe'
    });
  console.log(JSON.stringify(setup[action](options)));
}
