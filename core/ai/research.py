"""تحقیق: Groq (انگلیسی) جست‌وجو می‌کند ← Gemini فارسی می‌نویسد؛ بررسی خبر، نظریه‌ها و سناریوی دیپ‌دایو."""
import datetime as dt

import streamlit as st

from core import groq_client
from core.ai.config import SEARCH_PRIORITY
from core.ai.gemini import ask_ai
from core.ai.prompts_deep import DEEP_FORMAT, DEEP_STYLE_OVERRIDE, GROQ_DEEP_PROMPT
from core.ai.prompts_news import (CONSPIRACY_FORMAT, FROM_SOURCES_RULES, GROQ_CONSPIRACY_PROMPT, GROQ_NEWS_PROMPT,
                                  NEWS_PROMPT, NEWS_RULES, NEWS_STRUCTURE, STYLE_SAMPLE)
from core.groq_client import GroqError
from core.tz import today_local


def _materials(text, srcs, max_text=14000, max_snippets=6000):
    """متن یافته‌ها + منابع شماره‌دار، برای دادن به Gemini (با سقف طول)."""
    parts = ["[یافته‌های جست‌وجو]\n" + text[:max_text]]
    lines, used = [], 0
    for i, (url, meta) in enumerate(srcs.items(), 1):
        line = f"[{i}] {meta['title']} — {url}\n    {meta['content'][:500]}"
        if used + len(line) > max_snippets:
            break
        lines.append(line)
        used += len(line)
    if lines:
        parts.append("[منابع شماره‌دار]\n" + "\n".join(lines))
    return "\n\n".join(parts)


def _groq_cached(prompt):
    """نتیجهٔ جست‌وجوی Groq برای یک پرامپت در همین نشست نگه داشته می‌شود؛ اگر Gemini خطا داد و دوباره
    امتحان کردید، Groq دوباره صدا زده نمی‌شود (صرفه‌جویی در سهمیه)."""
    cache = st.session_state.setdefault("_groq_cache", {})
    if prompt in cache:
        return cache[prompt]
    res = groq_client.search(prompt)
    if len(cache) >= 6:
        cache.pop(next(iter(cache)))
    cache[prompt] = res
    return res


def _show_raw(gtext, srcs):
    with st.expander(":material/description: یافته‌های خام جست‌وجو (انگلیسی) — چون Gemini پاسخ نداد", expanded=True):
        st.markdown(gtext)
        if srcs:
            st.markdown("**منابع:**\n" + "\n".join(
                f"{i}. [{m['title']}]({u})" for i, (u, m) in enumerate(srcs.items(), 1)))
        st.caption("دوباره بزنید؛ جست‌وجوی Groq تکرار نمی‌شود و فقط نوشتن فارسی با Gemini دوباره امتحان می‌شود.")


def _groq_note(exc):
    st.info(f"Groq در دسترس نبود ({str(exc)[:120]}). با روش جایگزین (Gemini) ادامه می‌دهیم.")


def _hybrid(groq_prompt, gemini_body, fallback_prompt, box=None, gemini_first=False):
    """Groq جست‌وجو می‌کند → Gemini (بدون جست‌وجو) از روی مواد می‌نویسد، ارجاع‌های [n] به لینک تبدیل می‌شوند.
    اگر Groq نبود یا خطا داد، fallback_prompt با Gemini (و جست‌وجوی خودش)."""
    groq_ok = groq_client.available()
    if gemini_first and groq_ok:
        # اول جست‌وجوی خود Gemini (اگر سهمیهٔ جست‌وجو برگشته باشد)؛ اگر نشد، ادامه با Groq
        out = ask_ai(fallback_prompt, box, need_search=True, quiet=True)
        if out:
            return out
        st.session_state["_last_ai_call"] = 0   # درخواست بعدی به‌خاطر فاصلهٔ حداقل رد نشود
    if groq_ok:
        ph = st.empty()
        ph.caption(":material/search: در حال جست‌وجوی منابع...")
        try:
            gtext, srcs = _groq_cached(groq_prompt)
        except GroqError as exc:
            ph.empty()
            _groq_note(exc)
        else:
            ph.empty()
            prompt = (FROM_SOURCES_RULES.format(today=today_local().isoformat()) + gemini_body
                      + "\n\n" + _materials(gtext, srcs))
            out = ask_ai(prompt, box, ext_sources=[(u, m["title"]) for u, m in srcs.items()])
            if out and st.session_state.get("active_model"):
                st.session_state["active_model"] += " + منابع Groq"
            if not out:
                _show_raw(gtext, srcs)
            return out
    return ask_ai(fallback_prompt, box)


def research_news(title, desc, box=None):
    """تحقیق یک خبر (قالب ۶ بخشی، کوتاه و مارک‌داون، با بخش مفصل نظریه‌های توطئه)."""
    return _hybrid(GROQ_NEWS_PROMPT.format(title=title, desc=desc),
                   STYLE_SAMPLE + NEWS_STRUCTURE.format(title=title, desc=desc),
                   NEWS_PROMPT.format(title=title, desc=desc), box,
                   gemini_first=(SEARCH_PRIORITY == "gemini"))


def research_conspiracies(title, desc, box=None):
    """بررسی عمیق‌تر فقط نظریه‌ها و شایعات توطئه‌آمیز یک خبر (با یک جست‌وجوی جداگانهٔ Groq)."""
    return _hybrid(GROQ_CONSPIRACY_PROMPT.format(title=title, desc=desc),
                   CONSPIRACY_FORMAT.format(title=title, desc=desc),
                   NEWS_RULES + CONSPIRACY_FORMAT.format(title=title, desc=desc), box)


def research_deep(title, box=None):
    """سناریوی دیپ‌دایو: Groq انگلیسی جست‌وجو می‌کند، Gemini فارسی (۸ بخش + نریشن کامل) می‌نویسد."""
    body = DEEP_STYLE_OVERRIDE + DEEP_FORMAT.format(title=title)
    return _hybrid(GROQ_DEEP_PROMPT.format(title=title), body,
                   NEWS_RULES + DEEP_FORMAT.format(title=title), box)
