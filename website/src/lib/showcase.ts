// Website-only controls for the existing browser renderer. Never shipped to TVs.
type Theme = { id: string; title: string };
type PreviewWindow = Window & {
  RootLauncherRendered?: boolean;
  ThemeManager?: {
    list: () => Promise<Theme[]>;
    current: () => Theme;
    selectInstalled: (theme: Theme) => Promise<void>;
  };
};

export function initShowcase(element: HTMLElement) {
  const screen = element.querySelector<HTMLElement>('[data-demo-screen]')!;
  const status = element.querySelector<HTMLElement>('[data-demo-status]')!;
  const controls = element.querySelector<HTMLElement>('[data-demo-controls]')!;
  const fallback = element.querySelector<HTMLElement>('[data-showcase-start]')!;
  const keys = [
    ...element.querySelectorAll<HTMLButtonElement>('[data-demo-key]')
  ];
  let frame: HTMLIFrameElement | undefined;
  let readiness: Promise<PreviewWindow> | undefined;
  let generation = 0;
  let queue: Promise<unknown> = Promise.resolve();
  const theme = () =>
    element.querySelector<HTMLInputElement>('input:checked')!.value;
  const fit = () => {
    if (frame) frame.style.transform = `scale(${screen.clientWidth / 1920})`;
  };
  new ResizeObserver(fit).observe(screen);
  controls.hidden = false;
  fallback.hidden = true;
  keys.forEach((key) => (key.disabled = true));

  function ensureFrame() {
    if (readiness) return readiness;
    frame = document.createElement('iframe');
    frame.title = element.querySelector('.showcase-caption p')!.textContent!;
    frame.src = element.dataset.base + 'demo/root-launcher/index.html';
    frame.width = '1920';
    frame.height = '1080';
    screen.append(frame);
    fit();
    const loadingFrame = frame;
    readiness = new Promise<PreviewWindow>((resolve, reject) => {
      const deadline = Date.now() + 12000;
      function ready() {
        try {
          const win = loadingFrame.contentWindow as PreviewWindow | null;
          if (win?.RootLauncherRendered && win.ThemeManager)
            return resolve(win);
        } catch {
          // A network failure can replace the frame with a browser-owned error page.
          return reject(Error('Demo frame unavailable'));
        }
        if (Date.now() > deadline) return reject(Error('Demo startup timeout'));
        window.setTimeout(ready, 50);
      }
      ready();
    });
    return readiness;
  }

  async function start() {
    const run = ++generation;
    element.setAttribute('aria-busy', 'true');
    status.textContent = element.dataset.loading!;
    keys.forEach((key) => (key.disabled = true));
    try {
      const win = await ensureFrame();
      queue = queue
        .catch(() => {})
        .then(async () => {
          if (run !== generation) return;
          const selected = theme();
          const installed = (await win.ThemeManager!.list()).find(
            (item) => item.id === 'builtin:' + selected
          );
          if (!installed) throw Error('Bundled theme unavailable');
          if (run !== generation) return;
          await win.ThemeManager!.selectInstalled(installed);
        });
      await queue;
      if (run !== generation) return;
      element.dataset.live = 'true';
      status.textContent = element.dataset.ready!;
      keys.forEach((key) => (key.disabled = false));
      return win;
    } catch {
      if (run !== generation) return;
      frame?.remove();
      frame = undefined;
      readiness = undefined;
      delete element.dataset.live;
      status.textContent = element.dataset.error!;
    } finally {
      if (run === generation) element.setAttribute('aria-busy', 'false');
    }
  }

  async function home() {
    const win = await start();
    if (win) win.document.dispatchEvent(new Event('webOSRelaunch'));
  }
  element.querySelector('[data-home-demo]')!.addEventListener('click', home);
  for (const trigger of document.querySelectorAll<HTMLAnchorElement>(
    '[data-start-demo]'
  )) {
    trigger.addEventListener('click', (event) => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
        return;
      event.preventDefault();
      element.scrollIntoView({ block: 'start' });
      void home();
    });
  }
  element.addEventListener('change', () => {
    if (frame) void start();
  });
  const codes = { ArrowLeft: 37, ArrowRight: 39, Enter: 13 };
  for (const button of keys) {
    button.addEventListener('click', () => {
      const win = frame?.contentWindow;
      if (!win || element.dataset.live !== 'true') return;
      const key = button.dataset.demoKey as keyof typeof codes;
      for (const type of ['keydown', 'keyup'])
        win.document.dispatchEvent(
          new KeyboardEvent(type, {
            key,
            keyCode: codes[key],
            which: codes[key],
            bubbles: true
          })
        );
    });
  }
}
