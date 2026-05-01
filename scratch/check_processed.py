import os
import psycopg2

DATABASE_URL = "postgresql://neondb_owner:npg_hGFBPgpM4z1r@ep-icy-meadow-amgt56hx-pooler.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require"

def check():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT discord_id, processed FROM verified_users")
    rows = cur.fetchall()
    for r in rows:
        print(f"User: {r[0]}, Processed: {r[1]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    check()
