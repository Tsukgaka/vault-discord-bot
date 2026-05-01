MESSAGES = {
    "ja": {
        "set": {
            "title": "🔐 認証Bot 設定パネル",
            "description": "各ボタンから設定を変更できます。",
            "log_button": "📋 Logチャンネル設定",
            "lang_button": "🌐 言語設定",
            "vpn_button": "🛡️ VPN対策",
            "sub_button": "🔒 サブ垢対策",
            "on": "✅ オン",
            "off": "❌ オフ",
        },
        "check": {
            "modal_title": "ユーザー検索",
            "modal_label": "ユーザー名 / ユーザーID / 認証番号",
            "modal_placeholder": "例: username, 123456789, 3",
            "title": "🔍 ユーザー情報",
            "not_found": "❌ 該当するユーザーが見つかりませんでした。",
        },
        "log": {
            "title": "✅ 新規認証",
            "user": "ユーザー",
            "email": "メールアドレス",
            "ip": "IPアドレス",
            "vpn": "VPN",
            "time": "認証日時",
            "yes": "あり ⚠️",
            "no": "なし ✅",
        },
        "select_log_channel": "📋 ログを送信するチャンネルを選択してください。",
        "select_language": "🌐 言語を選択してください。",
    },
    "en": {
        "set": {
            "title": "🔐 Auth Bot Settings",
            "description": "Use the buttons below to configure settings.",
            "log_button": "📋 Log Channel",
            "lang_button": "🌐 Language",
            "vpn_button": "🛡️ VPN Protection",
            "sub_button": "🔒 Alt Account Protection",
            "on": "✅ ON",
            "off": "❌ OFF",
        },
        "check": {
            "modal_title": "User Search",
            "modal_label": "Username / User ID / Verification Number",
            "modal_placeholder": "e.g. username, 123456789, 3",
            "title": "🔍 User Info",
            "not_found": "❌ No user found.",
        },
        "log": {
            "title": "✅ New Verification",
            "user": "User",
            "email": "Email",
            "ip": "IP Address",
            "vpn": "VPN",
            "time": "Verified At",
            "yes": "Yes ⚠️",
            "no": "No ✅",
        },
        "select_log_channel": "📋 Select the channel to send logs to.",
        "select_language": "🌐 Select a language.",
    },
}


def t(lang: str, *keys: str) -> str:
    """Lookup a translation key like t('ja', 'set', 'title')"""
    data = MESSAGES.get(lang, MESSAGES["ja"])
    for k in keys:
        if isinstance(data, dict):
            data = data.get(k, ".".join(keys))
        else:
            return ".".join(keys)
    return data if isinstance(data, str) else ".".join(keys)
