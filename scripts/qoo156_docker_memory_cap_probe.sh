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
# bytearray touches every page so Linux RSS accounting is real, not virtual memory reservation.
# After successful allocation, hold pages for one second.
PYTHON_CODE='import sys,time; n=160*1024*1024; m=bytearray(n)
for i in range(0,n,4096): m[i]=1
print("QOO156_PAGE_TOUCH=160_MIB",flush=True); time.sleep(1)'
declare -A result
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
  if [[ "$limit" -lt 256 ]]; then
    [[ "$exited" == 137 && "$killed" == true ]] || {
      echo "QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: expected kernel OOM at $limit" | tee "$EVIDENCE/verdict.txt"
      exit 2
    }
  else
    [[ "$exited" == 0 && "$killed" == false ]] &&
      grep -Fq 'QOO156_PAGE_TOUCH=160_MIB' "$EVIDENCE/$limit-stdout.txt" || {
      echo "QOO156_DOCKER_MEMORY_CERTIFICATE=NOT_ADMITTED: no positive control" | tee "$EVIDENCE/verdict.txt"
      exit 2
    }
  fi
  printf 'QOO156_DOCKER_MEMORY_%s_MIB=PASS (OOMKilled=%s, exit=%s)\n' \
    "$limit" "$killed" "$exited" | tee "$EVIDENCE/$limit-result.txt"
done
echo 'QOO156_DOCKER_MEMORY_CERTIFICATE=PASS' | tee "$EVIDENCE/verdict.txt"
echo 'QOO156_CLI_INTERNAL_MEMORY_CERTIFICATE=NOT_TESTED' | tee "$EVIDENCE/cli-internal-verdict.txt"
