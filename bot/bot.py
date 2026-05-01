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
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    try:
        await tree.sync()
        print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ── /set command ───────────────────────────────────────────────────────────

@tree.command(name="set", description="認証Botの設定パネルを開く / Open settings panel")
@app_commands.default_permissions(administrator=True)
async def cmd_set(interaction: discord.Interaction):
    try:
        settings = get_guild_settings(str(interaction.guild_id))
        embed = settings_embed(settings)
        view = SettingsView(settings)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        print(f"Error in /set: {e}")
        await interaction.response.send_message(f"❌ Error: {e}\n設定を取得できませんでした。データベースを確認してください。", ephemeral=True)

# ── /check command ─────────────────────────────────────────────────────────

@tree.command(name="check", description="認証済みユーザーを確認 / Check verified user")
@app_commands.default_permissions(administrator=True)
async def cmd_check(interaction: discord.Interaction):
    try:
        settings = get_guild_settings(str(interaction.guild_id))
        lang = settings.get("language", "ja")
        await interaction.response.send_modal(CheckModal(lang))
    except Exception as e:
        print(f"Error in /check: {e}")
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# ── /panel command ──────────────────────────────────────────────────────────

@tree.command(name="panel", description="認証パネルを送信 / Send authentication panel")
@app_commands.describe(role="認証成功時に付与するロール / Role to give upon success")
@app_commands.default_permissions(administrator=True)
async def cmd_panel(interaction: discord.Interaction, role: discord.Role):
    try:
        await interaction.response.send_message("Generating...", ephemeral=True)

        if not interaction.guild_id:
            return await interaction.edit_original_response(content="❌ このコマンドはサーバー内でのみ使用できます。")

        settings = get_guild_settings(str(interaction.guild_id))
        raw_url = os.environ.get("WEB_URL", "https://discordverify.vercel.app")
        web_url = raw_url.replace("web_url=", "").replace("WEB_URL=", "").strip().rstrip("/")
        
        auth_url = f"{web_url}/api/auth?guild={interaction.guild_id}&user={interaction.user.id}&role={role.id}"

        embed = discord.Embed(
            title="✅ 認証 / Verification",
            description="サーバーに参加するには下のボタンを押して認証を完了してください。\n\nClick the button below to verify.",
            color=0x5865F2
        )
        embed.set_footer(text=f"Role: {role.name}")

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label="Verify / 認証", url=auth_url, style=discord.ButtonStyle.link))

        try:
            await interaction.channel.send(embed=embed, view=view)
            await interaction.edit_original_response(content="✅ 認証パネルを送信しました！")
        except discord.errors.Forbidden:
            await interaction.edit_original_response(content="❌ 権限エラー: このチャンネルで「メッセージ送信」および「埋め込みリンク」の権限がBotにあるか確認してください。")

    except Exception as e:
        print(f"Error in /panel: {e}")
        await interaction.edit_original_response(content=f"❌ 予期せぬエラー: {e}")

# ── Settings View ─────────────────────────────────────────────────────────

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
        await interaction.response.defer(ephemeral=True)
        settings = get_guild_settings(str(interaction.guild_id))
        lang = settings.get("language", "ja")
        channels = [c for c in interaction.guild.channels if isinstance(c, discord.TextChannel)]
        options = [discord.SelectOption(label=f"# {c.name}", value=str(c.id)) for c in channels[:25]]
        if not options: return await interaction.followup.send("チャンネルが見つかりません。", ephemeral=True)
        embed = discord.Embed(description=t(lang, "select_log_channel"), color=0x5865F2)
        view = discord.ui.View(timeout=None)
        view.add_item(ChannelSelect(options, lang))
        await interaction.edit_original_response(embed=embed, view=view)

class ChannelSelect(discord.ui.Select):
    def __init__(self, options: list, lang: str):
        super().__init__(placeholder="Select...", options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = update_guild_settings(str(interaction.guild_id), log_channel_id=self.values[0])
        await interaction.edit_original_response(embed=settings_embed(settings), view=SettingsView(settings))

class LangButton(discord.ui.Button):
    def __init__(self, lang: str):
        super().__init__(label=t(lang, "set", "lang_button"), style=discord.ButtonStyle.secondary)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(description="言語を選択してください / Select Language", color=0x5865F2)
        view = discord.ui.View(timeout=None)
        view.add_item(LangSelect())
        await interaction.edit_original_response(embed=embed, view=view)

class LangSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label="🇯🇵 日本語", value="ja"), discord.SelectOption(label="🇺🇸 English", value="en")]
        super().__init__(options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = update_guild_settings(str(interaction.guild_id), language=self.values[0])
        await interaction.edit_original_response(embed=settings_embed(settings), view=SettingsView(settings))

class VpnToggleButton(discord.ui.Button):
    def __init__(self, settings: dict):
        lang = settings.get("language", "ja")
        state = t(lang, "set", "on") if settings.get("vpn_protection") else t(lang, "set", "off")
        super().__init__(label=f"{t(lang, 'set', 'vpn_button')} [{state}]", style=discord.ButtonStyle.secondary)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = get_guild_settings(str(interaction.guild_id))
        new_val = not settings.get("vpn_protection", True)
        settings = update_guild_settings(str(interaction.guild_id), vpn_protection=new_val)
        await interaction.edit_original_response(embed=settings_embed(settings), view=SettingsView(settings))

class SubToggleButton(discord.ui.Button):
    def __init__(self, settings: dict):
        lang = settings.get("language", "ja")
        state = t(lang, "set", "on") if settings.get("sub_account_protection") else t(lang, "set", "off")
        super().__init__(label=f"{t(lang, 'set', 'sub_button')} [{state}]", style=discord.ButtonStyle.secondary)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = get_guild_settings(str(interaction.guild_id))
        new_val = not settings.get("sub_account_protection", True)
        settings = update_guild_settings(str(interaction.guild_id), sub_account_protection=new_val)
        await interaction.edit_original_response(embed=settings_embed(settings), view=SettingsView(settings))

class CheckModal(discord.ui.Modal):
    def __init__(self, lang: str):
        super().__init__(title=t(lang, "check", "modal_title"))
        self.query_input = discord.ui.TextInput(label=t(lang, "check", "modal_label"), required=True)
        self.add_item(self.query_input)
        self.lang = lang
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        user = get_verified_user_by_query(str(interaction.guild_id), self.query_input.value.strip())
        if not user: return await interaction.followup.send(t(self.lang, "check", "not_found"), ephemeral=True)
        await interaction.followup.send(embed=check_embed(user, self.lang), ephemeral=True)

token = os.environ.get("DISCORD_BOT_TOKEN")
if not token: print("❌ Error: Bot Token not found.")
else: bot.run(token)
