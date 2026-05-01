# 🔐 Discord OAuth2 認証Bot

PythonベースのDiscord認証システムです。  
Bot本体は `discord.py`、バックエンドはVercel（Pythonサーバーレス）で動きます。

---

## 📁 ファイル構成

```
discord-auth-bot/
├── bot/
│   ├── bot.py           # Botメインファイル
│   ├── db.py            # DB操作
│   ├── embeds.py        # 埋め込みビルダー
│   ├── i18n.py          # 日本語/英語翻訳
│   └── requirements.txt
│
├── web/
│   ├── api/
│   │   ├── auth.py      # OAuth2開始エンドポイント
│   │   ├── callback.py  # OAuth2コールバック（全セキュリティロジック）
│   │   ├── _db.py       # DB操作（web用）
│   │   ├── _vpn.py      # VPN検出
│   │   └── _discord.py  # Discord通知
│   ├── static/
│   │   └── verify.html  # 認証ページ
│   ├── requirements.txt
│   └── vercel.json      # Vercelの設定
│
├── schema.sql           # DBテーブル作成SQL
└── .env.example         # 環境変数テンプレート
```

---

## 🚀 セットアップ（順番通りにやればOK）

### Step 1: Discord Developer Portal

1. [discord.com/developers/applications](https://discord.com/developers/applications) を開く
2. **New Application** → 名前を入力して作成
3. **OAuth2** タブ
   - `Client ID` と `Client Secret` をメモ
   - **Redirects** に追加：`https://あなたのVercelURL/api/callback`
4. **Bot** タブ
   - **Add Bot** → Token をコピー
   - **Privileged Gateway Intents** → `Server Members Intent` をON

---

### Step 2: Botをサーバーに招待

以下のURLの `YOUR_CLIENT_ID` を置き換えてブラウザで開く：

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=268435457&scope=bot%20applications.commands
```

---

### Step 3: Neon（データベース）

1. [neon.tech](https://neon.tech) で無料アカウント作成
2. 新しいプロジェクトを作成
3. **Dashboard** → **Connection String** をコピー（`postgresql://...`）
4. **SQL Editor** を開いて `schema.sql` の内容を貼り付けて実行

---

### Step 4: Vercel にデプロイ（超簡単）

#### 方法A: GitHub経由（推奨）

1. `web/` フォルダをGitHubリポジトリにpush
2. [vercel.com](https://vercel.com) にログイン → **Add New Project** → リポジトリを選択
3. **Root Directory** を `web` に設定
4. **Environment Variables** に以下を追加：

| Key | Value |
|-----|-------|
| `DISCORD_CLIENT_ID` | DiscordのClient ID |
| `DISCORD_CLIENT_SECRET` | DiscordのClient Secret |
| `DISCORD_BOT_TOKEN` | BotのToken |
| `WEB_URL` | `https://あなたのプロジェクト.vercel.app` |
| `DATABASE_URL` | NeonのConnection String |
| `VERIFIED_ROLE_ID` | 認証後のロールID（任意） |

5. **Deploy** をクリック → 完了！

#### 方法B: Vercel CLI（コマンドラインで完結）

```bash
# Vercel CLIをインストール
npm i -g vercel

# webフォルダに移動
cd web

# デプロイ（初回は対話式でプロジェクト設定）
vercel

# 環境変数を設定
vercel env add DISCORD_CLIENT_ID
vercel env add DISCORD_CLIENT_SECRET
vercel env add DISCORD_BOT_TOKEN
vercel env add WEB_URL
vercel env add DATABASE_URL

# 本番デプロイ
vercel --prod
```

---

### Step 5: Botを起動

```bash
cd bot

# 依存パッケージをインストール
pip install -r requirements.txt

# .envを作成
cp ../.env.example .env
# .envを編集して値を入力

# Bot起動
python bot.py
```

#### サーバー上で常時起動させる場合

```bash
# systemdサービスとして登録（Linux）
# /etc/systemd/system/discord-bot.service に以下を記述

[Unit]
Description=Discord Auth Bot
After=network.target

[Service]
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 bot.py
EnvironmentFile=/path/to/bot/.env
Restart=always

[Install]
WantedBy=multi-user.target

# 有効化
systemctl enable discord-bot
systemctl start discord-bot
```

---

## 🤖 Botの使い方

### `/set` — 設定パネル（管理者のみ・自分にだけ表示）

| ボタン | 機能 |
|--------|------|
| 📋 Logチャンネル設定 | ドロップダウンでチャンネルを選択 |
| 🌐 言語設定 | 日本語 / English |
| 🛡️ VPN対策 [ON/OFF] | VPN/プロキシをブロック |
| 🔒 サブ垢対策 [ON/OFF] | 同一IP・メールの多重認証をブロック |

### `/check` — ユーザー情報確認（管理者のみ・自分にだけ表示）

モーダルに以下のどれかを入力：
- ユーザー名（例: `taro123`）
- Discord ID（例: `123456789012345678`）
- 認証番号（例: `5` → 5番目に認証した人）

→ メールアドレス・IP・VPN有無が表示される

---

## 🔒 セキュリティの仕組み

| 対策 | 内容 |
|------|------|
| CSRF対策 | StateをHTTP Only Cookieで検証 |
| ユーザー一致確認 | OAuthユーザーIDとボタン操作者のIDを比較 |
| VPN/プロキシ検出 | ip-api.com でproxy/hostingフラグを確認 |
| メール重複検出 | SHA-256ハッシュでDBと照合 |
| IP重複検出 | SHA-256ハッシュでDBと照合 |
| メール未確認ブロック | Discord未確認メールは弾く |

---

## ⚠️ 注意事項

- ip-api.comの無料プランは **45リクエスト/分** の制限あり
- 大規模サーバーでは有料プランの利用を推奨
- メールアドレスは個人情報です。利用規約・プライバシーポリシーの設置を推奨
