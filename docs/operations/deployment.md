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
- `MEAL_PYTHON_BIN` optionally selects the project Python executable. Without
  it the script accepts only `venv/bin/python` or `.venv/bin/python` from the
  production checkout. It never silently falls back to system `python3`.

The selected runner must already contain the dependencies declared in
`requirements.txt` and `requirements-test.txt`, including pytest. The release
script verifies imports and stops with a clear error when the runner is absent
or incomplete. It never installs packages during a release.

Examples use placeholders intentionally:

```bash
MEAL_SERVICE_NAME=meal-planner.service \
MEAL_EXPECTED_PORT=8000 \
MEAL_LOGIN_URL=http://127.0.0.1:8000/login \
MEAL_DB_KIND=postgres \
MEAL_DATABASE_URL='postgresql://USER:PASSWORD@127.0.0.1/DB' \
MEAL_BACKUP_ROOT=/path/to/backup-root \
./scripts/release-meal.sh origin/feature/x --dry-run
```

The actual service name, database URL/path and backup root must be supplied by
the VPS operator. They are not present in this repository. The recent release
record confirms a host service named `meal-planner.service` existed, but the
unit definition and database command remain host-owned and are not assumed by
this script.

For the optional MAP Control Center read integration, the Meal application
runtime may additionally set an exact comma-separated browser origin list:

```bash
MAP_CONTROL_CENTER_ORIGINS=https://map-ui.example
```

The default is empty (cross-origin access disabled). Wildcards, credentials,
paths and non-HTTP schemes are rejected at startup. This setting only lets the
configured browser origin read responses; Meal still requires its host-only
session cookie and `super_admin` for `/api/v1/admin/*`. It does not share
`SECRET_KEY`, credentials or database access with MAP.

## Apply flow

The candidate ref is tested in a temporary detached worktree with pytest and
`compileall`. The current checkout is also checked before the release. Both
gates run with `env -i`, dotenv disabled and `PYTHONPATH` pointing at the
source tree being tested. A fidelity check imports `app.core.config` and
requires it to come from that exact candidate/current checkout.

Each gate receives its own temporary SQLite `DATABASE_URL`, a non-secret test
`SECRET_KEY`, `APP_INSTANCE=test` and a temporary HOME/TMPDIR/pycache. The
directory is removed at the end. Tests never inherit the production `.env`,
never receive `MEAL_DATABASE_URL` and do not require a PostgreSQL server.

`MEAL_DATABASE_URL` belongs only to the later PostgreSQL backup step and is
passed only to `pg_dump`. It must never be copied to test `DATABASE_URL`.
After both isolated gates pass, the configured database is backed up with
SQLite `.backup` or `pg_dump`; the archive must be non-empty. Only after that
does the script perform an `--ff-only` merge into `main` and push
`origin/main`.

Dry-run verifies the project runner and prints the runner, candidate-source
policy, temporary SQLite policy and commands without printing the test secret,
database URL or any production DSN. It creates no test database or worktree.

The script restarts only `MEAL_SERVICE_NAME`, verifies systemd active state,
the configured port and `MEAL_LOGIN_URL` returning HTTP 200.

## Stop and recovery policy

Fetch, remote, clean-tree, ref, divergence/FF, test, backup, merge, push,
restart, listener and HTTP failures stop with a non-zero exit code. If
`systemctl restart` fails because operator privileges are required, the script
prints `STOP: systemctl restart failed; operator privileges may be required`.

There is no automatic reset, revert, data repair or service fallback. The
operator records the SHA and backup path and decides recovery manually.
