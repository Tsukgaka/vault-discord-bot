import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

from db import get_guild_settings, update_guild_settings, get_verified_user_by_query
from embeds import settings_embed, settings_view, check_embed, log_embed
from i18n import t

# ── Bot setup ─────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")


# ── /set command ───────────────────────────────────────────────────────────

@tree.command(name="set", description="認証Botの設定パネルを開く / Open settings panel")
@app_commands.default_permissions(administrator=True)
async def cmd_set(interaction: discord.Interaction):
    settings = get_guild_settings(str(interaction.guild_id))
    lang = settings.get("language", "ja")
    embed = settings_embed(settings)
    view = SettingsView(settings)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ── /check command ─────────────────────────────────────────────────────────

@tree.command(name="check", description="認証済みユーザーを確認 / Check verified user")
@app_commands.default_permissions(administrator=True)
async def cmd_check(interaction: discord.Interaction):
    settings = get_guild_settings(str(interaction.guild_id))
    lang = settings.get("language", "ja")
    await interaction.response.send_modal(CheckModal(lang))


# ── /panel command ──────────────────────────────────────────────────────────

@tree.command(name="panel", description="認証パネルを送信 / Send authentication panel")
@app_commands.describe(role="認証成功時に付与するロール / Role to give upon success")
@app_commands.default_permissions(administrator=True)
async def cmd_panel(interaction: discord.Interaction, role: discord.Role):
    # 自分にだけ見えるメッセージ
    await interaction.response.send_message("Generating...", ephemeral=True)

    settings = get_guild_settings(str(interaction.guild_id))
    lang = settings.get("language", "ja")

    # 認証リンク (OAuth2 URL)
    # クライアントID等は環境変数から取得するように変更可能だが、ユーザー指定のリンクを優先
    auth_url = "https://discord.com/oauth2/authorize?client_id=1499719961810173972&response_type=code&redirect_uri=https%3A%2F%2Fdiscordverify.vercel.app%2Fapi%2Fcallback&scope=identify+email+guilds.join"

    embed = discord.Embed(
        title="✅ 認証 / Verification",
        description=(
            "このサーバーに参加するには認証が必要です。\n"
            "下のボタンをクリックして開始してください。\n\n"
            "To join this server, you need to verify your account.\n"
            "Click the button below to start."
        ),
        color=0x5865F2
    )
    embed.set_footer(text=f"Role: {role.name}")

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(label="Verify / 認証", url=auth_url, style=discord.ButtonStyle.link))

    # 新しいメッセージとして送信
    await interaction.channel.send(embed=embed, view=view)


# ── Settings View (persistent) ─────────────────────────────────────────────

class SettingsView(discord.ui.View):
    def __init__(self, settings: dict):
        super().__init__(timeout=None)
        self.settings = settings
        lang = settings.get("language", "ja")

        self.add_item(LogChannelButton(lang))
        self.add_item(LangButton(lang))
        self.add_item(VpnToggleButton(settings))
        self.add_item(SubToggleButton(settings))


class LogChannelButton(discord.ui.Button):
    def __init__(self, lang: str):
        super().__init__(label=t(lang, "set", "log_button"), style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        settings = get_guild_settings(str(interaction.guild_id))
        lang = settings.get("language", "ja")
        channels = [
            c for c in interaction.guild.channels
            if isinstance(c, discord.TextChannel)
        ]
        options = [
            discord.SelectOption(label=f"# {c.name}", value=str(c.id))
            for c in channels[:25]
        ]
        embed = discord.Embed(description=t(lang, "select_log_channel"), color=0x5865F2)
        view = discord.ui.View(timeout=None)
        select = ChannelSelect(options, lang)
        view.add_item(select)
        await interaction.response.edit_message(embed=embed, view=view)


class ChannelSelect(discord.ui.Select):
    def __init__(self, options: list, lang: str):
        super().__init__(placeholder="Select a channel...", options=options)
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        channel_id = self.values[0]
        settings = update_guild_settings(str(interaction.guild_id), log_channel_id=channel_id)
        lang = settings.get("language", "ja")
        await interaction.response.edit_message(
            embed=settings_embed(settings),
            view=SettingsView(settings),
        )


class LangButton(discord.ui.Button):
    def __init__(self, lang: str):
        super().__init__(label=t(lang, "set", "lang_button"), style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        settings = get_guild_settings(str(interaction.guild_id))
        lang = settings.get("language", "ja")
        embed = discord.Embed(description=t(lang, "select_language"), color=0x5865F2)
        view = discord.ui.View(timeout=None)
        options = [
            discord.SelectOption(label="🇯🇵 日本語", value="ja"),
            discord.SelectOption(label="🇺🇸 English", value="en"),
        ]
        view.add_item(LangSelect(options))
        await interaction.response.edit_message(embed=embed, view=view)


class LangSelect(discord.ui.Select):
    def __init__(self, options: list):
        super().__init__(placeholder="Select language...", options=options)

    async def callback(self, interaction: discord.Interaction):
        new_lang = self.values[0]
        settings = update_guild_settings(str(interaction.guild_id), language=new_lang)
        await interaction.response.edit_message(
            embed=settings_embed(settings),
            view=SettingsView(settings),
        )


class VpnToggleButton(discord.ui.Button):
    def __init__(self, settings: dict):
        lang = settings.get("language", "ja")
        state = t(lang, "set", "on") if settings.get("vpn_protection") else t(lang, "set", "off")
        super().__init__(
            label=f"{t(lang, 'set', 'vpn_button')} [{state}]",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(self, interaction: discord.Interaction):
        settings = get_guild_settings(str(interaction.guild_id))
        new_val = not settings.get("vpn_protection", True)
        settings = update_guild_settings(str(interaction.guild_id), vpn_protection=new_val)
        await interaction.response.edit_message(
            embed=settings_embed(settings),
            view=SettingsView(settings),
        )


class SubToggleButton(discord.ui.Button):
    def __init__(self, settings: dict):
        lang = settings.get("language", "ja")
        state = t(lang, "set", "on") if settings.get("sub_account_protection") else t(lang, "set", "off")
        super().__init__(
            label=f"{t(lang, 'set', 'sub_button')} [{state}]",
            style=discord.ButtonStyle.secondary,
        )

    async def callback(self, interaction: discord.Interaction):
        settings = get_guild_settings(str(interaction.guild_id))
        new_val = not settings.get("sub_account_protection", True)
        settings = update_guild_settings(str(interaction.guild_id), sub_account_protection=new_val)
        await interaction.response.edit_message(
            embed=settings_embed(settings),
            view=SettingsView(settings),
        )


# ── /check Modal ───────────────────────────────────────────────────────────

class CheckModal(discord.ui.Modal):
    def __init__(self, lang: str):
        super().__init__(title=t(lang, "check", "modal_title"))
        self.lang = lang
        self.query_input = discord.ui.TextInput(
            label=t(lang, "check", "modal_label"),
            placeholder=t(lang, "check", "modal_placeholder"),
            max_length=100,
            required=True,
        )
        self.add_item(self.query_input)

    async def on_submit(self, interaction: discord.Interaction):
        query = self.query_input.value.strip()
        user = get_verified_user_by_query(str(interaction.guild_id), query)

        if not user:
            await interaction.response.send_message(
                t(self.lang, "check", "not_found"), ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=check_embed(user, self.lang), ephemeral=True
        )


# ── Run ────────────────────────────────────────────────────────────────────

bot.run(os.environ["DISCORD_BOT_TOKEN"])
