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


class ShopFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.env = mock.patch.dict(os.environ, {
            "ENV": "dev", "APP_INSTANCE": "dev", "SECRET_KEY": "dev-secret",
            "DATABASE_URL": f"sqlite:///{Path(self.tmp.name) / 'shop.db'}",
            "MEAL_PLANNER_LOAD_ENV_FILE": "0",
        }, clear=True)
        self.env.start()
        from fastapi.testclient import TestClient
        from app.core.security import get_current_user
        from app.db.models.user import User
        import app.main as main_module

        self.main = main_module
        self.db = main_module.SessionLocal()
        self.owner = User(username="shop-owner", hashed_password="x", role="super_admin")
        self.user = User(username="shop-user", hashed_password="x", role="user")
        self.db.add_all([self.owner, self.user])
        self.db.commit()
        self.db.refresh(self.owner)
        self.db.refresh(self.user)
        self.current_user = self.owner
        self.main.app.dependency_overrides[get_current_user] = lambda: self.current_user
        self.client = TestClient(self.main.app)

    def tearDown(self) -> None:
        self.main.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine
        engine.dispose()
        self.env.stop()
        self.tmp.cleanup()
        purge_app_modules()

    def test_owner_can_create_catalog_and_assign_store(self) -> None:
        store = self.client.post("/api/v1/stores", json={"name": "  Lidl  "})
        self.assertEqual(store.status_code, 201)
        self.assertEqual(store.json()["name"], "Lidl")
        ingredient = self.client.post("/api/v1/ingredients", json={"name": "  Ryż  "})
        self.assertEqual(ingredient.status_code, 201)
        ingredient_id = ingredient.json()["id"]
        assigned = self.client.patch(
            f"/api/v1/ingredients/{ingredient_id}/store",
            json={"preferred_store_id": store.json()["id"]},
        )
        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["preferred_store"]["name"], "Lidl")

        cleared = self.client.patch(
            f"/api/v1/ingredients/{ingredient_id}/store", json={"preferred_store_id": None}
        )
        self.assertIsNone(cleared.json()["preferred_store_id"])

    def test_catalog_rejects_case_insensitive_duplicates_and_unknown_store(self) -> None:
        self.assertEqual(self.client.post("/api/v1/stores", json={"name": "Lidl"}).status_code, 201)
        self.assertEqual(self.client.post("/api/v1/stores", json={"name": " lidl "}).status_code, 409)
        ingredient = self.client.post("/api/v1/ingredients", json={"name": "Ryż"})
        self.assertEqual(self.client.post("/api/v1/ingredients", json={"name": " ryż "}).status_code, 409)
        self.assertEqual(
            self.client.patch(f"/api/v1/ingredients/{ingredient.json()['id']}/store", json={"preferred_store_id": 999}).status_code,
            422,
        )

    def test_non_admin_cannot_mutate_catalog_but_can_read(self) -> None:
        self.current_user = self.user
        self.assertEqual(self.client.get("/api/v1/stores").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/stores", json={"name": "Biedronka"}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/ingredients", json={"name": "Mąka"}).status_code, 403)

    def test_existing_recipe_ingredient_text_is_not_rewritten(self) -> None:
        from app.db.models.ingredient import Ingredient
        from app.db.models.recipe import Recipe
        from app.db.models.recipe_ingredient import RecipeIngredient

        ingredient = Ingredient(name="mleko")
        recipe = Recipe(name="Zupa", ingredients="500 ml mleka", instructions="", user_id=self.owner.id)
        self.db.add_all([ingredient, recipe])
        self.db.flush()
        row = RecipeIngredient(
            recipe_id=recipe.id,
            ingredient_id=ingredient.id,
            original_text="500 ml mleka",
            parsed_name="mleko",
            quantity=500,
            unit="ml",
            sort_order=0,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        self.assertEqual(row.original_text, "500 ml mleka")
        self.assertEqual(recipe.ingredients, "500 ml mleka")


if __name__ == "__main__":
    unittest.main()
