# Recipe URL import

Recipe URL import is an explicit preview/confirm workflow. `POST
/api/v1/recipe-import/preview` fetches and parses a public HTML page but does
not write to the database. The browser displays the draft and the user may
edit the recipe fields and ingredient rows. `POST
/api/v1/recipe-import/confirm` persists only that edited payload.

The import package supports schema.org `Recipe` JSON-LD, including multiple
JSON-LD blocks, `@graph`, string/list `recipeInstructions`, `HowToStep`, and
string/list/ImageObject images. A small HTML metadata fallback is retained for
pages without Recipe JSON-LD and is returned with a warning for manual review.

The persisted data is deliberately limited to the current Recipe model:

* name, description, instructions and legacy free-text ingredients;
* `is_public` selected by the user;
* source URL, source name, source author and import timestamp;
* optional structured `RecipeIngredient` rows with no automatic Ingredient
  mapping;
* an optional downloaded JPEG, PNG or WebP image.

Servings, preparation/cooking times, categories and source-language metadata
are not presented as editable recipe fields because the current model does
not persist them. RecipeTranslation is not created by import. The UI language
switch changes labels only; imported recipe content remains source content.

## Fetch security

Only HTTP(S) URLs on ports 80 or 443 are accepted. Userinfo, non-HTTP schemes,
private/loopback/link-local/multicast/reserved/non-global IPs and malformed
ports are rejected. Every DNS result is checked, and the connection is pinned
to the validated public IP while preserving the original Host/SNI. Each
redirect is independently validated and pinned; redirects to private targets
cannot bypass the guard. The fetcher limits redirects, timeout, decompressed
HTML size and image size, uses an exact allowlist for HTML and image media
types, and disables environment-configured HTTP proxies so requests cannot
bypass the validated pinned destination. Error responses expose stable error
codes rather than resolved IPs or upstream response bodies.

Imported strings are untrusted. Backend values are returned as JSON and the
existing recipe UI renders them through DOM `textContent`/properties, never as
interpolated HTML.
