# Recipe ingredients and store preferences

Status: Active

The legacy `Recipe.ingredients` text remains the lossless display and edit
source. Structured `RecipeIngredient` rows are an explicit bridge: they retain
`original_text`, parsed quantity/unit/note and an optional `ingredient_id`.
Existing recipes are not automatically re-parsed or merged.

`Ingredient` is the small normalized catalogue entry. `IngredientAlias` is
available for an explicit, reviewed mapping; the application never merges
similar strings merely because case or whitespace differs. A `Store` is a
user-managed preference target. `Ingredient.preferred_store_id` is nullable,
so an ingredient can remain unassigned. This is not yet a persistent shopping
list or a route/category ordering system.

The owner can manage the catalogue through:

- `GET /api/v1/ingredients`
- `POST /api/v1/ingredients`
- `GET /api/v1/stores`
- `POST /api/v1/stores`
- `PATCH /api/v1/ingredients/{id}/store`

Read access requires a session; catalogue mutations require an admin role.
The existing `/ingredients/map` endpoint remains unchanged for recipe-card
checkbox defaults. Original recipe text and import confirmation are preserved.

The migration is additive and reversible. It creates `stores` and a nullable
foreign key on `ingredients`; it does not delete or rewrite existing recipe,
ingredient or structured ingredient rows.
