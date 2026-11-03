/* Trusted settings: poster URLs are borrowed from HomeWallpaper, never revoked here. */
(function(root){
 'use strict';
 var panel,preview,title,capability,actual,notice,dimValue,qualityButtons=[],minus,plus,reset;
 function t(source){var language=root.HomeI18n&&root.HomeI18n.language(),strings=root.HomeWallpaperLocales&&root.HomeWallpaperLocales[language];return strings&&strings[source]|| (root.HomeI18n?root.HomeI18n.t(source):source);}
 function node(tag,parent,id){var el=document.createElement(tag);if(id)el.id=id;parent.appendChild(el);return el;}
 function state(){return root.HomeWallpaper&&root.HomeWallpaper.state?root.HomeWallpaper.state():{};}
 function label(quality){return t(quality==='auto'?'Auto':quality==='image'?'Image':quality==='4k'?'4K':'1080p');}
 function refresh(){
  if(!panel)return;
  var focused=document.activeElement,wasInside=panel.contains(focused);
  var value=state(),available=value.available||[],hasPoster=!!value.posterURL,cap=value.capabilities||{},dim=typeof value.dim==='number'?value.dim:0;
  title.textContent=value.title||'Classic';
  preview.hidden=!hasPoster;
  if(hasPoster){if(preview.getAttribute('src')!==value.posterURL)preview.src=value.posterURL;preview.alt=t('Current theme wallpaper');}else preview.removeAttribute('src');
  capability.textContent=t('TV capability')+': '+t(cap.uhd===true?'4K supported':cap.uhd===false?'4K not detected':'Unknown');
  actual.textContent=t('Current mode')+': '+(hasPoster&&value.actualQuality?label(value.actualQuality):t('No wallpaper'));
  notice.textContent=!hasPoster?t('This theme has no wallpaper.'):available.indexOf('4k')<0&&available.indexOf('1080p')<0?t('This theme uses an image only.'):t('Auto uses detected TV support. Playback may fall back to an image.');
  if(value.notice)notice.textContent+=' '+t(value.notice);
  qualityButtons.forEach(function(button){var q=button.getAttribute('data-wallpaper-quality');button.textContent=label(q);button.disabled=!hasPoster||(q!=='auto'&&available.indexOf(q)<0)||(q==='4k'&&cap.uhd===false);button.setAttribute('aria-pressed',String((value.preferenceQuality||'auto')===q));});
  dimValue.textContent=t('Dimming')+': '+Math.round(dim*100)+'%';minus.textContent=t('Less dimming');plus.textContent=t('More dimming');reset.textContent=t('Reset to theme defaults');
  minus.disabled=!hasPoster||dim<=0;plus.disabled=!hasPoster||dim>=.85;reset.disabled=!hasPoster;
  if(wasInside&&focused.disabled){var target=hasPoster?(focused===plus?minus:focused===minus?plus:qualityButtons[0]):document.getElementById('settings-tab-wallpapers');if(target&&!target.disabled)target.focus();}
 }
 function change(method,value){
  if(!root.HomeWallpaper||!root.HomeWallpaper[method])return;
  try{Promise.resolve(root.HomeWallpaper[method](value)).then(refresh,function(){notice.textContent=t('Could not change wallpaper settings.');});}
  catch(_){notice.textContent=t('Could not change wallpaper settings.');}
 }
 function button(parent,id,action){var el=node('button',parent,id);el.type='button';el.onclick=action;return el;}
 function mount(host){
  if(panel){host.appendChild(panel);refresh();return;}
  panel=node('div',host,'homeWallpaperPanel');
  var summary=node('div',panel);summary.className='wallpaper-summary';
  preview=node('img',summary,'wallpaperPreview');
  var info=node('div',summary);info.className='wallpaper-info';title=node('h4',info,'wallpaperTitle');capability=node('p',info,'wallpaperCapability');actual=node('p',info,'wallpaperActual');
  notice=node('p',panel,'wallpaperNotice');notice.setAttribute('aria-live','polite');
  var qualities=node('div',panel);qualities.className='wallpaper-quality';qualities.setAttribute('role','group');qualities.setAttribute('aria-label',t('Wallpaper quality'));
  ['auto','4k','1080p','image'].forEach(function(q){var el=button(qualities,null,function(){change('setQuality',q);});el.setAttribute('data-wallpaper-quality',q);qualityButtons.push(el);});
  var dim=node('div',panel);dim.className='wallpaper-dim';dimValue=node('p',dim,'wallpaperDimValue');
  minus=button(dim,'wallpaperDimMinus',function(){change('setDim',Math.max(0,Math.round(((state().dim||0)-.05)*100)/100));});
  plus=button(dim,'wallpaperDimPlus',function(){change('setDim',Math.min(.85,Math.round(((state().dim||0)+.05)*100)/100));});
  reset=button(panel,'wallpaperReset',function(){change('resetPreferences');});refresh();
 }
 document.addEventListener('home-wallpaper-change',refresh);
 root.HomeWallpaperPanel={mount:mount,refresh:refresh,t:t};
}(window));
