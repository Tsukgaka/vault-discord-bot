import os
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_hGFBPgpM4z1r@ep-icy-meadow-amgt56hx-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("Migrating database...")
    try:
        cur.execute("ALTER TABLE verified_users ADD COLUMN IF NOT EXISTS processed BOOLEAN DEFAULT false;")
        cur.execute("ALTER TABLE verified_users ADD COLUMN IF NOT EXISTS role_id TEXT;")
        conn.commit()
        print("✅ Columns added successfully.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
