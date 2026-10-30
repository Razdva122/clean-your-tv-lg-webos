"""Small terminal layout with a readable plain-text fallback."""
import os
import shutil
import sys
import textwrap
from .i18n import translate as tr


def supports_ansi(stream=None):
    stream = sys.stdout if stream is None else stream
    if stream is None or not stream.isatty() or os.environ.get('TERM') == 'dumb':
        return False
    if os.name == 'nt':
        # Enable ANSI in classic Windows consoles as well as Windows Terminal.
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.GetStdHandle.restype = ctypes.c_void_p
        kernel.GetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
        kernel.SetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
        handle, mode = kernel.GetStdHandle(-12 if stream is sys.stderr else -11), ctypes.c_ulong()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 4))
    return True


class Console:
    def __init__(self, write=print, width=None, interactive=None, color=None):
        self.raw = write
        self.width = max(24, min(76, width or shutil.get_terminal_size((80, 24)).columns))
        self.interactive = write is print and supports_ansi() if interactive is None else interactive
        self.color = self.interactive and 'NO_COLOR' not in os.environ if color is None else color

    def __call__(self, message=''):
        self.text(message)

    def text(self, message, bold=False):
        for line in tr(message).split('\n'):
            if not line:
                self.raw('')
                continue
            indent = '  ' + line[:len(line) - len(line.lstrip())]
            rendered = textwrap.fill(line.strip(), width=self.width, initial_indent=indent,
                                     subsequent_indent=indent, break_long_words=False, break_on_hyphens=False)
            self.raw(self.bold(rendered) if bold else rendered)

    def bold(self, text):
        return '\x1b[1m' + text + '\x1b[0m' if self.color else text

    def error(self, message, heading=False):
        if heading:
            self.raw('')
        for line in tr(message).split('\n'):
            rendered = textwrap.fill(line, width=self.width, initial_indent='  ', subsequent_indent='  ',
                                     break_long_words=False, break_on_hyphens=False)
            self.raw('\x1b[31m' + rendered + '\x1b[0m' if self.color else rendered)

    def heading(self, title):
        self.raw('')
        self.raw('  ' + self.bold(tr(title)))

    def step(self, number, title, clear=True):
        if self.interactive and clear:
            # Scroll the previous page into history before clearing the viewport.
            self.raw('\n' * max(1, shutil.get_terminal_size((80, 24)).lines))
            self.raw('\x1b[2J\x1b[H')
        self.raw('  ' + self.bold('Clean Your TV / LG webOS'))
        self.heading(f'CYTV  /  STEP {number} / 4')
        self.raw('  ' + self.bold(tr(title)))
        rule = '-' * (self.width - 4)
        self.raw('  ' + ('\x1b[38;2;255;76;32m' + rule + '\x1b[0m' if self.color else rule))
        self.raw('')

    def option(self, key, label, detail=''):
        self.raw('')
        self.text('[' + str(key) + '] ' + tr(label), bold=True)
        if detail:
            self('    ' + detail)

    def prompt(self, text):
        return '\n  ' + self.bold('> ' + tr(text))

    def reader(self, ask):
        return lambda prompt: ask(self.prompt(prompt))

    def report(self, path):
        self.heading('Diagnostic report')
        self.raw('  ' + str(path.resolve()))

    def check(self, event):
        from .checks import STATUS
        message = '[' + tr(STATUS[event['status']]) + '] ' + tr(event['label'])
        if event['status'] in ('fail', 'unknown'):
            self.error(message)
        else:
            self.text(message)
        if event['detail'] and event['status'] in ('fail', 'unknown'):
            self.text(event['detail'])

    def recovery(self, profile):
        self('Removal is unfinished. Choose Set up my TV to finish removal and reinstall.')


def console(write):
    return write if isinstance(write, Console) else Console(write)
