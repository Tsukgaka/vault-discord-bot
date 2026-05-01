import os
import hashlib
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

# ❗ 即死防止（.getにする）
DATABASE_URL = os.environ.get("DATABASE_URL")


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def get_conn():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL is not set")

    conn = None
    try:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        yield conn
        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print("DB ERROR:", str(e))
        raise

    finally:
        if conn:
            conn.close()


def get_guild_settings(guild_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM guild_settings WHERE guild_id = %s",
                (guild_id,)
            )
            row = cur.fetchone()
            return dict(row) if row else None


def check_duplicates(guild_id: str, ip_hash: str, email_hash: str, discord_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "SELECT 1 FROM verified_users WHERE guild_id=%s AND ip_hash=%s LIMIT 1",
                (guild_id, ip_hash)
            )
            ip_exists = cur.fetchone() is not None

            cur.execute(
                "SELECT 1 FROM verified_users WHERE guild_id=%s AND email_hash=%s LIMIT 1",
                (guild_id, email_hash)
            )
            email_exists = cur.fetchone() is not None

            cur.execute(
                "SELECT 1 FROM verified_users WHERE guild_id=%s AND discord_id=%s LIMIT 1",
                (guild_id, discord_id)
            )
            discord_exists = cur.fetchone() is not None

    return {
        "ip": ip_exists,
        "email": email_exists,
        "discord": discord_exists
    }


def save_verified_user(data: dict) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO verified_users
                (guild_id, discord_id, discord_username, email, ip_address, ip_hash, email_hash, is_vpn)
                VALUES (%s, %s, %s, %s, %s::inet, %s, %s, %s)
                ON CONFLICT (guild_id, discord_id)
                DO UPDATE SET
                    discord_username = EXCLUDED.discord_username,
                    verified_at = NOW()
                """,
                (
                    data["guild_id"],
                    data["discord_id"],
                    data["discord_username"],
                    data["email"],
                    data["ip_address"],
                    data["ip_hash"],
                    data["email_hash"],
                    data["is_vpn"],
                ),
            )
