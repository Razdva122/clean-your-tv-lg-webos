(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.InstallerProgress = factory();
})(this, function () {
  'use strict';
  var preflight = [
      'homebrew-access',
      'root-user',
      'node-version',
      'installer-payload',
      'python-runtime',
      'installer-staging',
      'product-state',
      'home-compatibility'
    ],
    installation = [
      'install-request',
      'install-root',
      'install-updates',
      'install-readback',
      'activate-home'
    ],
    status = ['pending', 'running', 'pass', 'fail', 'unknown'],
    stages = {
      requested: 0,
      submitting: 0,
      submitted: 0,
      blocked: 0,
      'resume-submitted': 0,
      preparing: 0,
      snapshot: 0,
      reserved: 0,
      'root-deploy': 1,
      'root-updater': 2,
      supervisor: 2,
      readback: 3,
      complete: 4
    };

  function observe(
    inspection,
    operation,
    failure,
    checking,
    runtimePreparation
  ) {
    var checks = {};
    var backend = inspection && inspection.checks;
    preflight.concat(installation).forEach(function (key) {
      checks[key] =
        backend && status.indexOf(backend[key]) >= 0 ? backend[key] : 'pending';
    });
    if (checking && !inspection) checks['homebrew-access'] = 'running';
    if (runtimePreparation) checks['python-runtime'] = runtimePreparation;
    if (failure === 'homebrew_exec_denied') checks['homebrew-access'] = 'fail';
    else if (failure && !operation && checks['homebrew-access'] !== 'pass')
      checks['homebrew-access'] = 'unknown';
    if (!operation || operation.action !== 'install') return checks;
    var position = Object.prototype.hasOwnProperty.call(stages, operation.stage)
      ? stages[operation.stage]
      : -1;
    if (position < 0) {
      if (operation.state === 'unknown') checks['install-request'] = 'unknown';
      return checks;
    }
    installation.slice(0, position).forEach(function (key) {
      checks[key] = 'pass';
    });
    var active = installation[position],
      activation = operation.activation || {};
    if (failure || operation.state === 'unknown') checks[active] = 'unknown';
    else if (operation.state === 'recovery_required') checks[active] = 'fail';
    else if (position === 4 && operation.state === 'complete') {
      if (activation.completed === true) checks[active] = 'pass';
      else if (activation.state === 'pending') checks[active] = 'running';
      else if (activation.state !== 'cancelled' && activation.state)
        checks[active] = 'unknown';
    } else if (operation.state === 'pending') checks[active] = 'running';
    return checks;
  }

  return { observe: observe, preflight: preflight, installation: installation };
});
