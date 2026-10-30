"""Presentation of existing probes. Never run extra TV commands for the UI."""
STATUS = {'pending': 'Not checked', 'running': 'Checking…', 'pass': 'Passed',
          'fail': 'Failed', 'unknown': 'Could not verify'}
LABELS = {
    'ssh': 'SSH connection and sign-in', 'root-user': 'Root privileges',
    'python3': 'TV Python executable', 'python-json': 'Python json module',
    'python-fcntl': 'Python fcntl module', 'python-version': 'TV Python 3.9+',
    'node-version': 'TV Node.js 8+', 'luna-send': 'webOS Luna command',
    'apps-directory': 'webOS applications directory',
    'luna-services-directory': 'webOS service directory',
    'architecture': 'ARM32 userspace for Home Helper',
    'helper-node': 'TV Node.js 0.12.2+',
    'root-conflict': 'No conflicting Root Home routing',
    'helper-idle': 'Home Helper is stopped',
    'pairing': 'TV remote-control pairing', 'inventory': 'Read TV applications and inputs',
}
PYTHON_HINT = 'Setup can prepare private Python only after the other requirements pass; doctor does not install it.'
FAILED_HINT = 'The requirement failed or could not be verified. Save the diagnostic report.'


class CheckList:
    def __init__(self, emit=lambda event: None):
        self.emit = emit
        self.results = {}

    def prepare(self, edition, action):
        from .diagnostics import ROOT_REQUIREMENTS
        names = ROOT_REQUIREMENTS if edition == 'root' else ('architecture', 'helper-node', 'root-conflict', 'helper-idle')
        for name in ('ssh', *names, 'pairing', 'inventory'):
            detail = PYTHON_HINT if name == 'python3' else ''
            if action == 'doctor' and name in ('pairing', 'inventory'):
                detail = 'Not performed by doctor; this step runs during installation.'
            if action == 'doctor' and name in ('helper-node', 'helper-idle'):
                detail = 'Not performed by doctor; this step runs during installation.'
            self.update(name, 'pending', detail)

    def update(self, name, status, detail=None):
        previous = self.results.get(name, {})
        if detail is None:
            detail = previous.get('detail', '')
        event = {'id': name, 'label': LABELS[name], 'status': status, 'detail': detail}
        if event != previous:
            self.results[name] = event
            self.emit(dict(event))

    def finish_running(self, cancelled=False):
        for name, result in list(self.results.items()):
            if result['status'] == 'running':
                self.update(name, 'unknown' if cancelled else 'fail', FAILED_HINT)

    def probe(self, name, run):
        self.update(name, 'running')
        try:
            result = run()
        except BaseException:
            self.update(name, 'unknown', FAILED_HINT)
            raise
        self.update(name, 'pass' if result is True else 'fail' if result is False else 'unknown',
                    PYTHON_HINT if result is not True and name == 'python3'
                    else FAILED_HINT if result is None else '')
        return result
