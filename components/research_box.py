"""نسخه‌های تحقیق هر خبر، پرسش تکمیلی، تحقیق نظریه‌های توطئه و حالت دستی (بدون API)."""
import time

import streamlit as st

from core.ai import NEWS_STRUCTURE, STYLE_SAMPLE, ask_ai, build_followup_prompt, research_conspiracies
from core.helpers import H, fa
from core.state import ARCHIVE_DAYS, days_left, now_str, save_data


# رنگ هر نسخه به ترتیب (با CSS هم‌رنگ است: core/style/news.py)
VER_COLORS = ["🔵", "🟣", "🟠", "🟢", "🟡", "🔴"]


def add_version(item, question, text, secs=None):
    """هر تحقیق یا پاسخ تازه، یک نسخهٔ جدید زیر نسخه‌های قبلی می‌شود (هیچ نسخه‌ای بازنویسی نمی‌شود)."""
    versions = item.setdefault("research", [])
    versions.append({"v": len(versions) + 1, "ts": now_str(), "q": question, "text": text,
                     "model": st.session_state.get("active_model", ""), "secs": secs})
    save_data()


def research_block(idx, item):
    """نسخه‌های تحقیق + کادر پرسش تکمیلی از Gemini."""
    versions = item.get("research") or []
    if not versions:
        return
    st.caption(f":material/inventory_2: آرشیف: {fa(len(versions))} نسخه · تا {fa(days_left(item))} روز دیگر نگه‌داری می‌شود "
               f"(پس از {fa(ARCHIVE_DAYS)} روز بدون فعالیت، خودکار حذف می‌شود)")
    for i, v in enumerate(versions):
        title = "بررسی اولیه" if not v.get("q") else v["q"][:60] + ("…" if len(v["q"]) > 60 else "")
        c = i % len(VER_COLORS)   # هر نسخه رنگ خودش را دارد تا معلوم باشد متن هر پنجره کجا تمام می‌شود
        with st.container(key=f"ver_{idx}_{i}_clr{c}x"):
            with st.expander(f"{VER_COLORS[c]} نسخهٔ {fa(v['v'])} — {title} · {fa(v['ts'])}", expanded=False):
                st.markdown(v["text"])
                info = " · ".join(x for x in (v.get("model"), f"{fa(v['secs'])} ثانیه" if v.get("secs") else "") if x)
                if info:
                    st.caption(info)
                H(f'<div class="ver-end">{VER_COLORS[c]} پایان نسخهٔ {fa(v["v"])}</div>')

    if st.button(":material/travel_explore: بررسی عمیق‌تر نظریه‌های توطئه", key=f"cons_{idx}",
                 help="یک جست‌وجوی جداگانه فقط برای نظریه‌ها و شایعات؛ نتیجه به‌عنوان نسخهٔ جدید ذخیره می‌شود"):
        t0 = time.time()
        text = research_conspiracies(item["title"], item["desc"])
        if text:
            add_version(item, "نظریه‌های توطئه (بررسی عمیق)", text, round(time.time() - t0, 1))
            st.rerun()

    with st.expander(":material/forum: سؤال یا درخواست اطلاعات بیشتر"):
        with st.form(f"chat_{idx}", clear_on_submit=True):
            q = st.text_area("سؤال شما از Gemini", height=90,
                             placeholder="مثلاً: آمار دقیق‌تر بده / منبع این ادعا چیست؟ / از دید منتقدان بنویس")
            sent = st.form_submit_button("ارسال", type="primary")
        if sent and q.strip():
            t0 = time.time()
            text = ask_ai(build_followup_prompt(item, q.strip()))
            if text:
                add_version(item, q.strip(), text, round(time.time() - t0, 1))
                st.rerun()


MANUAL_RULES = (
    "تو نویسندهٔ متن یک کانال تکنولوژی فارسی‌زبان هستی. با جست‌وجوی وب تحقیق کن و ماجرای خبر را کامل، دقیق و "
    "به فارسی ساده و روان بنویس. اعداد، تاریخ‌ها و نام‌ها را بیاور و هر ادعای مهم را با نام منبعش همراه کن. "
    "در پایان بخشی به نام «منابع» با لینک واقعی صفحه‌هایی که واقعاً خوانده‌ای بیاور؛ هرگز لینک نساز. "
    "اگر دربارهٔ درستی چیزی مطمئن نیستی، صریحاً بگو.\n\n"
)


def manual_prompt(item):
    """همان قالب اپ، ولی برای چسباندن در چت Gemini (لینک منابع را خود چت می‌نویسد)."""
    return MANUAL_RULES + STYLE_SAMPLE + NEWS_STRUCTURE.format(title=item["title"], desc=item["desc"])


def _save_manual(idx):
    ss = st.session_state
    text = (ss.get(f"manual_{idx}") or "").strip()
    if len(text) < 80:
        ss[f"manual_err_{idx}"] = True
        return
    item = ss.news_list[idx]
    add_version(item, "نسخهٔ دستی (چت Gemini)", text, None)
    item["research"][-1]["model"] = "Gemini چت (دستی)"
    if item["status"] == "Pending":
        item["status"] = "Reviewing"
    ss[f"manual_err_{idx}"] = False
    ss[f"manual_{idx}"] = ""


def manual_box(idx, item):
    """حالت دستی بدون API: پرامپت آماده را در چت Gemini بزنید و جواب را اینجا بچسبانید (بدون هیچ سهمیهٔ API)."""
    with st.expander(":material/content_paste: بدون API: پرامپت آماده + چسباندن جواب"):
        st.caption("۱) متن زیر را کپی کنید (آیکن کپی بالا-گوشهٔ کادر) · ۲) در چت Gemini بچسبانید "
                   "· ۳) جواب را کپی کرده و پایین بچسبانید و ذخیره کنید.")
        st.code(manual_prompt(item), language=None)
        st.text_area("جوابِ چت Gemini را اینجا بچسبانید", height=200, key=f"manual_{idx}")
        if st.session_state.get(f"manual_err_{idx}"):
            st.warning("متن خیلی کوتاه است؛ جواب کامل را بچسبانید.")
        st.button(":material/save: ذخیره به‌عنوان نسخهٔ جدید", key=f"manual_save_{idx}", type="primary",
                  on_click=_save_manual, args=(idx,))
