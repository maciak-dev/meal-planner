# Store layout presets

Store routing is an add-on to the existing ingredient catalogue. A `Store` owns
ordered `StoreSection` rows. `IngredientStorePlacement` maps an ingredient to one
section in one store and may provide an optional position inside that section.
The same ingredient can therefore be placed differently in different stores.

The shopping list keeps insertion order as its fallback. Selecting a store layout
is a local UI preference; the layout itself is server data. Matching uses exact,
case-insensitive ingredient/canonical names (and API aliases), without guessing
from arbitrary free text. Unassigned items remain last in stable insertion order.

Store layout editing lives in Settings. The shopping list only selects and
consumes a preset. `Ingredient.preferred_store_id` remains for compatibility with
the previous catalogue release and is not the route source of truth.
