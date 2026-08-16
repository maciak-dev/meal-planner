# Recipe list contract

`GET /api/v1/recipes/` keeps returning a JSON array for compatibility. It now
accepts `page` (1-based), `page_size` (1–100, default 24) and an optional
`search` query. Search is applied in SQL before pagination and the ordering is
stable: `created_at DESC, id DESC`.

The response advertises pagination through:

- `X-Recipes-Page`
- `X-Recipes-Page-Size`
- `X-Recipes-Has-Next`

The recipes UI loads the first page, observes a sentinel with
`IntersectionObserver`, and appends only records not already in its current
query cache. Changing search aborts the previous request and starts at page 1.
The existing recipe cards, controls and theme remain the rendering surface.
