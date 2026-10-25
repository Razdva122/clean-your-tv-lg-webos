'use strict';
var Service = require('webos-service');
var fs = require('fs');
var execFile = require('child_process').execFile;
var service = new Service('com.cleanyourtv.root.preview.service');
function pythonCommand(){return require('/var/lib/clean-your-tv-root/python_boot.js').command('/var/lib/clean-your-tv-root');}

var runtime = '/var/lib/clean-your-tv-root/runtime/cli.py';
var handlers = require('./handlers')(function (command, transaction) {
  return new Promise(function (resolve, reject) {
    if (process.getuid() !== 0) return reject(new Error('Root recovery service required'));
    if (['boot', 'status', 'restore', 'enable', 'confirm'].indexOf(command) === -1) return reject(new Error('Unknown operation'));
    var selected = pythonCommand();
    var executable = command === 'boot' ? '/bin/sh' : selected;
    var args = command === 'boot' ? [__dirname + '/boot-recover.sh'] : [runtime, command];
    if (command === 'confirm') args.push(transaction);
    execFile(executable, args, {timeout:command === 'restore' ? 600000 : command === 'boot' ? 120000 : 30000,maxBuffer:65536}, function (error, stdout) {
      if (error) return reject(new Error('Recovery operation failed; inspect runtime status'));
      try { resolve(JSON.parse(stdout)); } catch (_) { reject(new Error('Invalid runtime response')); }
    });
  });
});
Object.keys(handlers).forEach(function (method) {
  service.register(method, function (message) {
    handlers[method](message.payload).then(function (result) { result.root = process.getuid() === 0; message.respond(result); });
  });
});
// Activity registration belongs to the root installer, not the web service.

var TOGGLES_PATH = '/media/developer/natxo/settings.json';
var TOGGLE_KEYS = ['earcFix', 'disableBluetooth', 'disableMicrophone'];
var APPLY_SCRIPT = __dirname + '/apply-toggles.sh';
function readToggles() {
  try { return JSON.parse(fs.readFileSync(TOGGLES_PATH, 'utf8')); }
  catch (_) { return {}; }
}
function saveToggles(toggles) {
  try { fs.mkdirSync('/media/developer/natxo', {recursive: true}); } catch (_) {}
  fs.writeFileSync(TOGGLES_PATH + '.tmp', JSON.stringify(toggles, null, 2));
  fs.renameSync(TOGGLES_PATH + '.tmp', TOGGLES_PATH);
}
function applyToggles() {
  execFile('/bin/sh', [APPLY_SCRIPT], {timeout: 30000}, function () {});
}
service.register('getToggles', function (message) {
  try { message.respond({returnValue: true, toggles: readToggles()}); }
  catch (e) { message.respond({returnValue: false, errorText: String(e)}); }
});
service.register('setToggle', function (message) {
  try {
    var key = message.payload.key, value = !!message.payload.value;
    if (TOGGLE_KEYS.indexOf(key) < 0) { message.respond({returnValue: false, errorText: 'Invalid toggle key'}); return; }
    var toggles = readToggles();
    toggles[key] = value;
    saveToggles(toggles);
    applyToggles();
    message.respond({returnValue: true, toggles: toggles});
  } catch (e) { message.respond({returnValue: false, errorText: String(e)}); }
});
applyToggles();

var inventoryPending=null;
service.register('listApps',function(message){
 if(!inventoryPending)inventoryPending=require('./app-inventory')();
 var request=inventoryPending;
 request.then(function(apps){if(inventoryPending===request)inventoryPending=null;message.respond({returnValue:true,apps:apps});},function(){if(inventoryPending===request)inventoryPending=null;message.respond({returnValue:false,errorText:'App inventory unavailable'});});
});
