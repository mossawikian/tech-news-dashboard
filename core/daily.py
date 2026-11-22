"""پیشنهاد خودکار روزانهٔ خبر.

قواعد برای صرفه‌جویی در سهمیه:
- هر روز فقط یک‌بار خودکار جستجو می‌شود (حتی اگر برنامه چندبار باز شود یا همهٔ مدل‌ها در انتظار سهمیه باشند).
  وضعیت تلاش در داده‌های ذخیره‌شده می‌ماند، پس با باز کردن دوبارهٔ اپ جستجوی تازه‌ای شروع نمی‌شود.
- اگر امروز سه خبر اضافه شده باشد، دیگر جستجو نمی‌شود.
- مدل ۵ خبر می‌آورد؛ سه تا امروز اضافه می‌شود و بقیه در «ذخیره» می‌ماند و فردا بدون جستجو استفاده می‌شود
  (به شرط آنکه هنوز در بازهٔ ۳ روز اخیر باشد).
- تلاش دوباره فقط با دکمهٔ دستی انجام می‌شود.
- «امروز» به وقت محلی (Asia/Karachi) حساب می‌شود؛ پس خبرهای جدید از ساعت ۰۰:۰۰ نیمه‌شب (اولین بازشدن برنامه) می‌آیند.
- علاوه بر این ۳ خبر، ۳ خبری که اعلان‌های نیمه‌شب را ساخته‌اند (GitHub Actions، فایل push_picks.json در Gist)
  هم با برچسب «پیشنهاد اعلان» به همان روز اضافه می‌شوند.
"""
import datetime as dt
import time

import streamlit as st

from core.ai import _get_keys, _similar, suggest_news
from core.state import save_data, week_start
from core.storage import load_picks, remote_enabled
from core.tz import today_local

DAILY_COUNT = 3          # تعداد خبر اضافه‌شده در هر روز
FETCH_COUNT = 6          # تعداد خبر درخواستی در هر جستجو (مازاد برای روزهای بعد ذخیره می‌شود)
WINDOW_DAYS = 3
SKIP_WEEKDAYS = {4}      # روزهای بدون پیشنهاد (۴ = جمعه). برای پیشنهاد در جمعه: set()


def _done_today(iso):
    return any(n.get("auto") and n.get("added") == iso for n in st.session_state.news_list)


def _add(items, today, iso):
    ss = st.session_state
    week = week_start(today).isoformat()
    for it in items:
        ss.news_list.append({
            "title": it["title"], "desc": f"{it['desc']} ({it['source']}، {it['date']})", "icon": "📰",
            "status": "Pending", "ai": "", "research": [], "added": iso, "week": week, "auto": True,
            "url": it.get("url", "")})


def _usable_reserve(today):
    """خبرهای ذخیره‌ای که هنوز در بازهٔ ۳ روز اخیر هستند و تکراری نیستند."""
    ss = st.session_state
    start = (today - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    have = {n["title"] for n in ss.news_list}
    return [r for r in ss.daily.get("reserve", []) if r.get("date", "") >= start and r["title"] not in have]


PICKS_CHECK_SECONDS = 300   # هر چند ثانیه حداکثر یک‌بار Gist برای خبرهای اعلان بررسی شود


def _add_push_picks():
    """خبرهای اعلان امروز (که اسکریپت نیمه‌شب در Gist گذاشته) را بدون هیچ درخواست هوش مصنوعی به صف اضافه می‌کند.
    هر روز فقط یک‌بار اضافه می‌شود؛ اگر هنوز نرسیده بود، حداکثر هر ۵ دقیقه دوباره نگاه می‌کند."""
    ss = st.session_state
    if not remote_enabled():
        return
    today = today_local()
    iso = today.isoformat()
    if ss.daily.get("picks_added") == iso or time.time() - ss.get("_picks_checked", 0) < PICKS_CHECK_SECONDS:
        return
    ss["_picks_checked"] = time.time()
    try:
        picks = load_picks()
    except Exception as exc:  # noqa: BLE001
        st.caption(f"خواندن خبرهای اعلان از Gist ناموفق بود: {str(exc)[:100]}")
        return
    date = picks.get("date", "")
    # فقط خبرهای امروز (به وقت محلی)؛ اگر اسکریپت هنوز اجرا نشده، فایلِ دیروز نادیده گرفته می‌شود
    if date != iso or not picks.get("items"):
        return
    have = [n["title"] for n in ss.news_list]
    week = week_start(today).isoformat()
    added = 0
    for it in picks["items"]:
        title = (it.get("title") or "").strip()
        if not title or any(_similar(title, h) for h in have):
            continue
        desc = (it.get("desc") or "").strip()
        meta = "، ".join(x for x in (it.get("source", ""), it.get("date", "")) if x)
        ss.news_list.append({
            "title": title, "desc": f"{desc} ({meta})" if meta else desc, "icon": "🔔", "status": "Pending",
            "ai": "", "research": [], "added": iso, "week": week, "push": True, "url": it.get("url", "")})
        have.append(title)
        added += 1
    ss.daily["picks_added"] = iso
    save_data()
    if added:
        st.toast(f"{added} خبر اعلان نیمه‌شب هم به صف اضافه شد.")


def ensure_daily_news():
    ss = st.session_state
    today = today_local()
    iso = today.isoformat()
    _add_push_picks()
    if today.weekday() in SKIP_WEEKDAYS or _done_today(iso):
        return

    # ۱) اول از خبرهای ذخیره‌شدهٔ روزهای قبل استفاده کن (بدون هیچ درخواستی)
    reserve = _usable_reserve(today)
    if len(reserve) >= DAILY_COUNT:
        _add(reserve[:DAILY_COUNT], today, iso)
        ss.daily["reserve"] = reserve[DAILY_COUNT:]
        save_data()
        st.toast(f"{DAILY_COUNT} خبر از ذخیرهٔ روزهای قبل اضافه شد.")
        return

    if not _get_keys():
        return

    # ۲) فقط یک تلاش خودکار در روز (ماندگار؛ با بازکردن دوبارهٔ اپ تکرار نمی‌شود)
    if ss.daily.get("tried") == iso:
        st.caption("پیشنهاد امروز هنوز دریافت نشده (سهمیه یا خطا). برای تلاش دوباره دکمه را بزنید.")
        if st.button(":material/refresh: دریافت دوبارهٔ پیشنهاد امروز", key="auto_retry"):
            ss.daily["tried"] = ""
            st.rerun()
        return
    ss.daily["tried"] = iso
    save_data()

    existing = [n["title"] for n in reversed(ss.news_list)]
    items, _sources = suggest_news(today, days=WINDOW_DAYS, n=FETCH_COUNT, existing=existing)
    if items is None:
        return        # خطا قبلاً نمایش داده شده
    pool = reserve + [i for i in items if i["title"] not in {r["title"] for r in reserve}]
    if not pool:
        st.info("امروز خبر تازه‌ای در بازهٔ ۳ روز اخیر پیدا نشد.")
        return
    _add(pool[:DAILY_COUNT], today, iso)
    ss.daily["reserve"] = pool[DAILY_COUNT:]
    save_data()
    st.toast(f"{len(pool[:DAILY_COUNT])} خبر تازهٔ امروز اضافه شد.")
