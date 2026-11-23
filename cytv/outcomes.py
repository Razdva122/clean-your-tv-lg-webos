"""Per-attempt observations, never deployment or recovery authority."""
from . import prompts
from .terminal import console

FIELDS = {
    'packages': ('not-verified', 'verified'),
    'launch_request': ('not-requested', 'submitted-unconfirmed', 'accepted'),
    'startup': ('not-checked', 'process-observed', 'root-state-verified', 'not-observed', 'unverified', 'stopped-during-setup'),
    'home_button': ('not-tested', 'confirmed-by-user', 'not-working'),
}
UNTESTED = 'The physical Home button has not been checked. A launch acknowledgement does not verify it.'
REVIEW = 'Review TV checks'
START_HELPER = 'Packages verified. Open Home Helper on the TV and choose Start Helper when ready.'
ROOT_SESSION_ONLY = 'Home control applies to this TV session.'

HOME_START = 'Open an app or TV input so neither Home screen is showing.'
HOME_PRESS = 'Briefly press Home once on the physical TV remote. Clean Your TV Home should open.'
HOME_RESULTS = {
    'cytv-home': ('Clean Your TV Home opened', 'confirmed-by-user', 'pass',
                  'You confirmed this physical Home press. Continue using Clean Your TV Home.'),
    'lg-home': ('LG Home opened', 'not-working', 'fail',
                'LG Home opened. Check Home control status before changing setup.'),
    'no-visible-response': ('The screen did not change', 'not-working', 'fail',
                            'The screen did not change. Keep the current setup and save the diagnostic report.'),
    None: ('Skip / no physical press or another result', 'not-tested', 'unknown', UNTESTED),
}


def ask_home_result(ask, write):
    write = console(write)
    write('Choose what you saw after the physical press. For a phone or network remote, choose Skip.')
    options = tuple(HOME_RESULTS)
    for index, (label, _, _, _) in enumerate(HOME_RESULTS.values(), 1):
        write.option(index, label)
    try:
        return options[prompts.number(ask, write, 'Home button result [4]: ', 1, 4, default=4) - 1]
    except (EOFError, KeyboardInterrupt, StopIteration):
        return None


def home_result_fields(destination):
    fields = {'home_button': HOME_RESULTS[destination][1]}
    if destination is not None:
        fields['home_destination'] = destination
    return fields


def summary(value):
    value = value if type(value) is dict else {}
    result = {key: value[key] if type(value.get(key)) is str and value[key] in allowed else 'unknown'
              for key, allowed in FIELDS.items()}
    destination = value.get('home_destination')
    if type(destination) is str and destination in HOME_RESULTS:
        if result['home_button'] == HOME_RESULTS[destination][1]:
            result['home_destination'] = destination
    if value.get('root_home_scope') == 'current-session':
        result['root_home_scope'] = 'current-session'
    return result


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

    def root_home_session_only(self):
        self.values['root_home_scope'] = 'current-session'

    def cancelled_by_stop(self):
        self.values['startup'] = 'stopped-during-setup'
        self.checks.update('startup', 'unknown', START_HELPER)

    def review_home(self, ask, write, non_interactive=False):
        if self.values['home_button'] != 'not-tested':
            return
        if self.values['startup'] == 'stopped-during-setup':
            write(START_HELPER)
            return
        if non_interactive:
            return
        write.heading('Check the physical Home button')
        write(HOME_START)
        write(HOME_PRESS)
        destination = ask_home_result(ask, write)
        self.values.update(home_result_fields(destination))
        _, _, status, detail = HOME_RESULTS[destination]
        self.checks.update('home-button', status, detail)
        if status == 'pass' and write.frontend == 'console':
            write(detail)
        write.heading(REVIEW)
