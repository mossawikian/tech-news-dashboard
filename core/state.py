"""دادهٔ برنامه: مقادیر پیش‌فرض، ذخیره و بارگذاری (data.json)."""
import copy
import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import streamlit as st

from core.storage import load_remote, remote_enabled, save_remote
from core.tz import now_local, now_naive, today_local

# تحقیق‌های هر خبر تا این تعداد روز پس از آخرین فعالیت در آرشیف می‌مانند، سپس خودکار حذف می‌شوند.
ARCHIVE_DAYS = 20
TS_FMT = "%Y-%m-%d %H:%M"
# خبرها هفته‌به‌هفته (شنبه تا جمعه) نگه داشته می‌شوند: هفتهٔ جاری + این‌تعداد هفتهٔ قبل؛ قدیمی‌تر خودکار حذف می‌شود.
KEEP_PREVIOUS_WEEKS = 2
WEEKDAY_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]  # به ترتیب date.weekday()


def week_start(d):
    """شنبهٔ هفتهٔ شمسی که d در آن است."""
    return d - dt.timedelta(days=(d.weekday() - 5) % 7)


def current_week():
    return week_start(today_local()).isoformat()

NEWS_DEFAULT = [
    {"title": "ربات‌های انسان‌نما با یادگیری شهودی",
     "desc": "قابلیت یادگیری کارهای خانه با مشاهدهٔ رفتار انسان.",
     "icon": "🤖", "status": "Pending", "ai": ""},
    {"title": "سیگنال‌های مرموز فضایی",
     "desc": "کشف امواج رادیویی ناشناخته از لبهٔ منظومهٔ شمسی.",
     "icon": "📡", "status": "Pending", "ai": ""},
    {"title": "بافت‌های زیستی چاپ‌شده سه‌بعدی",
     "desc": "ترمیم خودکار آسیب‌های بافتی داخل بدن.",
     "icon": "🧬", "status": "Pending", "ai": ""},
]
DEEP_DEFAULT = [
    {"title": "رازهای پنهان الگوریتم‌های کلود شانون", "status": "Pending", "scenario": ""},
    {"title": "تکنولوژی فراموش‌شدهٔ باتری‌های حالت جامد", "status": "Pending", "scenario": ""},
    {"title": "پشت پردهٔ پروژه‌های محرمانهٔ فضایی مهار انرژی خورشیدی", "status": "Pending", "scenario": ""},
]


DATA_FILE = Path(__file__).resolve().parent.parent / "data.json"


def now_str():
    return now_local().strftime(TS_FMT)


def _parse(ts):
    try:
        return dt.datetime.strptime(ts, TS_FMT)
    except (TypeError, ValueError):
        return None


def load_data():
    """اول از Gist (اگر تنظیم شده)، در غیر این صورت از فایل محلی."""
    ss = st.session_state
    if remote_enabled():
        try:
            return load_remote() or {}
        except Exception as exc:  # noqa: BLE001
            ss["storage_error"] = f"خواندن از Gist ناموفق بود: {str(exc)[:150]}"
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def save_data():
    """فقط وقتی داده تغییر کرده باشد ذخیره می‌کند (محلی + در صورت تنظیم، Gist)."""
    ss = st.session_state
    text = json.dumps({"news_list": ss.news_list, "deep_topics": ss.deep_topics, "events": ss.events, "daily": ss.get("daily", {})},
                      ensure_ascii=False, indent=1)
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    if ss.get("_saved_hash") == digest:
        return
    try:
        DATA_FILE.write_text(text, encoding="utf-8")
        ss["local_save_error"] = ""
    except Exception as exc:  # noqa: BLE001
        ss["local_save_error"] = str(exc)[:150]
    if remote_enabled():
        if time.time() < ss.get("_remote_retry_after", 0):
            return  # بعد از یک خطا، چند ثانیه صبر می‌کنیم
        try:
            save_remote(text)
            ss["storage_error"] = ""
            ss["last_remote_save"] = now_str()
        except Exception as exc:  # noqa: BLE001
            ss["storage_error"] = f"ذخیره در Gist ناموفق بود: {str(exc)[:150]}"
            ss["_remote_retry_after"] = time.time() + 60
            return
    ss["_saved_hash"] = digest


def normalize_news():
    """خبرهای قدیمی را به قالب جدید (تحقیق چندنسخه‌ای، روز و هفته) تبدیل می‌کند."""
    for n in st.session_state.news_list:
        n.setdefault("research", [])
        if n.get("ai") and not n["research"]:
            n["research"] = [{"v": 1, "ts": now_str(), "q": "", "text": n["ai"], "model": ""}]
        n["ai"] = ""
        if not n.get("added"):
            n["added"] = (n.get("decided") or "")[:10] or today_local().isoformat()
        if not n.get("week"):
            try:
                n["week"] = week_start(dt.date.fromisoformat(n["added"])).isoformat()
            except ValueError:
                n["added"], n["week"] = today_local().isoformat(), current_week()


def normalize_deep():
    """به موضوع‌های دیپ‌دایو روز و هفتهٔ افزودن را اضافه می‌کند (موضوع‌های قدیمی: هفتهٔ جاری)."""
    for t in st.session_state.deep_topics:
        t.setdefault("scenario", "")
        t.setdefault("narration", "")
        if not t.get("added"):
            t["added"] = today_local().isoformat()
        if not t.get("week"):
            try:
                t["week"] = week_start(dt.date.fromisoformat(t["added"])).isoformat()
            except ValueError:
                t["added"], t["week"] = today_local().isoformat(), current_week()


def new_topic(title):
    return {"title": title, "status": "Pending", "scenario": "", "narration": "",
            "added": today_local().isoformat(), "week": current_week()}


def purge_old_weeks():
    """خبرهای قدیمی‌تر از (هفتهٔ جاری + KEEP_PREVIOUS_WEEKS هفتهٔ قبل) را حذف می‌کند."""
    ss = st.session_state
    cutoff = (week_start(today_local()) - dt.timedelta(weeks=KEEP_PREVIOUS_WEEKS)).isoformat()
    keep = [n for n in ss.news_list if n.get("week", "") >= cutoff]
    old_topics = len(ss.deep_topics)
    ss.deep_topics = [t for t in ss.deep_topics if t.get("week", "") >= cutoff]
    if len(ss.deep_topics) != old_topics:
        for k in [k for k in ss.keys() if str(k).startswith("scn_edit_")]:
            del ss[k]  # کلیدها بر اساس شمارهٔ موضوع‌اند
        st.toast(f"{old_topics - len(ss.deep_topics)} موضوع دیپ‌دایو قدیمی‌تر از {KEEP_PREVIOUS_WEEKS + 1} هفته حذف شد.")
    removed = len(ss.news_list) - len(keep)
    if removed:
        ss.news_list = keep
        for k in [k for k in ss.keys() if str(k).startswith(("script_", "chat_"))]:
            del ss[k]  # کلیدهای ویجت بر اساس شمارهٔ خبرند و بعد از حذف نامعتبر می‌شوند
        st.toast(f"{removed} خبر قدیمی‌تر از {KEEP_PREVIOUS_WEEKS + 1} هفته از آرشیف حذف شد.")


def purge_expired():
    """تحقیق‌هایی که ARCHIVE_DAYS روز از آخرین فعالیتشان گذشته حذف می‌شوند (عنوان، وضعیت و اسکریپت می‌مانند)."""
    limit = now_naive() - dt.timedelta(days=ARCHIVE_DAYS)
    removed = 0
    for n in st.session_state.news_list:
        versions = n.get("research") or []
        last = _parse(versions[-1].get("ts")) if versions else None
        if last and last < limit:
            n["research"] = []
            removed += 1
    if removed:
        st.toast(f"{removed} تحقیق قدیمی‌تر از {ARCHIVE_DAYS} روز از آرشیف حذف شد.")


def days_left(item):
    """چند روز تا حذف خودکار تحقیق این خبر مانده است."""
    versions = item.get("research") or []
    last = _parse(versions[-1].get("ts")) if versions else None
    if not last:
        return ARCHIVE_DAYS
    return max((last + dt.timedelta(days=ARCHIVE_DAYS) - now_naive()).days, 0)


def init_state():
    ss = st.session_state
    today = today_local()
    saved = load_data() if "news_list" not in ss else {}
    ss.setdefault("news_list", saved.get("news_list") or copy.deepcopy(NEWS_DEFAULT))
    ss.setdefault("deep_topics", saved.get("deep_topics") or copy.deepcopy(DEEP_DEFAULT))
    ss.setdefault("events", saved.get("events") or [])
    ss.setdefault("daily", saved.get("daily") or {})   # {"tried": تاریخ آخرین تلاش، "reserve": خبرهای ذخیره برای روزهای بعد}
    ss.setdefault("cal_year", today.year)
    ss.setdefault("cal_month", today.month)
    ss.setdefault("views", [120, 250, 180, 300, 450, 380, 520])
    ss.setdefault("total_views", 12424)
    normalize_news()
    normalize_deep()
    purge_old_weeks()
    purge_expired()
