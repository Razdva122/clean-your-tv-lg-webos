/* Browser-only controls; all Home rendering is owned by the real launcher. */
(() => {
  const screen=document.getElementById('screen'),status=document.getElementById('presentationStatus');
  let context='empty';
  function frame(){return screen.contentWindow;}
  function describe(){const root=location.hash==='#root';status.textContent='Simulated '+(context==='content'?'application':'startup')+' · '+(root?'Root overlay behavior':'Root behavior preview; No-root on TV remains fullscreen')+'.';}
  function open(){const win=frame();win.PREVIEW_HOME_CONTEXT=context;if(win.HomePresentationController)win.HomePresentationController.show({});describe();}
  for(const button of document.querySelectorAll('[data-context]'))button.onclick=()=>{context=button.dataset.context;for(const item of document.querySelectorAll('[data-context]'))item.setAttribute('aria-pressed',String(item===button));open();};
  document.getElementById('previewHome').onclick=()=>{const win=frame(),controller=win.HomePresentationController;if(!controller)return;win.PREVIEW_HOME_CONTEXT=context;controller.state().visible?controller.relaunch({}):controller.show({});describe();};
  document.getElementById('previewBack').onclick=()=>{const win=frame();win.document.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Escape',keyCode:27,which:27,bubbles:true}));};
  screen.addEventListener('load',()=>{frame().PREVIEW_HOME_CONTEXT=context;describe();});
})();
