"""ذخیرهٔ دائمی اختیاری روی یک Gist خصوصی گیت‌هاب.

فایل‌های سرور Streamlit موقت‌اند و با Reboot یا به‌روزرسانی کد پاک می‌شوند. اگر در Secrets
مقدارهای GITHUB_TOKEN و GIST_ID را بگذارید، دادهٔ برنامه روی همان Gist هم ذخیره می‌شود.
"""
import json
import urllib.request

import streamlit as st

API = "https://api.github.com/gists/"
FILENAME = "data.json"
PICKS_FILENAME = "push_picks.json"   # خبرهای اعلان امروز؛ اسکریپت GitHub Actions (نیمه‌شب) آن را می‌نویسد
TIMEOUT = 10


def _creds():
    try:
        token, gist_id = st.secrets.get("GITHUB_TOKEN"), st.secrets.get("GIST_ID")
    except Exception:  # noqa: BLE001  (فایل secrets وجود ندارد)
        return None
    return (str(token).strip(), str(gist_id).strip()) if token and gist_id else None


def remote_enabled():
    return _creds() is not None


def _open(req):
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8")


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
            "User-Agent": "sade-dashboard", "Content-Type": "application/json"}


def load_remote():
    """محتوای data.json را به‌صورت dict برمی‌گرداند؛ در صورت خطا استثنا می‌دهد."""
    token, gist_id = _creds()
    info = json.loads(_open(urllib.request.Request(API + gist_id, headers=_headers(token))))
    f = info.get("files", {}).get(FILENAME)
    if not f:
        return {}
    if f.get("truncated"):
        content = _open(urllib.request.Request(f["raw_url"], headers=_headers(token)))
    else:
        content = f.get("content", "")
    return json.loads(content) if content.strip() else {}


def save_remote(text):
    token, gist_id = _creds()
    body = json.dumps({"files": {FILENAME: {"content": text}}}).encode("utf-8")
    _open(urllib.request.Request(API + gist_id, data=body, method="PATCH", headers=_headers(token)))


def load_picks():
    """خبرهای اعلان روزانه {"date": "YYYY-MM-DD", "items": [...]} از همان Gist؛ اگر نبود {}."""
    token, gist_id = _creds()
    info = json.loads(_open(urllib.request.Request(API + gist_id, headers=_headers(token))))
    f = info.get("files", {}).get(PICKS_FILENAME)
    if not f:
        return {}
    content = (_open(urllib.request.Request(f["raw_url"], headers=_headers(token))) if f.get("truncated")
               else f.get("content", ""))
    return json.loads(content) if content.strip() else {}
