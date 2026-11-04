#!/usr/bin/env bash
# QOO-156: Docker-DAEMON-enforced memory limit, no cgroup delegation required.
# Evidence is NOT proof that QuPRS --max-memory-mib works.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${QOO156_DOCKER_MEM_EVIDENCE:-$ROOT/evidence/qoo156-docker-memory}"
IMAGE="${QOO156_DOCKER_MEM_IMAGE:-python:3.12-slim}"
mkdir -p "$EVIDENCE"
printf 'QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED\n' > "$EVIDENCE/verdict.txt"
printf 'QOO156_CLI_INTERNAL_MEMORY_CERTIFICATE=NOT_TESTED\n' > "$EVIDENCE/cli-internal-verdict.txt"
git -C "$ROOT" rev-parse HEAD > "$EVIDENCE/source-sha.txt"
docker --version > "$EVIDENCE/docker-version.txt"
docker info --format '{{.CgroupVersion}}' > "$EVIDENCE/docker-cgroup-version.txt"
if ! grep -Fxq 2 "$EVIDENCE/docker-cgroup-version.txt"; then
  echo 'QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: requires cgroup v2' | tee "$EVIDENCE/verdict.txt"
  exit 2
fi
docker pull "$IMAGE" > "$EVIDENCE/image-pull.log"
docker image inspect "$IMAGE" --format '{{json .RepoDigests}}' > "$EVIDENCE/image-digest.json"
# Independent in-container parent observes actual kernel cgroup memory.events.
# A large *child* touches each 4096-byte page; memory pressure is physical,
# not a virtual-only RLIMIT_AS event. The parent survives to report evidence.
PYTHON_CODE='
import pathlib,subprocess,sys
def memory_events():
    path=pathlib.Path("/sys/fs/cgroup/memory.events")
    if not path.exists():
        print("QOO156_KERNEL_EVENTS=NOT_AVAILABLE",flush=True)
        sys.exit(4)
    return {k:int(v) for k,v in (line.split() for line in path.read_text().splitlines())}
child = """import time
n=160*1024*1024
p=bytearray(n)
for i in range(0,n,4096):
    p[i] = 1
print("QOO156_PAGE_TOUCH=160_MIB",flush=True)
time.sleep(1)
"""
before=memory_events()
p=subprocess.run([sys.executable,"-c",child],capture_output=True,text=True,timeout=20)
after=memory_events()
oom_kill_delta=after.get("oom_kill",0)-before.get("oom_kill",0)
oom_delta=after.get("oom",0)-before.get("oom",0)
print(f"QOO156_KERNEL_OOM_KILL_DELTA={oom_kill_delta}",flush=True)
print(f"QOO156_CHILD_EXIT={p.returncode}",flush=True)
print(f"QOO156_CHILD_OUTPUT={p.stdout.strip()}",flush=True)
print(f"QOO156_KERNEL_OOM_DELTA={oom_delta}",flush=True)
'
for limit in 64 128 256; do
  name="qoo156-docker-memory-$limit-$$"
  docker run --detach \
    --name "$name" \
    --memory="${limit}m" --memory-swap="${limit}m" \
    --pids-limit=32 --network=none --read-only \
    --cap-drop=ALL --security-opt no-new-privileges \
    --user 65534:65534 \
    "$IMAGE" python -c "$PYTHON_CODE" \
    > "$EVIDENCE/$limit-container-id.txt"
  set +e
  timeout 30s docker wait "$name" > "$EVIDENCE/$limit-wait.txt" 2>&1
  wait_code=$?
  set -e
  docker inspect "$name" --format \
    'limit_bytes={{.HostConfig.Memory}}
exit_code={{.State.ExitCode}}
oom_killed={{.State.OOMKilled}}
status={{.State.Status}}
error={{.State.Error}}' > "$EVIDENCE/$limit-inspect.txt"
  docker logs "$name" > "$EVIDENCE/$limit-stdout.txt" 2> "$EVIDENCE/$limit-stderr.txt" || true
  docker rm -f "$name" > /dev/null || true
  if [[ "$wait_code" -ne 0 ]]; then
    printf 'QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: wait timeout/error at %sMiB\n' "$limit" | tee "$EVIDENCE/verdict.txt"
    exit 2
  fi
  actual="$(sed -n 's/^limit_bytes=//p' "$EVIDENCE/$limit-inspect.txt")"
  exited="$(sed -n 's/^exit_code=//p' "$EVIDENCE/$limit-inspect.txt")"
  killed="$(sed -n 's/^oom_killed=//p' "$EVIDENCE/$limit-inspect.txt")"
  expected="$((limit * 1024 * 1024))"
  [[ "$actual" == "$expected" ]] || {
    echo "QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: cap not applied ($limit)" | tee "$EVIDENCE/verdict.txt"
    exit 2
  }
  # Docker State.OOMKilled is logged, but on some hosted runners it stays
  # false even for exit=137. Only Linux kernel memory.events deltas count.
  if [[ "$limit" -lt 256 ]]; then
    [[ "$exited" == 0 ]] &&
      grep -Eq '^QOO156_KERNEL_OOM_KILL_DELTA=[1-9][0-9]*$' "$EVIDENCE/$limit-stdout.txt" &&
      grep -Fxq 'QOO156_CHILD_EXIT=-9' "$EVIDENCE/$limit-stdout.txt" || {
      echo "QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: no kernel-confirmed OOM kill at $limit" | tee "$EVIDENCE/verdict.txt"
      exit 2
    }
  else
    [[ "$exited" == 0 ]] &&
      grep -Fxq 'QOO156_KERNEL_OOM_KILL_DELTA=0' "$EVIDENCE/$limit-stdout.txt" &&
      grep -Fxq 'QOO156_CHILD_EXIT=0' "$EVIDENCE/$limit-stdout.txt" &&
      grep -Fq 'QOO156_CHILD_OUTPUT=QOO156_PAGE_TOUCH=160_MIB' "$EVIDENCE/$limit-stdout.txt" || {
      echo "QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: no successful high-memory control" | tee "$EVIDENCE/verdict.txt"
      exit 2
    }
  fi
  printf 'QOO156_DOCKER_MEMORY_%s_MIB=PASS (OOMKilled=%s, exit=%s)\n' \
    "$limit" "$killed" "$exited" | tee "$EVIDENCE/$limit-result.txt"
done
echo 'QOO156_DOCKER_MEMORY_CERTIFICATE=PASS' | tee "$EVIDENCE/verdict.txt"
echo 'QOO156_CLI_INTERNAL_MEMORY_CERTIFICATE=NOT_TESTED' | tee "$EVIDENCE/cli-internal-verdict.txt"
