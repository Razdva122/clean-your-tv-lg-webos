# Root native startup input

Status: unpublished 1.5.3 candidate behavior, not a claim about stable 1.5.2.
Track implementation and affected acceptance in [#204](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/204).

## Behavior

After explicit **Change Home** activation has passed the existing input-health,
independent guardian and routing checks, Root optionally registers its existing
app as a native External Input Manager (EIM) input. It remembers that input through
EIM's `setLastInput` API. On the tested C3, bootd can choose this remembered MVPD
app for Cover App before the later guarded Home handler runs. The entry uses the
existing `supportGIP` and large icon; no firmware patch, new endpoint or LS2 grant
is introduced.

Native presentation does not grant input control. Restore-first, failsafe, package
integrity, fresh input/guardian requirements and explicit Off remain authoritative.
A missing or unsupported EIM API leaves ordinary guarded Home available, provided
any native operation already issued has been safely reversed. An existing unowned
Root input is not adopted, overwritten or deleted. This is not a universal promise
that Clean will be the first screen on every firmware.

A private root-owned `native-input.json` receipt records the fixed app identity,
previous remembered input and `adding`, `active`, `removing` or `disabled` phase.
It contains local device state and must not be included in public diagnostics.
The adapter lives in the existing authenticated `runtime/device_adapter.py`
destination, preserving the installed System supervisor's infrastructure contract.

## Off, emergency and recovery

Turning **Change Home** off, triple-Home emergency release, an unclassified input
fault, failed startup or failsafe recovery first restores ordinary Home routing.
Cleanup then restores the saved remembered input only if it still points to Clean,
and removes only the entry owned by the receipt. A different input chosen meanwhile
is preserved. Cleanup never launches Live TV or another foreground application.
Turning the TV off is distinct: a positively classified normal shutdown retains
Home intent and its native input for the next boot.

A timed-out operation remains pending. Readbacks, rather than acknowledgements or
blind replays, establish removal and a safe remembered input. An unavailable EIM
cannot prevent the initial emergency route restoration; cleanup errors retain the
receipt for recovery. Each optional native operation has a 1.5-second RPC budget,
including transport teardown, so it cannot monopolize the Home operation lock.

System update suspension removes the owned native entry before replacement;
normal verified Home resumption can register it again. Retained rollback and
uninstall use that same supported restoration path before replacing/removing the
runtime. Do not clear receipts, intent, failsafe or updater journals to force a
successful result. After interrupted recovery, inspect status and finish the
original operation before starting another install.

## Evidence and remaining acceptance

On maintainer-owned OLED55C3RLA, firmware 43.21.71 / webOS SDK 11.2.0,
macOS ARM64 host, remote model unknown, an authorized temporary EIM registration
of Root 0.6.2 from full build `41118810865:1` (signed QA `41120901055:1`)
produced one owner-observed cold boot with Clean first and no channel screen.
Native metadata placed Cover App submission at 14.72 seconds, Clean foreground
at 29.11 seconds and boot-done at 37.36 seconds; metadata alone is not visual proof.
The owner observation supplies that result. The trial entry was removed afterward.

A separate bounded native API roundtrip on the same unchanged candidate passed:
add a previously absent owned entry, remember Clean, restore the exact previous
DTV input and remove the trial entry. Foreground and Home intent were unchanged;
the original remembered input and unrelated entries were verified afterward.
This validates the inverse API, not the new implementation's package acceptance.

Final signed-package acceptance still needs ordinary enable/disable, triple-Home,
fault/failsafe recovery, independent app/input preservation, standby, cold boot,
update/retained rollback and uninstall. In particular, [#171](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/171)
remains a separate unresolved retained-intent failure after remote-power input
teardown. An enabled-mode first-screen experiment does not fix or accept it.
