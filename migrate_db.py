import sqlite3
import os

def migrate():
    db_path = "workflow.db"
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    print(f"Migrating database {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Add location_id to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN location_id INTEGER REFERENCES locations(id)")
        print("Column 'location_id' added to 'users' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'location_id' already exists in 'users' table.")
        else:
            print(f"Error adding location_id: {e}")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
