"""
Basic test - just check database connection
"""
import os
import sqlite3
from pathlib import Path

print("\n" + "="*60)
print("🧪 Basic Database Test")
print("="*60 + "\n")

db_path = Path(__file__).parent / "identity_manager.db"

if not db_path.exists():
    print(f"✗ Database not found at {db_path}")
    exit(1)

print(f"✓ Database found at {db_path}\n")

# Connect and query
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print(f"Tables ({len(tables)}):")
for table in tables:
    print(f"  - {table[0]}")

# Check users
cursor.execute('SELECT * FROM "identity-manager-users-tbl"')
users = cursor.fetchall()
print(f"\nUsers ({len(users)}):")
for user in users:
    print(f"  - {dict(user)}")

# Check applications
cursor.execute('SELECT * FROM "identity-manager-applications-tbl"')
apps = cursor.fetchall()
print(f"\nApplications ({len(apps)}):")
for app in apps:
    print(f"  - {dict(app)}")

conn.close()

print("\n" + "="*60)
print("✅ Database is ready!")
print("="*60 + "\n")
