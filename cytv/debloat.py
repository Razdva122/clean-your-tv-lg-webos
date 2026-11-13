"""Optional LG settings changes after installation, with per-setting readback."""
from contextlib import ExitStack
import json
import shlex
import time

from . import prompts
from .errors import UserError, TVRejected
from .i18n import translate as tr
from .state import private_write
from .tv import SSAP

TITLE = 'Debloat'
SELECT = 'Select Debloat settings: '
REVIEW = 'Review Debloat results: '
CONTINUE = 'Continue to customization'
RESTORE_PROMPT = 'Restore saved Debloat settings before removal?'
RESTORE_LABEL = 'Restore saved Debloat settings'
SKIP_RESTORE = 'Skip restoration'
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
SETTING_NAMES = {
    'homePromotion': 'Sponsored tiles',
    'contentRecommendation': 'Content recommendations',
    'screenSaverAd': 'Screen saver ads',
    'livePromotion': 'Promotions while watching',
    'webOSPromotionVideo': 'webOS promotional video',
    'livePlus': 'Live Plus',
    'adCookie': 'Advertising cookies',
    'lmt': 'Ad tracking limit',
    'aiNudge': 'Smart Tips',
    'sportsAlarm': 'Sports notifications',
}
RESULTS = {
    'already': ('✓', '#b4ada4', 'Already in the requested state'),
    'verified': ('✓', '#90cfad', 'Successfully applied and verified'),
    'failed': ('×', '#ff8580', 'Could not change the setting'),
    'firmware-blocked': ('×', '#ff8580', 'This TV firmware blocks changing this setting in No-root.'),
    'unverified': ('✓', '#b4ada4', 'Command sent. The result could not be verified.'),
}
DIAGNOSTIC_RESULTS = ('already', 'verified', 'pairing-rejected', 'pairing-timeout',
                      'pairing-unavailable', 'write-rejected', 'write-unavailable',
                      'journal-failed', 'verify-unavailable', 'verify-mismatch')
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


def set_value(remote, tv, category, key, value):
    payload = {'category': category, 'settings': {key: value}}
    if tv is not None:
        return tv.call('ssap://settings/setSystemSettings', payload, timeout=8)
    return remote.luna(SERVICE + 'setSystemSettings', payload, timeout=8)


def verify_value(remote, tv, category, key, value, previous):
    actual = read_current(remote, category, key, tv)
    # The on-disk snapshot can lag the SSAP action. Retry reads only.
    for delay in (.25, .5, 1):
        if actual == value or (actual is None and previous is None):
            break
        time.sleep(delay)
        actual = read_current(remote, category, key, tv)
    return actual


def offer_restore(remote, store, profile, ask, write):
    """Offer one best-effort restoration before the normal removal operation."""
    try:
        path = store.device_dir(profile) / 'debloat.json'
        journal = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(journal, dict) or journal.get('schema') != 1 or not isinstance(journal.get('settings'), dict):
            raise ValueError('Invalid Debloat record')
    except FileNotFoundError:
        return
    except (OSError, ValueError):
        write('Could not read the saved Debloat settings.')
        return

    entries = journal['settings']
    eligible = [
        key for key, (_, _, target) in SETTINGS.items()
        if isinstance(entries.get(key), dict)
        and entries[key].get('target') == target
        and entries[key].get('original') in ('on', 'off')
        and entries[key]['original'] != target
    ]
    if not eligible:
        return
    remaining = entries.copy()
    with ExitStack() as stack:
        tv = None
        current_values = {key: read(remote, SETTINGS[key][0], key) for key in eligible}
        # Live Plus can be read over an existing pairing without a TV prompt.
        if not remote.root and 'livePlus' in current_values and current_values['livePlus'] is None:
            try:
                tv = stack.enter_context(SSAP(profile['host'], path.parent, write,
                                             settings_write=True, reuse_only=True))
            except Exception:
                pass
            current_values['livePlus'] = read_ssap(tv, SETTINGS['livePlus'][0], 'livePlus')
        planned = {key for key, current in current_values.items() if current == entries[key]['target']}
        if write.frontend == 'desktop' and planned:
            write.step(1, 'Debloat restoration preview')
        else:
            write.heading('Debloat restoration preview')
        states = {'on': tr('On'), 'off': tr('Off')}
        for key, current in current_values.items():
            label = tr(SETTING_NAMES[key])
            if key in planned:
                original = entries[key]['original']
                write(f'{label} — {states[current]} → {states[original]}')
            elif current is None:
                write(f"{label} — {tr('Could not read the current value')}")
            else:
                write(f"{label} — {tr('Already at the saved original value')}")
        if not planned:
            return
        if write.frontend == 'android':
            write.option('y', RESTORE_LABEL)
            write.option('n', SKIP_RESTORE)
        if not prompts.confirm(RESTORE_PROMPT, ask, write):
            return

        write.heading('Debloat restoration results')
        pairing_failed = False
        for key in eligible:
            original = entries[key]['original']
            if key not in planned:
                if current_values[key] == original:
                    del remaining[key]
                continue
            category, _, target = SETTINGS[key]
            if not remote.root and tv is None and not pairing_failed:
                try:
                    tv = stack.enter_context(SSAP(profile['host'], path.parent, write, settings_write=True))
                except Exception:
                    pairing_failed = True
            current = read_current(remote, category, key, tv)
            if current == original:
                message = 'Already at the saved original value'
            elif current is None:
                message = 'Could not read the current value'
            elif current == target and (remote.root or tv is not None):
                try:
                    reply = set_value(remote, tv, category, key, original)
                except Exception:
                    reply = None
                if isinstance(reply, dict) and reply.get('returnValue') is True:
                    actual = verify_value(remote, tv, category, key, original, current)
                    message = 'Restored and verified' if actual == original else 'Could not verify the restored value'
                else:
                    message = 'Could not restore the setting'
            else:
                message = 'Could not restore the setting'
            if message in ('Already at the saved original value', 'Restored and verified'):
                del remaining[key]
            write(f'{tr(SETTING_NAMES[key])} — {tr(message)}')

    if remaining == entries:
        return
    journal['settings'] = remaining
    try:
        private_write(path, json.dumps(journal).encode())
    except OSError:
        write('Could not update the saved Debloat settings.')


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


def apply(installer, selected, progress=lambda _: None, *, diagnostic=None):
    if not isinstance(selected, list) or any(not isinstance(key, str) or key not in SETTINGS for key in selected):
        raise ValueError('Invalid Debloat selection')
    if not selected:
        return {}
    profile, remote = installer.profile, installer.remote
    directory = installer.store.device_dir(profile)
    results = {}
    events = diagnostic if diagnostic is not None else {}
    use_ssap = not remote.root
    tv = None
    pairing_failure = None
    with ExitStack() as stack:
        for key, (category, label, target) in SETTINGS.items():
            if key not in selected:
                continue
            progress(label)
            original = read(remote, category, key)
            if original == target:
                results[key] = events[key] = 'already'
                continue
            results[key] = 'failed'
            if use_ssap and tv is None and pairing_failure is None:
                try:
                    tv = stack.enter_context(SSAP(profile['host'], directory, progress, settings_write=True))
                except Exception as exc:
                    reason = exc.reason_code if isinstance(exc, UserError) else None
                    pairing_failure = reason if reason in ('pairing-rejected', 'pairing-timeout') else 'pairing-unavailable'
            if pairing_failure:
                events[key] = pairing_failure
                continue
            if original is None and use_ssap:
                original = read_ssap(tv, category, key)
                if original == target:
                    results[key] = events[key] = 'already'
                    continue
            if original is not None:
                try:
                    remember(directory / 'debloat.json', key, original, target)
                except Exception:
                    events[key] = 'journal-failed'
                    continue
            try:
                reply = set_value(remote, tv, category, key, target)
            except TVRejected:
                events[key] = 'write-rejected'
                continue
            except Exception as exc:
                rejected = isinstance(exc, UserError) and exc.reason_code == 'ssap-request-rejected'
                events[key] = 'write-rejected' if rejected else 'write-unavailable'
                continue
            if not isinstance(reply, dict) or reply.get('returnValue') is not True:
                rejected = isinstance(reply, dict) and reply.get('returnValue') is False
                events[key] = 'write-rejected' if rejected else 'write-unavailable'
                continue
            actual = verify_value(remote, tv, category, key, target, original)
            results[key] = 'verified' if actual == target else 'unverified' if actual is None else 'failed'
            events[key] = 'verified' if actual == target else 'verify-unavailable' if actual is None else 'verify-mismatch'
    return results


def run(installer, ask, write, *, diagnostic=None):
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
    events = diagnostic if diagnostic is not None else {}
    try:
        results = apply(installer, selected, write, diagnostic=events)
    except (OSError, ValueError):
        write.error('Could not apply Debloat settings.')
        return
    # The factory SSAP allowlist for this model and firmware excludes all Debloat keys (#610).
    if (not installer.remote.root and installer.tv_info.get('modelName') == '55UK7500PSA'
            and installer.tv_info.get('firmwareVersion') == '05.50.70'):
        for key in results:
            if events[key] == 'write-rejected':
                results[key] = 'firmware-blocked'
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
