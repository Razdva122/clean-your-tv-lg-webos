'use strict';
module.exports = function (execute, audio, startup, presentation) {
  var busy = false;
  function valid(payload, boot) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
    if (Object.keys(payload).some(function (key) { return key !== '$activity' && !(boot && key === 'reason'); })) return false;
    return !boot || (payload.reason === 'activity' && payload.$activity &&
      Number.isInteger(payload.$activity.activityId) && payload.$activity.activityId > 0);
  }
  function handler(command) {
    return async function (payload) {
      if (presentation && command === 'status' && payload && typeof payload === 'object' &&
          !Array.isArray(payload) && Object.keys(payload).length === 1 && payload.presentation === 'context') {
        try { return {returnValue:true,result:await presentation()}; }
        catch (_) { return {returnValue:true,result:{content:null}}; }
      }
      if (audio && payload && typeof payload === 'object' && !Array.isArray(payload)) {
        var keys = Object.keys(payload);
        if (command === 'status' && keys.length === 1 && payload.audio === 'status')
          return audio.audioRecoveryStatus({});
        if (command === 'enable' && keys.length === 2) {
          if (payload.audio === 'configure' && keys.indexOf('enabled') >= 0)
            return audio.setAudioRecoveryEnabled({enabled:payload.enabled});
          if (payload.audio === 'recover' && keys.indexOf('operation') >= 0)
            return audio.recoverAudio({operation:payload.operation});
        }
      }
      if (startup && payload && typeof payload === 'object' && !Array.isArray(payload)) {
        var startupKeys = Object.keys(payload), operation = null;
        if (command === 'status' && startupKeys.length === 1 && payload.startup === 'status') operation = 'status';
        if (command === 'enable' && startupKeys.length === 2 && payload.startup === 'configure' &&
            startupKeys.indexOf('sources') >= 0 && payload.sources && !Array.isArray(payload.sources) &&
            typeof payload.sources === 'object' && Object.keys(payload.sources).sort().join(',') === 'hdmi,tv,youtube' &&
            Object.keys(payload.sources).every(function (key) { return typeof payload.sources[key] === 'boolean'; })) operation = 'configure';
        if (operation) {
          if (busy) return {returnValue:false,errorText:'Recovery busy'};
          busy = true;
          try { return {returnValue:true,result:await startup(operation, payload.sources)}; }
          catch (_) { return {returnValue:false,errorText:'Startup choices are unavailable. Check status before retrying.'}; }
          finally { busy = false; }
        }
      }
      var confirmation = command === 'confirm';
      var allowed = confirmation ? payload && Object.keys(payload).length === 1 && typeof payload.transaction === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(payload.transaction) : valid(payload, command === 'boot');
      if (!allowed) return {returnValue:false,errorText:'Invalid recovery request'};
      if (busy) return {returnValue:false,errorText:'Recovery busy'};
      busy = true;
      try { return {returnValue:true,result:await execute(command, confirmation ? payload.transaction : undefined)}; }
      catch (error) { return {returnValue:false,errorText:error.message}; }
      finally { busy = false; }
    };
  }
  return {boot:handler('boot'),status:handler('status'),restore:handler('restore'),enable:handler('enable'),confirm:handler('confirm')};
};

module.exports.audio = function (uid, execute) {
  var busy = false;
  function valid(payload, key, values) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false;
    var keys = Object.keys(payload);
    return key ? keys.length === 1 && keys[0] === key && values.indexOf(payload[key]) >= 0 : keys.length === 0;
  }
  function handler(key, values, command) {
    return async function (payload) {
      if (uid() !== 0 || !valid(payload, key, values)) return {returnValue:false,errorCode:'invalid'};
      // Disabling policy and status must remain available during a reset.
      var mutating = command === 'recover';
      if (mutating && busy) return {returnValue:false,errorCode:'busy'};
      if (mutating) busy = true;
      try {
        return await execute(command === 'recover' ? payload.operation :
          command === 'configure' ? payload.enabled ? 'enable' : 'disable' : 'status');
      } catch (_) { return {returnValue:false,errorCode:'unavailable'}; }
      finally { if (mutating) busy = false; }
    };
  }
  return {
    audioRecoveryStatus:handler(null, null, 'status'),
    setAudioRecoveryEnabled:handler('enabled', [true, false], 'configure'),
    recoverAudio:handler('operation', ['restart-earc', 'restore-hdmi', 'restore-setting'], 'recover')
  };
};
