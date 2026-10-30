"""Android callbacks around the existing CYTV CLI. No device logic is duplicated."""
import json
import re
from pathlib import Path

from cytv import cli, state, i18n
from cytv.transport import SSH
from cytv.terminal import Console


def arguments(config, directory, identity=''):
    action = config.get('action', 'install')
    if action not in ('install', 'status', 'doctor', 'home-diagnostics', 'restore'):
        raise ValueError('Unsupported Android operation')
    profile = state.target(config.get('host', ''), config.get('edition', ''), config.get('port'))
    language = config.get('language', 'ru')
    if language not in i18n.LANGUAGES or language == 'auto':
        raise ValueError('Unsupported Android language')
    result = [action, '--host', profile['host'], '--edition', profile['edition'],
              '--port', str(profile['port']), '--no-discovery', '--language', language,
              '--data-dir', str(directory)]
    if identity and profile['edition'] == 'root':
        result += ['--identity', str(identity)]
    return result


class Callbacks:
    def __init__(self, native, identity='', directory=None):
        self.native = native
        self.directory = Path(directory).resolve() if directory else None
        self.identity = identity
        self.context = []

    def emit(self, **event):
        self.native.emit(json.dumps(event, ensure_ascii=False))

    def write(self, message):
        message = str(message)
        if self.directory and message.strip().endswith('.json'):
            path = Path(message.strip())
            if path.is_file() and path.resolve().parent == self.directory / 'reports' and re.fullmatch(r'diagnostic-[a-f0-9]{12}\.json', path.name):
                self.emit(kind='report-ready', name=path.name)
        self.context.append(message)
        self.context = self.context[-60:]
        self.emit(kind='log', text=message)

    def request(self, **event):
        answer = self.native.request(json.dumps(event, ensure_ascii=False))
        if answer is None:
            raise EOFError
        return str(answer)

    def ask(self, prompt):
        return self.request(kind='question', text=prompt, context='\n'.join(self.context))

    def secret(self, prompt):
        # CLI prompts have already been translated. Send a stable semantic tag
        # so the WebView never guesses the credential type from translated prose.
        labels = {'key': 'SSH key passphrase: ', 'root': 'Root SSH password (hidden): ',
                  'developer': 'Developer Mode passphrase: '}
        label_text = prompt.strip().removeprefix('> ').strip()
        kind = next((key for key, label in labels.items()
                     if label_text == i18n.translate(label).strip()), 'developer')
        return self.request(kind='secret', text=prompt, secretType=kind)

    def trust(self, value, root):
        return self.request(kind='trust', fingerprint=value, root=root) == 'yes'

    def connect(self, profile, directory, secret, trust):
        if profile['edition'] == 'root' and not self.identity:
            profile.pop('identity', None)
        def approve(fingerprint, root):
            if not self.trust(fingerprint, root):
                raise EOFError
            return True
        return SSH.connect(profile, directory, secret, approve)


class AndroidConsole(Console):
    """Emit progress from canonical CLI messages before Console translates them."""
    def __init__(self, callbacks):
        super().__init__(callbacks.write, interactive=False)
        self.callbacks = callbacks

    def error(self, message, heading=False):
        # Input mistakes can be corrected; the CLI exit code decides the result.
        self.callbacks.emit(kind='error', text=i18n.translate(message), heading=heading, fatal=False)

    def check(self, event):
        from cytv.checks import STATUS
        self.callbacks.emit(kind='check', checkId=event['id'], status=event['status'],
                            label=i18n.translate(event['label']), detail=i18n.translate(event['detail']),
                            statusText=i18n.translate(STATUS[event['status']]), title=i18n.translate('TV checks'))

    def text(self, message, bold=False):
        stages = {'Installing Home Helper…': 2, 'Installing Home…': 2,
                  'Uploading Root and recovery runtime…': 2,
                  'Installing Root Updater and preparing rollback…': 2,
                  'Configuring Home Helper…': 3, 'Turning on Root Home control…': 3,
                  'Opening Clean Your TV Home…': 3}
        stage = 1 if re.fullmatch(r'Read \d+ applications\.', str(message)) else stages.get(message)
        if stage is not None:
            self.callbacks.emit(kind='stage', stage=stage)
        super().text(message, bold)


def run(config_json, directory, payload, identity, native):
    callbacks = Callbacks(native, identity, directory)
    try:
        config = json.loads(config_json)
        args = arguments(config, directory, identity)
        # All text and confirmations use the same desktop localization and policies.
        code = cli.main(args, ask=callbacks.ask, write=AndroidConsole(callbacks),
                        secret=callbacks.secret, connect=callbacks.connect, payload_root=payload)
    except Exception as error:
        # Do not emit exception messages, which may contain credentials/paths.
        callbacks.emit(kind='error', text=type(error).__name__)
        code = 2
    callbacks.emit(kind='finished', code=code)
    return code


def inspect_connection(config_json):
    from cytv.inspect_tv import inspect
    config = json.loads(config_json)
    profile = state.target(config.get('host', ''), 'root', config.get('port', 22))
    return json.dumps({'kind': 'inspection', 'host': profile['host'], **inspect(profile['host'], profile['port'])})
