import os
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_hGFBPgpM4z1r@ep-icy-meadow-amgt56hx-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def check():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='verified_users'")
    cols = [r[0] for r in cur.fetchall()]
    print(f"Columns: {cols}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check()
