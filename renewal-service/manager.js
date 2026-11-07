'use strict';
var diagnostics = require('./diagnostics');
// A single service process owns this queue. Home interception is never called here.
module.exports = function (io) {
  var state,
    diagnostic = null,
    stopped = false,
    queue = Promise.resolve(),
    generation = 0;
  try {
    state = io.load() || {};
  } catch (error) {
    state = { enabled: false, error: 'storage-error' };
    diagnostic = diagnostics.storage('settings', 'read', error).diagnostic;
  }
  state.enabled = state.enabled === true;
  stopped = !state.enabled || !!state.updatePause;
  function status() {
    var result = JSON.parse(JSON.stringify(state));
    delete result.diagnostic;
    if (diagnostic) result.diagnostic = Object.assign({}, diagnostic);
    return result;
  }
  function save() {
    try {
      io.save(state);
      if (!state.error) diagnostic = null;
    } catch (error) {
      diagnostic = diagnostics.storage('settings', 'write', error).diagnostic;
      throw diagnostics.storage('settings', 'write', error);
    }
  }
  function enqueue(fn) {
    var p = queue.then(fn).catch(function (error) {
      stopped = true;
      state.enabled = false;
      state.error =
        error && error.storageFailure === true
          ? 'storage-error'
          : 'internal-error';
      diagnostic =
        state.error === 'storage-error'
          ? diagnostics.sanitize(error.diagnostic)
          : diagnostics.describe('renewal', 'operation', error);
      return status();
    });
    queue = p;
    return p;
  }
  async function check() {
    if (stopped || !state.enabled) return status();
    var result = await io.run();
    if (stopped || !state.enabled) return status();
    var resultDiagnostic = diagnostics.sanitize(result.diagnostic);
    if (result.status !== 'cooldown') {
      state.last = Object.assign({}, result);
      delete state.last.diagnostic;
    }
    if (result.status === 'renewed') state.lastRenewedAt = io.now();
    save();
    if (resultDiagnostic) diagnostic = resultDiagnostic;
    return status();
  }
  function validId(id) {
    return typeof id === 'string' && /^[a-zA-Z0-9-]{1,80}$/.test(id);
  }
  return {
    importUpdatePause: function (receipt) {
      return enqueue(async function () {
        if (
          !receipt ||
          !validId(receipt.id) ||
          receipt.confirmed !== true ||
          typeof receipt.wasEnabled !== 'boolean'
        )
          return Object.assign(status(), { error: 'invalid-pause-receipt' });
        if (state.completedUpdate === receipt.id && !state.updatePause)
          return status();
        if (state.updatePause) {
          if (state.updatePause.id !== receipt.id)
            return Object.assign(status(), { error: 'pause-import-conflict' });
          if (state.updatePause.confirmed && !state.error) return status();
        } else {
          if (
            state.completedUpdate ||
            state.error ||
            (state.enabled && !state.preferenceTouched)
          )
            return Object.assign(status(), { error: 'pause-import-conflict' });
          state.updatePause = {
            id: receipt.id,
            wasEnabled: state.preferenceTouched
              ? state.enabled
              : receipt.wasEnabled,
            confirmed: false
          };
        }
        generation++;
        stopped = true;
        state.error = null;
        state.enabled = false;
        save();
        var r;
        try {
          r = await io.cancel();
        } catch (_) {
          r = null;
        }
        if (!r || !(r.returnValue === true || r.errorCode === 2)) {
          state.error = 'cancel-unconfirmed';
          save();
          return status();
        }
        state.updatePause.confirmed = true;
        try {
          save();
        } catch (e) {
          state.updatePause.confirmed = false;
          throw e;
        }
        return status();
      });
    },
    pauseForUpdate: function (id) {
      if (!validId(id))
        return Promise.resolve(
          Object.assign(status(), { error: 'invalid-update-id' })
        );
      generation++;
      stopped = true;
      return enqueue(async function () {
        if (state.updatePause && state.updatePause.id !== id)
          return Object.assign(status(), { error: 'update-in-progress' });
        if (!state.updatePause)
          state.updatePause = {
            id: id,
            wasEnabled: state.enabled,
            confirmed: false
          };
        state.updatePause.confirmed = false;
        state.enabled = false;
        state.error = null;
        save();
        var r;
        try {
          r = await io.cancel();
        } catch (_) {
          r = null;
        }
        if (!r || !(r.returnValue === true || r.errorCode === 2)) {
          state.error = 'cancel-unconfirmed';
          save();
          return status();
        }
        state.updatePause.confirmed = true;
        try {
          save();
        } catch (e) {
          state.updatePause.confirmed = false;
          throw e;
        }
        return status();
      });
    },
    resumeAfterUpdate: function (id) {
      var ticket = generation;
      return enqueue(async function () {
        if (validId(id) && state.completedUpdate === id && !state.updatePause)
          return status();
        var pause = state.updatePause;
        if (
          !validId(id) ||
          !pause ||
          pause.id !== id ||
          pause.confirmed !== true
        )
          return Object.assign(status(), { error: 'invalid-update-pause' });
        if (pause.wasEnabled) {
          var r = await io.schedule();
          if (!r || r.returnValue !== true) {
            state.error = 'schedule-unavailable';
            save();
            return status();
          }
          if (ticket !== generation) {
            await io.cancel();
            return status();
          }
        }
        var previousCompleted = state.completedUpdate;
        state.enabled = pause.wasEnabled === true;
        state.error = null;
        state.completedUpdate = id;
        delete state.updatePause;
        try {
          save();
        } catch (e) {
          state.enabled = false;
          state.updatePause = pause;
          state.completedUpdate = previousCompleted;
          throw e;
        }
        stopped = !state.enabled;
        return status();
      });
    },
    restoreHistory: function (snapshot) {
      return enqueue(async function () {
        // Preserve diagnostics only, never import enabled=true or schedule renewal.
        if (
          state.enabled ||
          state.last ||
          !snapshot ||
          snapshot.enabled !== false
        )
          return status();
        var allowed = [
          'status',
          'checkedAt',
          'nextAt',
          'failures',
          'remainingSeconds'
        ];
        if (snapshot.last && typeof snapshot.last === 'object') {
          state.last = {};
          allowed.forEach(function (k) {
            var v = snapshot.last[k];
            if (
              (k === 'status' && typeof v === 'string' && v.length < 80) ||
              (k !== 'status' && typeof v === 'number' && Number.isFinite(v))
            )
              state.last[k] = v;
          });
        }
        if (
          typeof snapshot.lastRenewedAt === 'number' &&
          Number.isFinite(snapshot.lastRenewedAt)
        )
          state.lastRenewedAt = snapshot.lastRenewedAt;
        save();
        return status();
      });
    },
    allowed: function () {
      return !stopped && state.enabled;
    },
    status: status,
    check: function () {
      return enqueue(check);
    },
    enable: function () {
      var ticket = ++generation;
      return enqueue(async function () {
        if (state.updatePause)
          return Object.assign(status(), { error: 'update-in-progress' });
        state.preferenceTouched = true;
        state.enabled = false;
        state.error = null;
        save();
        var r = await io.schedule();
        if (!r || r.returnValue !== true) {
          state.error = 'schedule-unavailable';
          save();
          return status();
        }
        if (ticket !== generation) {
          await io.cancel();
          return status();
        }
        state.enabled = true;
        stopped = false;
        save();
        return check();
      });
    },
    disable: function () {
      generation++;
      stopped = true;
      return enqueue(async function () {
        state.preferenceTouched = true;
        state.enabled = false;
        state.error = null;
        if (state.updatePause) state.updatePause.wasEnabled = false;
        var persisted = true;
        try {
          save();
        } catch (_) {
          persisted = false;
        }
        var r;
        try {
          r = await io.cancel();
        } catch (_) {
          r = null;
        }
        if (!r || !(r.returnValue === true || r.errorCode === 2))
          state.error = 'cancel-unconfirmed';
        if (!persisted) state.error = 'disable-not-saved';
        try {
          save();
        } catch (_) {
          state.error = 'disable-not-saved';
        }
        return status();
      });
    }
  };
};
