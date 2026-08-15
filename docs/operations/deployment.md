# Meal Planner release contract

This repository contains the release checks for the production Meal Planner
runtime. It does not contain the VPS systemd unit.

## Boundaries

- VM: develop → test → commit → push.
- GitHub: source of truth and release boundary.
- VPS: run `scripts/release-meal.sh` from a clean production checkout.

The script never resets, force-pushes, reseeds data, changes auth, or restarts
any service other than the explicitly configured Meal Planner unit.

## Commands

```bash
./scripts/release-check.sh origin/feature/x
./scripts/release-meal.sh origin/feature/x --dry-run
./scripts/release-meal.sh origin/feature/x
```

The preflight verifies `git@github.com:maciak-dev/meal-planner.git`, requires a
clean worktree,
checks the release ref exists, reports merge-base and ahead/behind, and stops
if the release is behind or cannot be fast-forwarded from `origin/main`.
Apply mode fetches `origin --prune`; dry-run uses Git's fetch preview and does
not update refs.

Dry-run performs those read-only checks and prints the plan. It does not create
a backup, merge, push, restart the service or call the login URL.

## Explicit production configuration

Apply mode requires:

- `MEAL_SERVICE_NAME`: exact systemd unit name. No default is guessed.
- `MEAL_EXPECTED_PORT`: expected listening port.
- `MEAL_LOGIN_URL`: exact local or public login URL for smoke testing.
- `MEAL_DB_KIND`: `sqlite` or `postgres`.
- `MEAL_BACKUP_ROOT`: writable timestamped backup directory.
- `MEAL_DB_PATH` for SQLite, or `MEAL_DATABASE_URL` for PostgreSQL.
- `MEAL_PYTHON_BIN` optionally selects the production Python executable;
  default is `python3`.

Examples use placeholders intentionally:

```bash
MEAL_SERVICE_NAME=meal-planner.service \
MEAL_EXPECTED_PORT=8000 \
MEAL_LOGIN_URL=http://127.0.0.1:8000/login \
MEAL_DB_KIND=postgres \
MEAL_DATABASE_URL='postgresql://USER:PASSWORD@127.0.0.1/DB' \
MEAL_BACKUP_ROOT=/home/deploy/meal-backups \
./scripts/release-meal.sh origin/feature/x --dry-run
```

The actual service name, database URL/path and backup root must be supplied by
the VPS operator. They are not present in this repository. The recent release
record confirms a host service named `meal-planner.service` existed, but the
unit definition and database command remain host-owned and are not assumed by
this script.

## Apply flow

The candidate ref is tested in a temporary detached worktree with pytest and
`compileall`. The current checkout is also checked before the release. The
configured database is then backed up with SQLite `.backup` or `pg_dump`; the
archive must be non-empty. Only after that does the script perform an
`--ff-only` merge into `main` and push `origin/main`.

The script restarts only `MEAL_SERVICE_NAME`, verifies systemd active state,
the configured port and `MEAL_LOGIN_URL` returning HTTP 200.

## Stop and recovery policy

Fetch, remote, clean-tree, ref, divergence/FF, test, backup, merge, push,
restart, listener and HTTP failures stop with a non-zero exit code. If
`systemctl restart` fails because operator privileges are required, the script
prints `STOP: systemctl restart failed; operator privileges may be required`.

There is no automatic reset, revert, data repair or service fallback. The
operator records the SHA and backup path and decides recovery manually.
