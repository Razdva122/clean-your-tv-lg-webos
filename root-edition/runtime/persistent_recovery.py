"""Bind durable intent, guarded activation and transaction-specific recovery.

All effectful orchestration must use this operation lock. Intent is disabled
before an emergency restore; failures retain the binding and recovery evidence.
The returned start_guarded effect is a request, never permission to bypass input,
lease and provisioning readiness checks in the future activation adapter.
"""
from contextlib import contextmanager
import fcntl
import json
import os
import stat
import tempfile
import device_adapter as d
from persistent_lifecycle import identifier
from profile_recovery import validate as validate_route


class Coordinator:
    def __init__(self, store):
        self.store = store
        self.binding = store.root/'persistent-binding.json'

    @contextmanager
    def locked(self, expected):
        d.trusted_dir(self.store.root)
        fd = os.open(self.store.root/'persistent-operation.lock',
                     os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != d.EXPECTED_UID
                    or info.st_nlink != 1 or info.st_mode & 0o022):
                raise ValueError('Unsafe operation lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if self.store.read() != expected: raise ValueError('Stale operation')
            yield
        finally:
            os.close(fd)

    def write_binding(self, value):
        fd, temp = tempfile.mkstemp(dir=self.store.root, prefix='.binding-')
        try:
            with os.fdopen(fd, 'w') as out:
                json.dump(value, out, sort_keys=True); out.flush(); os.fsync(out.fileno())
            os.replace(temp, self.binding); d.sync(self.store.root)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def read_binding(self):
        try: value = d.safe_json(self.binding)
        except FileNotFoundError as exc: raise ValueError('No routing transaction binding') from exc
        if (not isinstance(value, dict) or set(value) != {'version','generation','token','transaction','restored'}
                or type(value['version']) is not int or value['version'] != 1
                or type(value['generation']) is not int or value['generation'] < 1
                or type(value['restored']) is not bool
                or not identifier(value['token']) or not identifier(value['transaction'])):
            raise ValueError('Invalid routing transaction binding')
        return value

    def route(self, tx):
        journal = d.safe_json(d.STATE/'profile-trial.json')
        validate_route(journal)
        if journal.get('transaction') != tx: raise ValueError('Different routing transaction')
        return journal

    def bind(self, expected, transaction):
        with self.locked(expected):
            return self._bind(expected, transaction)

    def _bind(self, expected, transaction):
        if self.store.read() != expected: raise ValueError('Stale binding request')
        if expected['phase'] not in ('trial','starting') or not identifier(transaction):
            raise ValueError('Binding requires an unconfirmed attempt')
        journal = self.route(transaction)
        if journal['state'] != 'pending': raise ValueError('Routing trial is not pending')
        value = dict(version=1, generation=expected['generation'], token=expected['token'],
                     transaction=transaction, restored=False)
        if os.path.lexists(self.binding):
            old = self.read_binding()
            if old == value: return old
            if not old['restored']: raise ValueError('Previous binding not restored')
        self.write_binding(value)
        return value

    def event(self, expected, kind, **fields):
        event = dict(kind=kind, generation=expected['generation'], token=expected['token'])
        event.update(fields)
        return self.store.apply(expected, event)

    def exit(self, expected, reason='exit'):
        if reason not in ('exit','fault'): raise ValueError('Invalid stop reason')
        with self.locked(expected):
            intent, effect = self.event(expected, reason)
            try:
                from cli import inhibit
                inhibit(d.STATE)
            except Exception: pass  # Audio state must never block emergency Home restoration.
            if effect == 'recover': return self._recover(intent)
            d.native_input_disable()
            return dict(intent=intent,effect=effect)

    def boot(self, expected, boot, token, failsafe):
        with self.locked(expected):
            intent, effect = self.event(expected, 'boot', boot=boot, token=token, failsafe=failsafe or not d.home_present())
            return self._recover(intent) if effect == 'recover' else dict(intent=intent,effect=effect)

    def resume_recovery(self, expected):
        with self.locked(expected):
            if expected['phase'] != 'recovering': raise ValueError('No pending intent recovery')
            return self._recover(expected)

    def _recover(self, intent):
        try:
            return self._recover_route(intent)
        finally:
            # Routing/emergency restoration takes priority over optional EIM RPCs.
            # Failed cleanup retains its receipt and is retried by explicit/boot
            # recovery, even when the routing intent is already disabled.
            if not self.store.read()['enabled']:
                d.native_input_disable()

    def _recover_route(self, intent):
        if intent['enabled'] and not d.home_present():intent,_=self.event(intent,'fault')
        try:
            if not os.path.lexists(self.binding) and not intent['enabled']:
                # A start may fail before any routing journal/binding was made.
                # Only reconcile that absence after independently proving stock.
                from profile_plan import plan
                if (os.path.lexists(d.TARGET) or os.path.lexists(d.STATE/'profile-candidate.stage')):
                    raise ValueError('Unbound profile evidence exists')
                current = d.read()
                plan({'returnValue':True,'profiles':current['profiles']},current['sam_home'])
                if os.path.lexists(d.STATE/'profile-trial.json'):
                    j = d.safe_json(d.STATE/'profile-trial.json'); validate_route(j)
                    if j['state'] != 'restored' or current != j['baseline']:
                        raise ValueError('Unbound routing journal is unresolved')
                updated, effect = self.event(intent, 'restored')
                return dict(intent=updated, effect=effect)
            binding = self.read_binding()
            if binding['generation'] > intent['generation']:
                raise ValueError('Binding belongs to a newer intent')
            if (binding['generation'] == intent['generation']
                    and binding['token'] != intent['token']):
                raise ValueError('Binding attempt mismatch')
            tx = binding['transaction']
            journal = self.route(tx)
            result = d.restore_once(expected_transaction=tx)
            if result != 'restored': raise ValueError('Routing recovery incomplete: '+str(result))
            after = self.route(tx)
            if (after['state'] != 'restored' or after['baseline'] != journal['baseline']
                    or d.read() != journal['baseline']):
                raise ValueError('Routing restoration not verified')
            self.write_binding(dict(binding, restored=True))
            updated, effect = self.event(intent, 'restored')
            return dict(intent=updated, effect=effect, restored_transaction=tx)
        except Exception:
            # Never turn a concurrent explicit stop back on. Recovery stays
            # resumable and the existing routing journal is not discarded.
            if self.store.read() == intent and intent['enabled']:
                self.event(intent, 'fault')
            raise

    def shutdown(self, expected):
        # Preserve the confirmed profile as well as intent: bootd reads the
        # generated profile before our recovery activity runs. Restoring here
        # makes LG Home the first app on the next boot. Boot recovery still
        # restores the old transaction before arming a fresh guarded route.
        with self.locked(expected):
            if not d.home_present(purpose='live'):
                intent,_=self.event(expected,'fault');self._recover(intent);return True
            if expected['phase'] not in ('active','stopping') or not expected['enabled']:
                raise ValueError('Shutdown cannot promote unconfirmed intent')
            # Persist classification before any RPC can stall or shutdown kills us.
            # Retry cannot turn this confirmed shutdown into an input fault.
            if expected['phase'] == 'active': self.event(expected,'shutdown')
            return True

    def _healthy(self, intent):
        from persistent_health import require_fresh, require_guardian
        binding = self.read_binding()
        if (binding['generation'],binding['token']) != (intent['generation'],intent['token']) or binding['restored']:
            raise ValueError('Inactive transaction binding')
        tx = binding['transaction']; journal = self.route(tx)
        require_fresh(tx)
        require_guardian(tx)
        if not d.active_guardian(journal): raise ValueError('Independent guardian is not ready')
        current = d.read(); candidate = journal['candidate']
        if (current['sam_home'] != candidate
                or current['profiles']['defaultApps']['categories']['home'] != candidate
                or current['profiles']['idleApp']['appId'] != candidate):
            raise ValueError('Candidate Home is not effective')
        return tx

    def confirm(self, expected):
        from provision import verify
        from helper_bridge import require_idle
        verify(); require_idle()
        with self.locked(expected):
            if expected['phase'] != 'trial': raise ValueError('No unconfirmed trial')
            # Serialize promotion with actual routing restore, not only intent
            # changes; the legacy recovery fallback holds this same lock.
            fd = os.open(d.STATE/'profile-trial.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                tx = self._healthy(expected)
                import time
                if self.route(tx)['deadline'] - time.monotonic() < 5:
                    raise ValueError('Too close to rollback deadline; start a new trial')
                intent, effect = self.event(expected, 'confirmed')
                return dict(intent=intent,effect=effect,transaction=tx,persistent=True)
            finally: os.close(fd)

    def restart(self, expected):
        import emergency_trial
        with self.locked(expected):
            if expected['phase'] != 'starting': raise ValueError('No verified boot recovery')
            try:
                d.require_home()
                result = emergency_trial.start(before_publish=lambda tx:self._bind(expected,tx))
                import time
                from persistent_health import require_fresh
                for attempt in range(20):
                    try:
                        require_fresh(result['transaction']); break
                    except (OSError,ValueError): time.sleep(.1)
                self._healthy(expected)
                intent, effect = self.event(expected,'ready')
                # Rearm protection without a foreground side effect here.
                # The boot dispatcher separately checks startup and foreground.
                return dict(intent=intent,effect=effect,trial=result,persistent=True)
            except Exception:
                current = self.store.read()
                if (current['generation'],current['token']) == (expected['generation'],expected['token']):
                    self.event(current,'fault')
                raise

    def enable(self, expected, boot, token):
        """Activate persistently once input and recovery are ready."""
        import time
        from persistent_health import require_fresh
        try:
            result = self.start_trial(expected, boot, token)
            for attempt in range(20):
                try:
                    require_fresh(result['trial']['transaction'])
                    break
                except (OSError, ValueError):
                    if attempt == 19: raise
                    time.sleep(.1)
            confirmed = self.confirm(result['intent'])
            with self.locked(confirmed['intent']):
                try:
                    confirmed['native_input'] = d.native_input_enable()
                except Exception:
                    # Missing EIM is an optional optimization. An issued native
                    # mutation must be cleaned before continuing ordinary Home.
                    d.native_input_disable()
                    confirmed['native_input'] = 'unavailable'
            return confirmed
        except Exception:
            current = self.store.read()
            if (current['generation'], current['token']) == (expected['generation'] + 1, token):
                self.exit(current, reason='fault')
            raise

    def start_trial(self, expected, boot, token):
        # The existing independent 60-second deadline is never removed here.
        import emergency_trial
        with self.locked(expected):
            d.require_home()
            intent, effect = self.event(expected, 'enable', boot=boot, token=token)
            try:
                result = emergency_trial.start(before_publish=lambda tx:self._bind(intent, tx))
                return dict(intent=intent, trial=result, persistent=False)
            except Exception:
                if self.store.read() == intent: self.event(intent, 'fault')
                raise


def bound_exit(transaction, reason=None):
    """Return None for a legacy trial; otherwise disable bound intent and restore."""
    from persistent_store import Store
    c = Coordinator(Store(d.STATE))
    if not os.path.lexists(c.binding): return None
    binding = c.read_binding()
    if binding['transaction'] != transaction: return None
    intent = c.store.read()
    if (binding['generation'], binding['token']) != (intent['generation'], intent['token']):
        # A newer lifecycle owns boot recovery; never disable it from an old observer.
        return None
    from intent_runtime import boot_identity
    try: current_boot = boot_identity()
    except (OSError,ValueError): current_boot = None
    home = d.home_present(purpose='live')
    failsafe = d.FAILSAFE.exists() if home else None
    safe = home and not failsafe
    if (reason != 'escape' and safe and intent['enabled']
            and intent['phase'] in ('active','stopping') and current_boot is not None
            and intent['boot'] != current_boot):
        # An old snapshot observer can run before boot dispatch changes the
        # generation. Leave restore-first and fresh input gates to that owner.
        # True also prevents callers falling back to an unbound route restore.
        return True
    if reason == 'escape':
        from update_guard import cancel
        try:cancel(d.STATE,d.EXPECTED_UID,intent)
        except Exception:
            c.exit(intent, reason='fault')
            raise
    from shutdown_state import stopping
    eligible = safe and current_boot == intent['boot'] and reason != 'escape' and intent['enabled']
    proof = stopping(transaction) if eligible and intent['phase'] == 'active' else None
    shutdown = eligible and (intent['phase'] == 'stopping' or (intent['phase'] == 'active' and proof))
    print(json.dumps(dict(event='bound-exit-decision',transaction=transaction,reason=reason,
                         phase=intent['phase'],enabled=intent['enabled'],shutdown=shutdown,
                         home_present=home,failsafe_present=failsafe,
                         current_session_known=current_boot is not None,
                         same_session=current_boot == intent['boot'] if current_boot is not None else None,
                         shutdown_proof=proof)),flush=True)
    if shutdown:
        print('Confirmed system shutdown: retaining active intent for boot recovery', flush=True)
        return c.shutdown(intent)
    result = c.exit(intent, reason='fault')
    return result.get('restored_transaction') == transaction
