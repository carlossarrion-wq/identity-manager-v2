"""
Initialize local PostgreSQL database with schema and seed data
"""
import os
import sys
import psycopg2
from pathlib import Path

def get_db_connection():
    """Get database connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "identity_manager"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

def execute_sql_file(conn, filepath):
    """Execute a SQL file"""
    print(f"Executing {filepath.name}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"✓ {filepath.name} executed successfully")

def init_database():
    """Initialize database with schema and seed data"""
    db_dir = Path(__file__).parent.parent / "database"
    
    print("\n" + "="*60)
    print("🗄️  Initializing Identity Manager Database")
    print("="*60 + "\n")
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = get_db_connection()
        print("✓ Connected successfully\n")
        
        # Execute schema files
        schema_files = [
            db_dir / "01_schema.sql",
            db_dir / "02_functions_views.sql",
            db_dir / "03_seed_data.sql"
        ]
        
        for sql_file in schema_files:
            if sql_file.exists():
                execute_sql_file(conn, sql_file)
            else:
                print(f"⚠️  Warning: {sql_file.name} not found, skipping...")
        
        # Execute migrations if they exist
        migrations_dir = db_dir / "migrations"
        if migrations_dir.exists():
            migration_files = sorted(migrations_dir.glob("*.sql"))
            if migration_files:
                print(f"\nApplying {len(migration_files)} migrations...")
                for migration_file in migration_files:
                    try:
                        execute_sql_file(conn, migration_file)
                    except Exception as e:
                        print(f"⚠️  Warning: Migration {migration_file.name} failed: {e}")
                        print("Continuing with next migration...\n")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Database initialization completed successfully!")
        print("="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        print("Please ensure PostgreSQL is running and credentials are correct.")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
