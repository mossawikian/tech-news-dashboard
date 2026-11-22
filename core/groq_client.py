"""جست‌وجوی وب با Groq (مدل openai/gpt-oss با ابزار browser_search) — بدون کتابخانهٔ اضافه (فقط urllib).
(سیستم‌های groq/compound و compound-mini طبق اعلام Groq از ۲۱ سپتامبر ۲۰۲۶ از رده خارج شده‌اند.)

Groq فقط «جست‌وجو و جمع‌آوری منبع» را انجام می‌دهد؛ نوشتن متن فارسی با Gemini است.
کلید در Streamlit Secrets با نام GROQ_API_KEY گذاشته می‌شود. اگر کلید نباشد یا Groq خطا بدهد،
برنامه خودکار به مسیر قبلی (Gemini) برمی‌گردد.
"""
import json
import time
import urllib.error
import urllib.request

import streamlit as st

URL = "https://api.groq.com/openai/v1/chat/completions"
MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]   # هر دو ابزار browser_search دارند؛ اگر اولی خطا داد، دومی
MAX_OUT_TOKENS = 3500   # سقف خروجی؛ پلن رایگان سقف توکن در دقیقه دارد
TIMEOUT = 120
MIN_GAP = 90            # حداقل فاصلهٔ (ثانیه) بین دو جست‌وجوی Groq؛ هر جست‌وجو چند هزار توکن مصرف می‌کند و سقف دقیقه‌ای پلن رایگان کم است
SYSTEM = ("You are a careful web research assistant. Use web search. Report only what you actually found in "
          "sources; never invent facts, dates or links. Always name the source of each claim.")


class GroqError(Exception):
    def __init__(self, msg, code=0, retry_after=None):
        super().__init__(msg)
        self.code = code
        self.retry_after = retry_after


@st.cache_resource
def _state():
    return {"until": 0.0, "why": ""}


def groq_key():
    try:
        return str(st.secrets.get("GROQ_API_KEY", "") or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def available():
    """کلید هست و Groq موقتاً (به‌خاطر سقف) کنار گذاشته نشده است."""
    return bool(groq_key()) and time.time() >= _state()["until"]


def blocked_info():
    s = _state()
    return (s["why"], max(int(s["until"] - time.time()), 0)) if time.time() < s["until"] else ("", 0)


def _post(body, key):
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "sade-dashboard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500].replace("\n", " ")
        raise GroqError(f"HTTP {e.code}: {detail}", e.code, e.headers.get("retry-after")) from e
    except Exception as e:  # noqa: BLE001  (شبکه، timeout، JSON خراب)
        raise GroqError(f"{type(e).__name__}: {str(e)[:200]}") from e


def _walk(o, out, depth=0):
    """هر دیکشنری‌ای که url داشته باشد را (از دادهٔ ساخت‌یافتهٔ ابزار، نه از متن مدل) جمع می‌کند."""
    if depth > 8:
        return
    if isinstance(o, dict):
        url = o.get("url")
        if isinstance(url, str) and url.startswith("http"):
            title = o.get("title") or o.get("name") or url
            content = o.get("content") or o.get("text") or o.get("snippet") or o.get("description") or ""
            out.setdefault(url, {"title": str(title).strip()[:200], "content": str(content).strip()})
        for v in o.values():
            _walk(v, out, depth + 1)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out, depth + 1)


def _sources(message):
    """لینک‌ها و خلاصهٔ محتوای نتایج جست‌وجو؛ {url: {title, content}}. فقط از دادهٔ ابزار/ارجاع‌ها، نه از متن مدل."""
    out = {}
    for key in ("executed_tools", "annotations", "citations"):
        _walk(message.get(key), out)
    return out


def _block(exc):
    msg = str(exc).lower()
    if exc.code == 429:
        if "per day" in msg or "tokens per day" in msg or "requests per day" in msg:
            secs = 3600
        else:
            try:
                secs = min(float(exc.retry_after), 300)
            except (TypeError, ValueError):
                secs = 60
        _state().update(until=time.time() + secs, why="سقف Groq")
    elif exc.code in (401, 403):
        _state().update(until=time.time() + 3600, why="کلید Groq نامعتبر یا بدون دسترسی")


def _wait_gap():
    """اگر آخرین جست‌وجوی Groq کمتر از MIN_GAP ثانیه پیش بوده، صبر می‌کند (برای نخوردن به سقف دقیقه‌ای)."""
    gap = MIN_GAP - (time.time() - _state().get("last", 0))
    if gap > 0:
        ph = st.empty()
        ph.caption(f":material/hourglass_top: برای رعایت سقف Groq، {int(gap) + 1} ثانیه صبر می‌کنیم...")
        time.sleep(gap)
        ph.empty()


def search(prompt):
    """یک جست‌وجو. خروجی: (متن یافته‌ها، {url: {title, content}}). در خطا GroqError."""
    try:
        return _search(prompt)
    finally:
        _state()["last"] = time.time()    # زمان پایان؛ فاصله از همین لحظه حساب می‌شود


def _search(prompt):
    key = groq_key()
    if not key:
        raise GroqError("GROQ_API_KEY تنظیم نشده است")
    if time.time() < _state()["until"]:
        raise GroqError(f"Groq موقتاً کنار گذاشته شده ({_state()['why']})")
    _wait_gap()
    last = None
    for model in MODELS:
        body = {"model": model, "temperature": 0.3, "max_completion_tokens": MAX_OUT_TOKENS,
                "tool_choice": "required", "tools": [{"type": "browser_search"}],
                "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
        try:
            data = _post(body, key)
            msg = (data.get("choices") or [{}])[0].get("message") or {}
            text = (msg.get("content") or "").strip()
            if not text:
                raise GroqError("پاسخ خالی از Groq")
            try:
                _state()["raw"] = json.dumps(msg.get("executed_tools"), ensure_ascii=False)[:1200]
            except Exception:  # noqa: BLE001
                _state()["raw"] = ""
            return text, _sources(msg)
        except GroqError as e:
            last = e
            if e.code in (0, 400, 404, 413, 429, 500, 502, 503):
                continue      # مدل بعدی
            break
    _block(last)
    raise last


PICK_SYSTEM = ("You are a precise technology news editor. Follow the requested output format exactly. "
               "Use only the information given; never invent facts, dates or links.")


def chat(prompt, max_tokens=2500):
    """گفت‌وگوی ساده بدون جست‌وجو (برای انتخاب خبر از فهرست آماده). خروجی: متن. در خطا GroqError."""
    key = groq_key()
    if not key:
        raise GroqError("GROQ_API_KEY تنظیم نشده است")
    if time.time() < _state()["until"]:
        raise GroqError(f"Groq موقتاً کنار گذاشته شده ({_state()['why']})")
    last = None
    for model in MODELS:
        body = {"model": model, "temperature": 0.2, "max_completion_tokens": max_tokens,
                "messages": [{"role": "system", "content": PICK_SYSTEM}, {"role": "user", "content": prompt}]}
        try:
            data = _post(body, key)
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
            if not text:
                raise GroqError("پاسخ خالی از Groq")
            return text
        except GroqError as e:
            last = e
            if e.code in (0, 400, 404, 413, 429, 500, 502, 503):
                continue
            break
    _block(last)
    raise last


def ping():
    """تست برای صفحهٔ تنظیمات: (True/False، توضیح). یک جست‌وجوی واقعی و کوچک می‌زند و تعداد لینک‌ها را می‌گوید."""
    if not groq_key():
        return False, "GROQ_API_KEY در Secrets نیست"
    try:
        text, srcs = search("List 2 recent technology news headlines from the last few days, with source names.")
    except GroqError as e:
        return False, str(e)[:500]
    info = f"پاسخ {len(text)} نویسه، {len(srcs)} لینک منبع از ابزار"
    if not srcs:
        info += " | ساختار executed_tools: " + (_state().get("raw") or "(خالی)")[:600]
    return True, info
