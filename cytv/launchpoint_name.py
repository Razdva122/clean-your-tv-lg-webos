"""Rename only an installed app's unambiguous primary launch point."""
from .package import normalize_tv_name

SERVICE = 'com.webos.applicationManager/'


def primary(reply, app):
    if reply.get('returnValue') is not True:
        raise ValueError('Launch points unavailable')
    points = reply.get('launchPoints')
    if not isinstance(points, list) or len(points) > 300:
        raise ValueError('Invalid launch points')
    matches = [point for point in points if isinstance(point, dict)
               and point.get('id') == app
               and isinstance(point.get('launchPointId'), str)
               and 0 < len(point['launchPointId']) <= 256
               and (point['launchPointId'] in (app, app + '_default')
                    or point.get('default') is True or point.get('type') == 'default')]
    if len(matches) != 1 or not isinstance(matches[0].get('title'), str):
        raise ValueError('Primary launch point unavailable or ambiguous')
    return matches[0]


def rename(remote, app, name):
    name = normalize_tv_name(name)
    before = primary(remote.luna(SERVICE + 'listLaunchPoints', {}, timeout=8), app)
    if before['title'] != name:
        reply = remote.luna(SERVICE + 'updateLaunchPoint', {
            'launchPointId': before['launchPointId'], 'title': name}, timeout=8)
        if reply.get('returnValue') is not True:
            raise ValueError('Launch point update unconfirmed')
    after = primary(remote.luna(SERVICE + 'listLaunchPoints', {}, timeout=8), app)
    if after['launchPointId'] != before['launchPointId'] or after['title'] != name:
        raise ValueError('Launch point readback unconfirmed')
