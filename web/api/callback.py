"""
GET /api/callback?code=CODE&state=STATE
→ Stable Discord OAuth2 callback (Vercel-safe)
"""

import os
import json
import base64
import hmac
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests as req

from _db import hash_value, get_guild_settings, check_duplicates, save_verified_user
from _vpn import check_ip
from _discord import send_log, add_member_to_guild, add_role, build_log_embed


WEB_URL = os.environ.get("WEB_URL", "").rstrip("/")
CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
VERIFIED_ROLE_ID = os.environ.get("VERIFIED_ROLE_ID", "")

BLOCKED_EMAIL_DOMAINS = {"usagica.com"}


def _parse_cookies(cookie_header: str) -> dict:
    cookies = {}
    if not cookie_header:
        return cookies
    for part in cookie_header.split(";"):
        if "=" in part:
            k, _, v = part.strip().partition("=")
            cookies[k.strip()] = v.strip()
    return cookies


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            code = (params.get("code") or [""])[0]
            state = (params.get("state") or [""])[0]

            if not code or not state:
                return self._error("invalid_request")

            # ── Cookie check ─────────────────────────────
            cookies = _parse_cookies(self.headers.get("Cookie", ""))
            raw_cookie = cookies.get("oauth_state")

            if not raw_cookie:
                return self._error("missing_cookie")

            # ── Safe decode state ────────────────────────
            try:
                padded = raw_cookie + "==="
                payload = json.loads(
                    base64.urlsafe_b64decode(padded.encode()).decode()
                )
                expected_state = payload.get("state")
                guild_id = payload.get("guild_id")
                user_id = payload.get("user_id")

                if not expected_state or not guild_id or not user_id:
                    return self._error("invalid_state")

            except Exception:
                return self._error("invalid_state")

            if not hmac.compare_digest(state, expected_state):
                return self._error("state_mismatch")

            # ── Token exchange ───────────────────────────
            token_resp = req.post(
                "https://discord.com/api/oauth2/token",
                data={
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": f"{WEB_URL}/api/callback",
                },
                timeout=10,
            )

            if not token_resp.ok:
                print("TOKEN ERROR:", token_resp.text)
                return self._error("token_exchange_failed")

            access_token = token_resp.json().get("access_token")

            # ── Fetch user ───────────────────────────────
            user_resp = req.get(
                "https://discord.com/api/users/@me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )

            if not user_resp.ok:
                print("USER ERROR:", user_resp.text)
                return self._error("user_fetch_failed")

            user = user_resp.json()

            discord_id = user.get("id")
            username = user.get("username")
            email = user.get("email")
            verified = user.get("verified", False)

            if not discord_id:
                return self._error("invalid_user")

            if not email or not verified:
                return self._error("email_not_verified")

            # ── email block ─────────────────────────────
            domain = email.split("@")[-1].lower()
            if domain in BLOCKED_EMAIL_DOMAINS:
                return self._error("email_blocked")

            # ── user match ──────────────────────────────
            if discord_id != user_id:
                return self._error("user_mismatch")

            # ── guild settings ──────────────────────────
            settings = get_guild_settings(guild_id)
            if not settings:
                return self._error("guild_not_configured")

            # ── IP detection ────────────────────────────
            client_ip = (
                self.headers.get("x-real-ip")
                or self.headers.get("x-forwarded-for", "127.0.0.1").split(",")[0].strip()
            )

            ip_info = check_ip(client_ip)

            if settings.get("vpn_protection") and ip_info.get("is_vpn"):
                return self._error("vpn_detected")

            # ── duplicate check ──────────────────────────
            ip_hash = hash_value(client_ip)
            email_hash = hash_value(email.lower())

            if settings.get("sub_account_protection"):
                dupes = check_duplicates(guild_id, ip_hash, email_hash, discord_id)
                if dupes.get("email"):
                    return self._error("email_already_used")
                if dupes.get("ip"):
                    return self._error("ip_already_used")

            # ── save user ───────────────────────────────
            save_verified_user({
                "guild_id": guild_id,
                "discord_id": discord_id,
                "discord_username": username,
                "email": email,
                "ip_address": client_ip,
                "ip_hash": ip_hash,
                "email_hash": email_hash,
                "is_vpn": ip_info.get("is_vpn", False),
            })

            # ── join guild ──────────────────────────────
            add_member_to_guild(guild_id, discord_id, access_token)

            if VERIFIED_ROLE_ID:
                add_role(guild_id, discord_id, VERIFIED_ROLE_ID)

            # ── log ──────────────────────────────────────
            if settings.get("log_channel_id"):
                embed = build_log_embed({
                    "discord_id": discord_id,
                    "discord_username": username,
                    "email": email,
                    "ip_address": client_ip,
                    "is_vpn": ip_info.get("is_vpn", False),
                }, settings.get("language", "ja"))

                send_log(settings["log_channel_id"], embed)

            # ── success redirect ─────────────────────────
            self.send_response(302)
            self.send_header(
                "Location",
                f"{WEB_URL}/verify?status=success&guild={guild_id}",
            )
            self.send_header("Set-Cookie", "oauth_state=; Max-Age=0; Path=/")
            self.end_headers()

        except Exception as e:
            print("FATAL ERROR:", str(e))
            traceback.print_exc()
            return self._error("internal_error")

    def _error(self, reason: str):
        try:
            self.send_response(302)
            self.send_header(
                "Location",
                f"{WEB_URL}/verify?status=error&reason={reason}",
            )
            self.end_headers()
        except Exception:
            pass

    def log_message(self, *args):
        pass
