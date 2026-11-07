# Legacy Root Beta and SSH fallback

Approved in the current maintainer chat on 2026-11-07. Related issue: #383.

The common CLI, desktop and Android installer offers No-root over the existing
trusted root SSH connection when the ordinary Root Node requirement fails.
Exactly Node 0.12.2 additionally offers an explicitly selected Root Beta, backed
by a separate compiled payload including recovery and updater code. Neither
choice replaces system Node or installs Developer Mode over existing root.

Product edition is separate from SSH authentication. Persist root SSH for the
No-root fallback, including subsequent status, recovery and removal. Persist the
Beta selection without changing the device operation identity or losing pending
receipts. Inspect pending operations across both editions before offering a
switch. Never switch after submitting packages or on an uncertain Node result.

Beta retains architecture, Python, native vendor module/bootstrap and Home
contract checks. The device rechecks its exact Node policy. Normal Root retains
Node 8+. Compile the full current Root closure with the existing Babel/core-js
pipeline; keep immutable hashes and signatures. Beta blocks ordinary OTA at the
device boundary and preserves local recovery/removal. No compatibility claim
follows from host fixtures or installation. Physical TV acceptance remains a
separate owner-authorized release gate.

Reuse shared prompts for all frontends. Explain Beta limitations and request
voluntary feedback after success or failure through the existing report/form
flow. Never upload or post diagnostics automatically. Record runtime variant in
allowlisted diagnostics. Update English and localized setup guidance.

Verify exact Node 0.12.2 generated code, strict version selection, consent and
cancel, pending-operation protection, saved SSH authentication, package closure,
ordinary runtime rejection, OTA refusal and recovery availability.
