"""Bounded data-only launcher profile; no renewal state or executable inputs."""
import base64
import binascii
import re
from .store import MAX_BYTES, encode
import json


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or set(value) - set(required) - set(optional):
        raise ValueError('invalid profile fields')


def _text(value, maximum=256, empty=False):
    if not isinstance(value, str) or (not value and not empty) or len(value.encode('utf-8')) > maximum or '\x00' in value:
        raise ValueError('invalid profile text')


def _ids(value):
    if not isinstance(value, list) or len(value) > 200: raise ValueError('invalid app IDs')
    for item in value: _text(item)
    if len(set(value)) != len(value): raise ValueError('duplicate app IDs')


def validate(value):
    raw = encode(value)
    if len(raw) > MAX_BYTES: raise ValueError('profile too large')
    _fields(value, ('schema', 'inventory', 'config', 'settings'))
    if type(value['schema']) is not int or value['schema'] != 1: raise ValueError('invalid profile schema')
    inventory = value['inventory']
    _fields(inventory, ('apps', 'inputs'))
    for key, maximum in (('apps', 200), ('inputs', 100)):
        if not isinstance(inventory[key], list) or len(inventory[key]) > maximum:
            raise ValueError('inventory too large')
    seen = set()
    for app in inventory['apps']:
        _fields(app, ('id', 'title', 'icon'), ('iconColor',))
        _text(app['id']); _text(app['title'])
        if app['id'] in seen: raise ValueError('duplicate app')
        seen.add(app['id'])
        icon = app['icon']
        if not isinstance(icon, str) or len(icon.encode('utf-8')) > 256 * 1024:
            raise ValueError('icon too large')
        if not re.fullmatch(r'data:image/(?:png|jpeg|webp);base64,[A-Za-z0-9+/]+={0,2}', icon):
            raise ValueError('invalid embedded icon')
        try: base64.b64decode(icon.split(',', 1)[1], validate=True)
        except (ValueError, binascii.Error) as error: raise ValueError('invalid embedded icon') from error
        if 'iconColor' in app:
            if not isinstance(app['iconColor'], str) or not re.fullmatch(r'#[0-9A-Fa-f]{6}', app['iconColor']):
                raise ValueError('invalid icon color')
    seen = set()
    for item in inventory['inputs']:
        _fields(item, ('appId', 'label'))
        _text(item['appId']); _text(item['label'])
        if item['appId'] in seen: raise ValueError('duplicate input')
        seen.add(item['appId'])
    config = value['config']
    _fields(config, ('columns', 'dockApps', 'hiddenApps'), ('liveTvApp',))
    if type(config['columns']) is not int or not 1 <= config['columns'] <= 8:
        raise ValueError('invalid columns')
    _ids(config['dockApps']); _ids(config['hiddenApps'])
    if 'liveTvApp' in config: _text(config['liveTvApp'], empty=True)
    _fields(value['settings'], (), ('tvhome.order', 'tvhome.language', 'tvhome.name'))
    if 'tvhome.name' in value['settings']:
        name=value['settings']['tvhome.name']
        _text(name,192)
        if len(name)>48 or re.search(r'[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028-\u202e\u2060-\u206f]',name):
            raise ValueError('invalid TV name')
    if 'tvhome.language' in value['settings'] and value['settings']['tvhome.language'] not in ('auto', 'en', 'cs', 'de', 'es', 'pt-BR', 'fr', 'it', 'ko', 'hi', 'pl', 'ru'):
        raise ValueError('invalid language')
    if 'tvhome.order' in value['settings']:
        _text(value['settings']['tvhome.order'], MAX_BYTES, empty=True)
        try:order=json.loads(value['settings']['tvhome.order'])
        except (ValueError,TypeError) as error:raise ValueError('unreadable tile order') from error
        _fields(order,('dock','ids'))
        _text(order['dock'], 65536, empty=True);_ids(order['ids'])
    return json.loads(raw)
