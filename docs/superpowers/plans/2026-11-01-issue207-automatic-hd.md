# Automatic HD package delivery for issue 207

Implement the user's authorized installer/OTA follow-up on `release/next` without selecting release versions or device acceptance. Keep native Helper unchanged.

## Design

Read only `luna://com.webos.service.tv.systemproperty/getSystemInfo` with `{"keys":["UHD"]}`. Require `returnValue === true`, and exact boolean or lower-case string true/false. True selects 1920x1080, false selects 1280x720; every unknown/denied/malformed result stops before install mutation. Do not infer from viewport, model names, panel/video dimensions or installed manifest.

Build both concrete Home IPKs and complete Root bundles before personalization. Payload catalogue:

```json
{"graphics":{"1920x1080":{"launcher":"launcher.ipk","root":"root"},"1280x720":{"launcher":"launcher-720p.ipk","root":"root-720p"}}}
```

Preserve FHD schema-1 feeds for published clients; add `system-update-{edition}-720p.json` with unchanged edition and exact fields, and strict `_720p_all.ipk` public names for selected launchers. A selected channel is not trust: verify proof, expected signed launcher URL and inspected package resolution. Retain original exact rollback descriptors/packages and all version rules. Existing independently provisioned supervisors require the supported host migration to acquire the selector; ordinary OTA cannot silently replace that infrastructure. Legacy Home HD feed requires a genuinely published prior HD rollback; otherwise refuse it rather than fabricate provenance.

## Tasks and checks

1. Shared installer: `cytv/graphics.py:resolution(info)`, `Installer.install` selects once before preflight/mutation; `install_root` copies selected bundle. Focused tests must first fail for unknown parser/selection; cover UHD true/false, invalid replies, missing/tampered variant, Root/No-root personalization, unchanged recovery/resume and Android shared entry.
2. Build/release: generate both variants and exhaustive hashes; verify ID/version/resolution in every embedded platform payload. Extend manual bundles, unsigned manifests, signing and publication verification/checksums. `system-manifests.json` gains root-720p/no-root-720p keys with unchanged editions. Signed legacy Root HD manifest is `root-720p`; first HD publication requires increasing Home/Root versions. Keep historical FHD verifiers/fixtures valid.
3. OTA: fixed capability call in both Python adapters and legacy Home service, strict feed choice in Node verifiers, expected signed naming and package resolution checks. Tiny parser copies in fixed adapters avoid adding retained-code module dependencies; cross-test same inputs. Prepare verifies capability/candidate once before mutation, resumed rollback uses retained exact bytes. Add red/green tests for cross-channel signed proof substitution, FHD bytes under HD descriptor, unknown capability, coherent selected sets and unchanged baseline rollback.
4. Document candidate-only automatic selection, unknown behavior, existing-supervisor migration and first HD legacy limitations in developer/manual and localized guides. No new TV connection/installation.
5. Independent implementation/security review, affected installer/TV/setup/release and Android packaging checks, selected PR CI. Merge only checked head to release/next; collect inventory, dated evidence, update #210 and #207 accurately. Original IR routing remains unresolved; no full-candidate or hardware claim.
