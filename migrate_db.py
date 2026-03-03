import sqlite3

def migrate():
    print("Migrating database...")
    conn = sqlite3.connect("workflow.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN closed_at DATETIME")
        print("Column 'closed_at' added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'closed_at' already exists.")
        else:
            print(f"Error closed_at: {e}")
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
