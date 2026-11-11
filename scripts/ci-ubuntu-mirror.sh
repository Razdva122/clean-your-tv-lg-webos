#!/usr/bin/env bash
set -euo pipefail

# Prefer the runner's configured Ubuntu mirrors when DNS is working.
if timeout 8 getent ahostsv4 azure.archive.ubuntu.com archive.ubuntu.com security.ubuntu.com >/dev/null; then
    exit 0
fi

. /etc/os-release
test "$ID" = ubuntu && test "$VERSION_CODENAME" = noble
sources=/etc/apt/sources.list.d/ubuntu.sources
grep -Fxq 'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg' "$sources"
mirror=https://mirrors.edge.kernel.org/ubuntu
curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 15 \
    "$mirror/dists/noble-security/InRelease" --output /dev/null
# Keep suites, components and the Ubuntu archive keyring from the runner.
sudo sed -i "s|^URIs: .*|URIs: $mirror|" "$sources"
printf '%s\n' "Using the Ubuntu archive mirror at $mirror"
