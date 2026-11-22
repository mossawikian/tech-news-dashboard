"""پیشنهاد هفتگی ۴ موضوع دیپ‌دایو، با نمره‌دهی، ذخیره و جایگزینیِ موضوع ردشده.

زمان: اولین بازشدن برنامه از شروع جمعه به وقت پاکستان (Asia/Karachi). برنامه در پس‌زمینه کار نمی‌کند؛ اگر جمعه
باز نشود، اولین بازشدن بعدی (تا جمعهٔ بعد) همان پیشنهاد هفته را می‌سازد. هر جمعه فقط یک تلاش خودکار.
هر تلاش ۸ موضوع نمره‌دار می‌آورد: ۴ برتر (با ترکیب نوع‌ها) نمایش داده می‌شود و ۴ تای دیگر در «ذخیره» می‌ماند.
با «رد» موضوع کامل حذف می‌شود و بهترین موضوع ذخیره بدون جست‌وجوی تازه جایگزین می‌شود.
"""
import datetime as dt
import time
from zoneinfo import ZoneInfo

import streamlit as st

from core.ai import MIN_SECONDS_BETWEEN_CALLS, _get_keys, _similar, pick_top, suggest_deep_topics
from core.helpers import fa
from core.state import new_topic, save_data, week_start

TZ = ZoneInfo("Asia/Karachi")
COUNT = 4
FETCH = 8
FRIDAY = 4
MAX_REJECTED = 60


def cycle_key(now=None):
    """تاریخ آخرین جمعه (به وقت پاکستان) که شروع شده است؛ هر جمعه یک «دوره» است."""
    d = (now or dt.datetime.now(TZ)).date()
    return (d - dt.timedelta(days=(d.weekday() - FRIDAY) % 7)).isoformat()


def _target_week(now):
    # هفتهٔ شمسی از شنبه شروع می‌شود؛ پیشنهادِ جمعه برای هفتهٔ بعد است (تا آن موقع در «هفتهٔ جاری» دیده می‌شود)
    return week_start(now.date() + dt.timedelta(days=1)).isoformat()


def _known_titles():
    ss = st.session_state
    return [t["title"] for t in ss.deep_topics] + list(ss.daily.get("deep_rejected", []))


def _make_topic(item, cycle, week, today_iso):
    t = new_topic(item["title"])
    t.update({"why": item["why"], "scores": item["scores"], "total": item["total"], "dtype": item["type"],
              "auto": True, "cycle": cycle, "week": week, "added": today_iso})
    return t


def _fresh_reserve():
    """ذخیره‌ای که تکراری یا شبیه ردشده‌ها نیست."""
    ss = st.session_state
    known = _known_titles()
    return [r for r in ss.daily.get("deep_reserve", []) if not any(_similar(r["title"], k) for k in known)]


def _explain_empty():
    """وقتی هیچ موضوعی نیامد: دلیل (چند خط خوانده شد و چرا حذف شد) + متن خام برای بررسی."""
    d = st.session_state.get("_deep_diag")
    if not d:
        return
    st.caption(f"مدل {fa(d['lines'])} موضوع نوشت؛ {fa(d['bad_format'])} خط قالب نامعتبر، {fa(d['low'])} با نمرهٔ بسیار کم، "
               f"{fa(d['dup'])} تکراری یا شبیه موضوع‌های قبلی/ردشده بود.")
    with st.expander("پاسخ خام مدل (برای بررسی)"):
        st.code(d.get("raw", ""), language=None)


def _fetch_and_store(cycle, week, today_iso, want):
    """یک جست‌وجو؛ want موضوع برتر اضافه می‌شود و بقیه به ذخیره می‌رود. برمی‌گرداند: تعداد اضافه‌شده یا None (خطا)."""
    ss = st.session_state
    items = suggest_deep_topics(_known_titles(), FETCH)
    if items is None:
        return None
    pool = _fresh_reserve() + [i for i in items if not any(_similar(i["title"], r["title"]) for r in _fresh_reserve())]
    pool.sort(key=lambda x: -x["total"])
    chosen, rest = pick_top(pool, want)
    for it in chosen:
        ss.deep_topics.append(_make_topic(it, cycle, week, today_iso))
    ss.daily["deep_reserve"] = rest
    save_data()
    return len(chosen)


def ensure_deep_suggestions():
    ss = st.session_state
    now = dt.datetime.now(TZ)
    cycle = cycle_key(now)
    if ss.daily.get("deep_tried") == cycle:
        return
    if not _get_keys():
        return
    ss.daily["deep_tried"] = cycle      # ماندگار: با باز کردن دوبارهٔ اپ تکرار نمی‌شود
    save_data()
    wait = MIN_SECONDS_BETWEEN_CALLS - (time.time() - ss.get("_last_ai_call", 0))
    if wait > 0:       # بعد از درخواست قبلی (مثلاً خبر روزانه) صبر کن تا محافظ فاصله مانع نشود
        time.sleep(wait + 0.5)
    n = _fetch_and_store(cycle, _target_week(now), now.date().isoformat(), COUNT)
    if n:
        st.toast(f"{n} موضوع جدید دیپ‌دایو پیشنهاد شد.")
    elif n == 0:
        st.info("این هفته موضوع تازهٔ مناسبی پیدا نشد.")
        _explain_empty()


def reject_topic(idx):
    """موضوع را کامل حذف می‌کند و (اگر پیشنهاد خودکار بود) بهترین موضوع ذخیره را جایگزین می‌کند."""
    ss = st.session_state
    topic = ss.deep_topics.pop(idx)
    rej = ss.daily.setdefault("deep_rejected", [])
    rej.append(topic["title"])
    del rej[:-MAX_REJECTED]
    for k in [k for k in ss.keys() if str(k).startswith("scn_edit_")]:
        del ss[k]      # کلیدها بر اساس شمارهٔ موضوع‌اند و بعد از حذف نامعتبر می‌شوند
    replaced = False
    if topic.get("auto"):
        reserve = _fresh_reserve()
        if reserve:
            best = max(reserve, key=lambda x: x["total"])
            ss.deep_topics.append(_make_topic(best, topic.get("cycle", ""), topic.get("week", ""),
                                              dt.datetime.now(TZ).date().isoformat()))
            ss.daily["deep_reserve"] = [r for r in reserve if r is not best]
            replaced = True
    save_data()
    return replaced


def refill_button(week_topics_count):
    """وقتی ذخیره خالی است و کمتر از ۴ پیشنهاد خودکار مانده، دکمهٔ جست‌وجوی دستی."""
    ss = st.session_state
    if week_topics_count >= COUNT or _fresh_reserve():
        return
    if st.button(":material/auto_awesome: پیشنهاد جدید (یک جست‌وجو)", key="deep_refill"):
        now = dt.datetime.now(TZ)
        n = _fetch_and_store(cycle_key(now), _target_week(now), now.date().isoformat(), COUNT - week_topics_count)
        if n:
            st.rerun()
        elif n == 0:
            st.info("موضوع تازهٔ مناسبی پیدا نشد.")
            _explain_empty()
