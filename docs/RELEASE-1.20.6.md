# v1.20.6

- Status and Doctor can report why a saved TV connection could not be read.
  Windows file locks are retried briefly. An explicitly selected readable
  connection remains available for limited status checks; recovery keeps
  using the saved identity (#624, #418).
- No-root removal can continue after some interrupted installs and can ask the
  TV to remove project packages missing from its normal app listing. When a
  package operation is uncertain, the installer retains recovery state (#630,
  #152, #472).
- Experimental Root removal can continue after a lost release reply when
  independent checks confirm the routing process has stopped and LG Home is
  back. Diagnostic reports distinguish the original stop from later cleanup
  failures (#623, #615, #418).
- Experimental W21 Home routing recognizes both stock callers used on the
  inspected A1/C1 firmware. Existing admission and rollback safeguards apply;
  live acceptance on the affected firmware is still unverified (#629, #615,
  #418).
- Root diagnostics report native Home and KeyFilters checks separately. When
  another Home integration needs to restore LG Home itself, the installer
  explains the next step (#631, #454, #519).

The Home and independent updater packages include Chinese font subsets regenerated
for the expanded installer translations.

| Component | v1.20.5 | v1.20.6 |
| --- | --- | --- |
| cytv | 0.20.5 | 0.20.6 |
| Android / versionCode | 0.19.5 / 42 | 0.19.6 / 43 |
| Home FHD/HD | 1.18.4 | 1.18.5 |
| Home Helper | 0.8.4 | 0.8.4 |
| Root edition | 0.19.5 | 0.19.6 |
| Independent updater | 0.5.15 | 0.5.16 |

See the [candidate record](https://github.com/Razdva122/clean-your-tv-lg-webos/pull/628)
for build and device verification.
