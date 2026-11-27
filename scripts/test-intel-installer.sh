#!/usr/bin/env bash
# Keep both partitions in the desktop build job that owns the installer-host receipt.
set -eu

timings=${1:?Expected timing output directory}
mkdir -p "$timings"
timings=$(cd "$timings" && pwd)
PYTHON=$("${PYTHON:-python}" -c 'import sys; print(sys.executable)')
export PYTHON
checkout=$(mktemp -d)
git worktree add --quiet --detach "$checkout" HEAD || { rmdir "$checkout"; exit 1; }
trap 'git worktree remove --force "$checkout"' EXIT
cp -R node_modules "$checkout/node_modules"

run_shard() {
  "$PYTHON" scripts/test-shard.py --shard "$1/2" -s tests/cytv -v \
    --timings "$timings/cytv-$1-of-2.json"
}

(cd "$checkout" && run_shard 1) &
first=$!
status=0
run_shard 2 || status=1
wait "$first" || status=1
exit "$status"
