#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python_bin="${MEAL_PLANNER_PYTHON:-}"
if [[ -z "$python_bin" ]]; then
    if [[ -x "$repo_root/venv/bin/python" ]]; then
        python_bin="$repo_root/venv/bin/python"
    else
        python_bin="$(command -v python3)"
    fi
fi

if [[ ! -x "$python_bin" ]]; then
    echo "Python interpreter not found: $python_bin" >&2
    exit 1
fi

cd "$repo_root"

test_env=(
    "PATH=$PATH"
    "HOME=${TMPDIR:-/tmp}/meal-planner-test-home"
    "PYTHONPATH=$repo_root"
    "ENV=prod"
    "APP_INSTANCE=test"
    "SECRET_KEY=test-only-secret"
    "DATABASE_URL=postgresql://test:test@127.0.0.1:5432/meal_planner_test"
    "EXPECTED_DATABASE_NAME=meal_planner_test"
    "PRODUCTION_DATABASE_NAME=fastapi_db"
    "JWT_ALGORITHM=HS256"
    "ACCESS_TOKEN_EXPIRE_MINUTES=60"
    "MEAL_PLANNER_LOAD_ENV_FILE=0"
)

env -i "${test_env[@]}" "$python_bin" -m compileall -q app tests
env -i "${test_env[@]}" "$python_bin" -m unittest discover -s tests -v

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    echo "Tracked .env detected" >&2
    exit 1
fi

if rg -n "DATABASE_URL\\s*=\\s*['\"]postgres(?:ql)?://" app/core scripts >/dev/null; then
    echo "Hardcoded active database URL detected" >&2
    exit 1
fi

echo "Sprint 0 isolated validation passed"
