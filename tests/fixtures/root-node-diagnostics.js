'use strict';
// Exercise actual generated preload and native fd writes. Substitute only TV
// root ownership metadata; no chmod/chown or system-directory writes occur.
var fs=require('fs'),Module=require('module'),load=Module._load,path=require('path');
var dir=process.argv[2],file=dir+'/startup-diagnostics.js';
var owned=Object.create(fs);
owned.lstatSync=function(name){var info=fs.lstatSync(name);info.uid=0;info.mode&=~18;return info;};
owned.fstatSync=function(fd){var info=fs.fstatSync(fd);info.uid=0;return info;};
Module._load=function(name,parent,isMain){if(name==='fs'&&parent.filename===file)return owned;return load.call(this,name,parent,isMain);};
require(file);
Module._load=load;
var record=path.dirname(dir)+'/recovery-service.json';
require('assert').equal(JSON.parse(fs.readFileSync(record,'utf8')).phase,'starting');
process.exit(23);
