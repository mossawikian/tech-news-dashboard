"""پیشنهاد هفتگی موضوع دیپ‌دایو: معیارها، نمره‌دهی، پرامپت‌ها و انتخاب."""
import datetime as dt
import re

import streamlit as st

from core import groq_client
from core.ai.gemini import ask_ai
from core.ai.research import _groq_cached, _groq_note, _materials
from core.ai.text_utils import _similar
from core.groq_client import GroqError
from core.tz import today_local


# ── پیشنهاد هفتگی موضوع دیپ‌دایو: نمره‌دهی شش‌معیاره (Groq انگلیسی جست‌وجو می‌کند ← Gemini فارسی می‌نویسد) ──
# وزن‌ها و حدها را اینجا عوض کنید. نمرهٔ کل = ۲×قلاب + ۲×مستندات + داستان + چرا الان + افسانه + فهم‌پذیری (حداکثر ۴۰)
DEEP_WEIGHTS = (2, 2, 1, 1, 1, 1)
DEEP_MIN_HOOK = 2          # موضوع با نمرهٔ قلاب کمتر از این کنار گذاشته می‌شود (فقط ۱ حذف می‌شود)
DEEP_MIN_DOCS = 2          # موضوع با نمرهٔ مستندات کمتر از این کنار گذاشته می‌شود (فقط ۱ حذف می‌شود)
DEEP_DEFAULT_SCORES = (3, 3, 3, 3, 3, 3)   # اگر مدل نمره‌ها را درست ننوشت، موضوع حذف نمی‌شود و این نمرهٔ متوسط را می‌گیرد
DEEP_TYPES = ("person", "forgotten", "debate", "now")   # ترکیب هر هفته: از هر نوع یکی (اگر باشد)
DEEP_TYPE_FA = {"person": "داستان آدم", "forgotten": "فناوری فراموش‌شده یا مرموز",
                "debate": "بحث و افسانه", "now": "موضوع داغ روز"}

GROQ_DEEP_IDEAS_PROMPT = (
    "Use web search to find {n} strong topics for an 8-10 minute documentary-style tech video (a 'deep dive') "
    "for a general, low-literacy audience. Today is {today}.\n"
    "Each topic must be an ENDURING story with a reason to watch NOW, not just this week's news, in one of "
    "these areas: biology/biotech, machines of every kind, artificial intelligence, space, weapons/defense tech, "
    "software/internet/cybersecurity, energy/materials, chips/computing. Spread them across DIFFERENT areas. "
    "Do not center on Elon Musk companies.\n"
    "Classify each topic as ONE type: person (a human story), forgotten (a forgotten, misunderstood or mysterious "
    "technology), debate (real controversy, myths or conspiracy theories that can be checked against evidence), "
    "now (a hot topic of the moment explained deeply). Aim for a mix of all four types.\n"
    "Score each topic 1-5 on SIX criteria, honestly (use the whole range, do not give everything 5): "
    "H = hook (one sentence grips and surprises); "
    "D = documentation (5 = at least three independent reliable sources including a primary source such as a paper, "
    "archive or interview, and you actually found them with web search; 1 = thin or only one source); "
    "S = story (people, conflict, turning point or mystery); "
    "W = why now (ties to a current news item, anniversary or ongoing public debate); "
    "M = myths (a popular claim or conspiracy theory with checkable evidence for and against); "
    "C = clarity (can be told with everyday analogies to a low-literacy audience).\n{avoid}"
    "Output EXACTLY {n} lines, nothing else, in this format:\n"
    "English title | one sentence on the surprising hook | H,D,S,W,M,C (six digits) | type | URL of one reliable source\n"
    "Never invent facts, scores based on sources you did not find, or URLs."
)
DEEP_IDEAS_FROM_SOURCES = (
    "تو ویراستار یک کانال تکنولوژی فارسی‌زبان هستی. مواد جست‌وجوی زیر شامل چند موضوع پیشنهادی برای ویدیوی دیپ‌دایو "
    "(مینی‌مستند ۸ تا ۱۰ دقیقه‌ای برای مخاطب عام و کم‌سواد) است. همهٔ آن‌ها را (حداکثر {n} موضوع) به فارسی روان "
    "بازنویسی کن. فقط بر اساس همین مواد؛ چیزی از خودت نساز. نمره‌ها (شش رقم) و نوع (person/forgotten/debate/now) را "
    "عیناً از مواد کپی کن و تغییر نده. فقط خط‌ها، بدون متن دیگر، با این قالب:\n"
    "عنوان فارسی کوتاه و جذاب | یک جمله: قلاب شگفت‌انگیزش چیست | H,D,S,W,M,C | type\n"
    "{avoid}\n"
)


def _digits(text):
    return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))


def deep_total(scores):
    return sum(w * x for w, x in zip(DEEP_WEIGHTS, scores))


def _find_scores(parts):
    """شش نمرهٔ ۱ تا ۵ را در هر ستونی (از ستون سوم به بعد) پیدا می‌کند؛ قالب‌های «4,3,5,2,3,4»، «[4 3 5 2 3 4]»،
    «H4 D3 S5 W2 M3 C4» همه پذیرفته می‌شوند. اگر نبود None."""
    for part in parts[2:]:
        digits = re.findall(r"[0-9]", re.sub(r"https?://\S+", "", part))
        if len(digits) == 6 and all(1 <= int(d) <= 5 for d in digits):
            return tuple(int(d) for d in digits)
    return None


def _parse_deep_ideas(text, existing, n, diag=None):
    """خطوط «عنوان | قلاب | شش نمره | نوع» را می‌خواند؛ تکراری و موضوع بسیار کم‌مستند حذف می‌شود؛ مرتب بر اساس نمرهٔ کل.
    قالب نمره و نوع سخت‌گیرانه نیست (اگر خراب بود، نمرهٔ متوسط می‌گیرد). diag (dict) شمارش دلیل حذف‌ها را می‌گیرد."""
    diag = diag if diag is not None else {}
    diag.update(lines=0, bad_format=0, no_scores=0, low=0, dup=0)
    if not text:
        return []
    body = text.partition("\n\n---\n")[0]
    out = []
    for line in _digits(body).splitlines():
        line = re.sub(r"^\s*(?:[-*•#]+|\d+[.)])\s*", "", line)
        if "|" not in line:
            continue
        parts = [x.strip(" *\t[]") for x in line.split("|")]
        if len(parts) < 2 or len(parts[0]) < 4:
            diag["bad_format"] += 1
            continue
        diag["lines"] += 1
        scores = _find_scores(parts)
        if scores is None:
            diag["no_scores"] += 1
            scores = DEEP_DEFAULT_SCORES
        elif scores[0] < DEEP_MIN_HOOK or scores[1] < DEEP_MIN_DOCS:
            diag["low"] += 1
            continue
        typ = next((p.lower() for p in parts[2:] if p.lower() in DEEP_TYPES), "")
        title, why = parts[0], parts[1]
        if any(_similar(title, e) for e in list(existing) + [o["title"] for o in out]):
            diag["dup"] += 1
            continue
        out.append({"title": title, "why": why, "scores": list(scores), "total": deep_total(scores), "type": typ})
    out.sort(key=lambda x: -x["total"])
    return out[:n]


def pick_top(items, k=4):
    """k موضوع برتر با ترکیب نوع‌ها (از هر نوع بهترینِ آن، اگر باشد) + بقیه بر اساس نمره. خروجی: (برگزیده‌ها، ذخیره)."""
    chosen = []
    for typ in DEEP_TYPES:
        best = next((i for i in items if i["type"] == typ and i not in chosen), None)
        if best and len(chosen) < k:
            chosen.append(best)
    for i in items:
        if len(chosen) >= k:
            break
        if i not in chosen:
            chosen.append(i)
    chosen.sort(key=lambda x: -x["total"])
    rest = [i for i in items if i not in chosen]
    return chosen, rest


def suggest_deep_topics(existing=(), n=8):
    """n موضوع نمره‌دار دیپ‌دایو (مرتب بر اساس نمره). خروجی: فهرست یا None در صورت خطا."""
    today = today_local().isoformat()
    avoid_en = ("ALREADY USED or REJECTED topics (do not repeat the same subjects): " + "; ".join(list(existing)[:40]) + "\n"
                if existing else "")
    avoid_fa = ("این موضوع‌ها قبلاً بوده یا رد شده‌اند و تکرارشان نکن: " + "؛ ".join(list(existing)[:40])) if existing else ""
    box = st.empty()
    text = None
    if groq_client.available():
        try:
            gtext, srcs = _groq_cached(GROQ_DEEP_IDEAS_PROMPT.format(n=n, today=today, avoid=avoid_en))
            if not srcs:
                raise GroqError("Groq لینک منبعی برنگرداند")
            prompt = DEEP_IDEAS_FROM_SOURCES.format(n=n, avoid=avoid_fa) + _materials(gtext, srcs)
            text = ask_ai(prompt, box, ext_sources=[(u, m["title"]) for u, m in srcs.items()])
            if not text:
                text = gtext
                st.caption("Gemini در دسترس نبود؛ پیشنهاد Groq (به انگلیسی) استفاده شد.")
        except GroqError as exc:
            _groq_note(exc)
    if not text:
        text = ask_ai(DEEP_IDEAS_FROM_SOURCES.format(n=n, avoid=avoid_fa)
                      + "\nبا جست‌وجوی وب موضوع‌های ماندگار و مستند پیدا کن (نه خبر همین هفته) و برای هر کدام "
                        "شش نمرهٔ ۱ تا ۵ سخت‌گیرانه بده: قلاب، مستندات، داستان، چرا الان، افسانه، فهم‌پذیری.",
                      box, need_search=True)
    box.empty()
    if not text:
        return None
    diag = {}
    items = _parse_deep_ideas(text, existing, n, diag)
    st.session_state["_deep_diag"] = {**diag, "raw": text[:1500]}   # برای نمایش دلیل وقتی چیزی پیدا نشد
    return items
