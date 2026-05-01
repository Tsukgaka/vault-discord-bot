import discord
from i18n import t


def settings_embed(settings: dict) -> discord.Embed:
    lang = settings.get("language", "ja")
    vpn = t(lang, "set", "on") if settings.get("vpn_protection") else t(lang, "set", "off")
    sub = t(lang, "set", "on") if settings.get("sub_account_protection") else t(lang, "set", "off")
    log_ch = f"<#{settings['log_channel_id']}>" if settings.get("log_channel_id") else "未設定 / Not set"

    embed = discord.Embed(
        title=t(lang, "set", "title"),
        description=t(lang, "set", "description"),
        color=0x5865F2,
    )
    embed.add_field(name="📋 Log", value=log_ch, inline=True)
    embed.add_field(name="🌐 Language", value="日本語" if lang == "ja" else "English", inline=True)
    embed.add_field(name="🛡️ VPN", value=vpn, inline=True)
    embed.add_field(name="🔒 Sub垢", value=sub, inline=True)
    return embed


def settings_view(lang: str) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(SettingsButton("settings_log", t(lang, "set", "log_button"), discord.ButtonStyle.secondary))
    view.add_item(SettingsButton("settings_lang", t(lang, "set", "lang_button"), discord.ButtonStyle.secondary))
    view.add_item(SettingsButton("settings_vpn", t(lang, "set", "vpn_button"), discord.ButtonStyle.secondary))
    view.add_item(SettingsButton("settings_sub", t(lang, "set", "sub_button"), discord.ButtonStyle.secondary))
    return view


class SettingsButton(discord.ui.Button):
    def __init__(self, custom_id: str, label: str, style: discord.ButtonStyle):
        super().__init__(custom_id=custom_id, label=label, style=style)


def check_embed(user: dict, lang: str) -> discord.Embed:
    import datetime
    embed = discord.Embed(title=t(lang, "check", "title"), color=0x5865F2)
    embed.add_field(name=t(lang, "log", "user"), value=f"<@{user['discord_id']}> ({user['discord_username']})", inline=False)
    embed.add_field(name="Discord ID", value=user["discord_id"], inline=True)
    embed.add_field(name=t(lang, "log", "email"), value=user["email"], inline=False)
    embed.add_field(name=t(lang, "log", "ip"), value=user["ip_address"], inline=True)
    vpn_val = t(lang, "log", "yes") if user.get("is_vpn") else t(lang, "log", "no")
    embed.add_field(name=t(lang, "log", "vpn"), value=vpn_val, inline=True)
    if user.get("verified_at"):
        ts = int(user["verified_at"].timestamp())
        embed.add_field(name=t(lang, "log", "time"), value=f"<t:{ts}:F>", inline=False)
    return embed


def log_embed(data: dict, lang: str) -> discord.Embed:
    embed = discord.Embed(title=t(lang, "log", "title"), color=0x57F287)
    embed.add_field(name=t(lang, "log", "user"), value=f"<@{data['discord_id']}> ({data['discord_username']})", inline=False)
    embed.add_field(name=t(lang, "log", "email"), value=_mask_email(data["email"]), inline=True)
    embed.add_field(name=t(lang, "log", "ip"), value=_mask_ip(data["ip_address"]), inline=True)
    vpn_val = t(lang, "log", "yes") if data.get("is_vpn") else t(lang, "log", "no")
    embed.add_field(name=t(lang, "log", "vpn"), value=vpn_val, inline=True)
    embed.timestamp = discord.utils.utcnow()
    return embed


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    return f"{local[:2]}***@{domain}"


def _mask_ip(ip: str) -> str:
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***.***"
    return ip[:8] + "***"
