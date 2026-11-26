# Prepare the webOS Homebrew catalog entry

**Draft, checked 2026-11-26.** The [v1.29.1 public assets](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/expanded_assets/v1.29.1)
contain the published desktop and Android installers. The on-TV application
`io.github.razdva122.cytvinstaller` and its Homebrew manifest still await publication.

## Listing and package identity

The [catalog YAML](io.github.razdva122.cytvinstaller.yml) describes the development
package with its current Root-only payload and `rootRequired: true`. The planned
autonomous installer will prefer Root and offer No-root after confirming both Root
incompatibility and support for on-TV No-root setup. See the
[edition-selection design](../../docs/superpowers/specs/2026-11-26-homebrew-edition-selection.md). Before advertising that flow, reconcile the listing, manifest,
payload and results for both editions on the selected artifact. An inconclusive
prerequisite check or an interrupted operation cannot establish incompatibility.

Copy the final YAML to `packages/io.github.razdva122.cytvinstaller.yml` in
`webosbrew/apps-repo`. Upstream derives the package ID from the filename and
checks it against the manifest. The IPK's appinfo must identify the same app.
The project is open source (`pool: main`), and `utility` is a catalog category.

The new ID uses the publisher's GitHub namespace. The linter uses the
lowercase GitHub login when suggesting a reverse-DNS package ID. Historical
development packages used `com.cleanyourtv.installer`; their manifests and
IPKs cannot be submitted under the new filename. See the
[upstream package review instructions](https://github.com/webosbrew/apps-repo/blob/bc55f62416e7c87e79edf5947c56400808bf7592/.github/instructions/packages.instructions.md)
and [namespace check](https://github.com/webosbrew/apps-repo/blob/bc55f62416e7c87e79edf5947c56400808bf7592/repogen/lintpkg.py#L184-L189).

## Catalog preflight

Use [the upstream submission rules](https://github.com/webosbrew/apps-repo#submit-your-application)
and [PR template](https://github.com/webosbrew/apps-repo/blob/main/.github/pull_request_template.md).
Keep the user-facing description in the YAML. Put AI-use disclosure and human
review evidence in the eventual PR. Put the exact artifact identity and
project acceptance results in the [acceptance record](../../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md).

- Verify the YAML against `content/schemas/packages/PackageInfo.json` and the
  generated manifest against `content/schemas/api/PackageManifest.json`.
  Check the filename against both the manifest ID and IPK appinfo.
- Check the public icon and open-source repository. For the project's screenshot
  gate, capture representative setup and maintenance views from the accepted
  TV build. Add public full-size HTTPS image URLs in the top-level `screenshots`
  list, in display order. Each item may have a `url` and a short `caption`
  for alt text. Upstream warns if screenshots are absent.
- Verify the final manifest at the YAML's stable latest-release URL. Its
  `ipkUrl` must still serve the accepted bytes from the original versioned
  release. Compare the public manifest and IPK against the frozen hashes
  and `SHA256SUMS`. Follow the [protected promotion procedure](../DEVELOPMENT.md#acceptance-and-existing-release-gate).
- From a current apps-repo checkout with its dependencies and Homebrew Toolbox
  installed, run the same steps as [upstream package CI](https://github.com/webosbrew/apps-repo/blob/main/.github/workflows/package-lint.yml).
  Use a temporary directory for the IPK:

  ```sh
  listing=packages/io.github.razdva122.cytvinstaller.yml
  package_file="$(mktemp -d)/installer.ipk"
  python -m repogen.lintpkg -f "$listing" --new
  python -m repogen.downloadipk -i "$listing" -o "$package_file"
  python -m repogen.check_compat -i "$listing" -p "$package_file"
  ```

### Local and public checks on 2026-11-26

The local Installer 0.0.0 candidate passed both upstream schemas at revision
`bc55f62416e7c87e79edf5947c56400808bf7592`. The IPK was 123,945,768 bytes,
SHA-256 `e0b87958e05660ece1773c5881194aa524185060453121b9f36e8f3e03f6d100`.
The serialized manifest SHA-256 was
`5446e40cc7a35d3dedafaa6a7a0788d7a05d94d8e5047a02c8286da16db26cea`.

| Upstream check | Observed result |
| --- | --- |
| `repogen.lintpkg --new` | Passed with the local manifest. The public source and icon resolved. The check warned about missing screenshots and requested manual license review. The [license file](../../LICENSE) contains the MIT terms and an Outfit font notice. |
| `repogen.downloadipk` | Passed using a local HTTP copy of the candidate. The downloaded SHA-256, appinfo and package ID matched. The IPK control field `Installed-Size` and manifest field `installedSize` both report 129,358,143 bytes. |
| `repogen.check_compat` | Passed with Homebrew Toolbox 0.10.0 for all seven firmware samples in the declared range (webOS 5.3.1 through 11.2.0). The verifier flagged the custom packager as a warning. |
| Live manifest URL | HTTP 404. Public delivery and real-TV acceptance remain pending. |

The catalog minimum of webOS 5.0 reflects the Node.js 8 prerequisite. LG lists
Node 8.12.0 for webOS 5.0 and Node 0.12.2 for webOS 4.x. On earlier releases,
use the computer or Android installer to check which editions are available.
[LG JavaScript service runtime table](https://webostv.developer.lge.com/develop/guides/js-service-basics#supported-nodejs-version)

The upstream IPK verifier scans JavaScript throughout the application tree.
Its unfiltered scan identified ES2017 in the embedded Node updater files,
which use async/await. All five scripts loaded by the Installer HTML parsed
as ES5. [Upstream web app analyzer](https://github.com/webosbrew/dev-toolbox-cli/blob/v20261017-2d5a7b6/common/webdetect/src/web.rs#L30-L47)

## Remaining submission gates

1. Complete the project installation, runtime, recovery, removal and physical
   Home/power cases for the selected artifact. Homebrew Channel
   [0.8.0](https://github.com/webosbrew/webos-homebrew-channel/releases/tag/v0.8.0)
   includes the access change for webOS 11. Use the current
   [verification ledger](../../docs/development/HOMEBREW-INSTALL-ACCEPTANCE.md#homebrew-080-verification-2026-11-25)
   to determine which cases still need evidence.
2. Obtain meaningful human development, testing and review. The upstream PR
   asks the submitter to attest to real-TV testing and compliance with its
   rules. Coding agents contributed to the application and this draft. Record
   the experienced developer's review and tests before making that declaration.
3. Freeze an independent Installer version and bind the approval to the exact
   IPK and serialized manifest. Development version `0.0.0` is ineligible.
   A successful candidate CI job alone cannot enable promotion.
4. After protected publication, verify the public files, complete the upstream
   checks above, and add the representative TV images. Submit the single
   package entry for catalog maintainer review when authorized.
