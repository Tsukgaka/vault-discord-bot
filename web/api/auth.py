"""
GET /api/auth?guild=GUILD_ID&user=USER_ID
→ Redirects to Discord OAuth2 with CSRF state cookie
IDK.lua
"""
import os
import json
import secrets
import base64
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

WEB_URL = os.environ.get("WEB_URL", "").rstrip("/")
CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        guild_id = (params.get("guild") or [""])[0]
        user_id = (params.get("user") or [""])[0]

        if not guild_id or not user_id:
            self._respond(400, "Missing guild or user")
            return

        # Generate CSRF state
        state = secrets.token_hex(16)
        cookie_payload = base64.urlsafe_b64encode(
            json.dumps({"state": state, "guild_id": guild_id, "user_id": user_id}).encode()
        ).decode()

        oauth_params = urlencode({
            "client_id": CLIENT_ID,
            "redirect_uri": f"{WEB_URL}/api/callback",
            "response_type": "code",
            "scope": "identify email guilds.join",
            "state": state,
        })

        redirect_url = f"https://discord.com/oauth2/authorize?{oauth_params}"

        self.send_response(302)
        self.send_header("Location", redirect_url)
        self.send_header(
            "Set-Cookie",
            f"oauth_state={cookie_payload}; HttpOnly; Secure; SameSite=Lax; Max-Age=600; Path=/"
        )
        self.end_headers()

    def _respond(self, code: int, body: str):
        self.send_response(code)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass
