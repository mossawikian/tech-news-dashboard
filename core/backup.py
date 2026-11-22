"""پشتیبان‌گیری و بازگردانی داده‌ها (اخبار، اسکریپت‌ها، تحقیق‌ها، دیپ‌دایو، رویدادها، ذخیرهٔ پیشنهاد روزانه)."""
import datetime as dt
import json

import streamlit as st

from core.state import normalize_news, save_data
from core.tz import now_local, today_local

KEYS = ("news_list", "deep_topics", "events", "daily")


def make_backup() -> str:
    ss = st.session_state
    data = {k: ss.get(k, {} if k == "daily" else []) for k in KEYS}
    data["_backup_at"] = now_local().isoformat(timespec="seconds")
    return json.dumps(data, ensure_ascii=False, indent=1)


def _valid(data):
    return (isinstance(data, dict) and isinstance(data.get("news_list"), list)
            and all(isinstance(n, dict) and "title" in n and "status" in n for n in data["news_list"]))


def backup_section():
    """بخش پشتیبان در صفحهٔ تنظیمات."""
    ss = st.session_state
    st.markdown("##### :material/save: پشتیبان‌گیری")
    n = len(ss.get("news_list", []))
    st.caption(f"{n} خبر در حافظه است. گاهی یک نسخهٔ پشتیبان دانلود کنید تا اگر Gist یا توکن مشکل پیدا کرد، چیزی از دست نرود.")
    st.download_button(":material/download: دانلود پشتیبان (JSON)", data=make_backup(),
                       file_name=f"sade-backup-{today_local().isoformat()}.json",
                       mime="application/json", key="dl_backup")
    up = st.file_uploader("بازگردانی از فایل پشتیبان", type=["json"], key="restore_file")
    if up is None:
        return
    try:
        data = json.loads(up.getvalue().decode("utf-8"))
    except Exception:  # noqa: BLE001
        st.error("فایل خوانده نشد؛ مطمئن شوید فایل پشتیبان همین برنامه است.")
        return
    if not _valid(data):
        st.error("ساختار فایل معتبر نیست.")
        return
    st.info(f"این فایل {len(data['news_list'])} خبر دارد"
            + (f" (تاریخ پشتیبان: {data['_backup_at']})" if data.get("_backup_at") else "")
            + ". بازگردانی داده‌های فعلی را جایگزین می‌کند.")
    if st.button(":material/restore: بازگردانی و جایگزینی داده‌های فعلی", type="primary", key="do_restore"):
        ss.news_list = data["news_list"]
        ss.deep_topics = data.get("deep_topics") or ss.get("deep_topics", [])
        ss.events = data.get("events") or []
        ss.daily = data.get("daily") or {}
        for k in [k for k in ss.keys() if str(k).startswith(("script_", "chat_"))]:
            del ss[k]
        normalize_news()
        ss["_saved_hash"] = None
        save_data()
        st.success("بازگردانی انجام شد.")
        st.rerun()
