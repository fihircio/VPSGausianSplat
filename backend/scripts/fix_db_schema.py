from sqlalchemy import text
from backend.utils.db import engine

def migrate():
    with engine.connect() as conn:
        print("Adding feature_mode column to feature_sets table...")
        try:
            conn.execute(text("ALTER TABLE feature_sets ADD COLUMN feature_mode VARCHAR(32) DEFAULT 'ORB'"))
            conn.commit()
            print("Successfully added feature_mode column.")
        except Exception as e:
            print(f"Skipped or failed: {e}")

if __name__ == "__main__":
    migrate()
