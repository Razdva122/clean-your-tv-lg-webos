'use strict';
const assert = require('assert');
const execFile = require('child_process').execFile;
const reader = require('../../root-edition/service/app-inventory');
(async function () {
  const cases = [
    ['timeout', 'setTimeout(function(){}, 10000)', { timeout: 50 }],
    [
      'oversized-reply',
      "process.stdout.write('PRIVATE'.repeat(10000))",
      { maxBuffer: 64 }
    ],
    ['malformed-reply', "process.stdout.write('PRIVATE')", {}],
    ['client-error', 'process.exit(7)', {}],
    [
      'permission-denied',
      "process.stdout.write(JSON.stringify({returnValue:false,errorCode:-1,errorText:'Permission denied PRIVATE'}))",
      {}
    ]
  ];
  for (const query of [reader, reader.inputs]) {
    for (const entry of cases) {
      let failure;
      try {
        await query(
          function (file, args, options, callback) {
            execFile(
              process.execPath,
              ['-e', entry[1]],
              Object.assign({}, options, entry[2]),
              callback
            );
          },
          function () {
            return 0;
          }
        );
      } catch (error) {
        failure = error;
      }
      assert(failure, 'must reject');
      assert.strictEqual(failure.inventory.reason, entry[0]);
      assert.strictEqual(JSON.stringify(failure).indexOf('PRIVATE'), -1);
    }
  }
  console.log(
    'PASS 10 actual child-process classifications on ' + process.version
  );
})().catch(function (error) {
  console.error(error);
  process.exitCode = 1;
});
