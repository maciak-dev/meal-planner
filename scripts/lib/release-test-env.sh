#!/usr/bin/env bash

resolve_meal_python_runner() {
  local repo_root="$1"
  local configured="${MEAL_PYTHON_BIN:-}"
  local candidate=""

  if [[ -n "$configured" ]]; then
    if [[ "$configured" == */* ]]; then
      candidate="$configured"
    else
      candidate="$(command -v "$configured" 2>/dev/null || true)"
    fi
  elif [[ -x "$repo_root/venv/bin/python" ]]; then
    candidate="$repo_root/venv/bin/python"
  elif [[ -x "$repo_root/.venv/bin/python" ]]; then
    candidate="$repo_root/.venv/bin/python"
  fi

  if [[ -z "$candidate" || ! -x "$candidate" ]]; then
    echo "STOP: Meal project Python runner is unavailable; set MEAL_PYTHON_BIN or prepare repo venv" >&2
    return 1
  fi

  candidate="$(cd "$(dirname "$candidate")" && pwd -P)/$(basename "$candidate")"
  if ! "$candidate" -c 'import pytest, bs4, httpx, jose, fastapi, sqlalchemy, alembic' >/dev/null 2>&1; then
    echo "STOP: Meal project Python runner is missing pytest or required project dependencies: $candidate" >&2
    return 1
  fi

  MEAL_RELEASE_PYTHON_BIN="$candidate"
}

print_meal_test_plan() {
  local python_bin="$1"

  echo "plan: test runner = $python_bin"
  echo "plan: test source = detached release candidate"
  echo "plan: test database = temporary isolated SQLite (never MEAL_DATABASE_URL)"
  echo "plan: test environment = dotenv disabled, APP_INSTANCE=test, candidate PYTHONPATH"
  echo "plan: test commands = python -m pytest; python -m compileall -q app tests"
}

run_in_meal_test_env() {
  local source_root="$1"
  local test_root="$2"
  local python_bin="$3"
  shift 3

  [[ -d "$source_root/app" ]] || {
    echo "STOP: candidate app source is missing: $source_root/app" >&2
    return 1
  }
  [[ -n "$test_root" ]] || {
    echo "STOP: isolated Meal test directory is missing" >&2
    return 1
  }

  mkdir -p "$test_root/home" "$test_root/tmp" "$test_root/pycache"
  local test_database_path="$test_root/meal-release-test.sqlite3"
  local test_database_url="sqlite:///$test_database_path"

  (
    cd "$source_root"
    env -i \
      "PATH=$PATH" \
      "HOME=$test_root/home" \
      "TMPDIR=$test_root/tmp" \
      "PYTHONPATH=$source_root" \
      "PYTHONPYCACHEPREFIX=$test_root/pycache" \
      "PYTEST_ADDOPTS=-p no:cacheprovider" \
      "ENV=prod" \
      "APP_INSTANCE=test" \
      "SECRET_KEY=meal-release-test-only" \
      "DATABASE_URL=$test_database_url" \
      "EXPECTED_DATABASE_NAME=meal-release-test.sqlite3" \
      "PRODUCTION_DATABASE_NAME=fastapi_db" \
      "JWT_ALGORITHM=HS256" \
      "ACCESS_TOKEN_EXPIRE_MINUTES=60" \
      "MEAL_PLANNER_LOAD_ENV_FILE=0" \
      "$python_bin" "$@"
  )
}

verify_meal_candidate_source() {
  local source_root="$1"
  local test_root="$2"
  local python_bin="$3"

  run_in_meal_test_env "$source_root" "$test_root" "$python_bin" -c '
import importlib.util
import importlib
from pathlib import Path
import sys

expected = Path(sys.argv[1]).resolve()
spec = importlib.util.find_spec("app")
locations = [] if spec is None or spec.submodule_search_locations is None else [Path(path).resolve() for path in spec.submodule_search_locations]
if set(locations) != {expected}:
    raise SystemExit(f"candidate source mismatch: expected {expected}, got {locations}")
config_module = importlib.import_module("app.core.config")
actual_config = Path(config_module.__file__).resolve()
expected_config = expected / "core" / "config.py"
if actual_config != expected_config:
    raise SystemExit(f"candidate config mismatch: expected {expected_config}, got {actual_config}")
print(f"candidate source: {locations[0]}")
print(f"candidate config: {actual_config}")
' "$source_root/app"
}

run_meal_test_gate() {
  local source_root="$1"
  local test_root="$2"
  local python_bin="$3"
  local label="$4"

  echo "== Meal test gate: $label =="
  echo "runner: $python_bin"
  echo "source: $source_root"
  echo "database: temporary isolated SQLite"
  verify_meal_candidate_source "$source_root" "$test_root" "$python_bin"
  run_in_meal_test_env "$source_root" "$test_root" "$python_bin" -m pytest
  run_in_meal_test_env "$source_root" "$test_root" "$python_bin" -m compileall -q app tests
}
