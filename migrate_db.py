import sqlite3

def migrate():
    print("Migrating database...")
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER REFERENCES tasks(id)")
        print("Column 'parent_id' added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'parent_id' already exists.")
        else:
            print(f"Error: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
