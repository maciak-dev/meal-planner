"""Backfill recipe_translations(language='pl') z legacy kolumn Recipe.

Dry-run domyślnie: wypisuje, co BY utworzył, i nie zapisuje niczego. Zapis
dopiero z --apply. Idempotentny - przepisy, które mają już wiersz 'pl', są
pomijane, więc ponowne uruchomienie jest bezpieczne.

Użycie (z katalogu repozytorium):
    python scripts/backfill_recipe_translations.py            # dry-run
    python scripts/backfill_recipe_translations.py --apply     # zapisuje

Skrypt jest świadomie samowystarczalny - nie importuje warstwy serwisów, bo
jest narzędziem jednorazowej migracji danych, nie częścią produktu. Dzięki temu
działa na checkoutcie, który ma sam schemat, bez funkcji tłumaczeń treści.

WAŻNE - procedura:
    1. Zawsze najpierw dry-run i ręczny przegląd wyniku.
    2. Potem --apply na RC (`fastapi_db_rc`), po świeżym backupie.
    3. Na produkcji WYŁĄCZNIE po osobnej, jawnej zgodzie administratora VPS -
       nie jest to część wdrożenia schematu ani krok automatyczny.
Patrz docs/operations/alembic-migrations.md.
"""
import argparse
import sys
from pathlib import Path

# Pozwala uruchomić skrypt jako `python scripts/backfill_recipe_translations.py`
# bez ustawiania PYTHONPATH - istotne, bo to polecenie wpisuje się ręcznie na
# serwerze, z runbooka.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app.db.models  # noqa: E402,F401 - rejestruje modele na Base.metadata
from app.core.database import SessionLocal  # noqa: E402
from app.db.models.recipe import Recipe  # noqa: E402
from app.db.models.recipe_translation import RecipeTranslation  # noqa: E402

# Język, w którym istnieje treść 64 przepisów produkcyjnych. Nie próbujemy
# wykrywać innego z samego tekstu - dałoby to fałszywe pozytywy, a każdy z nich
# oznaczałby przepis oznaczony błędnym językiem bez sposobu, żeby to zauważyć.
DEFAULT_LANGUAGE = "pl"


def has_translation(db, recipe_id: int, language: str) -> bool:
    return (
        db.query(RecipeTranslation.id)
        .filter(RecipeTranslation.recipe_id == recipe_id, RecipeTranslation.language == language)
        .first()
        is not None
    )


def backfill(db, apply: bool) -> tuple[int, int]:
    recipes = db.query(Recipe).order_by(Recipe.id).all()
    created = 0
    skipped = 0

    for recipe in recipes:
        if has_translation(db, recipe.id, DEFAULT_LANGUAGE):
            skipped += 1
            continue

        label = "APPLY" if apply else "DRY-RUN"
        print(f"[{label}] recipe #{recipe.id} \"{recipe.name}\" -> recipe_translations(language='{DEFAULT_LANGUAGE}')")
        created += 1

        if apply:
            db.add(RecipeTranslation(
                recipe_id=recipe.id,
                language=DEFAULT_LANGUAGE,
                name=recipe.name,
                description=recipe.description or "",
                instructions=recipe.instructions or "",
            ))

    if apply:
        db.commit()

    return created, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Actually write rows (default: dry-run only)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        created, skipped = backfill(db, args.apply)
    finally:
        db.close()

    mode = "Applied" if args.apply else "Would create"
    print(f"\n{mode}: {created} recipe_translations row(s). Skipped (already had '{DEFAULT_LANGUAGE}' translation): {skipped}.")
    if not args.apply:
        print("Dry-run only - re-run with --apply to write.")


if __name__ == "__main__":
    main()
