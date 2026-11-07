// Reintroducing a launch here can make SAM close the visible Home on low-RAM TVs.
const test = require('node:test'),
  assert = require('node:assert/strict'),
  fs = require('fs'),
  vm = require('vm');
test('legacy bootstrap never launches a native app when Home loads', () => {
  const calls = [];
  function PalmServiceBridge() {
    this.call = (uri, p) => calls.push({ uri, p });
    this.cancel = () => {};
  }
  vm.runInNewContext(
    fs.readFileSync(
      require('path').join(__dirname, '../../launcher/native-bootstrap.js'),
      'utf8'
    ),
    {
      PalmServiceBridge,
      setTimeout() {
        return 1;
      },
      clearTimeout() {}
    }
  );
  assert.deepEqual(calls, []);
});
