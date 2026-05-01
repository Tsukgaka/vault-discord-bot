import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_hGFBPgpM4z1r@ep-icy-meadow-amgt56hx-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def migrate():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE verified_users ADD COLUMN IF NOT EXISTS access_token TEXT;")
        cur.execute("ALTER TABLE verified_users ADD COLUMN IF NOT EXISTS refresh_token TEXT;")
        cur.execute("ALTER TABLE verified_users ADD COLUMN IF NOT EXISTS expires_in INT;")
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    migrate()
