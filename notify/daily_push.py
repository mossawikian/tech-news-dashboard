"""اعلان روزانهٔ ۳ تیتر برتر خبر به گوشی (Web Push)؛ در GitHub Actions اجرا می‌شود.

مراحل: جمع‌آوری خبر از همان فیدهای برنامه (بدون سهمیهٔ جست‌وجو) ← انتخاب ۳ خبر برتر از حوزه‌های متفاوت
← ترجمهٔ فارسی با یک فراخوان Gemini (اگر کلید نبود یا خطا شد، تیتر انگلیسی) ← ارسال ۳ اعلان جدا.
همین ۳ خبر (با عنوان و خلاصهٔ فارسی) در فایل push_picks.json در Gist هم ذخیره می‌شود تا برنامه آن‌ها را به بخش اخبار اضافه کند.
متغیرهای محیطی (Secrets): VAPID_PRIVATE_KEY، PUSH_SUBSCRIPTION (یک شیء JSON یا فهرستی از آن‌ها)، GEMINI_API_KEY (اختیاری)،
GIST_ID و GIST_TOKEN (اختیاری؛ همان GIST_ID و GITHUB_TOKEN برنامه؛ بدون آن‌ها اعلان کار می‌کند ولی خبرها در برنامه اضافه نمی‌شوند).
"""
import datetime as dt
import json
import os
import sys
import time
import types
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# core.feeds.collect از streamlit فقط برای کش نشست استفاده می‌کند؛ اینجا یک جانشین ساده کافی است.
_st = types.ModuleType("streamlit")
_st.session_state = {}
sys.modules.setdefault("streamlit", _st)

from core.feeds import collect  # noqa: E402
from core.feeds.sources import DOMAIN_FA  # noqa: E402
from core.tz import today_local  # noqa: E402

COUNT = 3
MODELS = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
SITE = "https://mossawikian.github.io/tech-news-dashboard/"
VAPID_SUB = os.environ.get("VAPID_EMAIL", "").strip() or "mailto:admin@example.com"
if not VAPID_SUB.startswith("mailto:"):
    VAPID_SUB = "mailto:" + VAPID_SUB


def pick_top(cands, n=COUNT):
    """n خبر برتر؛ ابتدا از حوزه‌های متفاوت (cands از قبل بر اساس امتیاز مرتب است)."""
    out, used = [], set()
    for c in cands:
        if c["domain"] not in used:
            out.append(c)
            used.add(c["domain"])
        if len(out) == n:
            return out
    for c in cands:
        if c not in out:
            out.append(c)
        if len(out) == n:
            break
    return out


def translate(cands):
    """عنوان و خلاصهٔ هر خبر را با یک فراخوان Gemini فارسی می‌کند. خروجی: فهرست (عنوان، خلاصه)؛
    اگر کلید نبود یا خطا شد، همان متن انگلیسی."""
    fallback = [(c["title"], c["desc"][:300]) for c in cands]
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY تنظیم نشده؛ متن‌ها انگلیسی می‌ماند.")
        return fallback
    items = [{"title": c["title"], "snippet": c["desc"][:400]} for c in cands]
    prompt = ("Translate these English tech news items into natural Persian (Farsi) for a Persian tech-news channel. "
              "For each item return a concise headline and a plain-language summary of 2 sentences (what happened and why "
              "it matters), based ONLY on the given title and snippet; do not add facts. Keep product and company names "
              f"in English. Return ONLY a JSON array of exactly {len(items)} objects with keys \"title\" and "
              "\"summary\", in the same order.\n" + json.dumps(items, ensure_ascii=False))
    try:   # همان کتابخانه‌ای که خود برنامه استفاده می‌کند؛ پس هر قالبی از کلید که در برنامه کار می‌کند اینجا هم کار می‌کند
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
    except Exception as exc:  # noqa: BLE001
        print(f"google-genai در دسترس نیست: {exc}")
        return fallback
    for model in MODELS:
        for attempt in (1, 2, 3):
            try:
                resp = client.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
                arr = json.loads(resp.text)
                if (isinstance(arr, list) and len(arr) == len(items)
                        and all(isinstance(x, dict) and str(x.get("title", "")).strip() for x in arr)):
                    return [(str(x["title"]).strip(), str(x.get("summary", "")).strip()) for x in arr]
                break
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                print(f"ترجمه با {model} (تلاش {attempt}) ناموفق: {type(exc).__name__}: {msg[:120]}")
                if attempt < 3 and any(w in msg for w in ("503", "UNAVAILABLE", "429", "overloaded")):
                    time.sleep(8 * attempt)     # شلوغی موقت سرور گوگل؛ کمی صبر و دوباره
                    continue
                break
    return fallback


def save_picks(top, texts, date_iso):
    """۳ خبر امروز را در Gist می‌نویسد (فایل push_picks.json) تا برنامه در بخش اخبار نشان بدهد. خطا اعلان را متوقف نمی‌کند."""
    gist_id, token = os.environ.get("GIST_ID", "").strip(), os.environ.get("GIST_TOKEN", "").strip()
    if not gist_id or not token:
        print("GIST_ID / GIST_TOKEN تنظیم نشده؛ خبرها در برنامه اضافه نمی‌شوند (اعلان‌ها بدون مشکل ارسال می‌شود).")
        return
    items = [{"title": t, "desc": d, "date": c["date"], "source": "، ".join(c["sources"][:2]),
              "domain": DOMAIN_FA.get(c["domain"], ""), "url": c["url"], "title_en": c["title"]}
             for c, (t, d) in zip(top, texts)]
    body = json.dumps({"files": {"push_picks.json": {"content": json.dumps(
        {"date": date_iso, "items": items}, ensure_ascii=False, indent=1)}}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/gists/" + gist_id, data=body, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "User-Agent": "sade-dashboard", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"{len(items)} خبر در Gist ذخیره شد (HTTP {resp.status}).")
    except Exception as exc:  # noqa: BLE001
        print(f"ذخیرهٔ خبرها در Gist ناموفق بود (اعلان‌ها ادامه می‌یابد): {type(exc).__name__}: {str(exc)[:150]}")


def get_news():
    today = today_local()
    for days in (1, 3):
        cands, _ = collect(today - dt.timedelta(days=days), today, refresh=True)
        top = pick_top(cands)
        if len(top) >= COUNT:
            return top
    return top


def subscriptions():
    raw = os.environ.get("PUSH_SUBSCRIPTION", "").strip()
    if not raw:
        sys.exit("PUSH_SUBSCRIPTION خالی است (کد اشتراک را در Secrets بگذارید).")
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def main():
    from pywebpush import WebPushException, webpush

    priv = os.environ.get("VAPID_PRIVATE_KEY", "").strip()
    if not priv:
        sys.exit("VAPID_PRIVATE_KEY خالی است.")
    subs = subscriptions()
    top = get_news()
    if not top:
        sys.exit("هیچ خبری پیدا نشد.")
    texts = translate(top)
    today_iso = today_local().isoformat()
    print(f"{len(top)} خبر انتخاب شد.")
    save_picks(top, texts, today_iso)
    failed = 0
    for i, (c, (title, _desc)) in enumerate(zip(top, texts), 1):
        dom = DOMAIN_FA.get(c["domain"], "")
        payload = {"title": f"📰 خبر {i} از {len(top)}" + (f" · {dom}" if dom else ""),
                   "body": title, "tag": f"sade-{today_iso}-{i}", "url": SITE}
        for sub in subs:
            try:
                webpush(subscription_info=sub, data=json.dumps(payload, ensure_ascii=False),
                        vapid_private_key=priv, vapid_claims={"sub": VAPID_SUB}, ttl=6 * 3600)
                print(f"ارسال شد {i}: {title[:60]}")
            except WebPushException as exc:
                failed += 1
                code = getattr(exc.response, "status_code", None)
                print(f"ارسال ناموفق ({code}): {exc}")
                if code in (404, 410):
                    print("اشتراک منقضی شده؛ صفحهٔ notify.html را دوباره باز و کد جدید را در Secrets بگذارید.")
        time.sleep(2)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
