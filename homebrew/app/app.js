(function(root){
 'use strict';
 var bridge=root.InstallerBridge,i18n=root.InstallerI18n,doc=root.document,content=doc.getElementById('content'),hint=doc.getElementById('hint'),key='cytv.installer.operation';
 var inspected=null,job=null,operation=null,supervisor=false,migrate=false,poll=null,busy=false,confirmation=null,opener=null,screen='checking',message=null,accessDenied=false;
 function t(k){return i18n.t(k);}
 function remember(id){if(!/^[a-f0-9]{32}$/.test(id))throw new Error('invalid_request');root.localStorage.setItem(key,id);operation=id;}
 try{var saved=root.localStorage.getItem(key);if(/^[a-f0-9]{32}$/.test(saved||''))operation=saved;}catch(_){}
 function element(tag,text,className){var node=doc.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
 function paragraph(keyName){content.appendChild(element('p',t(keyName)));}
 function controls(){var node=element('div',undefined,'actions');content.appendChild(node);return node;}
 function button(parent,id,text,action,style){var node=element('button',text,style);node.id=id;node.type='button';node.onclick=action;parent.appendChild(node);return node;}
 function focus(id){var target=doc.getElementById(id)||content.querySelector('button:not([disabled])')||doc.getElementById('language');if(target){target.focus();target.scrollIntoView(false);}}
 function begin(name,title){screen=name;clearTimeout(poll);content.textContent='';content.setAttribute('data-screen',name);content.appendChild(element('h2',t(title)));doc.getElementById('language').textContent=t('language');hint.textContent=t('navigation');}
 function ask(action,from,copy){confirmation=action;opener=from;begin('confirm',action==='install'?'review':action==='remove'?'remove':action==='activate'?'activate':action==='restore'?'restore':'prerequisites');paragraph(copy);var actions=controls();button(actions,'cancel',t('cancel'),cancel);button(actions,'confirm',t('confirm'),submit,'primary');focus('cancel');}
 function cancel(){confirmation=null;render();focus(opener);}
 function versions(){var v=inspected&&inspected.installation&&inspected.installation.versions;if(!v)return;var node=element('p',Object.keys(v).map(function(k){return (k==='root'?'Root Home':'Root Updater')+' '+v[k];}).join(' · '));node.id='versions';content.appendChild(node);}
 function render(){
  if(accessDenied){
   begin('homebrew-access','homebrewDeniedTitle');paragraph('homebrewDeniedBody');
   if(operation){paragraph('lost');content.appendChild(element('p',t('request')+': '+operation,'details'));}
   var denied=controls();button(denied,'refresh',t('refresh'),refresh);button(denied,'close',t('close'),close);focus('refresh');return;
  }
  if(!inspected){begin('checking','checking');return;}
  if(job){
   var pending=job.state==='pending',unknown=job.state==='unknown';
   begin(pending?'progress':'recovery',pending?'progress':'recovery');paragraph(message||(pending?'progressBody':unknown?'unknown':'recoveryBody'));
   if(operation)content.appendChild(element('p',t('request')+': '+operation,'details'));
   var jobs=controls();button(jobs,'refresh',t('refresh'),refresh,'primary');
   if(job.can_resume===true&&(job.action==='install'||job.action==='remove'))button(jobs,'resume',t('continueOriginal')+' · '+t(job.action==='install'?'install':'remove'),function(){ask('resume','resume','resumeConfirm');});
   button(jobs,'restore',t('restore'),function(){ask('restore','restore','restoreConfirm');});button(jobs,'close',t('close'),close);
   button(jobs,'details',t('details'),function(){var old=doc.getElementById('technical');if(old){old.parentNode.removeChild(old);return;}var safe=['stage','state','code','resume_reason'].map(function(k){return k+': '+String(job[k]||'').replace(/[^a-z0-9_-]/g,'').slice(0,80);}).join(' · ');var node=element('p',safe);node.id='technical';content.appendChild(node);});
   focus('refresh');if(pending&&!doc.hidden)poll=setTimeout(pollStatus,8000);return;
  }
  var state=inspected.state;
  if(state==='prerequisites'){
   begin('prerequisites','prerequisites');paragraph('runtimeBody');button(controls(),'prepare',t('prepare'),function(){ask('prepare-runtime','prepare','runtimeConfirm');},'primary');
  }else if(state==='installed'&&inspected.installation&&inspected.installation.can_maintain===true){
   begin('installed','installed');versions();paragraph(message||'installedBody');var maintenance=controls();
   button(maintenance,'activate',t('activate'),function(){ask('activate','activate','activateConfirm');},'primary');
   button(maintenance,'restore',t('restore'),function(){ask('restore','restore','restoreConfirm');});button(maintenance,'remove',t('remove'),function(){ask('remove','remove','removeConfirm');},'danger');paragraph('retained');
  }else if(state==='fresh'&&inspected.installation&&inspected.installation.can_install===true){
   begin('review','review');paragraph(message||'reviewBody');
   var details=element('div',undefined,'details');details.appendChild(element('p',t('components')));var candidate=root.InstallerCandidate;
   if(candidate)details.appendChild(element('p',Object.keys(candidate).map(function(k){return k+' '+candidate[k];}).join(' · ')));content.appendChild(details);
   var choices=controls();button(choices,'supervisor',t('supervisor')+': '+t(supervisor?'yes':'no'),function(){supervisor=!supervisor;refresh('supervisor');});button(choices,'migrate',t('migration')+': '+t(migrate?'yes':'no'),function(){migrate=!migrate;render();focus('migrate');});
   var actions=controls();button(actions,'install',t('install'),function(){ask('install','install','installConfirm');},'primary');button(actions,'close',t('close'),close);
  }else if(state==='unsupported'){
   begin('unsupported','unsupported');paragraph('unsupportedBody');button(controls(),'refresh',t('refresh'),refresh);
  }else{
   begin('recovery','recovery');paragraph(message||'recoveryBody');var recover=controls();button(recover,'refresh',t('refresh'),refresh);button(recover,'restore',t('restore'),function(){ask('restore','restore','restoreConfirm');});
  }
  focus('');
 }
 function refresh(focusId){
  if(busy)return;busy=true;clearTimeout(poll);var previous=doc.activeElement&&doc.activeElement.id;
  bridge.inspect({prepareSupervisor:supervisor}).then(function(result){
   accessDenied=false;inspected=result;var active=result.active_operation;
   if(active&&/^[a-f0-9]{32}$/.test(active.operation||''))remember(active.operation);
   if(operation&&result.state!=='prerequisites'&&result.state!=='unsupported')return bridge.status(operation).then(function(status){
    if(status.state==='complete'&&(status.current===true||(result.state==='installed'&&result.installation&&result.installation.can_maintain===true))){job=null;if(status.action==='remove'){operation=null;try{root.localStorage.removeItem(key);}catch(_){}}}
    else job=status;
   });
   job=null;
  }).then(function(){busy=false;render();focus(typeof focusId==='string'?focusId:previous);},function(error){busy=false;accessDenied=error.message==='homebrew_exec_denied';if(operation){job=job||{state:'unknown'};message='lost';}else{inspected={state:'unsupported'};}render();});
 }
 function pollStatus(){
  if(busy||!operation||doc.hidden)return;busy=true;
  var previous=doc.activeElement&&doc.activeElement.id;
  bridge.status(operation).then(function(result){busy=false;job=result;if(result.state==='complete'&&result.current===true){job=null;refresh();return;}render();focus(previous);},function(error){busy=false;accessDenied=error.message==='homebrew_exec_denied';message='lost';render();focus(previous);});
 }
 function uuid(){if(!root.crypto||!root.crypto.getRandomValues)throw new Error('secure_id_required');var bytes=new Uint8Array(16);root.crypto.getRandomValues(bytes);return Array.prototype.map.call(bytes,function(b){return ('0'+b.toString(16)).slice(-2);}).join('');}
 function submit(){
  if(busy||!confirmation)return;var action=confirmation;confirmation=null;busy=true;var promise;
  try{
   if(action==='install'||action==='remove'){
    remember(uuid());job={operation:operation,action:action,state:'pending',stage:'submitting'};message=null;render();
    var options={operation:operation,candidate:inspected.candidate_sha256};if(action==='install'){options.prepareSupervisor=supervisor;options.migrate=migrate;}
    promise=action==='install'?bridge.start(options):bridge.remove(options);
   }else if(action==='prepare-runtime')promise=bridge.prepareRuntime();
   else if(action==='activate')promise=bridge.activate();
   else if(action==='resume'){if(!job||job.can_resume!==true)throw new Error('not_recoverable');promise=bridge.resume(operation,job.action);job.can_resume=false;}
   else promise=bridge.restore();
  }catch(_){busy=false;message='failed';render();return;}
  if(action!=='install'&&action!=='remove'&&action!=='resume'){begin('checking','checking');paragraph(action==='prepare-runtime'?'runtimeBody':action==='activate'?'activateConfirm':'restoreConfirm');}
  promise.then(function(result){busy=false;if(action==='install'||action==='remove'||action==='resume'){job=result;message=null;render();return;}
   if(result.state==='complete'||result.state==='runtime_ready'){message=action==='activate'?'activationDone':action==='restore'?'restoreDone':null;refresh();}else{message='failed';inspected=result;render();}
  },function(error){busy=false;accessDenied=error.message==='homebrew_exec_denied';message=operation?'lost':'failed';if(operation)job=job||{state:'unknown'};render();});
 }
 function close(){if(root.close)root.close();}
 doc.getElementById('language').onclick=function(){if(busy)return;var old=screen;begin('language','language');var list=controls();Object.keys(i18n.names).forEach(function(code){var choice=button(list,'lang-'+code,i18n.names[code],function(){i18n.set(code);render();focus('language');});choice.lang=code;});button(list,'back',t('back'),function(){screen=old;render();focus('language');});focus('lang-'+doc.documentElement.lang);};
 doc.addEventListener('keydown',function(event){
  var code=event.keyCode,keyName=event.key,back=code===461||code===27||code===8||keyName==='Escape'||keyName==='Backspace';
  if(back){event.preventDefault();if(busy)return;if(screen==='confirm')cancel();else if(screen==='language'){render();focus('language');}else if(screen==='progress'){hint.textContent=t('progressBody');}else close();return;}
  if(keyName==='Enter'||code===13){if(doc.activeElement&&doc.activeElement.tagName==='BUTTON'){event.preventDefault();doc.activeElement.click();}return;}
  if([37,38,39,40].indexOf(code)<0&&['ArrowLeft','ArrowUp','ArrowRight','ArrowDown'].indexOf(keyName)<0)return;
  event.preventDefault();var nodes=Array.prototype.filter.call(doc.querySelectorAll('button'),function(n){return !n.disabled&&!n.hidden&&n.offsetWidth>0;}),index=nodes.indexOf(doc.activeElement),delta=code===37||code===38||keyName==='ArrowLeft'||keyName==='ArrowUp'?-1:1;
  if(nodes.length){var next=nodes[(index+delta+nodes.length)%nodes.length];next.focus();next.scrollIntoView(false);}
 });
 doc.addEventListener('visibilitychange',function(){clearTimeout(poll);if(!doc.hidden)refresh();});doc.addEventListener('webOSRelaunch',refresh);
 render();refresh();
}(window));
