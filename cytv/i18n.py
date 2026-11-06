"""Installer language preferences and presentation-only translations.

Machine identifiers, prompt labels and diagnostic JSON remain stable English.
Only the final terminal/widget boundary translates human-readable text.
"""
import json
import locale
import os
from pathlib import Path
import re
import sys

from . import state
from .translations import MESSAGES

LANGUAGES = {'auto': 'Auto', 'en': 'English', 'cs': 'Čeština', 'de': 'Deutsch', 'es': 'Español',
             'pt-BR': 'Português (Brasil)', 'fr': 'Français', 'it': 'Italiano',
             'ko': '한국어', 'hi': 'हिन्दी', 'pl': 'Polski', 'ru': 'Русский',
             'zh-Hans': '简体中文', 'zh-Hant': '繁體中文'}
_choice = 'auto'
_language = 'en'


def system_languages():
    values = []
    for key in ('LC_ALL', 'LC_MESSAGES', 'LANGUAGE', 'LANG'):
        values.extend(os.environ.get(key, '').split(':'))
    if sys.platform == 'win32':
        try:
            import ctypes
            buffer = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer)):
                values.append(buffer.value)
        except (AttributeError, OSError):
            pass
    elif sys.platform == 'darwin':
        try:
            import subprocess
            import plistlib
            result = subprocess.run(['/usr/bin/defaults', 'export', '-g', '-'], capture_output=True, timeout=2, check=True)
            values.extend(plistlib.loads(result.stdout).get('AppleLanguages', []))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    try:
        values.append(locale.getlocale()[0] or '')
    except ValueError:
        pass
    return values


def resolve_language(choice='auto', preferred=None):
    candidates = (system_languages() if preferred is None else preferred) if choice == 'auto' else [choice]
    for candidate in candidates:
        tag = str(candidate).split('.')[0].split('@')[0].replace('_', '-').lower()
        base = tag.split('-')[0]
        if base == 'zh':
            subtags = tag.split('-')[1:]
            if 'hans' in subtags:
                return 'zh-Hans'
            if 'hant' in subtags:
                return 'zh-Hant'
            return 'zh-Hant' if any(region in subtags for region in ('tw', 'hk', 'mo')) else 'zh-Hans'
        if base == 'pt':
            return 'pt-BR'
        if base in LANGUAGES and base != 'auto':
            return base
    return 'en'


def set_language(choice):
    global _choice, _language
    if choice not in LANGUAGES:
        raise ValueError('Unsupported language: ' + str(choice))
    _choice, _language = choice, resolve_language(choice)
    return _language


def configure(choice=None, data_dir=None):
    path = Path(data_dir or state.default_dir()) / 'settings.json'
    try:
        settings = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, ValueError):
        settings = {}
    selected = choice if choice is not None else settings.get('language', 'auto')
    if selected not in LANGUAGES:
        selected = 'auto'
    if choice is not None:
        settings['language'] = selected
        state.private_write(path, json.dumps(settings, ensure_ascii=False).encode('utf-8'))
    return set_language(selected)


def language_choice():
    return _choice


def resolved_language():
    return _language


_patterns = []
for _source, _values in sorted(MESSAGES.items(), key=lambda item: len(re.sub(r'\{\w+\}', '', item[0])), reverse=True):
    if '{' in _source:
        parts = re.split(r'(\{\w+\})', _source)
        expression = ''.join('(?P<' + part[1:-1] + '>.+?)' if re.fullmatch(r'\{\w+\}', part) else re.escape(part) for part in parts)
        _patterns.append((re.compile(expression, re.DOTALL), _values))


def translate(message):
    text = str(message)
    if _language == 'en' or not text:
        return text
    stripped = text.strip().replace(' | ', ' / ')
    values = MESSAGES.get(stripped)
    if values is None and stripped + ':' in MESSAGES:
        return translate(stripped + ':').rstrip(':： ')

    if values:
        result = values[_language]
    else:
        result = None
        for pattern, values in _patterns:
            match = pattern.fullmatch(stripped)
            if match:
                result = values[_language].format_map(match.groupdict())
                break
        if result is None:
            if '\n' in text:
                return '\n'.join(translate(line) for line in text.split('\n'))
            sentences = re.split(r'(?<=[.!?]) +', stripped)
            if len(sentences) > 1:
                return ' '.join(translate(sentence) for sentence in sentences)
            return text
    return text[:len(text) - len(text.lstrip())] + result + text[len(text.rstrip()):]
