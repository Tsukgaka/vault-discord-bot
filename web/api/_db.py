import os
import hashlib
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

# 環境変数はインポート時ではなく、必要な時に取得するようにするか、存在チェックを行う
DATABASE_URL = os.environ.get("DATABASE_URL", "")


@contextmanager
def get_conn():
    if not DATABASE_URL:
        print("CRITICAL: DATABASE_URL is not set!")
        raise ValueError("DATABASE_URL is not set")
    
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            print(f"Database transaction error: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def get_guild_settings(guild_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM guild_settings WHERE guild_id = %s", (guild_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def check_duplicates(guild_id: str, ip_hash: str, email_hash: str, discord_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM verified_users WHERE guild_id = %s AND ip_hash = %s LIMIT 1",
                (guild_id, ip_hash),
            )
            ip_exists = cur.fetchone() is not None

            cur.execute(
                "SELECT 1 FROM verified_users WHERE guild_id = %s AND email_hash = %s LIMIT 1",
                (guild_id, email_hash),
            )
            email_exists = cur.fetchone() is not None

            cur.execute(
                "SELECT 1 FROM verified_users WHERE guild_id = %s AND discord_id = %s LIMIT 1",
                (guild_id, discord_id),
            )
            discord_exists = cur.fetchone() is not None

    return {"ip": ip_exists, "email": email_exists, "discord": discord_exists}


def save_verified_user(data: dict) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO verified_users
                  (guild_id, discord_id, discord_username, email, ip_address, ip_hash, email_hash, is_vpn, role_id, processed, access_token, refresh_token, expires_in)
                VALUES (%s, %s, %s, %s, %s::inet, %s, %s, %s, %s, false, %s, %s, %s)
                ON CONFLICT (guild_id, discord_id) DO UPDATE
                  SET discord_username = EXCLUDED.discord_username,
                      role_id = EXCLUDED.role_id,
                      access_token = EXCLUDED.access_token,
                      refresh_token = EXCLUDED.refresh_token,
                      expires_in = EXCLUDED.expires_in,
                      processed = false,
                      verified_at = NOW()
                """,
                (
                    data["guild_id"], data["discord_id"], data["discord_username"],
                    data["email"], data["ip_address"], data["ip_hash"],
                    data["email_hash"], data["is_vpn"], data.get("role_id"),
                    data.get("access_token"), data.get("refresh_token"), data.get("expires_in")
                ),
            )

def get_auth_session(token: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM auth_sessions WHERE token = %s AND expires_at > NOW()",
                (token,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

def delete_auth_session(token: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM auth_sessions WHERE token = %s", (token,))
