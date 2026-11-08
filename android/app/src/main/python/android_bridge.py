"""Android callbacks around the existing CYTV CLI. No device logic is duplicated."""
import json
import re
from pathlib import Path

from cytv import cli, state, i18n
from cytv.transport import SSH
from cytv.terminal import Console


def arguments(config, directory, identity=''):
    action = config.get('action', 'install')
    if action not in ('install', 'status', 'doctor', 'home-diagnostics', 'recover', 'restore', 'uninstall'):
        raise ValueError('Unsupported Android operation')
    profile = state.target(config.get('host', ''), config.get('edition', ''), config.get('port'),
                           connection=config.get('connection'), root_variant=config.get('root_variant'))
    language = config.get('language', 'ru')
    if language not in i18n.LANGUAGES or language == 'auto':
        raise ValueError('Unsupported Android language')
    result = [action, '--host', profile['host'], '--edition', profile['edition'],
              '--port', str(profile['port']), '--no-discovery', '--language', language,
              '--data-dir', str(directory)]
    for field in ('connection', 'root_variant'):
        if profile.get(field):
            result += ['--'+field.replace('_','-'), profile[field]]
    if identity and (profile['edition'] == 'root' or profile.get('connection') == 'root-ssh'):
        result += ['--identity', str(identity)]
    return result


class Callbacks:
    def __init__(self, native, identity='', directory=None):
        self.native = native
        self.directory = Path(directory).resolve() if directory else None
        self.identity = identity
        self.context = []
        self.options = []

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
        options, self.options = self.options, []
        event = {'kind':'question', 'text':prompt, 'context':'\n'.join(self.context), 'defaultNo':'[y/N]' in prompt}
        if options:
            match = re.search(r'\[(\d+)\]', prompt)
            event.update(options=options, defaultChoice=match.group(1) if match else '')
        return self.request(**event)

    def secret(self, prompt):
        if hasattr(prompt, 'credential_type'):
            kind = prompt.credential_type
        else:
            # Exact compatibility for pre-typed callers only. Transport supplies
            # metadata for both raw passive and CLI-localized authentication.
            labels = {'key': 'SSH key passphrase: ', 'root': 'Root SSH password (hidden): ',
                      'developer': 'Developer Mode passphrase: '}
            text = prompt.strip().removeprefix('> ').strip()
            kind = next((key for key, label in labels.items()
                         if text in (label.strip(), i18n.translate(label).strip())), 'developer')
        if kind not in ('key', 'root', 'developer'):
            raise ValueError('Unsupported credential type')
        return self.request(kind='secret', text=prompt, secretType=kind)

    def trust(self, value, root):
        return self.request(kind='trust', fingerprint=value, root=root) == 'yes'

    def connect(self, profile, directory, secret, trust, persist=True):
        if persist and profile['edition'] == 'root' and not self.identity:
            profile.pop('identity', None)
        def approve(fingerprint, root):
            if not self.trust(fingerprint, root):
                raise EOFError
            return True
        return SSH.connect(profile, directory, secret, approve if persist else lambda *_:False, persist=persist)


class AndroidConsole(Console):
    """Emit progress from canonical CLI messages before Console translates them."""
    frontend = 'android'

    def __init__(self, callbacks):
        super().__init__(callbacks.write, interactive=False)
        self.callbacks = callbacks

    def option(self, key, label, detail=''):
        super().option(key, label, detail)
        self.callbacks.options.append({'value':str(key), 'label':i18n.translate(label),
                                       'detail':i18n.translate(detail)})

    def failure_help(self, value):
        super().failure_help(value)
        self.callbacks.emit(kind='failure-help', code=value['code'], title=i18n.translate(value['title']),
                            detail=i18n.translate(value['detail']), nextStep=i18n.translate(value['next_step']),
                            pending=value['pending'], canEditConnection=value['can_edit_connection'])

    def recovery(self, profile):
        self.recovery_plan({'state': 'review', 'summary': 'Review recovery options',
                            'next_step': 'Recovery data kept. Installation has not restarted.'})

    def selected_profile(self, profile):
        self.callbacks.emit(kind='selected-profile', profile={key:profile[key] for key in
                            ('host','edition','port','connection','root_variant') if key in profile})

    def recovery_plan(self, value):
        super().recovery_plan(value)
        from cytv.recovery_ui import removal_details, removal_restart_required
        from cytv.recovery_state import ACTIONS, REASONS
        optional = {key:value[key] for key in ('disposition',) if key in value}
        optional.update({key:value[key] for key in ('removed','verified_clean') if type(value.get(key)) is bool})
        optional['restart_required'] = removal_restart_required(value)
        if type(value.get('actions')) is list:
            optional['actions'] = [item for item in value['actions'] if type(item) is str and item in ACTIONS]
        removal = value.get('removal') if type(value.get('removal')) is dict else {}
        reason = value.get('reason', removal.get('reason'))
        if type(reason) is str and reason in REASONS:
            optional['reason'] = reason
        detail = removal_details(value)
        if detail:
            optional.update(stageText=i18n.translate(detail['stage_text']), blockerText=i18n.translate(detail['blocker_text']))
        self.callbacks.emit(kind='recovery-plan', state=value['state'],
                            summary=i18n.translate(value['summary']), nextStep=i18n.translate(value['next_step']),
                            **optional)

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
                  'Opening Clean Your TV Home…': 3, 'Starting Home Helper…': 3}
        stage = 1 if re.fullmatch(r'Read \d+ applications\.', str(message)) else stages.get(message)
        if stage is not None:
            self.callbacks.emit(kind='stage', stage=stage)
        super().text(message, bold)


def inspect_root_recovery(config, callbacks, payload=None):
    """Use original Android records for the submitted-install read, not a new CLI login."""
    from cytv import diagnostics, prompts, root_passive
    from cytv.errors import UserError
    from cytv.recovery import plan, REVIEW, KEPT, BLOCKED
    i18n.set_language(config.get('language', 'ru'))
    store = state.Store(callbacks.directory)
    profile = state.target(config.get('host', ''), 'root', config.get('port'))
    write = AndroidConsole(callbacks)
    try:
        saved = [p for p in store.profiles() if all(p[k] == profile[k] for k in ('host', 'port', 'edition'))]
        pending = store.pending(profile)
        actions = ('install', 'uninstall', 'activate-root', 'setup-root-updater',
                   'archive-root-state', 'enable-system-updates')
        if len(saved) != 1 or not pending or pending.get('action') not in actions:
            raise UserError('Original Android recovery records are missing or changed. Keep app data and stop.',
                            reason_code='pending-operation')
        profile = saved[0]  # Ignore the current form's key/password choice for this inspection.
        if pending.get('action') != 'install' or pending.get('stage') != 'coordinator-submitted':
            return None  # Other supported recovery states keep their existing explicit flow.
        plan(write, 'review', REVIEW)
        write('Read the original Root installation state only. No TV files, packages, Home settings or recovery records will be changed.')
        if not prompts.confirm('Check recovery options?', write.reader(callbacks.ask), write):
            write(KEPT)
            return 130
        def review(remote,passive):
            from cytv.operations import Installer
            from cytv.recovery import recover
            from cytv.recovery_state import assess
            event=dict(operation=pending['product_operation'],state='recovery_required',stage='blocked',
                       code='operation_requires_recovery',can_resume=False,passive=passive)
            result=dict(device={'product':event},can_resume_root_setup=False)
            result['assessment']=assess(profile,pending,result)
            installer=Installer(remote,store,profile,payload or '/unavailable-recovery-payload',{},write)
            recover(installer,write.reader(callbacks.ask),write,initial_observation=result)
            diagnostics.save_result(write,store,'recover',profile,'recover',installer.tv_info,
                                    status=installer.tv_info.get('status',result))
            return 2 if store.pending(profile) else 0
        return root_passive.inspect_saved(store,profile,pending.get('product_operation'),callbacks.secret,after_observe=review)
    except (EOFError, KeyboardInterrupt):
        from cytv.recovery import cancelled
        cancelled(write, store, profile, 'recover', 'recover')
        return 130
    except Exception as error:
        from cytv.failure_help import for_error
        # Authentication is performed inside inspect_saved. Classify that current
        # blocker without replacing the operation's original recorded failure.
        phase = 'ssh-connect' if getattr(error, 'observation_phase', None) == 'ssh-connect' else 'recover'
        help = for_error(error, phase, profile, store.pending(profile))
        if help:
            write.failure_help(help)
        plan(write, 'blocked', help['title'] if help else KEPT,
             help['next_step'] if help else 'Save diagnostic report…')
        write.error(help['title'] if help and help['code'] != 'pending-operation'
                    else str(error) if isinstance(error, UserError) else BLOCKED)
        diagnostics.suggest_issue(write, store, 'recover', profile, phase, error)
        return 2


def run(config_json, directory, payload, identity, native):
    callbacks = Callbacks(native, identity, directory)
    try:
        config = json.loads(config_json)
        args = arguments(config, directory, identity)
        code = (inspect_root_recovery(config, callbacks, payload)
                if config.get('action') == 'recover' and config.get('edition') == 'root' else None)
        if code is None:
            # Other operations retain the shared CLI and their explicit confirmations.
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
