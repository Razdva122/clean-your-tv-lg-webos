'use strict';
// Export fixed categories only: never paths, exception text, tokens or bus replies.
var components = ['settings', 'renewal', 'home'];
var operations = [
  'read',
  'parse',
  'mkdir',
  'write',
  'chmod',
  'rename',
  'wait',
  'authorize',
  'operation'
];
var codes = [
  'EACCES',
  'EPERM',
  'EROFS',
  'ENOSPC',
  'EDQUOT',
  'ENOENT',
  'EIO',
  'EMFILE',
  'ENFILE',
  'EEXIST',
  'ENOTDIR',
  'EISDIR',
  'ELOOP',
  'ENAMETOOLONG',
  'INVALID_JSON',
  'INVALID_STATE',
  'TOO_LARGE',
  'TIMEOUT',
  'BUSY',
  'CALLER_DENIED',
  'UNKNOWN'
];
function sanitize(value) {
  if (
    !value ||
    components.indexOf(value.component) < 0 ||
    operations.indexOf(value.operation) < 0 ||
    codes.indexOf(value.code) < 0
  )
    return null;
  return {
    component: value.component,
    operation: value.operation,
    code: value.code
  };
}
function describe(component, operation, error) {
  return sanitize({
    component: component,
    operation: operation,
    code:
      error && codes.indexOf(error.code) >= 0
        ? error.code
        : error && error.name === 'SyntaxError'
          ? 'INVALID_JSON'
          : 'UNKNOWN'
  });
}
function storage(component, operation, error) {
  var result = new Error('state-storage-failed');
  result.storageFailure = true;
  result.diagnostic =
    sanitize(error && error.diagnostic) ||
    describe(component, operation, error);
  return result;
}
module.exports = { sanitize: sanitize, describe: describe, storage: storage };
