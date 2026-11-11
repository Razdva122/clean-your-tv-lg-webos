#!/usr/bin/env bash
set -euo pipefail

# Prefer the runner's configured Ubuntu mirrors when DNS is working.
if timeout 8 getent ahostsv4 azure.archive.ubuntu.com archive.ubuntu.com security.ubuntu.com >/dev/null; then
    exit 0
fi

. /etc/os-release
test "$ID" = ubuntu
case "$VERSION_CODENAME" in jammy|noble) ;; *) exit 1 ;; esac
mirror=https://mirrors.edge.kernel.org/ubuntu
curl --fail --silent --show-error --proto '=https' --connect-timeout 5 --max-time 15 \
    "$mirror/dists/$VERSION_CODENAME-security/InRelease" --output /dev/null

# Keep the runner's suites, components and signature settings.
sources=/etc/apt/sources.list.d/ubuntu.sources
if [[ -f $sources ]]; then
    grep -Fxq 'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg' "$sources"
    sudo sed -i "s|^URIs: .*|URIs: $mirror|" "$sources"
else
    sources=/etc/apt/sources.list
    default_uri='mirror[+]file:/etc/apt/apt-mirrors[.]txt|https?://(azure[.]archive|archive|security)[.]ubuntu[.]com/ubuntu/?'
    line="^(deb(-src)?([[:space:]]+\[[^]]*\])?[[:space:]]+)($default_uri)([[:space:]]+)"
    grep -Eq "$line" "$sources"
    sudo sed -Ei "s@$line@\\1$mirror\\6@" "$sources"
fi
printf '%s\n' "Using the Ubuntu archive mirror at $mirror"
