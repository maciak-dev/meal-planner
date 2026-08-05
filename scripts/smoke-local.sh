#!/usr/bin/env bash
set -euo pipefail

port="${1:-8002}"
base_url="http://127.0.0.1:${port}"

check_get() {
    local path="$1"
    local expected="$2"
    local actual
    actual="$(curl -sS -o /dev/null -w '%{http_code}' "${base_url}${path}")"
    printf '%s -> %s (expected %s)\n' "$path" "$actual" "$expected"
    if [[ "$actual" != "$expected" ]]; then
        return 1
    fi
}

check_get / 307
check_get /login 200
check_get /static/main.css 200
check_get /recipes-ui 302
check_get /admin 401
