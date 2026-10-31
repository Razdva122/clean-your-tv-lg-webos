"""Semantic desktop bridge; TV work never runs on the UI thread."""
import queue
import re
from dataclasses import dataclass, field

from .terminal import Console


@dataclass(repr=False)
class Prompt:
    label: str
    options: list = field(default_factory=list)
    secret: bool = False

    @property
    def kind(self):
        if self.secret:
            return 'secret'
        if re.search(r'\[[Yy]/[Nn]\]', self.label):
            return 'confirm'
        if self.options:
            return 'choice'
        if 'Private key file' in self.label:
            return 'file'
        if 'Press Enter' in self.label:
            return 'ready'
        return 'text'

    @property
    def default(self):
        if self.kind == 'confirm':
            return 'y' if '[Y/n]' in self.label else 'n'
        match = re.search(r'\[(\d+)\]', self.label)
        return match.group(1) if match else ''

    @property
    def title(self):
        return re.sub(r'\s*\[[^]]+\]', '', self.label).strip().rstrip(':')


class DesktopConsole(Console):
    def __init__(self, emit):
        self.emit = emit
        self.options = []
        self.color = self.interactive = False
        self.raw = lambda text: emit('text', str(text).strip())

    def text(self, message, bold=False):
        message = str(message).strip()
        # These are keyboard instructions for the terminal, represented by controls here.
        if (not message or ' = ' in message or message.startswith(('q / Ctrl+C', 'Typing is hidden:', 'TV > Edition'))):
            return
        self.emit('text', message)

    def heading(self, title):
        self.emit('heading', title)

    def error(self, message, heading=False):
        # The window offers the failed attempt's report directly; CLI commands
        # remain useful only in the terminal adapter.
        message = {
            'TV rejected the operation. Run cytv doctor; no automatic retry was attempted.':
                'The TV rejected this step. No automatic retry was attempted.',
            'TV package operation failed. Run cytv status before retrying.':
                'The TV package operation failed. No automatic retry was attempted.',
            'TV command failed. Run cytv doctor; retain the operation journal.':
                'This step could not be confirmed. Check that the TV is on and connected to the same network.',
            'Operation could not be confirmed. Check TV connectivity and run cytv status or cytv doctor. Retain local and TV recovery state; do not retry blindly.':
                'This step could not be confirmed. Check that the TV is on and connected to the same network.',
        }.get(message, message)
        self.emit('error-heading' if heading else 'error', message)

    def step(self, number, title, clear=True):
        self.options = []
        self.emit('step', (number, title, clear))

    def option(self, key, label, detail=''):
        self.options.append((str(key), label, detail))

    def prompt(self, text):
        return text

    def reader(self, ask):
        return ask

    def report(self, path):
        self.emit('report', str(path.resolve()))

    def check(self, event):
        self.emit('check', event)

    def recovery(self, profile):
        super().recovery(profile)
        self.emit('recovery', dict(profile))


class Channel:
    def __init__(self, emit):
        self.emit = emit
        self.console = DesktopConsole(emit)
        self.answers = queue.Queue()

    def answer(self, value):
        self.answers.put(value)

    def ask(self, label, secret=False):
        options, self.console.options = self.console.options, []
        self.emit('prompt', Prompt(label, [] if secret else options, secret))
        value = self.answers.get()
        if value is None:
            raise EOFError
        return value

    def secret(self, label):
        return self.ask(label, secret=True)
