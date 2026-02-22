import sqlite3

# Connect to workflow.db
conn = sqlite3.connect('workflow.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables in workflow.db:', [t[0] for t in tables])

# Get tasks table schema
print('\n=== TASKS table schema ===')
cursor.execute('PRAGMA table_info(tasks)')
for col in cursor.fetchall():
    print(f"  {col}")

# Get workflow_steps table schema
print('\n=== WORKFLOW_STEPS table schema ===')
cursor.execute('PRAGMA table_info(workflow_steps)')
for col in cursor.fetchall():
    print(f"  {col}")

conn.close()
print('\n✓ Database schema verified successfully!')
