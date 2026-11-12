"""Optional installation choices; use existing Home storage and public service APIs."""
import json
import uuid

from . import prompts
from .i18n import translate as tr

TITLE = 'Set up your Clean Your TV'
PROMPT = 'Clean Your TV settings: '
THEMES = (('classic', 'Classic'), ('liquid-glass', 'Liquid Glass'), ('ribbon', 'Ribbon'))
WEATHER_HELP = 'Weather uses an approximate city from your internet connection. Change the city later in Home settings.'
RENEWAL_HELP = 'Auto-renewal is experimental. Keep checking the timer in the official Developer Mode app.'
FIRMWARE_HELP = 'Requires Homebrew Channel with root. Also blocks firmware security updates. A real TV restart is required; standby is not enough.'


def validate(value, profile):
    if not isinstance(value, dict) or set(value) - {'theme', 'weather', 'renewal', 'block_updates', 'tv_name'}:
        raise ValueError('Invalid installation settings')
    if 'tv_name' in value:
        if profile['edition'] != 'root':
            raise ValueError('Home screen naming requires Root Edition.')
        from .package import normalize_tv_name
        value = dict(value, tv_name=normalize_tv_name(value['tv_name']))
    if 'theme' in value and (type(value['theme']) is not str or value['theme'] not in dict(THEMES)):
        raise ValueError('Invalid installation theme')
    for key in ('weather', 'renewal', 'block_updates'):
        if key in value and type(value[key]) is not bool:
            raise ValueError('Invalid installation switch')
    if value.get('theme') == 'ribbon' and value.get('weather'):
        raise ValueError('Ribbon does not support weather')
    if 'renewal' in value and (profile['edition'] != 'no-root' or profile.get('connection') == 'root-ssh'):
        raise ValueError('Developer Mode renewal is unavailable in this mode')
    if 'block_updates' in value and profile['edition'] != 'root':
        raise ValueError('Firmware blocking requires Root Edition')
    return dict(value)


def read_service_current(installer):
    """Read only the edition's existing preference, never infer unknown as off."""
    try:
        if installer.profile['edition'] == 'root':
            reply = installer.remote.luna('org.webosbrew.hbchannel.service/getConfiguration', {}, timeout=5)
            if reply.get('returnValue') is True and reply.get('root') is True and type(reply.get('blockUpdates')) is bool:
                return {'block_updates':reply['blockUpdates']}
        elif installer.profile.get('connection') != 'root-ssh':
            reply = installer.remote.luna('com.gathin.tvhome.renewal/status', {}, timeout=5)
            state = reply.get('state', {})
            if reply.get('returnValue') is True and type(state.get('enabled')) is bool:
                return {'renewal':state['enabled']}
    except Exception:
        pass
    return {}


def read_current(installer):
    result = read_service_current(installer)
    if installer.profile['edition'] != 'root':
        return result
    try:
        from .launchpoint_name import primary, SERVICE
        from .package import ROOT_APP, normalize_tv_name
        point = primary(installer.remote.luna(SERVICE + 'listLaunchPoints', {}, timeout=8), ROOT_APP)
        result['tv_name'] = normalize_tv_name(point['title'])
    except Exception:
        pass
    return result


def collect(profile, ask, write, current=None):
    write.step(6, TITLE)
    write('Clean Your TV is installed.')
    if write.frontend == 'desktop':
        write.installation_settings(current or {})
        return validate(json.loads(prompts.answer(ask, PROMPT)), profile)
    if write.frontend == 'android':
        write.option('y', TITLE)
        write.option('n', 'Keep current settings')
    if not prompts.confirm('Customize Clean Your TV?', ask, write):
        return {}
    for number, (_, title) in enumerate(THEMES, 1):
        write.option(number, title)
    while True:
        choice = prompts.answer(ask, 'Theme [1]: ') or '1'
        if choice in ('1', '2', '3'):
            break
        write.error('Choose 1, 2 or 3.')
    result = {'theme': THEMES[int(choice) - 1][0]}
    if profile['edition'] == 'root':
        name = prompts.tv_name(ask, write)
        if name is not None:
            result['tv_name'] = name
    if result['theme'] == 'ribbon':
        write('Ribbon does not support weather.')
        result['weather'] = False
    else:
        write(WEATHER_HELP)
        if write.frontend == 'android':
            write.option('y', 'On')
            write.option('n', 'Off')
        result['weather'] = prompts.confirm('Show weather on Home', ask, write)
    if profile['edition'] == 'root':
        write(FIRMWARE_HELP)
        enabled = service_choice('Block LG firmware updates', ask, write)
        if enabled is not None:
            result['block_updates'] = enabled
    elif profile.get('connection') != 'root-ssh':
        write(RENEWAL_HELP)
        enabled = service_choice('Developer Mode auto-renewal (Beta)', ask, write)
        if enabled is not None:
            result['renewal'] = enabled
    return validate(result, profile)


def service_choice(title, ask, write):
    write.heading(title)
    write.option(0, 'Keep current settings')
    write.option(1, 'On')
    write.option(2, 'Off')
    while True:
        choice = prompts.answer(ask, tr(title) + ' [0]: ') or '0'
        if choice in ('0', '1', '2'):
            return {'0': None, '1': True, '2': False}[choice]
        write.error('Enter a valid choice.')


def apply_services(installer, value, write):
    value = validate(value, installer.profile)
    results = installer.tv_info.setdefault('installation_settings', {})
    if 'tv_name' in value:
        from .launchpoint_name import rename
        from .package import ROOT_APP
        try:
            rename(installer.remote, ROOT_APP, value['tv_name'])
            results['launchpoint_title'] = 'saved'
            write('LG launcher title verified. Check the loading screen on the TV.')
        except Exception:
            results['launchpoint_title'] = 'unconfirmed'
            write(tr('Optional setting unconfirmed: {setting}').format(setting=tr('Home screen name')))
            write('Installation of Clean Your TV completed separately.')
    appearance = {key:value[key] for key in ('theme', 'weather', 'tv_name') if key in value}
    if appearance:
        try:
            from .package import ROOT_APP
            app = ROOT_APP if installer.profile['edition'] == 'root' else 'com.gathin.tvhome'
            reply = installer.remote.luna('com.webos.applicationManager/launch', {
                'id': app, 'params': {'cytvSetup': dict(appearance, id=uuid.uuid4().hex)}})
            if reply.get('returnValue') is not True:
                raise ValueError('Home launch unconfirmed')
            results.update({key:'requested-in-home' for key in appearance})
            write('Appearance choices will be applied when Home opens. Check the result on the TV.')
        except Exception:
            results.update({key:'unconfirmed' for key in appearance})
            write('Installation of Clean Your TV completed separately.')
    for key in ('renewal', 'block_updates'):
        if key not in value:
            continue
        enabled = value[key]
        try:
            if key == 'renewal':
                reply = installer.remote.luna('com.gathin.tvhome.renewal/' + ('enable' if enabled else 'disable'), {})
                state = reply.get('state', {})
                if reply.get('returnValue') is not True or state.get('enabled') is not enabled or state.get('error'):
                    raise ValueError('Renewal preference unconfirmed')
                results[key] = 'saved'
                write('Developer Mode auto-renewal preference saved. Continue monitoring the official timer.')
            else:
                if not installer.remote.root:
                    raise ValueError('Root SSH required')
                uri = 'org.webosbrew.hbchannel.service/'
                before = installer.remote.luna(uri + 'getConfiguration', {})
                if before.get('returnValue') is not True or before.get('root') is not True or type(before.get('blockUpdates')) is not bool:
                    raise ValueError('Homebrew configuration unavailable')
                if before['blockUpdates'] is not enabled:
                    reply = installer.remote.luna(uri + 'setConfiguration', {'blockUpdates': enabled})
                    if reply.get('returnValue') is not True or reply.get('blockUpdates') is not enabled:
                        raise ValueError('Homebrew preference unconfirmed')
                after = installer.remote.luna(uri + 'getConfiguration', {})
                if after.get('returnValue') is not True or after.get('root') is not True or after.get('blockUpdates') is not enabled:
                    raise ValueError('Homebrew readback unconfirmed')
                results[key] = 'saved-restart-required'
                write('LG firmware update preference saved. Restart the TV through Homebrew Channel; active blocking has not been verified.')
        except Exception:
            # Never retry an uncertain write or misreport core installation as failed.
            # Raw API errors can contain device details and stay out of progress output.
            results[key] = 'unconfirmed'
            name = tr('Developer Mode auto-renewal (Beta)' if key == 'renewal' else 'Block LG firmware updates')
            write(tr('Optional setting unconfirmed: {setting}').format(setting=name))
            write('Check this setting in Home settings before trying again. Installation of Clean Your TV completed separately.')
