"""جمع‌آوری خودکار خبرهای تکنولوژی از منابع ساختاریافته (بدون هیچ سهمیهٔ جست‌وجو).

لایه‌ها:
  ۰) فیدهای RSS منابع منتخب هر حوزه (FEEDS) — مهم‌ترین منبع و بالاترین اولویت
  ۱) جست‌وجوی موضوعی Google News RSS برای هر حوزه (NEWS_QUERIES) — پوشش هزاران سایت دیگر
  ۲) Hacker News (API رایگان Algolia) — فقط برای «وایرال/بحث‌برانگیز بودن» (امتیاز و تعداد نظرها)
خروجی collect(): فهرست کاندیداهای رتبه‌بندی‌شده؛ Gemini از میان آن‌ها بهترین‌ها را انتخاب و فارسی می‌کند.

هر منبع جداگانه و با مهلت کوتاه گرفته می‌شود؛ اگر منبعی خراب یا مسدود بود، بی‌صدا کنار می‌رود.
برای دیدن وضعیت هر منبع: تنظیمات ← «تست منابع خبر». برای افزودن/حذف سایت، فقط فهرست FEEDS را ویرایش کنید.
"""
import datetime as dt
import time
from concurrent.futures import ThreadPoolExecutor, wait

import streamlit as st

from core.feeds.config import BUDGET, CACHE_SECONDS, WORKERS
from core.feeds.fetch import _fetch_hn, _gn_url, _job_feed
from core.feeds.rank import _build, _norm_url, _select
from core.feeds.sources import FEEDS, NEWS_QUERIES
from core.tz import today_local


# ── نقطهٔ ورود ─────────────────────────────────────────────────────────────────────────────
def collect(start, end, refresh=False):
    """خبرهای منتشرشده بین دو تاریخ (شامل هر دو) را از همهٔ لایه‌ها می‌گیرد.
    خروجی: (کاندیداهای رتبه‌بندی‌شده، گزارش سلامت منابع {نام: (ok, تعداد, خطا)})؛ نتیجه ۲۰ دقیقه کش می‌شود."""
    ss = st.session_state
    key = (start.isoformat(), end.isoformat())
    cached = ss.get("_feeds_cache")
    if cached and not refresh and cached[0] == key and time.time() - cached[1] < CACHE_SECONDS:
        return cached[2], cached[3]

    start_dt = dt.datetime.combine(start, dt.time.min, dt.timezone.utc)
    end_dt = dt.datetime.combine(end, dt.time.max, dt.timezone.utc)
    days = max((end - start).days, 1)
    jobs = []   # (برچسب، تابع)
    for domain, lst in FEEDS.items():
        for name, url in lst:
            jobs.append((f"{name}", lambda d=domain, n=name, u=url: _job_feed(d, n, u, 1.0)))
    for domain, queries in NEWS_QUERIES.items():
        for i, q in enumerate(queries, 1):
            jobs.append((f"Google News · {domain} #{i}",
                         lambda d=domain, q=q: _job_feed(d, "Google News", _gn_url(q, days), 0.6, strip_source=True)))
    jobs.append(("Hacker News", lambda: _fetch_hn(start_dt)))

    health, items, hn = {}, [], []
    pool = ThreadPoolExecutor(max_workers=WORKERS)
    futures = {pool.submit(fn): label for label, fn in jobs}
    done, pending = wait(futures, timeout=BUDGET)
    for f in done:
        label = futures[f]
        try:
            res = f.result()
        except Exception as exc:  # noqa: BLE001
            health[label] = (False, 0, f"{type(exc).__name__}: {str(exc)[:80]}")
            continue
        if label == "Hacker News":
            hn = res
            health[label] = (True, len(res), "")
            continue
        inside = [i for i in res if start_dt <= i["published"] <= end_dt + dt.timedelta(days=1)]
        items += inside
        health[label] = (True, len(inside), "")
    for f in pending:
        health[futures[f]] = (False, 0, "مهلت تمام شد")
        f.cancel()
    pool.shutdown(wait=False, cancel_futures=True)

    seen, uniq = set(), []
    for it in items:   # حذف تکراری‌های هم‌آدرس
        k = _norm_url(it["url"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    cands = _select(_build(uniq, hn, start_dt, end_dt))
    ss["_feeds_cache"] = (key, time.time(), cands, health)
    return cands, health


def shortlist(cands, per_domain=4, general=6):
    """نسخهٔ کوچک‌تر فهرست برای Groq (سقف توکن در دقیقهٔ پلن رایگان کم است)؛ شماره‌ها (id) همان می‌مانند."""
    count, out = {}, []
    for c in cands:           # cands از قبل بر اساس امتیاز مرتب است
        d = c["domain"]
        if count.get(d, 0) < (general if d == "general" else per_domain):
            count[d] = count.get(d, 0) + 1
            out.append(c)
    return out


def format_candidates(cands, snippet=200):
    lines = []
    for c in cands:
        hn = f" | HN: {c['points']} pts, {c['comments']} comments" if c["points"] else ""
        cov = f" | {c['n_sources']} independent sources" if c["n_sources"] > 1 else ""
        snip = f" | {c['desc'][:snippet]}" if c["desc"] else ""
        lines.append(f"[{c['id']}] ({c['domain']}) {c['title']} — {', '.join(c['sources'])} | {c['date']}{hn}{cov}{snip}")
    return "\n".join(lines)


def health_report():
    """برای دکمهٔ «تست منابع خبر» در تنظیمات."""
    today = today_local()
    start = today - dt.timedelta(days=3)
    cands, health = collect(start, today, refresh=True)
    ok = [k for k, v in health.items() if v[0]]
    bad = [(k, v[2]) for k, v in health.items() if not v[0]]
    empty = [k for k, v in health.items() if v[0] and v[1] == 0]
    st.markdown(f"**{len(ok)} منبع از {len(health)} پاسخ داد** · {len(cands)} کاندیدای رتبه‌بندی‌شده")
    if bad:
        st.warning("منابع ناموفق (اشکالی ندارد؛ خودکار کنار گذاشته می‌شوند):\n\n" +
                   "\n".join(f"- {k} — {e}" for k, e in bad))
    if empty:
        st.caption("بدون خبر در ۳ روز اخیر: " + "، ".join(empty))
    by = {}
    for c in cands:
        by[c["domain"]] = by.get(c["domain"], 0) + 1
    st.caption("کاندیداها به تفکیک حوزه: " + "، ".join(f"{d}: {n}" for d, n in by.items()))
    for c in cands[:8]:
        st.markdown(f"- **{c['score']}** · [{c['domain']}] {c['title']} _({', '.join(c['sources'][:2])}، {c['date']}"
                    + (f"، HN {c['points']}" if c["points"] else "") + ")_")
