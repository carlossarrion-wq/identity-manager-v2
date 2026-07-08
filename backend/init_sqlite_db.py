"""
Initialize SQLite database for local development
Converts PostgreSQL schema to SQLite-compatible format
"""
import sqlite3
import os
import sys
from pathlib import Path
import re

def convert_postgres_to_sqlite(sql_content):
    """Convert PostgreSQL SQL to SQLite-compatible SQL"""
    
    # Remove PostgreSQL-specific syntax
    sql_content = re.sub(r'::uuid', '', sql_content)
    sql_content = re.sub(r'::timestamp', '', sql_content)
    sql_content = re.sub(r'::text', '', sql_content)
    sql_content = re.sub(r'::integer', '', sql_content)
    sql_content = re.sub(r'::jsonb', '', sql_content)
    sql_content = re.sub(r'::json', '', sql_content)
    
    # Replace UUID functions
    sql_content = re.sub(r'gen_random_uuid\(\)', "lower(hex(randomblob(16)))", sql_content)
    sql_content = re.sub(r'uuid_generate_v4\(\)', "lower(hex(randomblob(16)))", sql_content)
    
    # Replace CURRENT_TIMESTAMP
    sql_content = sql_content.replace('CURRENT_TIMESTAMP', "datetime('now')")
    
    # Replace NOW()
    sql_content = sql_content.replace('NOW()', "datetime('now')")
    
    # Remove ON CONFLICT DO UPDATE (SQLite uses INSERT OR REPLACE)
    sql_content = re.sub(
        r'ON CONFLICT.*?DO UPDATE SET.*?;',
        ';',
        sql_content,
        flags=re.DOTALL
    )
    
    # Remove CREATE EXTENSION
    sql_content = re.sub(r'CREATE EXTENSION.*?;', '', sql_content, flags=re.IGNORECASE)
    
    # Remove COMMENT ON
    sql_content = re.sub(r'COMMENT ON.*?;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert SERIAL to INTEGER PRIMARY KEY AUTOINCREMENT
    sql_content = re.sub(r'\bSERIAL\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql_content, flags=re.IGNORECASE)
    sql_content = re.sub(r'\bBIGSERIAL\b', 'INTEGER PRIMARY KEY AUTOINCREMENT', sql_content, flags=re.IGNORECASE)
    
    # Convert TIMESTAMP to TEXT
    sql_content = re.sub(r'\bTIMESTAMP\b', 'TEXT', sql_content, flags=re.IGNORECASE)
    sql_content = re.sub(r'\bTIMESTAMPTZ\b', 'TEXT', sql_content, flags=re.IGNORECASE)
    
    # Convert UUID to TEXT
    sql_content = re.sub(r'\bUUID\b', 'TEXT', sql_content, flags=re.IGNORECASE)
    
    # Convert JSONB to TEXT
    sql_content = re.sub(r'\bJSONB\b', 'TEXT', sql_content, flags=re.IGNORECASE)
    
    # Convert BOOLEAN
    sql_content = re.sub(r'\bBOOLEAN\b', 'INTEGER', sql_content, flags=re.IGNORECASE)
    
    # Remove DROP statements for functions/procedures
    sql_content = re.sub(r'DROP FUNCTION.*?;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    sql_content = re.sub(r'DROP PROCEDURE.*?;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove CREATE FUNCTION/PROCEDURE (SQLite doesn't support them)
    sql_content = re.sub(r'CREATE OR REPLACE FUNCTION.*?\$\$;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    sql_content = re.sub(r'CREATE FUNCTION.*?\$\$;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    sql_content = re.sub(r'CREATE OR REPLACE PROCEDURE.*?\$\$;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove CREATE VIEW statements (we'll handle these separately if needed)
    sql_content = re.sub(r'CREATE OR REPLACE VIEW.*?;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove CREATE TRIGGER statements
    sql_content = re.sub(r'CREATE TRIGGER.*?;', '', sql_content, flags=re.DOTALL | re.IGNORECASE)
    
    return sql_content

def execute_sql_statements(conn, sql_content, filename):
    """Execute SQL statements one by one"""
    print(f"Processing {filename}...")
    
    # Split into statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    cursor = conn.cursor()
    success_count = 0
    skip_count = 0
    
    for i, statement in enumerate(statements, 1):
        try:
            # Skip empty statements or comments only
            if not statement or statement.startswith('--'):
                continue
                
            cursor.execute(statement)
            success_count += 1
        except sqlite3.Error as e:
            # Skip errors for already existing tables or syntax incompatibilities
            error_msg = str(e).lower()
            if 'already exists' in error_msg or 'duplicate column' in error_msg:
                skip_count += 1
            else:
                print(f"  ⚠️  Statement {i} warning: {e}")
                skip_count += 1
    
    conn.commit()
    print(f"  ✓ Executed {success_count} statements ({skip_count} skipped)")
    return success_count

def create_seed_user(conn):
    """Create a test user for login"""
    print("\nCreating test user...")
    
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("""
        SELECT COUNT(*) FROM "identity-manager-users-tbl" 
        WHERE email = 'admin@test.com'
    """)
    
    if cursor.fetchone()[0] > 0:
        print("  ℹ️  Test user already exists")
        return
    
    # Create test user
    cursor.execute("""
        INSERT INTO "identity-manager-users-tbl" 
        (id, cognito_user_id, email, username, is_active, created_at, updated_at)
        VALUES (
            'test-admin-uuid-001',
            'test-cognito-id-001',
            'admin@test.com',
            'admin',
            1,
            datetime('now'),
            datetime('now')
        )
    """)
    
    conn.commit()
    print("  ✓ Test user created: admin@test.com")

def init_sqlite_db():
    """Initialize SQLite database"""
    db_path = Path(__file__).parent / "identity_manager.db"
    db_dir = Path(__file__).parent.parent / "database"
    
    print("\n" + "="*60)
    print("🗄️  Initializing Identity Manager SQLite Database")
    print("="*60 + "\n")
    print(f"Database location: {db_path}")
    print()
    
    # Create connection
    conn = sqlite3.connect(str(db_path))
    
    try:
        # Process schema file
        schema_file = db_dir / "01_schema.sql"
        if schema_file.exists():
            with open(schema_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            sql_content = convert_postgres_to_sqlite(sql_content)
            execute_sql_statements(conn, sql_content, "01_schema.sql")
        
        # Process seed data file
        seed_file = db_dir / "03_seed_data.sql"
        if seed_file.exists():
            with open(seed_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            sql_content = convert_postgres_to_sqlite(sql_content)
            execute_sql_statements(conn, sql_content, "03_seed_data.sql")
        
        # Create test user for login
        create_seed_user(conn)
        
        # Verify tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        print(f"\n✓ Created {len(tables)} tables")
        print(f"  Tables: {', '.join([t[0] for t in tables[:5]])}{'...' if len(tables) > 5 else ''}")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ SQLite database initialized successfully!")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = init_sqlite_db()
    sys.exit(0 if success else 1)
