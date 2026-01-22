from pathlib import Path
import uuid

ALLOWED_EXT = {"jpg","jpeg","png","webp"}
STATIC_ROOT = Path("app/static")
UPLOAD_DIR = STATIC_ROOT / "uploads"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def save_image(file):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Invalid image type")

    filename = f"{uuid.uuid4()}.{ext}"
    path = UPLOAD_DIR / filename

    with open(path, "wb") as f:
        f.write(file.file.read())

    return f"/static/uploads/{filename}", path


def delete_image(image_url: str):
    if not image_url:
        return

    path = STATIC_ROOT / image_url.replace("/static/","")
    if path.exists():
        path.unlink()
