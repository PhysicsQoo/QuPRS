#!/usr/bin/env bash
# Publish an immutable snapshot first, then the stable alias. Signed release
# provenance and exact-source WASM/Chromium qualification are mandatory upstream.
set -euo pipefail
test "$#" = 4
site="$(realpath "$1")"
pages="$(realpath "$2")"
tag="$3"
source_sha="$4"
test -n "$GH_TOKEN"
test -n "$GITHUB_REPOSITORY"
test -n "$PAGES_BASE"
[[ "$tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]
[[ "$source_sha" =~ ^[a-f0-9]{40}$ ]]
test "$(tr -d '\r\n' < "$site/source-sha.txt")" = "$source_sha"
# Repeat signed-tag verification immediately before the public mutation, not
# just prior to the potentially expensive native/WASM/Chromium build.
test "$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$tag" --jq .object.type)" = tag
tag_object="$(gh api "repos/$GITHUB_REPOSITORY/git/ref/tags/$tag" --jq .object.sha)"
test "$(gh api "repos/$GITHUB_REPOSITORY/git/tags/$tag_object" --jq .object.sha)" = "$source_sha"
test "$(gh api "repos/$GITHUB_REPOSITORY/git/tags/$tag_object" --jq .verification.verified)" = true
test "$(gh release view "$tag" --repo "$GITHUB_REPOSITORY" --json isDraft,isPrerelease --jq '[.isDraft,.isPrerelease] | tostring')" = '[false,false]'

git -C "$pages" config user.name 'github-actions[bot]'
git -C "$pages" config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git -C "$pages" diff --quiet
test -z "$(git -C "$pages" diff --cached --name-only)"
test "$(git -C "$pages" rev-parse HEAD)" = "$(git -C "$pages" rev-parse refs/heads/gh-pages)"

commit_push() {
  local title="$1"
  if git -C "$pages" diff --cached --quiet; then return; fi
  git -C "$pages" diff --cached --check -- playground/versions.json playground/stable-release.json
  git -C "$pages" commit -m "$title"
  git -C "$pages" push origin HEAD:gh-pages
  git -C "$pages" fetch --no-tags origin gh-pages
  test "$(git -C "$pages" rev-parse HEAD)" = "$(git -C "$pages" rev-parse FETCH_HEAD)"
}

build_pages() {
  local build_url status
  build_url="$(gh api --method POST "repos/$GITHUB_REPOSITORY/pages/builds" --jq .url)"
  for _ in $(seq 1 40); do
    status="$(gh api "$build_url" --jq .status)"
    [[ "$status" == built ]] && return 0
    [[ "$status" == errored ]] && return 1
    sleep 15
  done
  echo "::error::Pages build timeout" >&2
  return 1
}

check_live() {
  local url="$1" sha="$2" file expected got matched
  matched=false
  for _ in $(seq 1 18); do
    if curl --fail --location --silent --show-error --max-time 15 \
       -H 'Cache-Control: no-cache' "$url/source-sha.txt?v=$sha" \
       -o "$RUNNER_TEMP/playground-live-sha" &&
       [[ "$(tr -d '\r\n' < "$RUNNER_TEMP/playground-live-sha")" == "$sha" ]]; then
      matched=true
      break
    fi
    sleep 10
  done
  test "$matched" = true
  for file in index.html app.js worker.js pkg/quprs_web_bg.wasm engines/gpmc.wasm; do
    curl --fail --location --silent --show-error --max-time 35 \
      -H 'Cache-Control: no-cache' "$url/$file?v=$sha" \
      -o "$RUNNER_TEMP/playground-live-asset"
    expected="$(sha256sum "$site/$file" | cut -d' ' -f1)"
    got="$(sha256sum "$RUNNER_TEMP/playground-live-asset" | cut -d' ' -f1)"
    test "$got" = "$expected"
  done
}

# A failed snapshot never changes the public stable root.
python3 source/scripts/web/stage-versioned-pages.py snapshot \
  "$site" "$pages" --tag "$tag" --sha "$source_sha"
commit_push "site: stage immutable Playground $tag"
build_pages
check_live "$PAGES_BASE/playground/$tag" "$source_sha"

before_alias="$(git -C "$pages" rev-parse HEAD)"
previous_sha=""
if [[ -f "$pages/playground/source-sha.txt" ]]; then
  previous_sha="$(tr -d '\r\n' < "$pages/playground/source-sha.txt")"
fi
promoted=false

rollback() {
  local failure=$?
  trap - ERR
  if [[ "$promoted" == true ]]; then
    # Never roll back somebody else's newer gh-pages revision. The publication
    # lock serializes cooperating workflows; this guard also protects against
    # unrelated out-of-band branch edits or a failed push.
    local local_sha remote_sha
    local_sha="$(git -C "$pages" rev-parse HEAD)"
    remote_sha="$(git -C "$pages" ls-remote origin refs/heads/gh-pages | cut -f1)" || remote_sha=""
    if [[ -n "$remote_sha" && "$remote_sha" == "$local_sha" &&
          "$local_sha" != "$before_alias" ]]; then
      echo "::error::Stable promotion failed; restoring prior alias on gh-pages" >&2
      if git -C "$pages" restore --source="$before_alias" --staged --worktree -- playground &&
         ! git -C "$pages" diff --cached --quiet; then
        git -C "$pages" commit -m "site: restore prior Playground stable alias"
        git -C "$pages" push origin HEAD:gh-pages || true
        build_pages || true
        if [[ -n "$previous_sha" ]]; then
          echo "Prior source SHA: $previous_sha" >> "$GITHUB_STEP_SUMMARY"
        fi
      fi
    else
      echo "::error::Could not safely roll back: publication HEAD differs from live gh-pages" >&2
    fi
  fi
  exit "$failure"
}
trap rollback ERR

python3 source/scripts/web/stage-versioned-pages.py promote \
  "$site" "$pages" --tag "$tag" --sha "$source_sha"
if ! git -C "$pages" diff --cached --quiet; then
  # Arm rollback before commit/push. A push may succeed even when a subsequent
  # confirmation API call fails; the remote equality guard prevents false undo.
  promoted=true
  commit_push "site: promote validated Playground $tag"
  build_pages
fi
current="$(python3 - "$pages/playground/stable-release.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['version'])
PY
)"
stable_sha="$(tr -d '\r\n' < "$pages/playground/source-sha.txt")"
# The root is a tiny redirect into the source-pinned version. A browser must
# never reuse unversioned JS or WASM assets from a different stable release.
matched=false
for _ in $(seq 1 18); do
  if curl --fail --location --silent --show-error --max-time 15 \
      -H 'Cache-Control: no-cache' \
      "$PAGES_BASE/playground/source-sha.txt?v=$stable_sha" \
      -o "$RUNNER_TEMP/stable-source-sha" &&
     [[ "$(tr -d '\r\n' < "$RUNNER_TEMP/stable-source-sha")" == "$stable_sha" ]] &&
     curl --fail --location --silent --show-error --max-time 15 \
      "$PAGES_BASE/playground/index.html?v=$stable_sha" \
      -o "$RUNNER_TEMP/stable-index.html" &&
     grep -Fq "href=\"./$current/\"" "$RUNNER_TEMP/stable-index.html"; then
    matched=true
    break
  fi
  sleep 10
done
test "$matched" = true
curl --fail --location --silent --show-error --max-time 20 \
 "$PAGES_BASE/playground/stable-release.json?v=$stable_sha" \
 -o "$RUNNER_TEMP/stable-release.json"
test "$(python3 - "$RUNNER_TEMP/stable-release.json" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['version'])
PY
)" = "$current"
trap - ERR
echo "Immutable Playground $tag and stable alias $current verified." >> "$GITHUB_STEP_SUMMARY"
