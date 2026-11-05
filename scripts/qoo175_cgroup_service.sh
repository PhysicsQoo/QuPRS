#!/usr/bin/env bash
# Transient delegated-service witness only; no global cgroup changes.
set -Eeuo pipefail
trap 'code=$?; printf "QOO175_SERVICE_STEP_FAIL code=%s line=%s command=%q\n" "$code" "$LINENO" "$BASH_COMMAND" >&2' ERR

echo "QOO175_SERVICE_START pid=$$ uid=$(id -u) euid=$EUID"
rel="$(awk -F: '$1 == "0" && $2 == "" {print $3}' /proc/self/cgroup)"
test -n "$rel"
self="/sys/fs/cgroup${rel}"
anchor="$(dirname "$self")"
printf 'QOO175_CGROUP_SELF=%s\nQOO175_CGROUP_PARENT=%s\n' "$self" "$anchor"
printf 'QOO175_SELF_SUBTREE_CONTROL: '; cat "$self/cgroup.subtree_control"
printf 'QOO175_PARENT_CONTROLLERS: '; cat "$anchor/cgroup.controllers"
printf 'QOO175_PARENT_SUBTREE_CONTROL: '; cat "$anchor/cgroup.subtree_control"
printf 'QOO175_PARENT_PROCS: '; cat "$anchor/cgroup.procs"
printf 'QOO175_PARENT_DIRECTORY: '; stat -c '%u:%g %a %n' "$anchor"
test -f "$anchor/cgroup.subtree_control"
grep -qw memory "$anchor/cgroup.controllers"
if ! grep -qw memory "$anchor/cgroup.subtree_control"; then
  # This is the *new transient service* delegated subtree only.
  echo +memory > "$anchor/cgroup.subtree_control"
fi
grep -qw memory "$anchor/cgroup.subtree_control"
echo "QOO175_KERNEL_INHERITANCE_BEGIN"
python3 scripts/qoo175_cgroup_kernel_pilot.py --memory-mib 192 | tee qoo175-kernel-admission.json
echo "QOO175_KERNEL_OOM_BEGIN"
python3 scripts/qoo175_cgroup_kernel_pilot.py --memory-mib 192 --oom | tee qoo175-kernel-oom.json
echo "QOO175_KERNEL_ADMISSION_AND_OOM_PASS"
