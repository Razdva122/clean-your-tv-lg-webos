'use strict';
var Service = require('webos-service');
var execFile = require('child_process').execFile;
var service = new Service('com.cleanyourtv.root.preview.service');
function pythonCommand(){return require('/var/lib/clean-your-tv-root/python_boot.js').command('/var/lib/clean-your-tv-root');}

var runtime = '/var/lib/clean-your-tv-root/runtime/cli.py';
// Audio recovery has a separate process-wide transaction lock and never runs on service load.
var audio = require('./handlers').audio(function () { return process.getuid(); }, function (command) {
  return new Promise(function (resolve, reject) {
    var executable = pythonCommand();
    execFile(executable, [runtime, 'audio', command],
      {timeout:45000,maxBuffer:16384}, function (error, stdout) {
        if (error) return reject(new Error('Audio recovery unavailable'));
        try { resolve(JSON.parse(stdout)); } catch (_) { reject(new Error('Invalid audio response')); }
      });
  });
});

var handlers = require('./handlers')(function (command, transaction) {
  return new Promise(function (resolve, reject) {
    if (process.getuid() !== 0) return reject(new Error('Root recovery service required'));
    if (['boot', 'status', 'restore', 'enable', 'confirm'].indexOf(command) === -1) return reject(new Error('Unknown operation'));
    var selected = pythonCommand();
    var executable = command === 'boot' ? '/bin/sh' : selected;
    var args = command === 'boot' ? [__dirname + '/boot-recover.sh'] : [runtime, command];
    if (command === 'confirm') args.push(transaction);
    // This selects a deadline only; Python authenticates the backend descriptor.
    var gateEnable = command === 'enable' && require('fs').existsSync('/var/lib/clean-your-tv-root/home-backend.json');
    execFile(executable, args, {timeout:command === 'restore' ? 600000 : command === 'boot' ? 120000 : gateEnable ? 90000 : 30000,maxBuffer:65536}, function (error, stdout) {
      if (error) return reject(new Error('Recovery operation failed; inspect runtime status'));
      try { resolve(JSON.parse(stdout)); } catch (_) { reject(new Error('Invalid runtime response')); }
    });
  });
}, audio, function (command, sources) {
  return new Promise(function (resolve, reject) {
    if (process.getuid() !== 0 || ['status','configure'].indexOf(command) < 0) return reject(Error('Root startup settings unavailable'));
    var child = execFile(pythonCommand(), [runtime, 'startup', command], {timeout:10000,maxBuffer:16384}, function (error, stdout) {
      if (error) return reject(Error('Root startup settings unavailable'));
      try { resolve(JSON.parse(stdout)); } catch (_) { reject(Error('Invalid startup response')); }
    });
    child.stdin.end(command === 'configure' ? JSON.stringify(sources) : '');
  });
}, require('./presentation-context')(execFile, function () { return process.getuid(); }));
Object.keys(handlers).forEach(function (method) {
  service.register(method, function (message) {
    handlers[method](message.payload).then(function (result) { result.root = process.getuid() === 0; message.respond(result); });
  });
});
// Activity registration belongs to the root installer, not the web service.

var inventoryPending=null,inputStatus=require('./app-inventory').inputHandler();
service.register('listApps',function(message){
 if(message.payload&&Object.prototype.hasOwnProperty.call(message.payload,'inputs'))return inputStatus(message);
 if(!inventoryPending)inventoryPending=require('./app-inventory')();
 var request=inventoryPending;
 request.then(function(apps){if(inventoryPending===request)inventoryPending=null;message.respond({returnValue:true,apps:apps});},function(){if(inventoryPending===request)inventoryPending=null;message.respond({returnValue:false,errorText:'App inventory unavailable'});});
});

// This HTTP receiver never exposes recovery or root runtime operations.
require('./theme-receiver')(service, {appId:'com.cleanyourtv.root.preview'});
