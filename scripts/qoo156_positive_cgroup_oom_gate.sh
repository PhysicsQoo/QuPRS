#!/usr/bin/env bash
# QOO-156: positive, fail-closed Linux cgroup v2 OOM admission.
# Run only on a deliberately delegated Linux VM / ephemeral self-hosted runner.
# No sudo, privileged Docker, systemd scope, or fallback to virtual memory.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${QOO156_OOM_EVIDENCE:-$ROOT/evidence/qoo156-oom-positive}"
mkdir -p "$EVIDENCE"
printf 'QOO156_CGROUP_OOM_CERTIFICATE=NOT_ADMITTED\n' > "$EVIDENCE/verdict.txt"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$EVIDENCE/utc-started.txt"
git -C "$ROOT" rev-parse HEAD > "$EVIDENCE/source-sha.txt"
uname -a > "$EVIDENCE/kernel.txt"
cat /proc/self/cgroup > "$EVIDENCE/self-cgroup.txt" 2>/dev/null || true
if [[ -r /sys/fs/cgroup/cgroup.controllers ]]; then
  cat /sys/fs/cgroup/cgroup.controllers > "$EVIDENCE/controllers.txt"
fi
if [[ "$(uname -s)" != "Linux" ]] || [[ ! -f /sys/fs/cgroup/cgroup.controllers ]]; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: Linux unified cgroup v2 required' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi

# The actual Rust CLI intentionally runs in a leaf cgroup. Under cgroup v2,
# the memory controller can be delegated on an EMPTY ancestor, not the leaf
# containing our process. Check the SAME ancestor topology as MemoryCgroup::new
# instead of falsely rejecting a healthy sibling-worker delegation.
relative="$(awk -F: '$1 == "0" && $2 == "" {print $3}' /proc/self/cgroup)"
if [[ -z "$relative" ]] || [[ "$relative" == *'..'* ]]; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: cannot resolve effective cgroup' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi
cgroot='/sys/fs/cgroup'
candidate="$(readlink -f "$cgroot/${relative#/}")"
if [[ "$candidate" != "$cgroot" && "$candidate" != "$cgroot/"* ]]; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: cgroup path escaped mount' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi
probe=''
selected=''
cleanup() {
  if [[ -n "$probe" && -d "$probe" ]]; then
    rmdir "$probe" 2>/dev/null || true
  fi
}
trap cleanup EXIT
while [[ "$candidate" == "$cgroot" || "$candidate" == "$cgroot/"* ]]; do
  if [[ -r "$candidate/cgroup.subtree_control" && -r "$candidate/cgroup.procs" ]] \
      && grep -qw 'memory' "$candidate/cgroup.subtree_control" \
      && [[ -z "$(cat "$candidate/cgroup.procs")" ]]; then
    attempted="$candidate/qoo156-oom-preflight-$$"
    if mkdir "$attempted" 2>"$EVIDENCE/probe-create.err"; then
      selected="$candidate"
      probe="$attempted"
      break
    fi
  fi
  if [[ "$candidate" == "$cgroot" ]]; then break; fi
  candidate="${candidate%/*}"
done
if [[ -z "$probe" ]]; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: no EMPTY writable memory-enabled ancestor' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi
printf 'own_cgroup=%s\\nselected_delegated_ancestor=%s\\nprobe=%s\\n' \
  "$relative" "$selected" "$probe" > "$EVIDENCE/selected-cgroup.txt"
if ! (printf '%s' 67108864 > "$probe/memory.max") 2>"$EVIDENCE/memory-max.err"; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: memory controller not delegated' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi
if ! (printf '1' > "$probe/memory.oom.group") 2>"$EVIDENCE/oom-group.err"; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: cannot configure group OOM' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi
if [[ "$(cat "$probe/memory.max")" != 67108864 ]] || [[ ! -w "$probe/cgroup.procs" ]] || [[ ! -w "$probe/cgroup.kill" ]]; then
  echo 'QOO156_CGROUP_READINESS=NOT_ADMITTED: cgroup controls do not round-trip' | tee "$EVIDENCE/readiness.txt"
  exit 2
fi
echo 'QOO156_CGROUP_READINESS=PASS (configurable empty worker group; not an OOM certificate)' | tee "$EVIDENCE/readiness.txt"
cleanup
trap - EXIT
if [[ "${QOO156_PREFLIGHT_ONLY:-0}" == "1" ]]; then
  echo 'QOO156_CGROUP_OOM_CERTIFICATE=NOT_ADMITTED (preflight only)' | tee "$EVIDENCE/verdict.txt"
  exit 0
fi

# Compile only this package/test, on the admitted delegated runner.
cargo --version > "$EVIDENCE/cargo.txt"
rustc --version > "$EVIDENCE/rustc.txt"
sha256sum "$ROOT/rust/cli/src/supervisor.rs" "$ROOT/rust/cli/tests/supervisor.rs" \
  > "$EVIDENCE/science-source-sha256.txt"
timeout --signal=TERM --kill-after=5s 360s cargo test \
  --manifest-path "$ROOT/rust/Cargo.toml" --locked -p QuPRS_cli \
  --test supervisor --no-run > "$EVIDENCE/build.log" 2>&1
# Positive witness from real worker: 64MiB memory.max, 192MiB page-touch,
# verified kernel memory.events oom_kill and typed exit=125. A regular test
# PASS with NOT_ADMITTED is never acceptable for this gate.
set +e
timeout --signal=TERM --kill-after=5s 45s cargo test \
  --manifest-path "$ROOT/rust/Cargo.toml" --locked -p QuPRS_cli \
  --test supervisor delegated_cgroup_physically_enforces_oom_or_records_not_admitted \
  -- --exact --nocapture > "$EVIDENCE/oom-test.log" 2>&1
code=$?
set -e
printf 'test_exit=%s\n' "$code" > "$EVIDENCE/test-exit.txt"
if [[ "$code" -eq 0 ]] && grep -Fq 'QOO156_MEMORY_POSITIVE_ADMITTED' "$EVIDENCE/oom-test.log" \
   && grep -Fq 'test result: ok.' "$EVIDENCE/oom-test.log"; then
  echo 'QOO156_CGROUP_OOM_CERTIFICATE=PASS' | tee "$EVIDENCE/verdict.txt"
  exit 0
fi
echo 'QOO156_CGROUP_OOM_CERTIFICATE=NOT_ADMITTED' | tee "$EVIDENCE/verdict.txt"
exit 2
