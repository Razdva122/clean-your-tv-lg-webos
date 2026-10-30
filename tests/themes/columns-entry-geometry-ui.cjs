// Real CSS/layout listeners: hiding Columns must not clamp Appearance scroll.
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '../..');
const source = file => fs.readFileSync(path.join(root, file), 'utf8');
(async () => {
  const browser = await chromium.launch({headless: true, channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    for (const edition of ['root-edition/ui/root-settings', 'launcher/renewal-panel']) {
      for (const [width, height] of [[1920, 1080], [1920, 720], [640, 720]]) {
        const page = await browser.newPage({viewport: {width, height}});
        try {
          await page.setContent('<style>' + source(edition + '.css') +
            '#content{height:50vh;width:900px;overflow:auto}#themes{height:850px}</style>' +
            (edition.indexOf('root-edition')===0 ? '<section class="root-settings"><div class="root-settings-card settings-main settings-workspace">' : '<section id="renewalPanel"><div class="renewal-card settings-main settings-workspace">') +
            '<div class="settings-columns"><div id="content" class="settings-content">' +
            '<section id="appearance" class="settings-pane"><div id="themes">' +
            '<button id="apply">Apply Alpine</button><input id="field"><div id="card">Theme card</div></div>' +
            '<div id="row" class="renewal-actions settings-layout"><button id="homeColumns">Columns</button></div>' +
            '<button id="next">Fallback</button></section>' +
            '<section id="other" class="settings-pane" hidden>Other pane</section></div></div></div></section>');
          await page.addScriptTag({content: `var available=true;
            window.HomeLayoutState={state:function(){return {allowColumnOverride:available}}};
            var panel={hidden:false},buttons=[document.getElementById('homeColumns')],selected=0,index=0;
            function openNow(){return !panel.hidden}
            function move(){document.getElementById('next').focus()}
            function focus(){move()}`});
          await page.addScriptTag({content: source('launcher/layout-panel.js')});
          const listener = source(edition + '.js').split('\n').find(line => line.includes("document.addEventListener('home-layout-change'"));
          assert(listener); await page.addScriptTag({content: listener});
          for (const focused of ['apply', 'field', 'body']) {
            const result = await page.evaluate(focused => {
              available=true;document.dispatchEvent(new Event('home-layout-change'));
              const content=document.getElementById('content'),card=document.getElementById('card');
              if(focused==='body')document.activeElement.blur();else document.getElementById(focused).focus();
              content.scrollTop=content.scrollHeight;
              const snap=()=>({top:content.scrollTop,max:content.scrollHeight-content.clientHeight,
                row:document.getElementById('row').getBoundingClientRect().height,display:getComputedStyle(document.getElementById('row')).display,
                marginTop:parseFloat(getComputedStyle(document.getElementById('row')).marginTop),
                buttonHeight:document.getElementById('homeColumns').getBoundingClientRect().height,
                buttonMarginBottom:parseFloat(getComputedStyle(document.getElementById('homeColumns')).marginBottom),y:card.getBoundingClientRect().y});
              const before=snap();available=false;document.dispatchEvent(new Event('home-layout-change'));
              return {before,after:snap(),sameDOM:card===document.getElementById('card'),
                focus:document.activeElement.id,hidden:document.getElementById('homeColumns').hidden};
            }, focused);
            assert.equal(result.before.display,'flex','actual Columns wrapper flex precondition');
            if(height===1080) {
              assert.equal(result.before.row,94,'live TV wrapper height precondition');
              assert.equal(result.before.buttonHeight,76,'live TV button height precondition');
              assert.equal(result.before.buttonMarginBottom,18,'live TV button margin precondition');
              assert.equal(result.before.marginTop,16,'live TV wrapper margin precondition');
            }
            assert.deepEqual(result.after,result.before,edition+' '+height+' stable scroll/row/card geometry');
            assert(result.sameDOM && result.hidden);
            assert.equal(result.focus,focused==='body'?'':focused,'preserve actual focus');
          }
          // CSS overriding display for footprint must not expose a hidden control.
          assert.equal(await page.locator('#row').getAttribute('aria-hidden'),'true');
          assert.equal(await page.locator('#homeColumns').evaluate(el=>{
            const r=el.getBoundingClientRect();
            return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===el;
          }),false,'pointer hit-testing skips hidden Columns');
          await page.locator('#homeColumns').evaluate(el=>el.focus());
          assert.notEqual(await page.evaluate(()=>document.activeElement.id),'homeColumns');
          await page.locator('#field').focus();await page.keyboard.press('Tab');
          assert.equal(await page.evaluate(()=>document.activeElement.id),'next','Tab skips hidden Columns');
          const session=await page.context().newCDPSession(page);
          const ax=await session.send('Accessibility.getFullAXTree');
          assert(!ax.nodes.some(node=>!node.ignored && node.role?.value==='button' && node.name?.value==='Columns'),
            'hidden Columns absent from accessibility tree');await session.detach();
          await page.evaluate(()=>{available=true;document.dispatchEvent(new Event('home-layout-change'));});
          assert.equal(await page.locator('#row').getAttribute('aria-hidden'),'false');
          await page.locator('#homeColumns').focus();
          assert.equal(await page.evaluate(()=>document.activeElement.id),'homeColumns','available Columns focus works');
          await page.evaluate(()=>{available=false;document.dispatchEvent(new Event('home-layout-change'));});
          assert.equal(await page.evaluate(()=>document.activeElement.id),'next','actual Columns focus retains fallback');
          assert.equal(await page.locator('#other').evaluate(el=>el.getBoundingClientRect().height),0,'other pane remains hidden');
          await page.evaluate(()=>{document.getElementById('appearance').hidden=true;panel.hidden=true;available=true;document.dispatchEvent(new Event('home-layout-change'));});
          assert.equal(await page.locator('#row').evaluate(el=>el.getBoundingClientRect().height),0,'closed pane remains hidden');
        } finally {await page.close();}
      }
    }
    console.log('PASS Columns row geometry, focus, navigation and accessibility in both editions at 1080/720 and narrow width');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
