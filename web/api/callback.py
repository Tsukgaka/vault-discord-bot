"""
GET /api/callback?code=CODE&state=STATE
→ Full OAuth2 + security verification flow
"""
import os
import json
import base64
import hmac
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests as req

from _db import hash_value, get_guild_settings, check_duplicates, save_verified_user
from _vpn import check_ip, get_client_ip
from _discord import send_log, add_member_to_guild, add_role, build_log_embed

# 環境変数の取得（存在しない場合はエラーではなくNoneを返すようにし、後でチェックする）
WEB_URL = os.environ.get("WEB_URL", "").rstrip("/")
CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
VERIFIED_ROLE_ID = os.environ.get("VERIFIED_ROLE_ID", "")

# メールドメインブロックリスト（これらのドメインからの認証を拒否）
BLOCKED_EMAIL_DOMAINS = {
    "usagica.com",
}


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
            self._handle_request()
        except Exception as e:
            print(f"CRITICAL ERROR in do_GET: {e}")
            import traceback
            traceback.print_exc()
            self._error("internal_error")

    def _handle_request(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        code = (params.get("code") or [""])[0]
        state = (params.get("state") or [""])[0]

        # ── 1. CSRF state check ──────────────────────────────────────────
        cookie_header = self.headers.get("Cookie", "")
        cookies = _parse_cookies(cookie_header)
        raw_cookie = cookies.get("oauth_state", "")

        if not raw_cookie or not code or not state:
            return self._error("invalid_request")

        try:
            payload = json.loads(base64.urlsafe_b64decode(raw_cookie.encode()).decode())
            expected_state = payload["state"]
            guild_id = payload["guild_id"]
            user_id = payload["user_id"]
        except Exception:
            return self._error("invalid_state")

        if not hmac.compare_digest(state, expected_state):
            return self._error("state_mismatch")

        # ── 2. Token exchange ────────────────────────────────────────────
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
            return self._error("token_exchange_failed")

        access_token = token_resp.json().get("access_token")

        # ── 3. Fetch Discord user ────────────────────────────────────────
        user_resp = req.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if not user_resp.ok:
            return self._error("user_fetch_failed")

        discord_user = user_resp.json()
        discord_id = discord_user.get("id")
        username = discord_user.get("username")
        email = discord_user.get("email")
        email_verified = discord_user.get("verified", False)

        if not email or not email_verified:
            return self._error("email_not_verified")

        # ── 3b. Blocked email domain check ──────────────────────────────
        email_domain = email.lower().split("@")[-1] if "@" in email else ""
        if email_domain in BLOCKED_EMAIL_DOMAINS:
            return self._error("email_domain_blocked")

        # ── 4. User identity check ───────────────────────────────────────
        if discord_id != user_id:
            return self._error("user_mismatch")

        # ── 5. Guild settings ────────────────────────────────────────────
        settings = get_guild_settings(guild_id)
        if not settings:
            print(f"Error: No settings found for guild {guild_id}")
            return self._error("guild_not_configured")

        lang = settings.get("language", "ja")

        # ── 6. VPN check ─────────────────────────────────────────────────
        # Vercel passes real IP via x-real-ip header
        client_ip = (
            self.headers.get("x-real-ip") 
            or self.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or "127.0.0.1"
        )

        ip_info = check_ip(client_ip)

        if settings.get("vpn_protection") and ip_info["is_vpn"]:
            return self._error("vpn_detected")

        # ── 7. Duplicate check ────────────────────────────────────────────
        ip_hash = hash_value(client_ip)
        email_hash = hash_value(email.lower())

        if settings.get("sub_account_protection"):
            dupes = check_duplicates(guild_id, ip_hash, email_hash, discord_id)
            if dupes["email"]:
                return self._error("email_already_used")
            if dupes["ip"]:
                return self._error("ip_already_used")

        # ── 8. Save user ──────────────────────────────────────────────────
        save_verified_user({
            "guild_id": guild_id,
            "discord_id": discord_id,
            "discord_username": username,
            "email": email,
            "ip_address": client_ip,
            "ip_hash": ip_hash,
            "email_hash": email_hash,
            "is_vpn": ip_info["is_vpn"],
        })

        # ── 9. Join guild + add role ──────────────────────────────────────
        add_member_to_guild(guild_id, discord_id, access_token)
        if VERIFIED_ROLE_ID:
            add_role(guild_id, discord_id, VERIFIED_ROLE_ID)

        # ── 10. Send log ──────────────────────────────────────────────────
        if settings.get("log_channel_id"):
            embed = build_log_embed({
                "discord_id": discord_id,
                "discord_username": username,
                "email": email,
                "ip_address": client_ip,
                "is_vpn": ip_info["is_vpn"],
            }, lang)
            send_log(settings["log_channel_id"], embed)

        # ── 11. Redirect to success ───────────────────────────────────────
        self.send_response(302)
        self.send_header("Location", f"{WEB_URL}/verify?status=success&guild={guild_id}")
        self.send_header("Set-Cookie", "oauth_state=; Max-Age=0; Path=/")
        self.end_headers()

    def _error(self, reason: str):
        self.send_response(302)
        self.send_header("Location", f"{WEB_URL}/verify?status=error&reason={reason}")
        self.end_headers()

    def log_message(self, *args):
        pass
