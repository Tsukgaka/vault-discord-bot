import os
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_hGFBPgpM4z1r@ep-icy-meadow-amgt56hx-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("Migrating database...")
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token VARCHAR(64) PRIMARY KEY,
                guild_id VARCHAR(20) NOT NULL,
                user_id VARCHAR(20) NOT NULL,
                role_id VARCHAR(20),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            );
        """)
        conn.commit()
        print("✅ auth_sessions table created successfully.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
