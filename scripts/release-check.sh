#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/release-check.sh <remote-branch-or-ref> [--expected-sha SHA] [--dry-run]

Read-only release preflight. Fetches origin, but never merges, pushes,
resets, stashes, deploys, or restarts services.
EOF
}

release_ref=""
expected_sha=""
dry_run=0
while (($#)); do
  case "$1" in
    --expected-sha)
      [[ $# -ge 2 ]] || { echo "STOP: --expected-sha requires a SHA" >&2; exit 2; }
      expected_sha="$2"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "STOP: unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)
      [[ -z "$release_ref" ]] || { echo "STOP: release ref supplied more than once" >&2; exit 2; }
      release_ref="$1"; shift ;;
  esac
done
[[ -n "$release_ref" ]] || { usage >&2; exit 2; }

repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "STOP: not inside a Git repository" >&2
  exit 1
}
cd "$repo_root"

remote_url="$(git remote get-url origin 2>/dev/null)" || {
  echo "STOP: origin remote is missing" >&2
  exit 1
}
case "$remote_url" in
  git@github.com:maciak-dev/meal-planner.git|https://github.com/maciak-dev/meal-planner.git) ;;
  *)
    echo "STOP: origin is not maciak-dev/meal-planner.git: $remote_url" >&2
    exit 1
    ;;
esac

if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git status --porcelain)" ]]; then
  echo "STOP: worktree is dirty" >&2
  git status --short >&2
  exit 1
fi

echo "== Meal Planner release preflight =="
echo "repo: $repo_root"
echo "remote: $remote_url"
echo "fetch: origin --prune"
if ((dry_run)); then
  git fetch --dry-run origin --prune
else
  git fetch origin --prune
fi

normalized_ref="$release_ref"
normalized_ref="${normalized_ref#refs/remotes/origin/}"
normalized_ref="${normalized_ref#origin/}"
normalized_ref="${normalized_ref#refs/heads/}"
[[ -n "$normalized_ref" ]] || { echo "STOP: empty release ref" >&2; exit 1; }

main_ref="refs/remotes/origin/main"
candidate_ref="refs/remotes/origin/$normalized_ref"
git show-ref --verify --quiet "$main_ref" || { echo "STOP: origin/main is missing" >&2; exit 1; }
git show-ref --verify --quiet "$candidate_ref" || {
  echo "STOP: remote release ref does not exist: origin/$normalized_ref" >&2
  exit 1
}

main_sha="$(git rev-parse "$main_ref")"
candidate_sha="$(git rev-parse "$candidate_ref")"
if [[ -n "$expected_sha" && "$candidate_sha" != "$expected_sha" ]]; then
  echo "STOP: expected SHA $expected_sha, got $candidate_sha" >&2
  exit 1
fi

read -r behind ahead < <(git rev-list --left-right --count "$main_ref...$candidate_ref")
merge_base="$(git merge-base "$main_ref" "$candidate_ref")"
echo "main: $main_sha"
echo "release: $candidate_sha (origin/$normalized_ref)"
echo "merge-base: $merge_base"
echo "ahead/behind release vs main: $ahead/$behind"
if ((behind != 0)); then
  echo "STOP: release ref is behind origin/main" >&2
  exit 1
fi
if ! git merge-base --is-ancestor "$main_ref" "$candidate_ref"; then
  echo "STOP: release ref cannot be fast-forwarded into main" >&2
  exit 1
fi

current_branch=""
if ! current_branch="$(git symbolic-ref --short -q HEAD 2>/dev/null)"; then
  current_branch=""
fi
if [[ "$current_branch" != "main" ]]; then
  if ((dry_run)); then
    echo "dry-run: current branch is $current_branch; apply mode requires main"
  else
    echo "STOP: apply mode must run from clean main (current: ${current_branch:-detached})" >&2
    exit 1
  fi
fi

echo "PASS: Meal Planner release preflight"
