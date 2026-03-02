import sqlite3
import os

DB_PATH = "workflow.db"

def migrate():
    print(f"Migrating database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database file not found. Skipping migration (it will be created by the app).")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add Asset table (if not exists)
    # Note: create_all handles this if the app starts, but let's be safe or just focus on the ALTER TABLE.
    # Actually, let's just do the ALTER TABLE for tasks.
    
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN asset_id INTEGER REFERENCES assets(id)")
        print("Column 'asset_id' added to 'tasks' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'asset_id' already exists in 'tasks' table.")
        else:
            print(f"Error adding column: {e}")
            
    conn.commit()
    conn.close()
    print("Migration finished.")

if __name__ == "__main__":
    migrate()
