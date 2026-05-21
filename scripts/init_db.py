from app.core.database import Base, engine

# Import models so SQLAlchemy registers tables
from app.db.models.user import User
from app.db.models.recipe import Recipe
from app.db.models.login_log import LoginLog

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Database initialization completed.")
