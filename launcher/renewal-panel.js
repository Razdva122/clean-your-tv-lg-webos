(window.HomeI18n?HomeI18n.ready:function(callback){callback();})(function(){
(function(){
 'use strict';
 function tr(s,p){return window.HomeI18n?HomeI18n.t(s,p):s.replace(/\{(\w+)\}/g,function(m,k){return p&&p[k]!==undefined?p[k]:m;});}function ht(s){return window.HomeI18n?HomeI18n.html(s):s;}
 var panel=document.createElement('section');panel.id='renewalPanel';panel.className='hidden';panel.setAttribute('role','dialog');panel.setAttribute('aria-label',tr('Home settings'));
 panel.setAttribute('aria-modal','true');
 panel.innerHTML=ht([
  "<div id=\"settingsMain\" class=\"renewal-card settings-main\"><div class=\"settings-heading\"><h2>Home settings</h2><span class=\"settings-edition\">No-root Edition</span></div><section class=\"settings-home\"><h3>Your Home screen</h3><p>Home is your app screen. Home Helper makes the Home button open it.</p><p id=\"homeRoutingStatus\" class=\"settings-status\" aria-live=\"polite\">Checking Home control…</p>",
  "<div class=\"renewal-actions home-routing-actions\"><button id=\"homeRoutingToggle\" class=\"home-routing-switch\" role=\"switch\" aria-checked=\"false\" hidden disabled>Change Home</button><button id=\"homeVisit\" class=\"home-visit-button\" aria-describedby=\"homeVisitHint\">Open LG Home</button></div><p id=\"homeVisitHint\" class=\"home-visit-hint\">Open LG Home once, keeping your Home choice.</p>",
  "<div class=\"renewal-actions settings-layout\"><div id=\"homeThemeHost\"></div></div><div class=\"renewal-actions settings-layout\"><button id=\"homeColumns\">Columns</button></div></section>",
  "<div id=\"homeAppSettings\" class=\"renewal-actions settings-layout\"><button id=\"homeShowAddApp\" class=\"home-routing-switch\" role=\"switch\" aria-checked=\"true\">Show Add app tile</button><button id=\"homeAddApp\">Add app</button><p id=\"homeAppsError\" role=\"alert\"></p></div>",
  "<div class=\"renewal-actions settings-links settings-section\"><button id=\"homeLanguage\">Language<span class=\"settings-chevron\" aria-hidden=\"true\"></span></button><button id=\"renewalUpdates\">Software updates<span class=\"settings-update-dot\" aria-hidden=\"true\"></span><span class=\"settings-chevron\" aria-hidden=\"true\"></span></button><button id=\"renewalTV\">TV settings<span class=\"settings-chevron\" aria-hidden=\"true\"></span></button></div><div class=\"renewal-actions settings-developer\"><button id=\"developerOpen\" aria-controls=\"developerSettings\" aria-describedby=\"renewalSummary\"><span><span>Developer Mode</span> <span class=\"settings-beta\">Beta</span><span id=\"renewalSummary\" class=\"renewal-summary\" aria-live=\"polite\">Checking auto-renewal…</span></span><span class=\"settings-chevron\" aria-hidden=\"true\"></span></button></div><div class=\"settings-footer\">",
  "<div class=\"renewal-actions\"><button id=\"renewalClose\">Back to Home</button></div></div>",
  "</div><div id=\"developerSettings\" class=\"renewal-card hidden\"><div class=\"settings-heading\"><h2>Developer Mode</h2><span class=\"settings-edition\">Beta</span></div><p>Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.</p><p>Developer Mode keeps Home installed. Auto-renewal tries to extend its session while your TV is on and online.</p>",
  "<div class=\"renewal-actions\"><button id=\"renewalToggle\" class=\"home-routing-switch\" role=\"switch\" aria-checked=\"false\">Turn on auto-renewal</button></div><p class=\"renewal-warning\">Beta: renewal is not yet verified on no-root TVs. Keep checking the timer in the Developer Mode app.</p>",
  "<div id=\"renewalStatus\" aria-live=\"polite\">Checking auto-renewal…</div><div class=\"renewal-actions\"><button id=\"renewalCheck\">Check session</button><button id=\"renewalDiagnostics\" aria-expanded=\"false\" aria-controls=\"renewalDetails\">Show diagnostics</button></div><pre id=\"renewalDetails\" class=\"hidden\"></pre><div class=\"settings-footer\"><div class=\"renewal-actions\"><button id=\"developerBack\">Back</button></div></div>",
  "</div>"
 ].join(''));
 document.body.appendChild(panel);
 var status=document.getElementById('renewalStatus'),toggle=document.getElementById('renewalToggle'),check=document.getElementById('renewalCheck'),details=document.getElementById('renewalDetails');
 var previous,developerOpen=false,categories;
 var main=document.getElementById('settingsMain'),developer=document.getElementById('developerSettings'),summary=document.getElementById('renewalSummary');
 var buttons=Array.prototype.slice.call(panel.querySelectorAll('button')),index=0,state=null,busy=false,serviceVersion=null,homeReplies={},homeGeneration=0;
 buttons.splice(buttons.indexOf(document.getElementById('renewalDiagnostics'))+1,0,details);
 details.setAttribute('tabindex','0');details.setAttribute('aria-label',tr('Show diagnostics'));
 var developerButtons=['renewalToggle','renewalCheck','renewalDiagnostics','renewalDetails','developerBack'].map(function(id){return document.getElementById(id);});
 var checkingUpdates=false;
 function checkUpdates(){
  if(checkingUpdates||!window.HomeUpdates||!window.HomeUpdates.rpc)return;
  checkingUpdates=true;
  function badge(available){
   var button=document.getElementById('renewalUpdates');
   button.setAttribute('data-update-available',String(available));
   if(categories)categories.setUpdateAvailable(available);
   button.setAttribute('aria-label',tr(available?'Software updates. Update available.':'Software updates'));
  }
  function legacy(){
   return new Promise(function(resolve){window.HomeUpdates.rpc('check',{},function(offer){
    if(offer)badge(offer.state==='available'||offer.state==='helper-update-required');resolve();
   });});
  }
  var check=window.SystemUpdates?window.SystemUpdates.check('no-root',legacy).then(function(offer){if(offer)badge(offer.canInstall===true);}):legacy();
  check.catch(function(){}).then(function(){checkingUpdates=false;});
 }

 function openNow(){return !panel.classList.contains('hidden');}
 function focus(i){var direction=i<index?-1:1;for(var n=0;n<buttons.length;n++,i+=direction){var j=(i+buttons.length*2)%buttons.length;if((!categories||buttons[j].offsetHeight>0)&&!buttons[j].disabled&&!buttons[j].hidden&&!(buttons[j]===details&&details.classList.contains('hidden'))&&(developerButtons.indexOf(buttons[j])>=0)===developerOpen){index=j;buttons[index].focus();return;}}}
 function rpc(method,callback){
  var bridge,done=false,timer=setTimeout(function(){finish(null);},45000);
  function finish(r){if(done)return;done=true;clearTimeout(timer);if(bridge)try{bridge.cancel();}catch(_){}callback(r);}
  try{bridge=new PalmServiceBridge();bridge.onservicecallback=function(raw){try{finish(JSON.parse(raw));}catch(_){finish(null);}};bridge.call('luna://com.gathin.tvhome.renewal/'+method,'{}');}catch(_){finish(null);}
 }
 var homeToggle=document.getElementById('homeRoutingToggle'),homeVisit=document.getElementById('homeVisit'),homeStatus=document.getElementById('homeRoutingStatus'),homeEnabled=null,homeBusy=false;
 function hideHomeChoice(){
  var focused=document.activeElement===homeToggle;
  homeToggle.hidden=true;homeToggle.disabled=true;
  if(focused&&openNow())focus(index);
 }
 function homeRPC(method,payload,callback){
  var b,done=false,generation=homeGeneration,t=setTimeout(function(){finish({returnValue:false,diagnostic:{component:'home',operation:'rpc',code:'TIMEOUT'}});},10000);
  function finish(r){if(done)return;done=true;clearTimeout(t);if(b)try{b.cancel();}catch(_){}if(generation!==homeGeneration)return;
   var reply={returnValue:!!(r&&r.returnValue===true)},diagnostic=safeDiagnostic(r&&r.diagnostic);
   if(r&&typeof r.errorCode==='number'&&r.errorCode%1===0&&r.errorCode>=-2147483648&&r.errorCode<=2147483647)reply.errorCode=r.errorCode;
   if(r&&typeof r.enabled==='boolean')reply.enabled=r.enabled;
   if(!diagnostic&&(!reply.returnValue||(method!=='openLGHome'&&typeof reply.enabled!=='boolean')))diagnostic={component:'home',operation:'rpc',code:reply.returnValue?'INVALID_RESPONSE':'REQUEST_FAILED'};
   if(diagnostic)reply.diagnostic=diagnostic;homeReplies[method]=reply;
   if(!details.classList.contains('hidden'))renderDiagnostics();callback(r||{returnValue:false});
  }
  try{b=new PalmServiceBridge();b.onservicecallback=function(raw){try{finish(JSON.parse(raw));}catch(_){finish({returnValue:false,diagnostic:{component:'home',operation:'rpc',code:'INVALID_JSON'}});}};b.call('luna://com.gathin.tvhome.renewal/'+method,JSON.stringify(payload));}catch(_){finish({returnValue:false,diagnostic:{component:'home',operation:'rpc',code:'BRIDGE_ERROR'}});}
 }
 function renderHome(r){
  homeBusy=false;homeVisit.disabled=false;
  if(!r||r.returnValue!==true||typeof r.enabled!=='boolean'){
   homeEnabled=null;hideHomeChoice();homeStatus.textContent=tr('Home status is unknown. The Home button may still work.');return;
  }
  homeEnabled=r.enabled;homeToggle.hidden=false;homeToggle.disabled=false;homeToggle.setAttribute('aria-checked',String(homeEnabled));
  homeStatus.textContent=homeEnabled?tr('Home and return from apps open Clean Your TV.'):tr('Home and return from apps open LG Home.');
  if(openNow()&&(!categories||(panel.contains(document.activeElement)&&!categories.nav.contains(document.activeElement))))focus(index);
 }
 function refreshHome(){hideHomeChoice();homeStatus.textContent=tr('Checking Home control…');homeRPC('homeStatus',{},renderHome);}
 homeToggle.onclick=function(){
  if(homeBusy||homeEnabled===null)return;homeBusy=true;homeToggle.disabled=true;homeVisit.disabled=true;homeStatus.textContent=tr('Changing Home control…');
  homeRPC('setHomeControl',{enabled:!homeEnabled},function(r){
   if(r.returnValue===true)renderHome(r);
   else homeRPC('homeStatus',{},function(status){renderHome(status);homeStatus.textContent=tr('Change was not confirmed. Check the switch and try again.');});
  });
 };
 homeVisit.onclick=function(){
  if(homeBusy)return;homeBusy=true;homeVisit.disabled=true;
  homeRPC('openLGHome',{},function(r){homeBusy=false;homeVisit.disabled=false;
   if(r.returnValue===true)close();else homeStatus.textContent=tr('Could not open LG Home. Check Home Helper and try again.');
  });
 };
 function date(v){return typeof v==='number'?(window.HomeI18n?HomeI18n.formatDateTime(v):new Date(v).toLocaleString()):tr('Not yet');}
 var labels={healthy:tr('Session checked'),renewed:tr('Renewal confirmed'),retry:tr('Connection failed — retry scheduled'),unverified:tr('LG response could not confirm renewal'),expired:tr('Session expired — open Developer Mode'),unavailable:tr('No readable Developer Mode session'), 'session-changed':tr('Session changed — retry scheduled'),'storage-error':tr('Could not save state'),'internal-error':tr('Check failed')};
 function render(){
  toggle.setAttribute('aria-checked',String(!!(state&&state.enabled)));
  toggle.textContent=state&&state.enabled?tr('Turn off auto-renewal'):tr('Turn on auto-renewal');
  check.disabled=busy||!state||!state.enabled;toggle.disabled=busy||!state;
  if(!state)return;
  var last=state.last||{};
  var text=state.enabled?tr('Auto-renewal enabled (Beta)'):tr('Auto-renewal off');
  var brief=text;
  if(last.status&&last.status!=='healthy'&&last.status!=='renewed')brief+=' · '+(labels[last.status]||tr('Check pending'));
  if(typeof last.remainingSeconds==='number')brief+=' · '+tr('{hours} hours remaining (estimate)',{hours:Math.floor(Math.max(0,last.remainingSeconds-(Date.now()-last.checkedAt)/1000)/3600)});
  if(state.error)brief+=' · '+tr('Setup error: {error}. Use Developer Mode manually.',{error:state.error});
  summary.textContent=brief;summary.classList.toggle('settings-danger',!!state.error||last.status==='expired'||last.status==='unavailable');
  if(last.status)text+='\n'+(labels[last.status]||tr('Check pending'));
  if(typeof last.remainingSeconds==='number')text+=' · '+tr('{hours} hours remaining (estimate)',{hours:Math.floor(Math.max(0,last.remainingSeconds-(Date.now()-last.checkedAt)/1000)/3600)});
  text+='\n'+tr('Last checked: {date}',{date:date(last.checkedAt)})+'\n'+tr('Last confirmed renewal: {date}',{date:date(state.lastRenewedAt)});
  if(state.error==='disable-not-saved')text+='\n'+tr('Disable could not be saved. Retry before restarting the service.');
  if(state.error)text+='\n'+tr('Setup error: {error}. Use Developer Mode manually.',{error:state.error});
  status.textContent=text;if(!details.classList.contains('hidden'))renderDiagnostics();if(openNow()&&(!categories||(panel.contains(document.activeElement)&&!categories.nav.contains(document.activeElement))))focus(index);
 }
 function action(method){if(busy)return;busy=true;status.textContent=tr('Working…');summary.textContent=tr('Working…');toggle.disabled=true;check.disabled=true;
  rpc(method,function(r){busy=false;if(!r||r.returnValue!==true){state=null;serviceVersion=null;status.textContent=tr('Service unavailable. Install the complete Home package and try again. Manage your Developer Mode timer manually.');summary.textContent=status.textContent;summary.classList.add('settings-danger');toggle.disabled=true;check.disabled=true;if(!details.classList.contains('hidden'))renderDiagnostics();if(openNow()&&(!categories||(panel.contains(document.activeElement)&&!categories.nav.contains(document.activeElement))))focus(index);return;}serviceVersion=typeof r.version==='string'&&/^\d{1,4}\.\d{1,4}\.\d{1,4}$/.test(r.version)?r.version:null;state=r.state;render();});
 }
 toggle.onclick=function(){if(state)action(state.enabled?'disable':'enable');};
 check.onclick=function(){action('check');};
 function safeDiagnostic(value){
  if(!value||['settings','renewal','home'].indexOf(value.component)<0||['read','parse','mkdir','write','chmod','rename','wait','authorize','operation','rpc'].indexOf(value.operation)<0||['EACCES','EPERM','EROFS','ENOSPC','EDQUOT','ENOENT','EIO','EMFILE','ENFILE','EEXIST','ENOTDIR','EISDIR','ELOOP','ENAMETOOLONG','INVALID_JSON','INVALID_STATE','TOO_LARGE','TIMEOUT','BUSY','CALLER_DENIED','UNKNOWN','REQUEST_FAILED','INVALID_RESPONSE','BRIDGE_ERROR'].indexOf(value.code)<0)return null;
  return {component:value.component,operation:value.operation,code:value.code};
 }
 function renderDiagnostics(){
  var last=state&&state.last||{};
  function number(value){return typeof value==='number'&&isFinite(value)&&value>=0?value:null;}
  var error=state&&state.error;
  if(error&&['storage-error','internal-error','schedule-unavailable','cancel-unconfirmed','disable-not-saved','update-in-progress','invalid-update-pause','invalid-update-id','pause-import-conflict','invalid-pause-receipt'].indexOf(error)<0)error='unknown';
  var result=last.status||'not-checked';
  if(['not-checked','healthy','renewed','retry','expired','unverified','unavailable','session-changed','storage-error','internal-error','disabled','cooldown'].indexOf(result)<0)result='unknown';
  var report={serviceVersion:serviceVersion,beta:true,enabled:state&&typeof state.enabled==='boolean'?state.enabled:null,status:result,checkedAt:number(last.checkedAt),remainingSeconds:number(last.remainingSeconds),lastRenewedAt:number(state&&state.lastRenewedAt),error:error||null,diagnostic:safeDiagnostic(state&&state.diagnostic),home:homeReplies};
  // Keep nested diagnostic tuples compact enough to read on a TV.
  var rows=Object.keys(report).map(function(key){return '  '+JSON.stringify(key)+': '+JSON.stringify(report[key]);});
  details.textContent=tr('Share this with your TV model and firmware at:')+'\ngithub.com/Razdva122/clean-your-tv-lg-webos/issues\n{\n'+rows.join(',\n')+'\n}';
 }
 document.getElementById('renewalDiagnostics').onclick=function(){
  renderDiagnostics();
  details.classList.toggle('hidden');
  this.textContent=details.classList.contains('hidden')?tr('Show diagnostics'):tr('Hide diagnostics');
  this.setAttribute('aria-expanded',String(!details.classList.contains('hidden')));
  focus(buttons.indexOf(details.classList.contains('hidden')?this:details));
  if(!details.classList.contains('hidden')&&details.scrollIntoView)details.scrollIntoView(false);
 };
 function showDeveloper(show){
  developerOpen=show;main.classList.toggle('hidden',show);developer.classList.toggle('hidden',!show);
  panel.setAttribute('aria-label',tr(show?'Developer Mode':'Home settings'));
  if(show){details.classList.add('hidden');document.getElementById('renewalDiagnostics').textContent=tr('Show diagnostics');document.getElementById('renewalDiagnostics').setAttribute('aria-expanded','false');}
  focus(buttons.indexOf(document.getElementById(show?'renewalToggle':'developerOpen')));
 }
 document.getElementById('developerOpen').onclick=function(){showDeveloper(true);};
 document.getElementById('developerBack').onclick=function(){showDeveloper(false);};
 function close(){if(window.HomeThemePanel)HomeThemePanel.unmount();panel.classList.add('hidden');if(window.ThemeRuntime)ThemeRuntime.resume('settings');if(previous&&previous.focus)previous.focus();}
 document.getElementById('renewalClose').onclick=close;
 document.getElementById('homeLanguage').onclick=function(){if(window.HomeI18n)HomeI18n.openLanguagePicker();};
 document.addEventListener('home-layout-change',function(event){if(openNow()&&buttons[index].hidden&&event.homeColumnsFocus===buttons[index])focus(index+1);});
 if(window.HomeThemePanel)HomeThemePanel.mount(document.getElementById('homeThemeHost'));
 document.getElementById('homeShowAddApp').onclick=function(){if(window.HomeAppControls)HomeAppControls.toggle();};
 document.getElementById('homeAddApp').onclick=function(){if(window.HomeAppControls){close();HomeAppControls.add();}};
 document.getElementById('homeColumns').onclick=function(){if(window.HomeLayoutPanel)HomeLayoutPanel.open();};
 document.getElementById('renewalUpdates').onclick=function(){panel.classList.add('hidden');window.HomeUpdates.open({onClose:function(){panel.classList.remove('hidden');focus(buttons.indexOf(document.getElementById('renewalUpdates')));checkUpdates();}});};
 document.getElementById('renewalTV').onclick=function(){close();try{var b=new PalmServiceBridge();b.onservicecallback=function(){b.cancel();};b.call('luna://com.webos.applicationManager/launch',JSON.stringify({id:'com.palm.app.settings',params:{}}));}catch(_){}};
 // Reflow can move Columns beneath a parked cursor. Only real pointer movement
 // may take focus back from the remote or category navigation.
 var pointerX=null,pointerY=null,pointerMoved=false;
 document.addEventListener('mousemove',function(e){pointerMoved=e.clientX!==pointerX||e.clientY!==pointerY;pointerX=e.clientX;pointerY=e.clientY;},true);
 buttons.forEach(function(b,i){b.onfocus=function(){index=i;};b.addEventListener('mousemove',function(){if(pointerMoved)focus(i);});});
 document.addEventListener('keydown',function(e){if(!openNow()||window.HomeThemePanel&&HomeThemePanel.handlesKey(e))return;var k=e.keyCode;
  if([9,37,38,39,40,13,461,27].indexOf(k)<0)return;
  e.preventDefault();e.stopImmediatePropagation();
  if(document.activeElement===details&&(k===38||k===40)){
   var before=developer.scrollTop;developer.scrollTop+=k===38?-80:80;
   if(developer.scrollTop===before)focus(index+(k===38?-1:1));return;
  }
  if(document.activeElement===details&&k===13){focus(buttons.indexOf(document.getElementById('renewalDiagnostics')));return;}
  if(k===461||k===27){if(developerOpen)showDeveloper(false);else close();}else if(k===13){if(!e.repeat)buttons[index].click();}else focus(index+(k===37||k===38||(k===9&&e.shiftKey)?-1:1));
 },true);
 if(window.SettingsCategories)categories=SettingsCategories.attach(panel,main,[
  {id:'home',label:'Your Home screen',elements:[main.querySelector('.settings-home')]},
  {id:'appearance',label:'Appearance',elements:[document.getElementById('homeColumns').parentNode,document.getElementById('homeAppSettings')]},
  {id:'themes',label:'Themes',elements:[document.getElementById('homeThemeHost').parentNode]},
  {id:'language',label:'Language',elements:[document.getElementById('homeLanguage')]},
  {id:'updates',label:'Software updates',elements:[document.getElementById('renewalUpdates')]},
  {id:'advanced',label:'Advanced',elements:[document.getElementById('renewalTV')]},
  {id:'developer',label:'Developer Mode',elements:[document.getElementById('developerOpen').parentNode]}
 ]);
 window.RenewalPanel={isOpen:openNow,open:function(){if(openNow())return;if(window.HomeAppControls)HomeAppControls.refresh();if(window.HomeLayoutPanel)HomeLayoutPanel.refreshAvailability();if(window.ThemeRuntime)ThemeRuntime.suspend('settings');previous=document.activeElement;developerOpen=false;homeGeneration++;homeReplies={};main.classList.remove('hidden');developer.classList.add('hidden');panel.setAttribute('aria-label',tr('Home settings'));panel.classList.remove('hidden');details.classList.add('hidden');document.getElementById('renewalDiagnostics').textContent=tr('Show diagnostics');document.getElementById('renewalDiagnostics').setAttribute('aria-expanded','false');focus(0);action('status');refreshHome();checkUpdates();if(categories)categories.open();}};
 // No session request, token access or scheduler setup happens on launcher startup.
}());

});
