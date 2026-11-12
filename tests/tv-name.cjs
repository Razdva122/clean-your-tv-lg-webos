'use strict';
const assert = require('node:assert/strict');
const name = require('../root-edition/ui/tv-name');
assert.equal(name.normalize(' Aashiyaan '), 'Aashiyaan');
assert.equal(name.normalize('Cafe\u0301'), 'Café');
assert.equal(name.normalize('आशियाना'), 'आशियाना');
assert.equal(name.normalize('📺'.repeat(48)), '📺'.repeat(48));
for (const value of ['x'.repeat(49), 'bad\nname', 'bad\u202ename', 'a\u061cb', '\ud800'])
  assert.throws(() => name.normalize(value));
console.log('Root Home screen name normalization passed.');
