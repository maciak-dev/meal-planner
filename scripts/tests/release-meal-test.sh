#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$repo_root/scripts/lib/release-test-env.sh"

test_root="$(mktemp -d "${TMPDIR:-/tmp}/meal-release-tooling-test.XXXXXX")"
cleanup() {
  case "$test_root" in
    "${TMPDIR:-/tmp}"/meal-release-tooling-test.*) rm -rf -- "$test_root" ;;
    *) echo "refusing unexpected cleanup path: $test_root" >&2; exit 1 ;;
  esac
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  [[ "$haystack" == *"$needle"* ]] || fail "expected output to contain: $needle"
}

assert_not_contains() {
  local haystack="$1"
  local needle="$2"
  [[ "$haystack" != *"$needle"* ]] || fail "output unexpectedly contained: $needle"
}

candidate="$test_root/candidate source with spaces"
mkdir -p "$candidate/app/core"
printf '%s\n' 'CANDIDATE_MARKER = "candidate"' > "$candidate/app/core/config.py"

valid_runner="$test_root/valid python"
cat > "$valid_runner" <<'EOF'
#!/usr/bin/env sh
exit 0
EOF
chmod +x "$valid_runner"

missing_dependency_runner="$test_root/python without pytest"
cat > "$missing_dependency_runner" <<'EOF'
#!/usr/bin/env sh
exit 1
EOF
chmod +x "$missing_dependency_runner"

if MEAL_PYTHON_BIN="$test_root/missing-python" resolve_meal_python_runner "$candidate" 2>/dev/null; then
  fail "missing runner must STOP"
fi

if MEAL_PYTHON_BIN="$missing_dependency_runner" resolve_meal_python_runner "$candidate" 2>/dev/null; then
  fail "runner without pytest/dependencies must STOP"
fi

MEAL_PYTHON_BIN="$valid_runner" resolve_meal_python_runner "$candidate"
[[ "$MEAL_RELEASE_PYTHON_BIN" == "$valid_runner" ]] || fail "valid explicit runner was not selected"

if run_in_meal_test_env "$candidate" "" /bin/true 2>/dev/null; then
  fail "missing isolated test directory must STOP"
fi

production_sentinel="$test_root/production-database-sentinel"
printf '%s\n' 'do-not-touch' > "$production_sentinel"
captured="$({
  MEAL_DATABASE_URL="postgresql://production.example/meal" \
    run_in_meal_test_env "$candidate" "$test_root/isolated env with spaces" /bin/sh -c '
      printf "DATABASE_URL=%s\n" "$DATABASE_URL"
      printf "MEAL_DATABASE_URL=%s\n" "${MEAL_DATABASE_URL:-}"
      printf "SECRET_KEY=%s\n" "$SECRET_KEY"
      printf "APP_INSTANCE=%s\n" "$APP_INSTANCE"
      printf "EXPECTED_DATABASE_NAME=%s\n" "$EXPECTED_DATABASE_NAME"
      printf "PRODUCTION_DATABASE_NAME=%s\n" "$PRODUCTION_DATABASE_NAME"
      printf "MEAL_PLANNER_LOAD_ENV_FILE=%s\n" "$MEAL_PLANNER_LOAD_ENV_FILE"
      printf "PYTEST_ADDOPTS=%s\n" "$PYTEST_ADDOPTS"
      printf "PYTHONPATH=%s\n" "$PYTHONPATH"
      printf "PWD=%s\n" "$PWD"
    '
})"

assert_contains "$captured" "DATABASE_URL=sqlite:////"
assert_contains "$captured" "meal-release-test.sqlite3"
assert_contains "$captured" "MEAL_DATABASE_URL="
assert_not_contains "$captured" "production.example"
assert_contains "$captured" "SECRET_KEY=meal-release-test-only"
assert_contains "$captured" "APP_INSTANCE=test"
assert_contains "$captured" "EXPECTED_DATABASE_NAME=meal-release-test.sqlite3"
assert_contains "$captured" "PRODUCTION_DATABASE_NAME=fastapi_db"
assert_contains "$captured" "MEAL_PLANNER_LOAD_ENV_FILE=0"
assert_contains "$captured" "PYTEST_ADDOPTS=-p no:cacheprovider"
assert_contains "$captured" "PYTHONPATH=$candidate"
assert_contains "$captured" "PWD=$candidate"
[[ "$(<"$production_sentinel")" == "do-not-touch" ]] || fail "production sentinel was mutated"

source_output="$(verify_meal_candidate_source "$candidate" "$test_root/source check" "$(command -v python3)")"
assert_contains "$source_output" "candidate source: $candidate/app"
assert_contains "$source_output" "candidate config: $candidate/app/core/config.py"

plan="$(print_meal_test_plan "/project venv/bin/python")"
assert_contains "$plan" "test runner = /project venv/bin/python"
assert_contains "$plan" "detached release candidate"
assert_contains "$plan" "temporary isolated SQLite"
assert_contains "$plan" "never MEAL_DATABASE_URL"
assert_not_contains "$plan" "production.example"
assert_not_contains "$plan" "SECRET_KEY="
assert_not_contains "$plan" "DATABASE_URL="

if rg -n 'DATABASE_URL=.*MEAL_DATABASE_URL' \
  "$repo_root/scripts/release-meal.sh" \
  "$repo_root/scripts/lib/release-test-env.sh" >/dev/null; then
  fail "production backup URL must never be assigned to test DATABASE_URL"
fi

if find "$candidate" -name __pycache__ -o -name '*.pyc' | grep -q .; then
  fail "candidate source was mutated with Python cache files"
fi

echo "PASS: Meal release isolated test environment regression suite"
