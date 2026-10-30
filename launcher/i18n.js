/* Offline localization shared by the two Home editions and the updater. */
(function(root){
 'use strict';
 var key='tvhome.language',catalogs={},active='en',dialog=null,previous=null,systemLanguage=null,pending=false,callbacks=[];
 var languages=[{code:'en',name:'English'},{code:'de',name:'Deutsch'},{code:'es',name:'Español'},{code:'pt-BR',name:'Português (Brasil)'},{code:'fr',name:'Français'},{code:'it',name:'Italiano'},{code:'ko',name:'한국어'},{code:'hi',name:'हिन्दी'},{code:'pl',name:'Polski'},{code:'ru',name:'Русский'},{code:'zh-Hans',name:'简体中文'},{code:'zh-Hant',name:'繁體中文'}];
 function normalize(value){
  var parts=String(value||'').split('.')[0].split('@')[0].replace(/_/g,'-').toLowerCase().split('-'),base=parts[0];
  if(base==='zh'){
   if(parts.indexOf('hans')>=0)return 'zh-Hans';
   if(parts.indexOf('hant')>=0)return 'zh-Hant';
   return parts.indexOf('tw')>=0||parts.indexOf('hk')>=0||parts.indexOf('mo')>=0?'zh-Hant':'zh-Hans';
  }
  if(base==='pt')return 'pt-BR';
  for(var i=0;i<languages.length;i++)if(languages[i].code===base)return base;
  return null;
 }
 function preference(){try{var p=root.localStorage.getItem(key);return p==='auto'||languages.some(function(l){return l.code===p;})?p:'auto';}catch(_){return 'auto';}}
 function resolve(){var p=preference();if(p!=='auto')return p;
  if(systemLanguage)return normalize(systemLanguage)||'en';
  var nav=root.navigator||{},choices=nav.languages&&nav.languages.length?nav.languages:[nav.language||nav.userLanguage];
  for(var i=0;i<choices.length;i++){var code=normalize(choices[i]);if(code)return code;}return 'en';
 }
 function refresh(){active=resolve();if(root.document){root.document.documentElement.lang=active;root.document.documentElement.dir='ltr';}return active;}
 function add(values){Object.keys(values).forEach(function(code){if(!catalogs[code])catalogs[code]={};Object.keys(values[code]).forEach(function(k){catalogs[code][k]=values[code][k];});});}
 function t(source,params){var map=catalogs[active]||{},text=Object.prototype.hasOwnProperty.call(map,source)?map[source]:source;
  return String(text).replace(/\{([a-zA-Z0-9_]+)\}/g,function(token,name){return params&&Object.prototype.hasOwnProperty.call(params,name)?String(params[name]):token;});
 }
 function escape(text){return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
 function html(markup){
  // Only literal interface markup enters here. Translation values are always escaped.
  return markup.replace(/>([^<>]+)</g,function(match,text){var clean=text.trim();return clean?'>'+text.slice(0,text.indexOf(clean))+escape(t(clean))+text.slice(text.indexOf(clean)+clean.length)+'<':match;})
   .replace(/\b(aria-label|title|placeholder)="([^"]*)"/g,function(_,attr,text){return attr+'="'+escape(t(text))+'"';});
 }
 function apply(element){if(!element||!element.querySelectorAll)return;var nodes=element.querySelectorAll('[data-i18n]');for(var i=0;i<nodes.length;i++)nodes[i].textContent=t(nodes[i].getAttribute('data-i18n'));}
 function setLanguage(code){if(code!=='auto'&&!languages.some(function(l){return l.code===code;}))return false;
  try{root.localStorage.setItem(key,code);}catch(_){return false;}
  refresh();if(root.location&&root.location.reload)root.location.reload();return true;
 }
 function formatDate(value,options){try{return new Date(value).toLocaleDateString(active,options||{weekday:'long',day:'numeric',month:'long'});}catch(_){return new Date(value).toLocaleDateString();}}
 function formatDateTime(value){try{return new Date(value).toLocaleString(active);}catch(_){return new Date(value).toLocaleString();}}
 function formatTime(value){try{return new Date(value).toLocaleTimeString(active,{hour:'2-digit',minute:'2-digit'});}catch(_){var d=new Date(value);return d.getHours()+':'+('0'+d.getMinutes()).slice(-2);}}
 function closePicker(){if(dialog)dialog.hidden=true;if(root.ThemeRuntime)root.ThemeRuntime.resume('language');if(previous&&previous.focus)previous.focus();}
 function renderLanguageChoices(list,error){
  var doc=root.document,buttons=[],selected=0,choices=[{code:'auto',name:t('Automatic (system language)')}].concat(languages);
  choices.forEach(function(item,index){var button=doc.createElement('button');button.type='button';button.textContent=item.name;button.lang=item.code==='auto'?active:item.code;button.dataset.language=item.code;button.setAttribute('aria-pressed',String(preference()===item.code));if(preference()===item.code)selected=index;
   button.onclick=function(){if(!setLanguage(item.code))error.textContent=t('Could not save language. Please try again.');};list.appendChild(button);buttons.push(button);});
  return {buttons:buttons,selected:selected};
 }
 function mountLanguagePicker(host){
  var doc=root.document,hint=doc.createElement('p'),list=doc.createElement('div'),error=doc.createElement('p');
  hint.textContent=t('Choose a language. Home will reload.');list.id='settingsLanguageChoices';error.setAttribute('role','alert');
  host.appendChild(hint);host.appendChild(list);host.appendChild(error);renderLanguageChoices(list,error);
 }
 function openLanguagePicker(){
  if(!root.document)return;if(root.ThemeRuntime)root.ThemeRuntime.suspend('language');var doc=root.document;previous=doc.activeElement;
  if(!dialog){dialog=doc.createElement('section');dialog.id='languagePicker';dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-labelledby','languageTitle');doc.body.appendChild(dialog);}
  dialog.hidden=false;dialog.innerHTML='<div class="language-card"><h2 id="languageTitle">'+escape(t('Language'))+' / Language</h2><p>'+escape(t('Choose a language. Home will reload.'))+'</p><div id="languageChoices"></div><p id="languageError" role="alert"></p></div>';
  var list=doc.getElementById('languageChoices'),state=renderLanguageChoices(list,doc.getElementById('languageError')),buttons=state.buttons,selected=state.selected;
  var back=doc.createElement('button');back.textContent=t('Back');back.onclick=closePicker;list.appendChild(back);buttons.push(back);dialog._buttons=buttons;dialog._selected=selected;buttons[selected].focus();
 }
 // Shared by Home updates and the independent recovery app; loaded before their key handlers.
 var confirmation=null,confirmationButtons,confirmationCallback,confirmationPrevious,confirmationSelected=0,swallowOK=false;
 function closeConfirmation(accept){
  if(!confirmation||confirmation.hidden)return;
  var callback=confirmationCallback;confirmationCallback=null;confirmation.hidden=true;if(root.ThemeRuntime)root.ThemeRuntime.resume('confirmation');
  if(confirmationPrevious&&confirmationPrevious.focus)confirmationPrevious.focus();
  if(accept&&callback)callback();
 }
 function confirmAction(options,callback){
  if(confirmation&&!confirmation.hidden)return;
  if(root.ThemeRuntime)root.ThemeRuntime.suspend('confirmation');
  var doc=root.document;confirmationPrevious=doc.activeElement;
  if(!confirmation){
   confirmation=doc.createElement('section');confirmation.id='homeConfirmation';confirmation.setAttribute('role','alertdialog');confirmation.setAttribute('aria-modal','true');confirmation.setAttribute('aria-labelledby','homeConfirmationTitle');confirmation.setAttribute('aria-describedby','homeConfirmationMessage');
   var card=doc.createElement('div');card.className='confirmation-card';confirmation.appendChild(card);
   var title=doc.createElement('h2');title.id='homeConfirmationTitle';card.appendChild(title);
   var message=doc.createElement('p');message.id='homeConfirmationMessage';card.appendChild(message);
   var actions=doc.createElement('div');actions.className='confirmation-actions';card.appendChild(actions);
   confirmationButtons=[doc.createElement('button'),doc.createElement('button')];
   confirmationButtons.forEach(function(button,index){button.type='button';button.onclick=function(){closeConfirmation(index===1);};actions.appendChild(button);});
   doc.body.appendChild(confirmation);
  }
  confirmation.children[0].children[0].textContent=t(options.title);
  confirmation.children[0].children[1].textContent=t(options.message,options.params);
  confirmationButtons[0].textContent=t('Cancel');confirmationButtons[1].textContent=t(options.action);
  confirmationCallback=callback;confirmationSelected=0;confirmation.hidden=false;confirmationButtons[0].focus();
 }
 root.HomeI18n={ready:function(cb){if(pending)callbacks.push(cb);else cb();},languages:languages,normalize:normalize,language:function(){return active;},preference:preference,refresh:refresh,add:add,t:t,html:html,apply:apply,setLanguage:setLanguage,formatDate:formatDate,formatDateTime:formatDateTime,formatTime:formatTime,openLanguagePicker:openLanguagePicker,mountLanguagePicker:mountLanguagePicker,confirm:confirmAction};
 refresh();
 if(root.PalmServiceBridge&&preference()==='auto'){
  pending=true;var bridge,timer,finished=false;
  function finish(value){if(finished)return;finished=true;root.clearTimeout(timer);if(bridge)try{bridge.cancel();}catch(_){}systemLanguage=value;refresh();pending=false;var queued=callbacks;callbacks=[];queued.forEach(function(cb){cb();});if(root.document)apply(root.document);}
  timer=root.setTimeout(function(){finish(null);},1200);
  try{bridge=new root.PalmServiceBridge();bridge.onservicecallback=function(raw){var language=null;try{var r=JSON.parse(raw);if(r.returnValue===true)language=r.settings.localeInfo.locales.UI;}catch(_){}finish(language);};bridge.call('luna://com.webos.settingsservice/getSystemSettings',JSON.stringify({key:'localeInfo'}));}catch(_){finish(null);}
 }
 if(root.document){
  root.document.addEventListener('focusin',function(e){if(!confirmation||confirmation.hidden)return;var index=confirmationButtons.indexOf(e.target);if(index>=0)confirmationSelected=index;else confirmationButtons[confirmationSelected].focus();},true);
  ['keydown','keyup'].forEach(function(type){root.document.addEventListener(type,function(e){
   if(e.keyCode===13&&swallowOK){e.preventDefault();e.stopImmediatePropagation();if(type==='keyup')swallowOK=false;return;}
   if(!confirmation||confirmation.hidden)return;
   e.preventDefault();e.stopImmediatePropagation();if(type==='keyup')return;
   var k=e.keyCode,index=confirmationButtons.indexOf(root.document.activeElement);
   if(k===27||k===461){closeConfirmation(false);return;}
   if(k===13){if(!e.repeat){swallowOK=true;confirmationButtons[index<0?0:index].click();}return;}
   if([9,37,38,39,40].indexOf(k)>=0)confirmationButtons[index===0?1:0].focus();
  },true);});
  root.document.addEventListener('DOMContentLoaded',function(){apply(root.document);root.document.title=t(root.document.title);});
  root.document.addEventListener('focusin',function(e){if(!dialog||dialog.hidden||!dialog._buttons)return;var index=dialog._buttons.indexOf(e.target);if(index>=0){dialog._selected=index;return;}dialog._buttons[dialog._selected||0].focus();},true);
  // Registered before other modal handlers: a language choice cannot also activate Home.
  ['keydown','keyup'].forEach(function(type){root.document.addEventListener(type,function(e){if(!dialog||dialog.hidden)return;var k=e.keyCode;if([9,13,27,37,38,39,40,461].indexOf(k)<0)return;e.preventDefault();e.stopImmediatePropagation();if(type==='keyup')return;
   var buttons=dialog._buttons,index=buttons.indexOf(root.document.activeElement);if(k===461||k===27){closePicker();return;}if(k===13){if(!e.repeat&&buttons[index])buttons[index].click();return;}
   var delta=k===38?-2:k===40?2:k===37||(k===9&&e.shiftKey)?-1:1;buttons[(index+delta+buttons.length)%buttons.length].focus();
  },true);});
 }
}(typeof window!=='undefined'?window:this));
