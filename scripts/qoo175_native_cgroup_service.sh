#!/usr/bin/env bash
# Research-only scoped delegated-cgroup native Python API witness.
set -Eeuo pipefail
trap 'code=$?; echo "QOO175_NATIVE_SERVICE_FAILURE code=$code line=$LINENO command=$BASH_COMMAND" >&2' ERR

: "${QOO175_NATIVE_PYTHON:?missing installed Python interpreter}"
test -x "$QOO175_NATIVE_PYTHON"
rel="$(awk -F: '$1 == "0" && $2 == "" {print $3}' /proc/self/cgroup)"
self="/sys/fs/cgroup${rel}"
parent="$(dirname "$self")"
printf 'QOO175_NATIVE_SERVICE_CGROUP=%s\n' "$self"
printf 'QOO175_NATIVE_PARENT_SUBTREE_CONTROL='
cat "$parent/cgroup.subtree_control"
test -f "$parent/cgroup.subtree_control"
grep -qw memory "$parent/cgroup.controllers"
if ! grep -qw memory "$parent/cgroup.subtree_control"; then
    # Only mutate this transient, explicitly delegated systemd unit.
    echo +memory > "$parent/cgroup.subtree_control"
fi
grep -qw memory "$parent/cgroup.subtree_control"
echo "QOO175_NATIVE_API_BEGIN interpreter=$QOO175_NATIVE_PYTHON"
"$QOO175_NATIVE_PYTHON" scripts/qoo175_native_cgroup_api_pilot.py | tee qoo175-native-api.json
echo "QOO175_NATIVE_API_KERNEL_PASS"
