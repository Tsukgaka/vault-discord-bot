import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

DATABASE_URL = os.environ["DATABASE_URL"]


@contextmanager
def get_conn():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Guild Settings ─────────────────────────────────────────────────────────

def get_guild_settings(guild_id: str) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM guild_settings WHERE guild_id = %s", (guild_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
            # Insert defaults
            cur.execute(
                """
                INSERT INTO guild_settings (guild_id, language, vpn_protection, sub_account_protection)
                VALUES (%s, 'ja', true, true)
                RETURNING *
                """,
                (guild_id,),
            )
            return dict(cur.fetchone() or {})


def _default_settings(guild_id: str) -> dict:
    return {
        "guild_id": guild_id,
        "log_channel_id": None,
        "language": "ja",
        "vpn_protection": True,
        "sub_account_protection": True,
    }


def update_guild_settings(guild_id: str, **kwargs) -> dict:
    allowed = {"log_channel_id", "language", "vpn_protection", "sub_account_protection"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return get_guild_settings(guild_id)

    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [guild_id]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE guild_settings SET {set_clause}, updated_at = NOW() WHERE guild_id = %s RETURNING *",
                values,
            )
            row = cur.fetchone()
            return dict(row) if row else get_guild_settings(guild_id)


# ── Verified Users ─────────────────────────────────────────────────────────

def get_verified_user_by_query(guild_id: str, query: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # By number (N番目の人)
            if query.isdigit():
                cur.execute(
                    """
                    SELECT * FROM verified_users
                    WHERE guild_id = %s
                    ORDER BY verified_at ASC
                    LIMIT 1 OFFSET %s
                    """,
                    (guild_id, int(query) - 1),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

            # By Discord ID
            if len(query) >= 17 and query.isdigit():
                cur.execute(
                    "SELECT * FROM verified_users WHERE guild_id = %s AND discord_id = %s",
                    (guild_id, query),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)

            # By username (case-insensitive)
            cur.execute(
                "SELECT * FROM verified_users WHERE guild_id = %s AND LOWER(discord_username) = LOWER(%s)",
                (guild_id, query),
            )
            row = cur.fetchone()
            return dict(row) if row else None
# ── Verification Tracking for Bot ───────────────────────────────────────────

def get_unprocessed_verifications() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM verified_users WHERE processed = false")
            return [dict(row) for row in cur.fetchall()]


def mark_verification_processed(guild_id: str, discord_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE verified_users SET processed = true WHERE guild_id = %s AND discord_id = %s", (guild_id, discord_id))
