const version = document.currentScript.dataset.version;
async function watch() {
  try {
    const response = await fetch('/preview/version', { cache: 'no-store' });
    if (response.ok && (await response.text()) !== version) {
      location.reload();
      return;
    }
  } catch (_) {
    /* Retry when the local server is available again. */
  }
  setTimeout(watch, 1000);
}
setTimeout(watch, 1000);
