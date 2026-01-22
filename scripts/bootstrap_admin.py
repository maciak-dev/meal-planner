from app.core.database import SessionLocal
from app.db.models.user import User
from app.core.security import hash_password

def main():
    db = SessionLocal()

    admin = db.query(User).filter(User.username == "admin").first()
    if admin:
        print("Admin already exists")
        return

    admin = User(
        username="admin",
        hashed_password=hash_password("admin"),
        role="super_admin"
    )

    db.add(admin)
    db.commit()
    print("Admin created successfully")

if __name__ == "__main__":
    main()