import uuid

from app.services.recipe_import.fetcher import fetch_image
from app.utils.file_utils import STATIC_ROOT, UPLOAD_DIR


async def download_and_store_image(url: str) -> str:
    """Pobiera obraz (ten sam SSRF guard co fetch_html) i zapisuje go pod
    własną, losową nazwą. Zwraca ścieżkę statyczną (/static/uploads/<uuid>.<ext>)
    do zapisania na Recipe.image.

    Nazwa pliku pochodzi wyłącznie z uuid4() + rozszerzenia wykrytego z
    faktycznej treści (magic bytes w fetch_image) - nigdy z URL. Podnosi
    RecipeImportError, jeśli pobranie się nie uda; wywołujący (confirm
    endpoint) decyduje, czy zapisać przepis bez zdjęcia.
    """
    image = await fetch_image(url)

    filename = f"{uuid.uuid4()}.{image.extension}"
    path = UPLOAD_DIR / filename
    # uuid4 collisions are astronomically unlikely, but never overwrite an
    # existing file regardless - pick another name if one somehow exists.
    while path.exists():
        filename = f"{uuid.uuid4()}.{image.extension}"
        path = UPLOAD_DIR / filename

    try:
        with open(path, "wb") as f:
            f.write(image.content)
    except OSError:
        path.unlink(missing_ok=True)
        raise

    return f"/static/uploads/{filename}"


def delete_stored_image(image_path: str | None) -> None:
    """Usuwa zapisany obraz - używane, gdy zapis przepisu w bazie zawiedzie
    PO tym, jak obraz już trafił na dysk."""
    if not image_path:
        return
    path = STATIC_ROOT / image_path.replace("/static/", "")
    if path.exists():
        path.unlink()
