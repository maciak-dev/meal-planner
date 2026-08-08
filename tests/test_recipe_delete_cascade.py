import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class RecipeDeleteCascadeTests(unittest.TestCase):
    """Usuwanie przepisu, który ma dzieci w recipe_translations i/lub
    recipe_ingredients.

    Regresja: obie tabele mają recipe_id NOT NULL z ON DELETE CASCADE po
    stronie bazy, ale relacje ORM nie deklarowały kaskady, więc SQLAlchemy
    przed DELETE próbowało wykonać UPDATE ... SET recipe_id = NULL i całe
    usuwanie kończyło się IntegrityError (HTTP 500). Dotyczyło to każdego
    przepisu utworzonego przez create_recipe/create_recipe_from_import oraz
    każdego przepisu legacy po uruchomieniu backfillu tłumaczeń.

    Testy sprawdzają obie strony: że DELETE przechodzi i że dzieci naprawdę
    znikają, zamiast zostać osierocone z martwym recipe_id.
    """

    def setUp(self) -> None:
        # ignore_cleanup_errors + engine.dispose() w tearDown: SQLite trzyma
        # uchwyt do pliku na Windows, patrz test_recipe_translation_compatibility.
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "cascade.db"
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        )
        self._env_patch.start()

        import app.db.models  # noqa: F401 - rejestruje modele na Base.metadata
        from app.core.bootstrap import initialize_database_schema

        initialize_database_schema()

        from app.core.database import SessionLocal
        from app.db.models.user import User

        self.db = SessionLocal()
        user = User(username="deleteuser", hashed_password="x", role="user")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user = user

    def tearDown(self) -> None:
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    # --- helpers -----------------------------------------------------------

    def _make_recipe(self, name: str = "Do usuniecia"):
        from app.db.models.recipe import Recipe

        recipe = Recipe(
            name=name,
            description="D",
            instructions="I",
            ingredients="a\nb",
            user_id=self.user.id,
        )
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)
        return recipe

    def _add_translation(self, recipe, language: str = "pl"):
        from app.db.models.recipe_translation import RecipeTranslation

        translation = RecipeTranslation(
            recipe_id=recipe.id,
            language=language,
            name=f"{recipe.name} ({language})",
            description="D",
            instructions="I",
        )
        self.db.add(translation)
        self.db.commit()
        return translation

    def _add_structured_ingredient(self, recipe, text: str = "2 lyzki oliwy", ingredient_id: int | None = None):
        from app.db.models.recipe_ingredient import RecipeIngredient

        item = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient_id,
            original_text=text,
            parsed_name="oliwa",
            quantity=2,
            unit="lyzka",
            sort_order=0,
            needs_review=False,
        )
        self.db.add(item)
        self.db.commit()
        return item

    def _add_ingredient(self, name: str = "czosnek"):
        from app.db.models.ingredient import Ingredient

        ingredient = Ingredient(name=name, is_essential=True)
        self.db.add(ingredient)
        self.db.commit()
        self.db.refresh(ingredient)
        return ingredient

    def _counts(self, recipe_id: int):
        from app.db.models.recipe_ingredient import RecipeIngredient
        from app.db.models.recipe_translation import RecipeTranslation

        return (
            self.db.query(RecipeTranslation).filter(RecipeTranslation.recipe_id == recipe_id).count(),
            self.db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe_id).count(),
        )

    # --- testy -------------------------------------------------------------

    def test_delete_recipe_with_translations(self) -> None:
        from app.services import recipe_service

        recipe = self._make_recipe()
        self._add_translation(recipe, "pl")
        self._add_translation(recipe, "en")
        recipe_id = recipe.id
        self.assertEqual(self._counts(recipe_id), (2, 0))

        recipe_service.delete_recipe(self.db, recipe, self.user)

        self.assertIsNone(recipe_service.get_recipe_by_id(self.db, recipe_id))
        self.assertEqual(self._counts(recipe_id), (0, 0))

    def test_delete_recipe_with_structured_ingredients(self) -> None:
        from app.services import recipe_service

        recipe = self._make_recipe()
        self._add_structured_ingredient(recipe, "2 lyzki oliwy")
        self._add_structured_ingredient(recipe, "1 cebula")
        recipe_id = recipe.id
        self.assertEqual(self._counts(recipe_id), (0, 2))

        recipe_service.delete_recipe(self.db, recipe, self.user)

        self.assertIsNone(recipe_service.get_recipe_by_id(self.db, recipe_id))
        self.assertEqual(self._counts(recipe_id), (0, 0))

    def test_delete_recipe_with_both_child_types(self) -> None:
        from app.services import recipe_service

        recipe = self._make_recipe()
        self._add_translation(recipe, "pl")
        self._add_translation(recipe, "en")
        self._add_structured_ingredient(recipe, "2 lyzki oliwy")
        recipe_id = recipe.id
        self.assertEqual(self._counts(recipe_id), (2, 1))

        recipe_service.delete_recipe(self.db, recipe, self.user)

        self.assertIsNone(recipe_service.get_recipe_by_id(self.db, recipe_id))
        self.assertEqual(self._counts(recipe_id), (0, 0))

    def test_delete_works_for_every_recipe_after_a_backfill(self) -> None:
        """Stan, w który wprowadza backfill tłumaczeń: KAŻDY przepis ma wiersz
        w recipe_translations. Bez kaskady oznaczałoby to, że po backfillu żadnego
        z 64 przepisów produkcyjnych nie da się usunąć."""
        from app.services import recipe_service

        recipes = [self._make_recipe(f"Przepis {index}") for index in range(5)]
        for recipe in recipes:
            self._add_translation(recipe, "pl")

        for recipe in recipes:
            recipe_id = recipe.id
            recipe_service.delete_recipe(self.db, recipe, self.user)
            self.assertIsNone(recipe_service.get_recipe_by_id(self.db, recipe_id))
            self.assertEqual(self._counts(recipe_id), (0, 0))

    def test_delete_does_not_touch_other_recipes_children(self) -> None:
        """Kaskada nie może zabrać ze sobą dzieci sąsiedniego przepisu."""
        from app.services import recipe_service

        doomed = self._make_recipe("Do usuniecia")
        self._add_translation(doomed, "pl")
        self._add_structured_ingredient(doomed)

        survivor = self._make_recipe("Zostaje")
        self._add_translation(survivor, "pl")
        self._add_structured_ingredient(survivor)
        survivor_id = survivor.id

        recipe_service.delete_recipe(self.db, doomed, self.user)

        self.assertEqual(self._counts(survivor_id), (1, 1))
        self.assertIsNotNone(recipe_service.get_recipe_by_id(self.db, survivor_id))

    def test_delete_recipe_keeps_the_normalized_ingredient(self) -> None:
        """Kaskada nie może sięgnąć do słownika składników.

        `recipe_ingredients.ingredient_id` celowo NIE ma ON DELETE CASCADE -
        wskazuje na znormalizowany wpis współdzielony przez wiele przepisów.
        Usunięcie przepisu ma skasować jego pozycje składników, ale sam
        `Ingredient` musi zostać: inaczej usunięcie jednego przepisu wycinałoby
        słownik spod wszystkich pozostałych.
        """
        from app.db.models.ingredient import Ingredient
        from app.services import recipe_service

        ingredient = self._add_ingredient("czosnek")
        ingredient_id = ingredient.id

        recipe = self._make_recipe()
        self._add_translation(recipe, "pl")
        self._add_structured_ingredient(recipe, "1 zabek czosnku", ingredient_id=ingredient_id)
        recipe_id = recipe.id
        self.assertEqual(self._counts(recipe_id), (1, 1))

        recipe_service.delete_recipe(self.db, recipe, self.user)

        # Dzieci przepisu znikają...
        self.assertIsNone(recipe_service.get_recipe_by_id(self.db, recipe_id))
        self.assertEqual(self._counts(recipe_id), (0, 0))

        # ...a znormalizowany składnik zostaje nietknięty.
        survivor = self.db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
        self.assertIsNotNone(survivor, "Ingredient zniknął razem z przepisem")
        self.assertEqual(survivor.name, "czosnek")
        self.assertTrue(survivor.is_essential)
        self.assertEqual(self.db.query(Ingredient).count(), 1)

    def test_ingredient_shared_by_two_recipes_survives_deleting_one(self) -> None:
        """Wariant, w którym błąd bolałby najbardziej: ten sam składnik używany
        przez dwa przepisy. Usunięcie jednego nie może naruszyć pozycji drugiego."""
        from app.db.models.ingredient import Ingredient
        from app.services import recipe_service

        ingredient = self._add_ingredient("czosnek")
        ingredient_id = ingredient.id

        doomed = self._make_recipe("Do usuniecia")
        self._add_structured_ingredient(doomed, "1 zabek czosnku", ingredient_id=ingredient_id)

        survivor = self._make_recipe("Zostaje")
        self._add_structured_ingredient(survivor, "2 zabki czosnku", ingredient_id=ingredient_id)
        survivor_id = survivor.id

        recipe_service.delete_recipe(self.db, doomed, self.user)

        self.assertIsNotNone(self.db.query(Ingredient).filter(Ingredient.id == ingredient_id).first())
        self.assertEqual(self._counts(survivor_id), (0, 1))

    def test_no_orphan_rows_remain_anywhere_after_delete(self) -> None:
        """Twardy warunek: po usunięciu żaden wiersz potomny nie może wskazywać
        na nieistniejący przepis. Łapie wariant, w którym DELETE 'przechodzi',
        bo baza nie egzekwuje kluczy obcych, a dzieci po cichu zostają."""
        from app.db.models.recipe import Recipe
        from app.db.models.recipe_ingredient import RecipeIngredient
        from app.db.models.recipe_translation import RecipeTranslation
        from app.services import recipe_service

        recipe = self._make_recipe()
        self._add_translation(recipe, "pl")
        self._add_structured_ingredient(recipe)

        recipe_service.delete_recipe(self.db, recipe, self.user)

        live_ids = {row[0] for row in self.db.query(Recipe.id).all()}
        orphan_translations = [
            t.recipe_id for t in self.db.query(RecipeTranslation).all() if t.recipe_id not in live_ids
        ]
        orphan_ingredients = [
            i.recipe_id for i in self.db.query(RecipeIngredient).all() if i.recipe_id not in live_ids
        ]

        self.assertEqual(orphan_translations, [])
        self.assertEqual(orphan_ingredients, [])


if __name__ == "__main__":
    unittest.main()
