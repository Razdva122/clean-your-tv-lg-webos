'use strict';
module.exports = function (io) {
  var busy = false;
  function save(s) {
    io.save(s);
    return s;
  }
  function pending(s) {
    return (
      s &&
      [
        'preparing',
        'pausing-renewal',
        'renewal-recovery',
        'restoring-renewal',
        'installing',
        'rolling-back',
        'recovery-required',
        'awaiting-launch'
      ].indexOf(s.status) >= 0
    );
  }
  async function pause(s) {
    s.status = 'pausing-renewal';
    save(s);
    try {
      var receipt = await io.pauseRenewal(s.id);
      if (
        !receipt ||
        receipt.id !== s.id ||
        receipt.confirmed !== true ||
        typeof receipt.wasEnabled !== 'boolean'
      )
        throw Error('pause-unconfirmed');
      s.renewal = receipt;
      s.renewalRestored = false;
      save(s);
      return true;
    } catch (_) {
      s.status = 'renewal-recovery';
      save(s);
      return false;
    }
  }
  async function restore(s, target) {
    s.terminalStatus = target;
    s.status = 'restoring-renewal';
    save(s);
    try {
      var r = await io.resumeRenewal(s.renewal);
      if (!r || r.restored !== true) throw Error('resume-unconfirmed');
      s.renewalRestored = true;
      s.status = target;
      save(s);
    } catch (_) {
      s.status = 'renewal-recovery';
      save(s);
    }
    return s;
  }
  async function install(candidate, prior, snapshot) {
    if (busy || pending(io.load())) throw Error('transaction-pending');
    busy = true;
    try {
      if (!(await io.root())) throw Error('root-required');
      var v = await io.versions();
      if (
        !prior ||
        prior.home !== v.home ||
        candidate.helper !== v.helper ||
        prior.helper !== v.helper ||
        require('./policy').compare(candidate.home, v.home) <= 0
      )
        throw Error('incompatible-update');
      await io.backup(snapshot);
      var s = save({
        schema: 1,
        id: require('crypto').randomBytes(16).toString('hex'),
        status: 'preparing',
        candidate: candidate,
        prior: prior,
        profile: snapshot,
        startedAt: Date.now()
      });
      if (!(await pause(s))) return s;
      s.status = 'installing';
      save(s);
      try {
        await io.install(candidate);
        s.status = 'awaiting-launch';
        save(s);
      } catch (e) {
        if (!e.definite) {
          s.status = 'recovery-required';
          save(s);
          return s;
        }
        s.status = 'rolling-back';
        save(s);
        try {
          await io.install(prior);
          s.status = 'rolled-back';
        } catch (_) {
          s.status = 'recovery-required';
        }
        save(s);
        if (s.status === 'rolled-back') return restore(s, 'rolled-back');
      }
      return s;
    } finally {
      busy = false;
    }
  }
  async function reconcile() {
    if (busy) throw Error('busy');
    busy = true;
    try {
      var s = io.load();
      if (!pending(s)) return s;
      if (
        ['pausing-renewal', 'renewal-recovery', 'restoring-renewal'].indexOf(
          s.status
        ) >= 0
      ) {
        if (s.terminalStatus) return restore(s, s.terminalStatus);
        if (!(await pause(s))) return s;
        return restore(s, s.pauseAbortStatus || 'aborted');
      }
      var v = await io.versions();
      s.observedVersion = v.home;
      // A version query is not terminal installer evidence. Keep uncertain jobs
      // blocked even if the old or new version is already visible in SAM.
      if (s.status !== 'awaiting-launch') s.status = 'recovery-required';
      return save(s);
    } finally {
      busy = false;
    }
  }
  async function healthy(version) {
    if (busy) throw Error('busy');
    busy = true;
    try {
      var s = io.load();
      if (!s || s.status !== 'awaiting-launch' || s.candidate.home !== version)
        throw Error('unexpected-health');
      var v = await io.versions();
      if (v.home !== version) throw Error('version-mismatch');
      return restore(s, 'complete');
    } finally {
      busy = false;
    }
  }
  async function rollback() {
    if (busy) throw Error('busy');
    busy = true;
    try {
      var s = io.load();
      if (!s || ['awaiting-launch', 'complete'].indexOf(s.status) < 0)
        throw Error('unsafe-retry');
      if (!(await io.root())) throw Error('root-required');
      var v = await io.versions();
      if (v.home !== s.candidate.home || v.helper !== s.prior.helper)
        throw Error('version-mismatch');
      if (s.renewalRestored) {
        s.id = require('crypto').randomBytes(16).toString('hex');
        delete s.terminalStatus;
        s.pauseAbortStatus = 'complete';
        if (!(await pause(s))) return s;
      }
      s.status = 'rolling-back';
      save(s);
      try {
        await io.install(s.prior);
        s.status = 'rolled-back';
      } catch (_) {
        s.status = 'recovery-required';
      }
      save(s);
      return s.status === 'rolled-back' ? restore(s, 'rolled-back') : s;
    } finally {
      busy = false;
    }
  }
  return {
    install: install,
    status: io.load,
    reconcile: reconcile,
    healthy: healthy,
    rollback: rollback
  };
};
