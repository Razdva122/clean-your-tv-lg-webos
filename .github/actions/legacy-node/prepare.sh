#!/usr/bin/env bash
set -euo pipefail

manifest=$(cd "$(dirname "$0")" && pwd)/SHA256SUMS
archives="$RUNNER_TEMP/legacy-node-archives"
runtimes=$(mktemp -d "$RUNNER_TEMP/legacy-node.XXXXXX")
mkdir -p "$archives"
cd "$archives"

while read -r checksum archive; do
    distribution=${archive%.tar.gz}
    version=${distribution#node-}
    version=${version%-linux-x64}
    case "$version" in
        v0.10.15) variable=NODE010 ;;
        v0.10.25) variable=NODE01025 ;;
        v0.12.2) variable=NODE012 ;;
        *) exit 1 ;;
    esac
    if [[ ! -f "$archive" || -L "$archive" ]] || ! printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c - >/dev/null 2>&1; then
        rm -f -- "$archive"
        curl --fail --silent --show-error --location --retry 3 \
            "https://nodejs.org/dist/$version/$archive" --output "$archive"
    fi
    printf '%s  %s\n' "$checksum" "$archive" | sha256sum -c -
    tar -xzf "$archive" -C "$runtimes"
    printf '%s=%s/%s/bin/node\n' "$variable" "$runtimes" "$distribution" >> "$GITHUB_ENV"
done < "$manifest"
