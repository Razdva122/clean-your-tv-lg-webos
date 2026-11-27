"""Optional LG settings changes with per-setting readback."""
from contextlib import ExitStack
import json
import shlex
import time

from . import prompts
from .debloat_policy import GROUPS, LOG_UPLOADS, SETTINGS, valid_value, valid_record
from .errors import UserError, TVRejected
from .i18n import translate as tr
from .state import private_write
from .tv import SSAP

TITLE = 'Debloat'
SELECT = 'Select Debloat settings: '
REVIEW = 'Review Debloat results: '
CONTINUE = 'Continue to customization'
APPLY = 'Apply selected settings'
RESTORE_PROMPT = 'Restore saved Debloat settings before removal?'
SELECT_RESTORE = 'Choose a saved setting to restore'
CONFIRM_ONE = 'Restore this saved setting?'
RESTORE_LABEL = 'Restore saved Debloat settings'
SKIP_RESTORE = 'Skip restoration'
NOTICE = 'If the original value cannot be read, the selected change cannot be automatically undone.'
SETTING_NAMES = {
    'homePromotion': 'Sponsored tiles',
    'contentRecommendation': 'Content recommendations',
    'screenSaverAd': 'Screen saver ads',
    'livePromotion': 'Promotions while watching',
    'webOSPromotionVideo': 'webOS promotional video',
    'livePlus': 'Live Plus',
    'dbgLogUpload': 'Debug log uploads to LG',
    'faultLogUpload': 'Fault log uploads to LG',
    'adCookie': 'Advertising cookies',
    'lmt': 'Ad tracking limit',
    'aiNudge': 'Smart Tips',
    'sportsAlarm': 'Sports notifications',
    'promotionStreamer': 'LG promotional streams',
}
RESULTS = {
    'already': ('✓', '#b4ada4', 'Already in the requested state'),
    'verified': ('✓', '#90cfad', 'Successfully applied and verified'),
    'failed': ('×', '#ff8580', 'Could not change the setting'),
    'write-rejected': ('×', '#ff8580', 'The TV rejected the request to change this setting.'),
    'firmware-blocked': ('×', '#ff8580', 'This TV firmware blocks changing this setting in No-root.'),
    'unavailable': ('–', '#b4ada4', 'Setting unavailable on this connection. Skipped.'),
    'unverified': ('✓', '#b4ada4', 'Command sent. The result could not be verified.'),
}
RESTORE_RESULTS = {
    'restored': ('✓', '#90cfad', 'Restored and verified'),
    'restore-already': ('✓', '#b4ada4', 'Already at the saved original value'),
    'restore-unavailable': ('–', '#b4ada4', 'Could not read the current value'),
    'restore-unverified': ('?', '#b4ada4', 'Could not verify the restored value'),
    'restore-failed': ('×', '#ff8580', 'Could not restore the setting'),
}
RESULTS.update(RESTORE_RESULTS)
DIAGNOSTIC_RESULTS = ('already', 'verified', 'pairing-rejected', 'pairing-timeout',
                      'pairing-unavailable', 'write-rejected', 'write-unavailable',
                      'journal-failed', 'unavailable', 'verify-unavailable', 'verify-mismatch',
                      *RESTORE_RESULTS)
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
        var setting = data[args[1]];
        if (typeof setting === 'boolean' || setting === 'on' || setting === 'off') value = setting;
    }
} catch (error) {}
process.stdout.write(JSON.stringify(value));
'''


def result_message(key, status):
    message = tr(RESULTS[status][2])
    home_menu = {'homePromotion': 'Home Promotion', 'contentRecommendation': 'Content Recommendation'}
    if status == 'write-rejected' and key in home_menu:
        path = tr('On webOS 6 and 22: All Settings → General → System → Additional Settings → Home Settings → {setting} → Off.')
        return message + ' ' + path.format(setting=tr(home_menu[key]))
    return message


def read(remote, category, key):
    try:
        if remote.root:
            reply = remote.luna(SERVICE + 'getSystemSettings', {'category': category, 'keys': [key]}, timeout=5)
            value = reply.get('settings', {}).get(key) if reply.get('returnValue') is True else None
        else:
            command = shlex.join(['/usr/bin/node', '-e', READ_PREFERENCE, json.dumps([category, key])])
            value = json.loads(remote.run(command, timeout=5))
        return value if valid_value(key, value) else None
    except Exception:
        return None


def read_ssap(tv, category, key):
    if tv is None or (key != 'livePlus' and key not in LOG_UPLOADS):
        return None
    try:
        reply = tv.call('ssap://settings/getSystemSettings', {'category': category, 'keys': [key]}, timeout=5)
        value = reply.get('settings', {}).get(key) if reply.get('returnValue') is True else None
        return value if valid_value(key, value) else None
    except Exception:
        return None


def read_current(remote, category, key, tv):
    current = read(remote, category, key)
    return current if current is not None else read_ssap(tv, category, key)


def set_value(remote, tv, category, key, value):
    payload = {'category': category, 'settings': {key: value}}
    if tv is not None:
        return tv.call('ssap://settings/setSystemSettings', payload, timeout=8)
    return remote.luna(SERVICE + 'setSystemSettings', payload, timeout=8)


def verify_value(remote, tv, category, key, value, previous, *, paired_upload=False):
    def readback():
        # A stale file can already contain the target before the SSAP write.
        # If SSAP supplied the upload switch, verify through the same source.
        if paired_upload:
            return read_ssap(tv, category, key)
        return read_current(remote, category, key, tv)

    actual = readback()
    # The on-disk snapshot can lag the SSAP action. Retry reads only.
    for delay in (.25, .5, 1):
        if actual == value or (actual is None and previous is None):
            break
        time.sleep(delay)
        actual = readback()
    return actual


def offer_restore(remote, store, profile, ask, write, *, maintenance=False, diagnostic=None):
    """Return True when maintenance handled a single saved setting."""
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
    eligible = [key for key in SETTINGS if valid_record(key, entries.get(key))]
    if not eligible:
        return
    if maintenance:
        write.heading(SELECT_RESTORE)
        write.option(0, 'Adjust LG settings (Debloat)')
        for index, key in enumerate(eligible, 1):
            write.option(index, SETTING_NAMES[key])
        choice = prompts.number(ask, write, SELECT_RESTORE + ' [0]: ', 0, len(eligible), default=0)
        if not choice:
            return False
        eligible = [eligible[choice - 1]]

    remaining = entries.copy()
    events = diagnostic if diagnostic is not None else {}
    with ExitStack() as stack:
        tv = None
        current_values = {key: read(remote, SETTINGS[key][0], key) for key in eligible}
        paired_preview = set()
        paired_reads = [key for key, current in current_values.items()
                        if key in LOG_UPLOADS or (key == 'livePlus' and current is None)]
        if not remote.root and paired_reads:
            try:
                # Only prompt for pairing before the preview when the owner
                # explicitly selected a saved upload setting in Maintenance.
                reuse_only = not (maintenance and eligible[0] in LOG_UPLOADS)
                tv = stack.enter_context(SSAP(profile['host'], path.parent, write,
                                             settings_write=True, reuse_only=reuse_only))
            except Exception:
                pass
            for key in paired_reads:
                paired_value = read_ssap(tv, SETTINGS[key][0], key)
                if paired_value is not None:
                    current_values[key] = paired_value
                    paired_preview.add(key)
        planned = {key for key, current in current_values.items() if current == entries[key]['target']}
        if write.frontend == 'desktop' and planned:
            write.step(1, 'Debloat restoration preview')
        else:
            write.heading('Debloat restoration preview')
        states = {'on': tr('On'), True: tr('On'), 'off': tr('Off'), False: tr('Off')}
        for key, current in current_values.items():
            label = tr(SETTING_NAMES[key])
            if key in planned:
                original = entries[key]['original']
                write(f'{label} — {states[current]} → {states[original]}')
            elif current is None:
                write(f"{label} — {tr('Could not read the current value')}")
            else:
                write(f"{label} — {tr('Already at the saved original value')}")
        if planned:
            if write.frontend == 'android':
                write.option('y', RESTORE_LABEL)
                write.option('n', SKIP_RESTORE)
            if not prompts.confirm(CONFIRM_ONE if maintenance else RESTORE_PROMPT, ask, write):
                return maintenance
            write.heading('Debloat restoration results')
        elif not maintenance:
            return
        pairing_failed = False
        for key in eligible:
            original = entries[key]['original']
            if key not in planned:
                if current_values[key] == original:
                    del remaining[key]
                    events[key] = 'restore-already'
                else:
                    events[key] = 'restore-unavailable'
                continue
            category, _, target = SETTINGS[key]
            if not remote.root and tv is None and not pairing_failed:
                try:
                    tv = stack.enter_context(SSAP(profile['host'], path.parent, write, settings_write=True))
                except Exception:
                    pairing_failed = True
            paired_value = read_ssap(tv, category, key) if key in LOG_UPLOADS else None
            if paired_value is not None or (key in LOG_UPLOADS and key in paired_preview):
                current = paired_value
            elif key in LOG_UPLOADS:
                current = read(remote, category, key)
            else:
                current = read_current(remote, category, key, tv)
            if current == original:
                status = 'restore-already'
            elif current is None:
                status = 'restore-unavailable'
            elif current == target and (remote.root or tv is not None):
                try:
                    reply = set_value(remote, tv, category, key, original)
                except Exception:
                    reply = None
                if isinstance(reply, dict) and reply.get('returnValue') is True:
                    actual = verify_value(remote, tv, category, key, original, current,
                                          paired_upload=paired_value is not None)
                    status = 'restored' if actual == original else 'restore-unverified'
                else:
                    status = 'restore-failed'
            else:
                status = 'restore-failed'
            events[key] = status
            if status in ('restore-already', 'restored'):
                del remaining[key]
            write(f'{tr(SETTING_NAMES[key])} — {tr(RESTORE_RESULTS[status][2])}')

    if remaining == entries:
        return maintenance
    journal['settings'] = remaining
    try:
        private_write(path, json.dumps(journal).encode())
    except OSError:
        write('Could not update the saved Debloat settings.')
    return maintenance


def remember(path, key, original, target):
    try:
        journal = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        journal = {'schema': 1, 'settings': {}}
    if journal['schema'] != 1 or not isinstance(journal['settings'], dict):
        raise ValueError('Invalid Debloat record')
    if key in journal['settings'] and not valid_record(key, journal['settings'][key]):
        raise ValueError('Invalid Debloat setting record')
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
            if original is None and (key == 'promotionStreamer' or (remote.root and key in LOG_UPLOADS)):
                results[key] = events[key] = 'unavailable'
                continue
            if original == target and (remote.root or key not in LOG_UPLOADS):
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
            paired_upload = False
            if use_ssap and (original is None or key in LOG_UPLOADS):
                paired_value = read_ssap(tv, category, key)
                if paired_value is not None:
                    original = paired_value
                    paired_upload = key in LOG_UPLOADS
                if original is None and key in LOG_UPLOADS:
                    results[key] = events[key] = 'unavailable'
                    continue
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
            actual = verify_value(remote, tv, category, key, target, original, paired_upload=paired_upload)
            results[key] = 'verified' if actual == target else 'unverified' if actual is None else 'failed'
            events[key] = 'verified' if actual == target else 'verify-unavailable' if actual is None else 'verify-mismatch'
    return results


def run(installer, ask, write, *, diagnostic=None, maintenance=False):
    events = diagnostic if diagnostic is not None else {}
    if maintenance:
        write.heading(TITLE)
        if offer_restore(installer.remote, installer.store, installer.profile, ask, write,
                         maintenance=True, diagnostic=events):
            if events and write.frontend == 'desktop':
                write.debloat_results(events)
                prompts.answer(ask, REVIEW)
            return
    else:
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
        results = apply(installer, selected, write, diagnostic=events)
    except (OSError, ValueError):
        write.error('Could not apply Debloat settings.')
        return
    if not installer.remote.root:
        # The factory SSAP allowlist on this model and firmware excludes all Debloat keys (#610).
        known_firmware_block = (installer.tv_info.get('modelName') == '55UK7500PSA'
                                and installer.tv_info.get('firmwareVersion') == '05.50.70')
        for key in results:
            if events[key] == 'write-rejected':
                results[key] = 'firmware-blocked' if known_firmware_block else 'write-rejected'
    if write.frontend == 'desktop':
        write.debloat_results(results)
        prompts.answer(ask, REVIEW)
    else:
        write.heading('Debloat results')
        for key, status in results.items():
            icon = RESULTS[status][0]
            write(f'{icon} {tr(SETTINGS[key][1])} — {result_message(key, status)}')
        if write.frontend == 'android':
            write.option('1', CONTINUE)
        if not maintenance:
            prompts.answer(ask, tr('Continue to customization: '))
