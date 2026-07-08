"""
Create a minimal SQLite database for login testing
"""
import sqlite3
import os
from pathlib import Path
import uuid
from datetime import datetime, timedelta

def init_minimal_db():
    """Create minimal tables and seed data for login testing"""
    db_path = Path(__file__).parent / "identity_manager.db"
    
    print("\n" + "="*60)
    print("🗄️  Creating Minimal SQLite Database for Testing")
    print("="*60 + "\n")
    print(f"Database: {db_path}\n")
    
    # Remove existing database
    if db_path.exists():
        print("Removing existing database...")
        db_path.unlink()
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Create essential tables for login
        print("Creating tables...")
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-users-tbl" (
                id TEXT PRIMARY KEY,
                cognito_user_id TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                username TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-tokens-tbl" (
                id TEXT PRIMARY KEY,
                jti TEXT NOT NULL UNIQUE,
                cognito_user_id TEXT NOT NULL,
                cognito_email TEXT NOT NULL,
                application_profile_id TEXT,
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_used_at TEXT,
                is_revoked INTEGER NOT NULL DEFAULT 0,
                revoked_at TEXT,
                revocation_reason TEXT,
                regenerated_at TEXT,
                regenerated_from_jti TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-applications-tbl" (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-models-tbl" (
                id TEXT PRIMARY KEY,
                model_id TEXT NOT NULL UNIQUE,
                model_name TEXT NOT NULL,
                model_arn TEXT,
                provider TEXT NOT NULL,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-profiles-tbl" (
                id TEXT PRIMARY KEY,
                profile_name TEXT NOT NULL,
                cognito_group_name TEXT NOT NULL,
                application_id TEXT,
                model_id TEXT NOT NULL,
                model_arn TEXT NOT NULL,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (cognito_group_name, application_id, model_id)
            )
        """)
        
        # Config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-config-tbl" (
                id TEXT PRIMARY KEY,
                config_key TEXT NOT NULL UNIQUE,
                config_value TEXT,
                description TEXT,
                is_sensitive INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Permission types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-permission-types-tbl" (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                level INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Modules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-modules-tbl" (
                id TEXT PRIMARY KEY,
                application_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                display_order INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (application_id, name)
            )
        """)
        
        # Module permissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "identity-manager-module-permissions-tbl" (
                id TEXT PRIMARY KEY,
                module_id TEXT NOT NULL,
                cognito_group_name TEXT NOT NULL,
                permission_type_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (module_id, cognito_group_name)
            )
        """)
        
        conn.commit()
        print("✓ Tables created\n")
        
        # Insert seed data
        print("Inserting seed data...")
        
        now = datetime.now().isoformat()
        
        # Insert test user
        user_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO "identity-manager-users-tbl"
            (id, cognito_user_id, email, username, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (user_id, 'test-cognito-admin', 'admin@test.com', 'admin', now, now))
        
        # Insert test application
        app_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO "identity-manager-applications-tbl"
            (id, name, description, is_active, display_order, created_at, updated_at)
            VALUES (?, ?, ?, 1, 1, ?, ?)
        """, (app_id, 'identity-mgmt', 'Identity Manager', now, now))
        
        # Insert test model
        model_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO "identity-manager-models-tbl"
            (id, model_id, model_name, model_arn, provider, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (model_id, 'eu.anthropic.claude-sonnet-4-5-v2:0', 'Claude Sonnet 4.5', 
              'arn:aws:bedrock:eu-west-1::foundation-model/eu.anthropic.claude-sonnet-4-5-v2:0',
              'Anthropic', 'Claude Sonnet 4.5 model', now, now))
        
        # Insert test profile
        profile_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO "identity-manager-profiles-tbl"
            (id, profile_name, cognito_group_name, application_id, model_id, model_arn, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """, (profile_id, 'test-profile', 'admin-group', app_id, model_id,
              'arn:aws:bedrock:eu-west-1::application-inference-profile/test', 
              'Test profile', now, now))
        
        # Insert config
        cursor.execute("""
            INSERT INTO "identity-manager-config-tbl"
            (id, config_key, config_value, description, is_sensitive, created_at, updated_at)
            VALUES 
            (?, 'jwt_secret_key', 'local-dev-secret', 'JWT secret key', 1, ?, ?),
            (?, 'token_expiry_hours', '2160', 'Token expiry hours', 0, ?, ?)
        """, (str(uuid.uuid4()), now, now, str(uuid.uuid4()), now, now))
        
        conn.commit()
        
        # Verify
        cursor.execute('SELECT COUNT(*) FROM "identity-manager-users-tbl"')
        user_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchall()
        
        print(f"✓ Seed data inserted")
        print(f"  - {user_count} test user(s)")
        print(f"  - {len(tables)} tables created\n")
        
        print("="*60)
        print("✅ Database initialized successfully!")
        print("="*60)
        print("\nTest Credentials:")
        print("  Email: admin@test.com")
        print("  (Auth will be mocked for local development)\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    success = init_minimal_db()
    sys.exit(0 if success else 1)
