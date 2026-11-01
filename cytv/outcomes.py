"""Per-attempt observations, never deployment or recovery authority."""
from . import prompts

FIELDS = {
    'packages': ('not-verified', 'verified'),
    'launch_request': ('not-requested', 'submitted-unconfirmed', 'accepted'),
    'startup': ('not-checked', 'process-observed', 'root-state-verified', 'not-observed', 'unverified'),
    'home_button': ('not-tested', 'confirmed-by-user', 'not-working'),
}
UNTESTED = 'The physical Home button has not been checked. A launch acknowledgement does not verify it.'
REVIEW = 'Review TV checks'


def summary(value):
    value = value if type(value) is dict else {}
    return {key: value[key] if type(value.get(key)) is str and value[key] in allowed else 'unknown'
            for key, allowed in FIELDS.items()}


class SetupOutcome:
    def __init__(self, checks, info):
        self.checks, self.info = checks, info

    @property
    def values(self):
        return self.info.setdefault('setup_outcome', {key: values[0] for key, values in FIELDS.items()})

    def begin(self):
        self.info['setup_outcome'] = {key: values[0] for key, values in FIELDS.items()}
        self.checks.update('packages', 'pending')
        self.checks.update('startup', 'unknown', 'Startup has not been verified.')
        self.checks.update('home-button', 'unknown', UNTESTED)

    def packages_verified(self):
        self.values['packages'] = 'verified'
        self.checks.update('packages', 'pass', 'Package verification does not verify startup or the Home button.')

    def launch_submitted(self):
        self.values['launch_request'] = 'submitted-unconfirmed'
        self.checks.update('startup', 'unknown', 'Launch was submitted; its result has not been confirmed.')

    def launch_accepted(self):
        self.values['launch_request'] = 'accepted'
        self.checks.update('startup', 'unknown', 'Launch request accepted. Runtime startup has not been verified.')

    def startup_observed(self, state):
        state = state if state in FIELDS['startup'] else 'unverified'
        self.values['startup'] = state
        detail = {'process-observed': 'A Helper process was observed. This does not verify Home-button behavior.',
                  'root-state-verified': 'Root guardian and Home routes were read back. This does not verify a physical Home press.',
                  'not-observed': 'No Helper process was observed in this check. Do not reinstall just to repeat it.'}.get(
                      state, 'Startup could not be verified. Save the diagnostic report; do not reinstall blindly.')
        self.checks.update('startup', 'pass' if state in ('process-observed', 'root-state-verified') else 'unknown', detail)

    def review_home(self, ask, write, non_interactive=False):
        self.values['home_button'] = 'not-tested'
        self.checks.update('home-button', 'unknown', UNTESTED)
        if non_interactive:
            return
        write.heading('Check the physical Home button')
        write('On the TV, open another app, then briefly press Home once on your remote. Did Clean Your TV Home appear?')
        write('Choose only what you observed. This records a local result; it does not change Home control or publish a report.')
        write.option(1, 'Clean Your TV Home opened')
        write.option(2, 'LG Home opened or Home did not work')
        write.option(3, 'Not tested / skip')
        try:
            choice = prompts.number(ask, write, 'Home button result [3]: ', 1, 3, default=3)
        except (EOFError, KeyboardInterrupt, StopIteration):
            choice = 3
        self.values['home_button'] = {1: 'confirmed-by-user', 2: 'not-working', 3: 'not-tested'}[choice]
        detail = {1: 'You confirmed this physical Home press. Other controls, sound and power transitions remain untested.',
                  2: 'You reported that Home did not open Clean Your TV. Save the report; do not repeat installation.',
                  3: UNTESTED}[choice]
        self.checks.update('home-button', {1: 'pass', 2: 'fail', 3: 'unknown'}[choice], detail)
        write.heading(REVIEW)
