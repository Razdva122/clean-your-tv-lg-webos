# Outbound HTTPS trust on the TV

Developer Mode renewal and both update downloaders use a bundled Mozilla CA store,
with certificate and hostname verification enabled. This avoids relying on the
firmware's old Node/OpenSSL CA store. The WSS connection to the TV's own SSAP
endpoint is separate from these outbound HTTPS clients.

The unmodified bundle was downloaded over verified HTTPS from
[curl's Mozilla CA conversion](https://curl.se/docs/caextract.html).
Mozilla snapshot: **2026-10-20**. Download URL:
[`cacert.pem`](https://curl.se/ca/cacert.pem). The file SHA-256 was checked against
[`cacert.pem.sha256`](https://curl.se/ca/cacert.pem.sha256):

```text
796f1389bfea13c0ed78f663b765baaff54a508e5483786bd6ece73c5e3e3cbe
```

Three isolated service packages carry identical copies of `ca-bundle.crt` and the
Mozilla Public License 2.0 in `ca-LICENSE.txt`:

- `renewal-service/`
- `updater-service/`
- `root-edition/updater/`

These copies let source runs and installed services use the same local paths,
without reaching outside the service sandbox. Packagers include the bundle and
license; Root Updater also pins their hashes in its infrastructure inventory.

To refresh the store, download the new snapshot and its published SHA-256 over
verified HTTPS, compare the file digest, replace all three copies, update this
record and run `node tests/tls-ca.cjs` plus the packaging tests. Do not fetch trust
material dynamically on the TV or fall back to disabling certificate checks.
The curl conversion does not include all browser-specific CA name constraints;
see the source page for that limitation.

Existing on-TV services need their package/infrastructure updated explicitly.
Root Updater's independently provisioned code is deliberately immutable during
ordinary Home updates; those updates alone will not refresh an older CA store.
Use the existing host recovery/migration workflow for that infrastructure.
After the 1.1.0 supervisor is explicitly provisioned, a compatible signed
whole-edition update can replace its allowlisted Root Updater infrastructure,
including the CA store, with verified rollback. This does not update the fixed
supervisor itself or turn a legacy Home-only update into an infrastructure update.
See [transition and recovery](UPDATES.md).

Wrong TV time, expired leaf certificates, a proxy's private CA and unsupported TLS
protocols still cause a safe failure. The bundled roots do not bypass those checks.


<a id="computer-installer-local-tv-control-tls-compatibility-unreleased"></a>

## Computer installer: local TV control TLS compatibility

The `cytv` installer first connects to the TV's SSAP endpoint at
`wss://TV:3001` using Python's default TLS cipher policy. If this connection
raises an SSL error before pairing starts, it retries once at the same encrypted
endpoint, adding only `AES128-GCM-SHA256` and `AES256-GCM-SHA384` to the end of the
default cipher list. Some older TV endpoints offer these static-RSA suites but
none of the default forward-secret suites. The retry retains the default TLS
1.2 minimum and OpenSSL security level; it does not enable TLS 1.0/1.1, CBC,
3DES or RC4, lower `SECLEVEL`, or fall back to plaintext `ws://TV:3000`.
Static RSA does not provide forward secrecy, so the normal cipher policy is
always attempted first.

The TV's local certificate is accepted under the existing SSAP policy; this
change adds no new trust exception. Internet downloads and their certificate
verification are outside this compatibility path. Connection timeouts, refused
connections, WebSocket upgrade failures and pairing rejections are not SSL
handshake retries. A second SSL failure propagates normally. Pairing keys are
sent only after a successful TLS and WebSocket connection; this mode does not
store a transport preference or change the registration manifest.

This change covers installer SSAP pairing, not the separate legacy `lgtv.py`
manual scripts or the on-TV Helper's TLS implementation. It requires a rebuilt
computer installer to ship. Local loopback tests exercise both RSA/AES-GCM
suites with real TLS 1.2 WebSocket connections, first pairing and saved-key
reconnection. They do not establish compatibility on a physical TV, or verify
Home routing, sound, standby, cold boot, OTA or rollback.

Related issue: [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152).
