// Run with Playwright available in NODE_PATH. Exercises real packaged Root UI
// and shared Home UI with deterministic device replies; never connects to a TV.
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  path = require('node:path'),
  os = require('node:os'),
  http = require('node:http'),
  { execFileSync } = require('node:child_process');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const root = path.resolve(__dirname, '..'),
    tmp = fs.realpathSync(
      fs.mkdtempSync(path.join(os.tmpdir(), 'cytv-companion-'))
    );
  // Build both standalone apps exactly as their production builders stage them.
  execFileSync(
    process.env.PYTHON || 'python3',
    [
      '-c',
      `
import sys,runpy
from pathlib import Path
sys.path.insert(0,'root-edition')
import build_updater
sys.path.insert(0,'.')
from cytv.package import data_files
work=Path(sys.argv[1])
root=build_updater.build(work/'bundle')
runpy.run_path('scripts/build-cytv.py')['stage_updater'](work)
for package,folder,app in ((root,'root','com.cleanyourtv.root.updater'),(work/'updater.ipk','updater-app','com.cleanyourtv.updater')):
 prefix='usr/palm/applications/'+app+'/'
 for name,data in data_files(package.read_bytes()).items():
  if name.startswith(prefix):
   out=work/folder/name[len(prefix):];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
`,
      tmp
    ],
    { cwd: root }
  );
  const server = http.createServer((req, res) => {
    let name = decodeURIComponent(req.url.split('?')[0]);
    let file;
    if (name.startsWith('/root/') || name.startsWith('/updater-app/'))
      file = path.join(tmp, name);
    else file = path.join(root, name);
    if (!file.startsWith(root + path.sep) && !file.startsWith(tmp + path.sep)) {
      res.writeHead(403);
      return res.end();
    }
    const types = {
      '.html': 'text/html',
      '.js': 'text/javascript',
      '.css': 'text/css',
      '.ttf': 'font/ttf',
      '.png': 'image/png'
    };
    try {
      res.setHeader(
        'Content-Type',
        types[path.extname(file)] || 'application/octet-stream'
      );
      res.end(fs.readFileSync(file));
    } catch (_) {
      res.writeHead(404);
      res.end();
    }
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      ...(process.env.CHROMIUM_PATH
        ? { executablePath: process.env.CHROMIUM_PATH }
        : { channel: 'chrome' })
    });
    const page = await browser.newPage({
        viewport: { width: 1920, height: 1080 }
      }),
      errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('response', (r) => {
      if (
        r.status() >= 400 &&
        ['script', 'stylesheet', 'font'].includes(r.request().resourceType())
      )
        errors.push('Asset ' + r.status() + ': ' + r.url());
    });
    await page.route('**/launcher/apps.js', (r) =>
      r.fulfill({
        body: 'window.TV_APPS={apps:[{id:"test.app",title:"Test App",icon:"brand-v2-icon.png"}],inputs:[]};'
      })
    );
    await page.route('**/launcher/config.js', (r) =>
      r.fulfill({
        body: 'window.CONFIG={columns:5,dockApps:[],hiddenApps:[]};'
      })
    );
    await page.addInitScript(() => {
      localStorage.setItem('tvhome.language', 'ru');
      window.calls = [];
      window.helperRunning = true;
      window.helperBlocked = false;
      window.update = null;
      window.systemUpdate = null;
      window.failStatus = false;
      window.supervisorAbsent =
        new URL(location.href).searchParams.get('supervisor') === 'absent';
      window.PalmSystem = {
        launchParams: JSON.stringify({ showHelper: true })
      };
      window.PalmServiceBridge = class {
        cancel() {
          clearTimeout(this.timer);
        }
        call(uri, raw) {
          const p = JSON.parse(raw);
          window.calls.push({ uri, p });
          let reply = { returnValue: true };
          if (uri.endsWith('/getSystemSettings'))
            reply.settings = { localeInfo: { locales: { UI: 'ru-RU' } } };
          else if (uri.endsWith('/homeStatus')) reply.enabled = true;
          else if (uri === 'luna://com.local.nativehome.service/status')
            Object.assign(reply, {
              running: window.helperRunning,
              blocked: window.helperBlocked
            });
          else if (
            uri.startsWith('luna://com.cleanyourtv.system.updater.service/')
          ) {
            if (supervisorAbsent)
              reply = {
                returnValue: false,
                errorText: 'Service does not exist'
              };
            else if (failStatus)
              reply = {
                returnValue: false,
                errorText: 'Status is unavailable.'
              };
            else
              reply.result = uri.endsWith('/restoreProfile')
                ? null
                : window.systemUpdate;
          } else if (
            uri.startsWith('luna://com.cleanyourtv.updater.service/') ||
            uri.startsWith('luna://com.cleanyourtv.root.updater.service/')
          ) {
            reply = failStatus
              ? { returnValue: false, errorText: 'Status is unavailable.' }
              : { returnValue: true, result: window.update };
          } else if (uri.endsWith('/status'))
            reply.state = { enabled: false, last: {} };
          else if (uri.endsWith('/listApps')) reply.apps = [];
          else if (
            uri.endsWith('/launch') &&
            p.params &&
            p.params.nativeHomeStart
          ) {
            window.helperRunning = true;
            window.helperBlocked = false;
          }
          this.timer = setTimeout(
            () => this.onservicecallback(JSON.stringify(reply)),
            10
          );
        }
      };
    });
    const base = 'http://127.0.0.1:' + server.address().port;
    await page.goto(base + '/launcher/index.html');
    const helper = page.locator('.root-settings').filter({
      has: page.getByRole('heading', { name: 'Home Helper', exact: true })
    });
    await helper.waitFor();
    await page.locator('#tiles .item[data-app-id]').waitFor();
    assert.equal(
      await page.evaluate(() => document.activeElement.textContent),
      'Открыть Home',
      'initial Helper panel retains focus after Home renders'
    );
    fs.mkdirSync(path.join(root, 'build/companion-ui'), { recursive: true });
    await page.screenshot({
      path: path.join(root, 'build/companion-ui/helper-ru.png')
    });
    await page.keyboard.press('Enter');
    await helper.waitFor({ state: 'hidden' });
    assert(
      !(await page.evaluate(() => calls.some((c) => c.p.id === 'test.app'))),
      'closing Helper must not launch the underlying app on OK release'
    );
    await page.evaluate(() =>
      document.dispatchEvent(new CustomEvent('webOSRelaunch', { detail: {} }))
    );
    await helper.waitFor({ timeout: 1500 });
    await page.keyboard.press('Escape');
    await page.evaluate(() => {
      helperRunning = false;
      helperBlocked = true;
      document.dispatchEvent(
        new CustomEvent('webOSRelaunch', { detail: { showHelper: true } })
      );
    });
    await helper.waitFor();
    await helper.getByText(/остановлен для безопасности/).waitFor();
    assert((await helper.innerText()).includes('остановлен для безопасности'));
    assert(
      !(await page.evaluate(() =>
        calls.some((c) => c.p.params && c.p.params.nativeHomeStart)
      )),
      'viewing stopped Helper must not restart it'
    );
    await helper
      .getByRole('button', { name: 'Запустить Helper', exact: true })
      .click();
    await page.locator('#homeConfirmation').waitFor();
    await page
      .locator('#homeConfirmation')
      .getByRole('button', { name: 'Отмена' })
      .click();
    assert(
      !(await page.evaluate(() =>
        calls.some((c) => c.p.params && c.p.params.nativeHomeStart)
      ))
    );
    await helper
      .getByRole('button', { name: 'Запустить Helper', exact: true })
      .click();
    await page
      .locator('#homeConfirmation')
      .getByRole('button', { name: 'Запустить Helper', exact: true })
      .click();
    assert.equal(
      await page.evaluate(
        () =>
          calls.filter((c) => c.p.params && c.p.params.nativeHomeStart).length
      ),
      1
    );
    await page.waitForFunction(
      () =>
        Array.from(document.querySelectorAll('.root-settings button')).some(
          (b) => b.textContent === 'Запустить Helper' && b.hidden
        ),
      null,
      { timeout: 4000 }
    );
    assert.equal(
      await page.evaluate(() => document.activeElement.textContent),
      'Открыть Home',
      'focus leaves the hidden restart action'
    );
    await helper
      .getByRole('button', { name: 'Обновить состояние', exact: true })
      .click();
    await helper.getByRole('button', { name: 'Настроить кнопку Home' }).click();
    await page.locator('#renewalPanel').waitFor();
    async function noMutations() {
      assert(
        !(await page.evaluate(() =>
          calls.some((c) => /\/(install|rollback|confirm)$/.test(c.uri))
        )),
        'viewing or cancelling must not install, roll back or confirm'
      );
    }
    await noMutations();
    for (const supervisor of ['present', 'absent'])
      for (const url of ['/updater-app/index.html', '/root/index.html']) {
        const system = supervisor === 'present';
        await page.goto(base + url + (system ? '' : '?supervisor=absent'));
        if (system) {
          const panel = page.locator('#systemUpdates');
          await panel.waitFor();
          await page
            .locator('#systemUpdateStatus')
            .filter({
              hasText: 'Предыдущее обновление для отката пока не сохранено.'
            })
            .waitFor();
          assert(await page.locator('#systemUpdateInstall').isHidden());
          assert(await page.locator('#systemUpdateRollback').isDisabled());
          assert.equal(
            await page.evaluate(
              () =>
                calls.filter(
                  (c) =>
                    c.uri ===
                      'luna://com.cleanyourtv.updater.service/reconcile' ||
                    c.uri ===
                      'luna://com.cleanyourtv.root.updater.service/status'
                ).length
            ),
            0,
            'present supervisor owns recovery'
          );
          await page.evaluate(() => {
            failStatus = true;
            document.dispatchEvent(new Event('webOSRelaunch'));
          });
          await page
            .getByText('Не удалось проверить состояние.', { exact: true })
            .waitFor();
          assert(await page.locator('#systemUpdateRollback').isDisabled());
          assert(
            !(await page.evaluate(() =>
              calls.some(
                (c) =>
                  c.uri ===
                    'luna://com.cleanyourtv.updater.service/reconcile' ||
                  c.uri === 'luna://com.cleanyourtv.root.updater.service/status'
              )
            )),
            'failed present supervisor must not fall back'
          );
          await page.evaluate(
            (edition) => {
              failStatus = false;
              systemUpdate = {
                id: 'a'.repeat(32),
                edition,
                phase: 'complete',
                canRollback: true
              };
              document.dispatchEvent(new Event('webOSRelaunch'));
            },
            url.includes('updater-app') ? 'no-root' : 'root'
          );
          await page.waitForFunction(
            () => !document.getElementById('systemUpdateRollback').disabled
          );
          await page.locator('#systemUpdateRollback').click();
          await page.locator('#homeConfirmation').waitFor();
          assert(
            (await page.locator('#homeConfirmation').innerText()).includes(
              'будут потеряны'
            )
          );
          await page.keyboard.press('Escape');
          await noMutations();
          await page.locator('#systemUpdateBack').click();
          await panel.waitFor({ state: 'hidden' });
          assert(
            await page.evaluate(
              (home) =>
                calls.some(
                  (c) =>
                    c.uri === 'luna://com.webos.applicationManager/launch' &&
                    c.p.id === home
                ),
              url.includes('updater-app')
                ? 'com.gathin.tvhome'
                : 'com.cleanyourtv.root.preview'
            ),
            'recovery returns to its own edition Home'
          );
          await page.evaluate(() =>
            document.dispatchEvent(new Event('webOSRelaunch'))
          );
          await panel.waitFor();
          assert(
            await page.evaluate(() => {
              const button = document.activeElement,
                panel = document.getElementById('systemUpdates');
              return (
                button.tagName === 'BUTTON' &&
                panel.contains(button) &&
                button.offsetWidth > 0 &&
                button.offsetHeight > 0 &&
                !button.disabled &&
                !button.hidden
              );
            }),
            'reopened recovery retains an enabled visible button inside the System panel'
          );
        } else {
          await page
            .getByText('Восстановление не требуется.', { exact: false })
            .waitFor();
          assert(
            (await page.locator('body').innerText()).includes(
              'Обычные обновления доступны в настройках Home.'
            )
          );
          assert.equal(
            await page
              .getByRole('button', {
                name: /Восстановить предыдущую версию|Откатить/
              })
              .count(),
            0
          );
          assert(
            await page.evaluate(() =>
              calls.some(
                (c) =>
                  c.uri ===
                  'luna://com.cleanyourtv.system.updater.service/status'
              )
            ),
            'legacy fallback follows confirmed supervisor absence'
          );
          if (url.includes('updater-app')) {
            assert(await page.locator('#restore').isHidden());
            assert.equal(
              await page.evaluate(() => document.activeElement.id),
              'open'
            );
            await page.evaluate(() => {
              failStatus = true;
              document.dispatchEvent(new Event('webOSRelaunch'));
            });
            await page
              .getByText('Не удалось проверить состояние.', { exact: true })
              .waitFor();
            assert(await page.locator('#restore').isHidden());
            await page.evaluate(() => {
              failStatus = false;
              update = { status: 'complete', prior: { home: '1.3.5' } };
              document.dispatchEvent(new Event('webOSRelaunch'));
            });
            await page.locator('#restore').waitFor();
            await page.locator('#restore').click();
            await page.locator('#homeConfirmation').waitFor();
            assert(
              (await page.locator('#homeConfirmation').innerText()).includes(
                'будут потеряны'
              )
            );
            await page.keyboard.press('Escape');
            await noMutations();
          }
          if (url === '/root/index.html') {
            await page
              .getByRole('button', { name: 'Открыть Home', exact: true })
              .click();
            await page
              .locator('.root-updates')
              .filter({ visible: true })
              .waitFor({ state: 'hidden' });
            await page.evaluate(() =>
              document.dispatchEvent(new Event('webOSRelaunch'))
            );
            await page
              .locator('.root-updates')
              .filter({ visible: true })
              .waitFor({ timeout: 1500 });
            assert.equal(
              await page.evaluate(() => document.activeElement.textContent),
              'Открыть Home'
            );
          }
        }
        await noMutations();
        await page.evaluate(() => document.fonts.ready);
        const actions = await page
          .locator('button:visible')
          .evaluateAll((bs) => bs.map((b) => b.getBoundingClientRect().bottom));
        assert(
          actions.every((y) => y <= 1080),
          'actions fit TV viewport'
        );
        fs.mkdirSync(path.join(root, 'build/companion-ui'), {
          recursive: true
        });
        await page.screenshot({
          path: path.join(
            root,
            'build/companion-ui',
            supervisor +
              '-' +
              (url.includes('updater-app')
                ? 'updater-ru.png'
                : 'root-updater-ru.png')
          )
        });
      }
    assert.deepEqual(errors, []);
    console.log(
      'PASS companion UI: manual Helper focus/OK release, emergency restart consent, settings, both packaged Updaters with present/absent System supervisor, unavailable status and cancelled restore confirmation without mutations'
    );
  } finally {
    if (browser) await browser.close();
    await new Promise((r) => server.close(r));
    fs.rmSync(tmp, { recursive: true, force: true });
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
