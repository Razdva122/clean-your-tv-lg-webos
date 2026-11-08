<a id="early-root-admission-and-connection-guidance-unreleased"></a>

# Early Root admission and connection guidance

[CLI](../CLI.md) · [Diagnostic evidence](INSTALLER-DIAGNOSTICS.md) ·
[Recovery journey](INSTALLER-RECOVERY.md)

Root installation checks the existing Settings Service `getSystemSettings`
(`general`, `defaultApps`) and System Profile `getProfiles` (`defaultApps`,
`idleApp`, no subscription) read contracts before preparing private Python or
submitting packages. These are the two endpoints already required by Root
provisioning; no new service dependency, permission or TV runtime is introduced.
The host now invokes those reads earlier. The nine existing runtime checks remain.

Replies must explicitly succeed and match the provisioning schema. An absent
Settings `defaultApps.home` override is allowed when the effective profiles are
readable. Profile `idleApp.support` must be Boolean; `false` is valid under the
existing contract. Required route strings must be nonempty and trimmed. Negative,
malformed or unconfirmed replies stop installation and leave failed/unknown rows
visible. Failed prerequisites sort ahead of successful prerequisites; package,
startup and owner-observed Home outcome rows retain first position.

Each read has a five-second reply timeout, in addition to existing SSH command
deadlines. Initial missing-interface failure precedes private-runtime/package
preparation. Root reinstall checks before removal, then rechecks during setup;
a later failure does not prove earlier steps made no changes. Readable interfaces
do not prove write permissions, firmware support, successful provisioning or
physical Home interception. There is no Settings-only adapter or recovery bypass.

Default maintenance preflight is unchanged. Root Doctor adds the two reads only
without pending state; pending recovery does not acquire new probes or authority.
Doctor as a whole is not guaranteed passive: existing status paths may stage
verified support code. Do not run it blindly against an unresolved operation.

## Error-specific guidance

Console, Qt and Android use one fixed, localized advice table. Typed errors and
the current phase distinguish SSH reachability, sign-in, local Root key data,
negotiation/identity, Developer Mode Key Server availability/response/unlock and
TV pairing. Unknown failures retain the original diagnostic path instead of
guessing a cause from exception text. Root never receives Developer Mode advice.
An unavailable Key Server is not described as a wrong passphrase. Saved addresses
and custom ports remain local and are preserved when reviewing connection data.

Unresolved pending state takes precedence over connection advice: retain the
original records, export the report and use only verified recovery. Guidance
never connects, retries, repairs, deletes profiles, changes trust or grants
recovery authority. Trust failures require verification through existing trusted
access. Android error results offer report export and Done, plus manual connection
review only where appropriate; generic Status/Restore shortcuts are removed.
Qt retains the missing-report warning when report creation fails.

Reports export only an allowlisted guidance code and Boolean pending flag, plus
two fixed Root capability keys with enumerated reasons and bounded numeric Luna
error codes. No routes, reply bodies, exception text, addresses, key data or free
text are added. Cached/exported summaries are revalidated. First-error retention,
pending journals, SSH trust verification and existing recovery guards remain
authoritative. Local reports still require inspection before sharing.

Source checks improve refusal and troubleshooting; they do not recover existing
#133/#216 operations or establish the cause/resolution of #217's connection
failure. [Dated verification](../history/2026-11-01-installer-preflight-help.md).
