"""Cykl życia migracji Alembica i zachowanie istniejących danych.

Każdy test uruchamia prawdziwego Alembica przez API programowe (nie subprocess)
na jednorazowej bazie SQLite w katalogu tymczasowym. Żaden test nie dotyka
PostgreSQL, RC ani produkcji.

Dlaczego to jest testowane, a nie tylko sprawdzone raz ręcznie: migracje wchodzą
w te same tabele, w których żyje 64 przepisów produkcyjnych i 5 kont. Pojedyncza
kolumna NOT NULL bez server_default albo brakujący downgrade() zamienia
wdrożenie w operację bez drogi powrotnej.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = "41e1afa8db94"
HEAD = "69eea78ac02c"
EXPECTED_CHAIN = [
    "41e1afa8db94",  # baseline - schemat produkcyjny
    "d17abcef39ac",  # users.language
    "5a84c10939a0",  # recipe_translations
    "f67f683f4e28",  # store_sections
    "539387eab2be",  # ingredients + ingredient_aliases + recipe_ingredients
    "8f9e43e7e225",  # recipes.source_*
    "69eea78ac02c",  # recipe_ingredients.parsed_name
]


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class MigrationTestCase(unittest.TestCase):
    """Wspólna obsługa jednorazowej bazy i konfiguracji Alembica."""

    def setUp(self) -> None:
        # ignore_cleanup_errors: SQLite trzyma uchwyt do pliku na Windows nawet
        # po dispose(), co inaczej zamienia sprzątanie katalogu w PermissionError.
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self._tmpdir.name) / "migrations.db"
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": f"sqlite:///{self.db_path}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        try:
            from app.core.database import engine

            engine.dispose()  # zwalnia uchwyt do pliku SQLite przed cleanupem
        except Exception:
            pass
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    def _alembic_config(self):
        from alembic.config import Config

        config = Config(str(REPO_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
        return config

    def upgrade(self, revision: str = "head") -> None:
        from alembic import command

        command.upgrade(self._alembic_config(), revision)

    def downgrade(self, revision: str) -> None:
        from alembic import command

        command.downgrade(self._alembic_config(), revision)

    def current_revision(self) -> str | None:
        from alembic.migration import MigrationContext

        from app.core.database import engine

        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()

    def table_names(self) -> set[str]:
        from sqlalchemy import inspect

        from app.core.database import engine

        return set(inspect(engine).get_table_names())

    def column_names(self, table: str) -> set[str]:
        from sqlalchemy import inspect

        from app.core.database import engine

        return {col["name"] for col in inspect(engine).get_columns(table)}


class MigrationChainTests(MigrationTestCase):
    def test_exactly_one_head(self) -> None:
        """Dwa heady oznaczają rozgałęzioną historię, której `upgrade head` nie
        potrafi zastosować - to blokuje wdrożenie, nie tylko utrudnia review."""
        from alembic.script import ScriptDirectory

        heads = ScriptDirectory.from_config(self._alembic_config()).get_heads()
        self.assertEqual(list(heads), [HEAD])

    def test_chain_is_linear_and_in_expected_order(self) -> None:
        from alembic.script import ScriptDirectory

        script = ScriptDirectory.from_config(self._alembic_config())
        revisions = [rev.revision for rev in script.walk_revisions()]
        self.assertEqual(list(reversed(revisions)), EXPECTED_CHAIN)

    def test_every_migration_has_a_downgrade(self) -> None:
        """Migracja bez downgrade() zamienia wdrożenie w operację bez drogi
        powrotnej - rollback aplikacji jest wtedy niemożliwy bez restore bazy."""
        import re

        versions_dir = REPO_ROOT / "alembic" / "versions"
        for path in sorted(versions_dir.glob("*.py")):
            with self.subTest(migration=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertRegex(source, r"def downgrade\(\)")
                body = source.split("def downgrade()", 1)[1]
                # Samo `pass` to downgrade tylko na papierze.
                self.assertNotRegex(
                    body.strip(), r'^-> None:\s*"""[^"]*"""\s*pass\s*$',
                    msg=f"{path.name}: downgrade() jest pusty",
                )


class EmptyDatabaseLifecycleTests(MigrationTestCase):
    def test_full_upgrade_from_scratch(self) -> None:
        self.upgrade("head")

        self.assertEqual(self.current_revision(), HEAD)
        self.assertLessEqual(
            {
                "users", "recipes", "ingredients", "login_log", "request_log",
                "recipe_translations", "recipe_ingredients", "ingredient_aliases",
                "store_sections",
            },
            self.table_names(),
        )

    def test_downgrade_to_baseline_removes_only_new_objects(self) -> None:
        self.upgrade("head")
        self.downgrade(BASELINE)

        self.assertEqual(self.current_revision(), BASELINE)
        tables = self.table_names()
        for new_table in ("recipe_translations", "recipe_ingredients", "ingredient_aliases", "store_sections"):
            self.assertNotIn(new_table, tables)
        # Tabele produkcyjne muszą przetrwać rollback.
        for kept in ("users", "recipes", "ingredients", "login_log", "request_log"):
            self.assertIn(kept, tables)

        self.assertNotIn("language", self.column_names("users"))
        self.assertNotIn("source_url", self.column_names("recipes"))

    def test_upgrade_downgrade_upgrade_is_repeatable(self) -> None:
        """Rollback musi dać stan, z którego da się wjechać ponownie - inaczej
        jedna nieudana próba wdrożenia blokuje kolejną."""
        self.upgrade("head")
        self.downgrade(BASELINE)
        self.upgrade("head")

        self.assertEqual(self.current_revision(), HEAD)
        self.assertIn("parsed_name", self.column_names("recipe_ingredients"))

    def test_no_model_drift_after_upgrade(self) -> None:
        """Odpowiednik `alembic check`: modele i migracje muszą opisywać ten sam
        schemat, inaczej autogenerate przy następnej zmianie wyprodukuje śmieci."""
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        self.upgrade("head")

        import app.db.models  # noqa: F401 - rejestruje modele na Base.metadata
        from app.core.database import Base, engine

        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)

        self.assertEqual(diff, [], f"Drift między modelami a schematem: {diff}")


class ProductionFixtureTests(MigrationTestCase):
    """Migracje na danych o kształcie produkcyjnym: 64 przepisy, konta,
    składniki. To jest test, który łapie kolumnę NOT NULL bez server_default -
    na pustej bazie taka migracja przechodzi bez problemu."""

    RECIPE_COUNT = 64
    PUBLIC_COUNT = 32

    def seed_baseline_data(self) -> None:
        from sqlalchemy import text

        from app.core.database import engine

        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (username, hashed_password, role, created_at) "
                "VALUES ('prod_user', 'hash', 'user', '2026-01-01 00:00:00')"
            ))
            connection.execute(text(
                "INSERT INTO users (username, hashed_password, role, created_at) "
                "VALUES ('prod_admin', 'hash', 'super_admin', '2026-01-01 00:00:00')"
            ))
            for index in range(self.RECIPE_COUNT):
                connection.execute(
                    text(
                        "INSERT INTO recipes (name, description, instructions, ingredients, "
                        "created_at, is_public, image, user_id) "
                        "VALUES (:name, 'opis', 'instrukcje', :ingredients, "
                        "'2026-01-01 00:00:00', :is_public, '', 1)"
                    ),
                    {
                        "name": f"Przepis {index}",
                        "ingredients": "2 łyżki oliwy\n1 cebula",
                        "is_public": 1 if index % 2 else 0,
                    },
                )
            connection.execute(text(
                "INSERT INTO ingredients (name, is_essential) VALUES ('pomidor', 1)"
            ))
            connection.execute(text(
                "INSERT INTO ingredients (name, is_essential) VALUES ('czosnek', 0)"
            ))

    def scalar(self, sql: str):
        from sqlalchemy import text

        from app.core.database import engine

        with engine.connect() as connection:
            return connection.execute(text(sql)).scalar()

    def rows(self, sql: str):
        from sqlalchemy import text

        from app.core.database import engine

        with engine.connect() as connection:
            return connection.execute(text(sql)).fetchall()

    def setUp(self) -> None:
        super().setUp()
        self.upgrade(BASELINE)
        self.seed_baseline_data()

    def test_recipes_survive_full_upgrade(self) -> None:
        self.upgrade("head")
        self.assertEqual(self.scalar("SELECT count(*) FROM recipes"), self.RECIPE_COUNT)

    def test_is_public_is_preserved_exactly(self) -> None:
        before = self.rows("SELECT id, is_public FROM recipes ORDER BY id")
        self.upgrade("head")
        after = self.rows("SELECT id, is_public FROM recipes ORDER BY id")

        self.assertEqual(before, after)
        self.assertEqual(self.scalar("SELECT count(*) FROM recipes WHERE is_public = 1"), self.PUBLIC_COUNT)

    def test_recipe_text_is_not_rewritten(self) -> None:
        before = self.rows("SELECT id, name, description, instructions, ingredients FROM recipes ORDER BY id")
        self.upgrade("head")
        after = self.rows("SELECT id, name, description, instructions, ingredients FROM recipes ORDER BY id")

        self.assertEqual(before, after)

    def test_existing_users_get_default_language(self) -> None:
        """users.language jest NOT NULL. Bez server_default ALTER TABLE wywalilby
        się na istniejących kontach - to jest ten test."""
        self.upgrade("head")

        languages = [row[0] for row in self.rows("SELECT language FROM users ORDER BY id")]
        self.assertEqual(languages, ["pl", "pl"])

    def test_existing_ingredients_are_not_lost_and_get_timestamps(self) -> None:
        """Migracja rozbudowuje `ingredients` w miejscu (nie drop + create), a
        created_at/updated_at są NOT NULL - istniejące wiersze muszą je dostać."""
        self.upgrade("head")

        self.assertEqual(self.scalar("SELECT count(*) FROM ingredients"), 2)
        names = [row[0] for row in self.rows("SELECT name FROM ingredients ORDER BY id")]
        self.assertEqual(names, ["pomidor", "czosnek"])
        # is_essential to jedyne pole, z którego dziś korzysta GET /ingredients/map.
        self.assertEqual(
            self.rows("SELECT name, is_essential FROM ingredients ORDER BY id"),
            [("pomidor", 1), ("czosnek", 0)],
        )
        self.assertIsNotNone(self.scalar("SELECT created_at FROM ingredients WHERE name = 'pomidor'"))
        self.assertIsNotNone(self.scalar("SELECT updated_at FROM ingredients WHERE name = 'pomidor'"))

    def test_new_recipe_columns_are_null_for_existing_rows(self) -> None:
        self.upgrade("head")

        self.assertEqual(
            self.scalar("SELECT count(*) FROM recipes WHERE source_url IS NOT NULL"), 0
        )
        self.assertEqual(
            self.scalar("SELECT count(*) FROM recipes WHERE imported_at IS NOT NULL"), 0
        )

    def test_translations_table_starts_empty(self) -> None:
        """Migracja tworzy schemat, nie dane. Backfill jest osobnym, ręcznym
        krokiem - inaczej wdrożenie schematu modyfikowałoby dane w tym samym,
        nieodwracalnym ruchu."""
        self.upgrade("head")
        self.assertEqual(self.scalar("SELECT count(*) FROM recipe_translations"), 0)

    def test_data_survives_downgrade_and_second_upgrade(self) -> None:
        self.upgrade("head")
        self.downgrade(BASELINE)

        self.assertEqual(self.scalar("SELECT count(*) FROM recipes"), self.RECIPE_COUNT)
        self.assertEqual(self.scalar("SELECT count(*) FROM ingredients"), 2)
        self.assertEqual(self.scalar("SELECT count(*) FROM users"), 2)

        self.upgrade("head")
        self.assertEqual(self.scalar("SELECT count(*) FROM recipes"), self.RECIPE_COUNT)
        self.assertEqual(self.scalar("SELECT count(*) FROM recipes WHERE is_public = 1"), self.PUBLIC_COUNT)


class BackfillScriptTests(MigrationTestCase):
    """Skrypt backfillu: domyślnie dry-run, idempotentny.

    Uruchamiany wyłącznie na tej jednorazowej bazie SQLite. Na RC i produkcji
    jest krokiem ręcznym, wymagającym osobnej zgody - patrz docstring skryptu.
    """

    def setUp(self) -> None:
        super().setUp()
        self.upgrade("head")

        from sqlalchemy import text

        from app.core.database import engine

        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (username, hashed_password, role, created_at, language) "
                "VALUES ('prod_user', 'hash', 'user', '2026-01-01 00:00:00', 'pl')"
            ))
            for index in range(5):
                connection.execute(
                    text(
                        "INSERT INTO recipes (name, description, instructions, ingredients, "
                        "created_at, is_public, image, user_id) "
                        "VALUES (:name, 'opis', 'instrukcje', 'a', '2026-01-01 00:00:00', 0, '', 1)"
                    ),
                    {"name": f"Przepis {index}"},
                )

    def _run(self, apply: bool) -> tuple[int, int]:
        import importlib

        module = importlib.import_module("scripts.backfill_recipe_translations")
        importlib.reload(module)

        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            return module.backfill(db, apply)
        finally:
            db.close()

    def count_translations(self) -> int:
        from sqlalchemy import text

        from app.core.database import engine

        with engine.connect() as connection:
            return connection.execute(text("SELECT count(*) FROM recipe_translations")).scalar()

    def test_dry_run_writes_nothing(self) -> None:
        created, skipped = self._run(apply=False)

        self.assertEqual((created, skipped), (5, 0))
        self.assertEqual(self.count_translations(), 0)

    def test_apply_creates_one_translation_per_recipe(self) -> None:
        created, skipped = self._run(apply=True)

        self.assertEqual((created, skipped), (5, 0))
        self.assertEqual(self.count_translations(), 5)

    def test_second_apply_is_idempotent(self) -> None:
        self._run(apply=True)
        created, skipped = self._run(apply=True)

        self.assertEqual((created, skipped), (0, 5))
        self.assertEqual(self.count_translations(), 5)

    def test_backfill_copies_legacy_text(self) -> None:
        from sqlalchemy import text

        from app.core.database import engine

        self._run(apply=True)
        with engine.connect() as connection:
            row = connection.execute(text(
                "SELECT language, name, description, instructions FROM recipe_translations "
                "WHERE recipe_id = 1"
            )).fetchone()

        self.assertEqual(row, ("pl", "Przepis 0", "opis", "instrukcje"))

    def test_script_does_not_import_product_service_layer(self) -> None:
        """Backfill musi działać na checkoutcie mającym sam schemat, bez warstwy
        serwisów tłumaczeń - ta wchodzi osobnym PR-em."""
        source = (REPO_ROOT / "scripts" / "backfill_recipe_translations.py").read_text(encoding="utf-8")
        self.assertNotIn("recipe_translation_service", source)


if __name__ == "__main__":
    unittest.main()
