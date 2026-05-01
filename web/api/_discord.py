import os
import requests

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
BASE = "https://discord.com/api/v10"


def send_log(channel_id: str, embed: dict) -> None:
    requests.post(
        f"{BASE}/channels/{channel_id}/messages",
        headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"},
        json={"embeds": [embed]},
        timeout=5,
    )


def add_member_to_guild(guild_id: str, user_id: str, access_token: str) -> None:
    requests.put(
        f"{BASE}/guilds/{guild_id}/members/{user_id}",
        headers={"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"},
        json={"access_token": access_token},
        timeout=5,
    )


def add_role(guild_id: str, user_id: str, role_id: str) -> None:
    requests.put(
        f"{BASE}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
        headers={"Authorization": f"Bot {BOT_TOKEN}"},
        timeout=5,
    )


def build_log_embed(data: dict, lang: str) -> dict:
    is_ja = lang == "ja"

    def mask_email(email):
        local, _, domain = email.partition("@")
        return f"{local[:2]}***@{domain}"

    def mask_ip(ip):
        parts = ip.split(".")
        return f"{parts[0]}.{parts[1]}.***.***" if len(parts) == 4 else ip[:8] + "***"

    vpn_val = ("あり ⚠️" if is_ja else "Yes ⚠️") if data.get("is_vpn") else ("なし ✅" if is_ja else "No ✅")

    return {
        "color": 0x57F287,
        "title": "✅ 新規認証" if is_ja else "✅ New Verification",
        "fields": [
            {"name": "ユーザー" if is_ja else "User",
             "value": f"<@{data['discord_id']}> ({data['discord_username']})", "inline": False},
            {"name": "メールアドレス" if is_ja else "Email",
             "value": mask_email(data["email"]), "inline": True},
            {"name": "IPアドレス" if is_ja else "IP Address",
             "value": mask_ip(data["ip_address"]), "inline": True},
            {"name": "VPN", "value": vpn_val, "inline": True},
        ],
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
