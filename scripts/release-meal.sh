#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/release-meal.sh <remote-branch-or-ref> [options]

Options:
  --dry-run          Run checks and print the plan; do not mutate anything.
  --expected-sha SHA Require the remote ref to point at SHA.
  -h, --help         Show this help.

Apply mode requires explicit service, port, URL and database configuration.
See docs/operations/deployment.md.
EOF
}

release_ref=""
expected_sha=""
dry_run=0
while (($#)); do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    --expected-sha)
      [[ $# -ge 2 ]] || { echo "STOP: --expected-sha requires a SHA" >&2; exit 2; }
      expected_sha="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "STOP: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      [[ -z "$release_ref" ]] || { echo "STOP: release ref supplied more than once" >&2; exit 2; }
      release_ref="$1"; shift ;;
  esac
done
[[ -n "$release_ref" ]] || { usage >&2; exit 2; }

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "STOP: not inside a Git repository" >&2; exit 1; }
cd "$repo_root"
source "$repo_root/scripts/lib/release-test-env.sh"

check_args=("$release_ref")
[[ -n "$expected_sha" ]] && check_args+=(--expected-sha "$expected_sha")
((dry_run)) && check_args+=(--dry-run)
"$repo_root/scripts/release-check.sh" "${check_args[@]}"

normalized_ref="${release_ref#refs/remotes/origin/}"
normalized_ref="${normalized_ref#origin/}"
normalized_ref="${normalized_ref#refs/heads/}"
candidate_ref="refs/remotes/origin/$normalized_ref"
candidate_sha="$(git rev-parse "$candidate_ref")"
main_before="$(git rev-parse HEAD)"

required_env=(MEAL_SERVICE_NAME MEAL_EXPECTED_PORT MEAL_LOGIN_URL MEAL_DB_KIND)
for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    if ((dry_run)); then
      echo "dry-run: $name is not set; apply mode would STOP"
    else
      echo "STOP: required environment variable is not set: $name" >&2
      exit 1
    fi
  fi
done

echo "plan: release origin/$normalized_ref ($candidate_sha)"
echo "plan: tests = pytest + compileall"
echo "plan: backup = configured Meal Planner database"
echo "plan: merge = --ff-only into main, then push origin/main"
echo "plan: restart = systemctl restart ${MEAL_SERVICE_NAME:-<unset>}"
echo "plan: smoke = systemd active + port ${MEAL_EXPECTED_PORT:-<unset>} + ${MEAL_LOGIN_URL:-<unset>}"
resolve_meal_python_runner "$repo_root"
python_bin="$MEAL_RELEASE_PYTHON_BIN"
print_meal_test_plan "$python_bin"
if ((dry_run)); then
  echo "PASS: Meal Planner release dry-run (no backup, merge, push, restart, or smoke mutation)"
  exit 0
fi

[[ -n "${MEAL_DB_PATH:-}" || -n "${MEAL_DATABASE_URL:-}" ]] || {
  echo "STOP: set MEAL_DB_PATH for sqlite or MEAL_DATABASE_URL for postgres" >&2
  exit 1
}

candidate_dir=""
release_test_dir=""
candidate_worktree_added=0
cleanup_candidate() {
  if ((candidate_worktree_added)) && [[ -n "$candidate_dir" && -d "$candidate_dir" ]]; then
    git worktree remove "$candidate_dir" || echo "STOP: failed to remove candidate worktree: $candidate_dir" >&2
  elif [[ -n "$candidate_dir" && -d "$candidate_dir" ]]; then
    case "$candidate_dir" in
      "${TMPDIR:-/tmp}"/meal-release.*) rmdir "$candidate_dir" 2>/dev/null || true ;;
      *) echo "STOP: refusing to remove unexpected candidate directory: $candidate_dir" >&2 ;;
    esac
  fi
  if [[ -n "$release_test_dir" && -d "$release_test_dir" ]]; then
    case "$release_test_dir" in
      "${TMPDIR:-/tmp}"/meal-release-tests.*) rm -rf -- "$release_test_dir" ;;
      *) echo "STOP: refusing to remove unexpected test directory: $release_test_dir" >&2 ;;
    esac
  fi
}
trap cleanup_candidate EXIT
candidate_dir="$(mktemp -d "${TMPDIR:-/tmp}/meal-release.XXXXXX")"
release_test_dir="$(mktemp -d "${TMPDIR:-/tmp}/meal-release-tests.XXXXXX")"
git worktree add --detach "$candidate_dir" "$candidate_ref"
candidate_worktree_added=1
run_meal_test_gate "$candidate_dir" "$release_test_dir/candidate" "$python_bin" "detached candidate $candidate_sha"
git worktree remove "$candidate_dir"
candidate_worktree_added=0
candidate_dir=""

run_meal_test_gate "$repo_root" "$release_test_dir/current" "$python_bin" "current main $main_before"

backup_root="${MEAL_BACKUP_ROOT:-}"
[[ -n "$backup_root" ]] || { echo "STOP: MEAL_BACKUP_ROOT is required" >&2; exit 1; }
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$backup_root/meal-$timestamp-$candidate_sha"
mkdir -p "$backup_dir"
case "$MEAL_DB_KIND" in
  sqlite)
    [[ -n "${MEAL_DB_PATH:-}" ]] || { echo "STOP: MEAL_DB_PATH is required for sqlite backup" >&2; exit 1; }
    [[ -f "$MEAL_DB_PATH" ]] || { echo "STOP: sqlite database does not exist: $MEAL_DB_PATH" >&2; exit 1; }
    command -v sqlite3 >/dev/null || { echo "STOP: sqlite3 is required for sqlite backup" >&2; exit 1; }
    sqlite3 "$MEAL_DB_PATH" ".backup '$backup_dir/meal-planner.sqlite3'"
    ;;
  postgres)
    [[ -n "${MEAL_DATABASE_URL:-}" ]] || { echo "STOP: MEAL_DATABASE_URL is required for postgres backup" >&2; exit 1; }
    command -v pg_dump >/dev/null || { echo "STOP: pg_dump is required for postgres backup" >&2; exit 1; }
    pg_dump --format=custom --file="$backup_dir/meal-planner.dump" "$MEAL_DATABASE_URL"
    ;;
  *)
    echo "STOP: MEAL_DB_KIND must be sqlite or postgres" >&2
    exit 1
    ;;
esac
backup_file="$(find "$backup_dir" -maxdepth 1 -type f -size +0c -print -quit)"
[[ -n "$backup_file" ]] || { echo "STOP: database backup is missing or empty" >&2; exit 1; }
printf '%s\n' "$candidate_sha" > "$backup_dir/release-sha.txt"
printf '%s\n' "$main_before" > "$backup_dir/main-before.txt"

git merge --ff-only "$candidate_ref"
git push origin main
main_after="$(git rev-parse HEAD)"

if ! systemctl restart "$MEAL_SERVICE_NAME"; then
  echo "STOP: systemctl restart failed; operator privileges may be required" >&2
  exit 1
fi
systemctl is-active --quiet "$MEAL_SERVICE_NAME" || { echo "STOP: service is not active: $MEAL_SERVICE_NAME" >&2; exit 1; }
if ! ss -ltn | awk -v port=":$MEAL_EXPECTED_PORT" '$4 ~ port "$" { found=1 } END { exit(found ? 0 : 1) }'; then
  echo "STOP: expected listener is not active on port $MEAL_EXPECTED_PORT" >&2
  exit 1
fi
curl --fail --silent --show-error --max-time "${MEAL_HTTP_TIMEOUT_SECONDS:-10}" "$MEAL_LOGIN_URL" >/dev/null

cat <<EOF
PASS: Meal Planner release
main before: $main_before
main after:  $main_after
backup:      $backup_dir
service:     $MEAL_SERVICE_NAME
port:        $MEAL_EXPECTED_PORT
tests:       passed
smoke:       passed
EOF
