# Install and activate Root Edition

Install Root on an already rooted TV with working root SSH access and recovery
backups. [1.4.0 acceptance](../docs/RELEASE-1.4.0-ACCEPTANCE.md) covers the recorded
C3 configuration; it does not establish other-model compatibility.

## 1. Download or build, then verify

Use the [installation guide](../docs/INSTALL.md) for desktop or Android.
Source builders and manual archive users should follow the
[manual Root procedure](../docs/MANUAL_INSTALL.md#7-root-first-installation-checks-and-persistent-activation)
and [bundle contract](package/README.md). Keep complete matching Root and Root
Updater bundles and verify included hashes. An IPK alone does not provision recovery.
Published archives use their included instructions; unreleased source commands
are identified separately in the manual guide.

## 2. Check access and install without activating

Root requires Python 3.9+, TV Node.js 8+, Homebrew services and supported ARM32
Magic Remote input. Eligible TVs may use [managed Python](../docs/OPTIONAL-PYTHON.md).
Keep strict SSH host-key verification. [Doctor](DOCTOR.md) is read-only and cannot
certify compatibility.

Normal desktop/Android cytv setup verifies recovery, stops Home Helper, enables
Home control and opens Clean without a trial countdown or Keep confirmation.
The remaining provisioning/activation steps in this section describe **manual
source bundles**, whose install request leaves Home control off.

Normal current source setup installs Root Home and Root Updater together through
the shared coordinator. Keep the original operation UUID and inspect status until
`state: complete` **and** `current: true`. A successful submission is not completion.
Pending means inspect again; conflict, recovery-required or unknown outcomes stop
activation. Do not repeat setup or replace an operation ID to bypass a pending request.

Packaged-profile migration copies validated JSON/config/icons only; it never
modifies the source installation or imports arbitrary browser storage.

## 2a. Install the independent updater once

Root Updater belongs to normal full-product setup. Signed whole-edition updates
also require explicit computer bootstrap of the separate **System Updater**.
See [updates and the original 1.3.0 → 1.4.0 OTA limitation](UPDATES.md).
Existing retained infrastructure requires matching recovery/transition review;
fresh-setup commands are not a migration shortcut.

## 3. Turn on Home control

Normal cytv setup performs activation after recovery verification. If it stops
before completion, inspect status and use **Finish Root setup** only when offered.

For manual setup or later explicit reactivation, stop Home Helper if it is running:
press Home three times within two seconds
(Helper through 0.6.13: hold Home about two seconds). Release all buttons.
Root refuses activation while Helper is present and never clears its safety latch.

Open **Home Root → Home settings → Change Home** and turn it on.
Activation checks input, the independent guardian and actual routing before
saving permanent intent. No countdown or second confirmation is required.
Check arrows/OK, short Home and Back on your TV.

## 4. Persistent operation

Root runs without an always-on computer. Confirmed normal shutdown retains the
selected profile; startup reconciles the previous transaction and requires fresh
health checks. Faults, failsafe and explicit/emergency off inhibit reactivation.
Use normal webOS power controls; direct `systemctl reboot` can be classified as
an input fault. C3 startup/standby evidence is in [current acceptance](../docs/RELEASE-1.4.0-ACCEPTANCE.md).

## Controls and recovery

| Action | Result |
| --- | --- |
| Short Home | Open Clean through system Home routing |
| Back inside an app | App handles navigation and exit confirmation |
| Confirmed Back exit | Return through native Home routing on the tested setup |
| Three short Home presses within two seconds | Restore LG Home and disable Root intent |
| Home settings → Change Home off | Restore LG routing and disable Root intent |
| Open LG Home | Visit LG Home once; retain routing preference |

Release Home between taps. Long Home is not the emergency action and can invoke
LG features such as magnification. Exit does not remove root or resume Helper.
After verified restoration, explicitly open Home Helper to return to No-root.

From a computer, run `cytv status`, then `cytv restore` if routing recovery is
needed, and inspect status again. For a manual archive, use its retained matching
`setup.py status` / `setup.py restore` through the existing root SSH alias.
Keep conflicts and recovery evidence; never delete state or repeatedly activate.
See [recovery](RECOVERY.md).

## Remove or replace Root Edition

In published v1.11.0 and later, choose **Uninstall Clean Your TV** on desktop
or Android, or run `cytv uninstall`, using the saved Root connection. Confirm once.
Removal stops owned controls/startup, removes registered project packages and
known present files, and skips missing items even after partial setup. When asked,
disconnect and reconnect TV power, wait for the network and choose **Try again**
for the final sweep. Standby and Quick Start are not a full restart. A lost
connection offers the same Retry; CYTV never restarts the TV automatically.
Completion requires both removed and verified-clean proof. See the
[current removal procedure](../docs/RECOVERY.md#next-candidate-original-operation-recovery-and-full-removal).

Published v1.11.0 retains required journals, archives and referenced Python
slots after removal and retires owned private recovery,
configuration, credentials and runtime data; minimal non-executable removal records
or genuine ownership backups may remain. Do not delete records manually to force
installation. Original unknown install outcomes remain unknown; current cleanup
readback does not invent their cause or certify physical TV behavior.

## Release scope

Root does not deliver early boot artwork, system-library changes or system ad
removal. [Current limits](STATUS.md) and [historical evidence](HISTORY.md) remain
specific to their exact builds and test scenarios. [Homebrew Installer](../homebrew/README.md)
is an unreleased separate setup client.
