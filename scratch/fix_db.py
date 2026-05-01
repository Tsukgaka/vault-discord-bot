import os
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_hGFBPgpM4z1r@ep-icy-meadow-amgt56hx-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def fix_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("Fixing database processed flags...")
    try:
        cur.execute("UPDATE verified_users SET processed = true WHERE processed = false")
        conn.commit()
        print("✅ All existing verified users marked as processed.")
    except Exception as e:
        print(f"❌ Failed: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    fix_db()
