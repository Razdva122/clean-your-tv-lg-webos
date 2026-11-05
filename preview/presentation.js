/* Browser-only remote controls for the real, full-screen Home renderer. */
(() => {
  const screen=document.getElementById('screen'),status=document.getElementById('presentationStatus');
  function frame(){return screen.contentWindow;}
  function describe(){status.textContent=(location.hash==='#root'?'Root':'No-root')+' Home preview with its own wallpaper. TV functions are simulated.';}
  document.getElementById('previewHome').onclick=()=>{const win=frame();win.document.dispatchEvent(new win.Event('webOSRelaunch'));win.focus();};
  document.getElementById('previewBack').onclick=()=>{const win=frame();win.document.dispatchEvent(new win.KeyboardEvent('keydown',{key:'Escape',keyCode:27,which:27,bubbles:true}));win.focus();};
  screen.addEventListener('load',describe);
  describe();
})();
