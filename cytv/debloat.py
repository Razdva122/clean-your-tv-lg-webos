"""Optional LG settings changes after installation, with per-setting readback."""
from contextlib import ExitStack
import json
import shlex
import time

from . import prompts
from .i18n import translate as tr
from .state import private_write
from .tv import SSAP

TITLE = 'Debloat'
SELECT = 'Select Debloat settings: '
REVIEW = 'Review Debloat results: '
CONTINUE = 'Continue to customization'
NOTICE = 'If the original value cannot be read, the selected change cannot be automatically undone.'
GROUPS = (
    ('LG Home', (
        ('homePromotion', 'general', 'Turn off sponsored tiles', 'off'),
        ('contentRecommendation', 'other', 'Turn off content recommendations', 'off'),
    )),
    ('Ads and promotions', (
        ('screenSaverAd', 'general', 'Turn off screen saver ads', 'off'),
        ('livePromotion', 'option', 'Turn off promotions while watching', 'off'),
        ('webOSPromotionVideo', 'option', 'Turn off webOS promotional video', 'off'),
    )),
    ('Privacy', (
        ('livePlus', 'option', 'Turn off Live Plus', 'off'),
        ('adCookie', 'general', 'Turn off advertising cookies', 'off'),
        ('lmt', 'general', 'Limit ad tracking', 'on'),
    )),
    ('Tips and notifications', (
        ('aiNudge', 'general', 'Turn off Smart Tips', 'off'),
        ('sportsAlarm', 'general', 'Turn off sports notifications', 'off'),
    )),
)
SETTINGS = {key: (category, label, target) for _, rows in GROUPS for key, category, label, target in rows}
RESULTS = {
    'already': ('✓', '#b4ada4', 'Already in the requested state'),
    'verified': ('✓', '#90cfad', 'Successfully applied and verified'),
    'failed': ('×', '#ff8580', 'Could not change the setting'),
    'unverified': ('✓', '#b4ada4', 'Command sent. The result could not be verified.'),
}
SERVICE = 'com.webos.settingsservice/'
# Execute in the existing Developer Mode SSH jail. Return only the requested
# value so private data from the preferences files never leaves the TV.
READ_PREFERENCE = r'''
var fs = require('fs');
var args = JSON.parse(process.argv[process.argv.length - 1]);
var path = '/var/luna/preferences/' + args[0];
var value = null;
try {
    var info = fs.statSync(path);
    if (info.isFile() && info.size <= 1048576) {
        var data = JSON.parse(fs.readFileSync(path, 'utf8'));
        if (data[args[1]] === 'on' || data[args[1]] === 'off') value = data[args[1]];
    }
} catch (error) {}
process.stdout.write(JSON.stringify(value));
'''


def read(remote, category, key):
    try:
        if remote.root:
            reply = remote.luna(SERVICE + 'getSystemSettings', {'category': category, 'keys': [key]}, timeout=5)
            value = reply.get('settings', {}).get(key) if reply.get('returnValue') is True else None
        else:
            command = shlex.join(['/usr/bin/node', '-e', READ_PREFERENCE, json.dumps([category, key])])
            value = json.loads(remote.run(command, timeout=5))
        return value if value in ('on', 'off') else None
    except Exception:
        return None


def read_ssap(tv, category, key):
    # Only Live Plus is known to be readable over paired SSAP.
    if tv is None or key != 'livePlus':
        return None
    try:
        reply = tv.call('ssap://settings/getSystemSettings', {'category': category, 'keys': [key]}, timeout=5)
        value = reply.get('settings', {}).get(key) if reply.get('returnValue') is True else None
        return value if value in ('on', 'off') else None
    except Exception:
        return None


def read_current(remote, category, key, tv):
    return read(remote, category, key) or read_ssap(tv, category, key)


def remember(path, key, original, target):
    try:
        journal = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        journal = {'schema': 1, 'settings': {}}
    if journal['schema'] != 1 or not isinstance(journal['settings'], dict):
        raise ValueError('Invalid Debloat record')
    if key not in journal['settings']:
        journal['settings'][key] = {'original': original, 'target': target}
        private_write(path, json.dumps(journal).encode())


def apply(installer, selected, progress=lambda _: None):
    if not isinstance(selected, list) or any(not isinstance(key, str) or key not in SETTINGS for key in selected):
        raise ValueError('Invalid Debloat selection')
    if not selected:
        return {}
    profile, remote = installer.profile, installer.remote
    directory = installer.store.device_dir(profile)
    results = {}
    use_ssap = profile['edition'] == 'no-root'
    tv = None
    ssap_unavailable = False
    with ExitStack() as stack:
        for key, (category, label, target) in SETTINGS.items():
            if key not in selected:
                continue
            progress(label)
            original = read(remote, category, key)
            results[key] = 'already' if original == target else 'failed'
            if original == target or (use_ssap and ssap_unavailable):
                continue
            try:
                if use_ssap and tv is None:
                    ssap_unavailable = True
                    tv = stack.enter_context(SSAP(profile['host'], directory, progress, settings_write=True))
                    ssap_unavailable = False
                if original is None and use_ssap:
                    original = read_ssap(tv, category, key)
                    if original == target:
                        results[key] = 'already'
                        continue
                if original is not None:
                    remember(directory / 'debloat.json', key, original, target)
                payload = {'category': category, 'settings': {key: target}}
                if use_ssap:
                    reply = tv.call('ssap://settings/setSystemSettings', payload, timeout=8)
                elif remote.root:
                    reply = remote.luna(SERVICE + 'setSystemSettings', payload, timeout=8)
                else:
                    continue
                if reply.get('returnValue') is not True:
                    continue
            except Exception:
                continue
            actual = read_current(remote, category, key, tv)
            # The on-disk snapshot can lag the SSAP action. Retry reads only.
            for delay in (.25, .5, 1):
                if actual == target or (actual is None and original is None):
                    break
                time.sleep(delay)
                actual = read_current(remote, category, key, tv)
            results[key] = 'verified' if actual == target else 'unverified' if actual is None else 'failed'
    return results


def run(installer, ask, write):
    write.step(5, TITLE)
    if write.frontend == 'desktop':
        try:
            selected = json.loads(prompts.answer(ask, SELECT))
        except (ValueError, TypeError):
            selected = None
    else:
        selected = []
        if write.frontend == 'android':
            write.option('y', TITLE)
            write.option('n', 'Skip Debloat')
        if prompts.confirm('Apply optional Debloat settings?', ask, write):
            write(NOTICE)
            for group, rows in GROUPS:
                write.heading(group)
                for _, _, label, _ in rows:
                    write(label)
                write.option(0, 'Skip this group')
                write.option(1, 'Select all in this group')
                write.option(2, 'Choose individual settings')
                choice = prompts.number(ask, write, 'Debloat group [0]: ', 0, 2, default=0)
                if choice == 1:
                    selected.extend(key for key, *_ in rows)
                elif choice == 2:
                    for key, _, label, _ in rows:
                        if write.frontend == 'android':
                            write.option('y', 'Apply')
                            write.option('n', 'Skip')
                        if prompts.confirm(tr(label) + '?', ask, write):
                            selected.append(key)
        if selected:
            write.heading('Selected Debloat changes')
            for key in selected:
                write(SETTINGS[key][1])
            if write.frontend == 'android':
                write.option('y', 'Continue')
                write.option('n', 'Skip Debloat')
            if not prompts.confirm('Apply the selected changes?', ask, write):
                return
    if not selected:
        return
    try:
        results = apply(installer, selected, write)
    except (OSError, ValueError):
        write.error('Could not apply Debloat settings.')
        return
    if write.frontend == 'desktop':
        write.debloat_results(results)
        prompts.answer(ask, REVIEW)
    else:
        write.heading('Debloat results')
        for key, status in results.items():
            icon, _, message = RESULTS[status]
            write(f'{icon} {tr(SETTINGS[key][1])} — {tr(message)}')
        if write.frontend == 'android':
            write.option('1', CONTINUE)
        prompts.answer(ask, tr('Continue to customization: '))
