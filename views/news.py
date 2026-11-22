"""صفحهٔ اخبار: جریان کاری + اسکریپت خبرهای تأییدشده + خروجی Word + افزودن خبر."""
import datetime as dt

import streamlit as st

from components.script_box import approved_sections
from components.workflow import render_workflow
from core.ai import suggest_news
from core.state import current_week
from core.export import DOCX_MIME, HAS_DOCX, make_docx
from core.daily import ensure_daily_news
from core.helpers import header
from core.tz import today_local


def _suggest_box():
    ss = st.session_state
    with st.expander(":material/newspaper: پیشنهاد خبرهای تازه (فقط ۳ روز تا تاریخ انتخاب‌شده)"):
        day = st.date_input("تا تاریخ", value=today_local(), key="sugg_date")
        st.caption(f"فقط خبرهای منتشرشده از {day - dt.timedelta(days=3)} تا {day} پیشنهاد می‌شود. "
                   "هر بار یک درخواست مصرف می‌شود.")
        if st.button("دریافت پیشنهاد", key="sugg_go", type="primary"):
            items, sources = suggest_news(day, existing=[n["title"] for n in ss.news_list])
            if items is not None:
                ss["suggestions"], ss["sugg_sources"] = items, sources
                if not items:
                    st.info("خبر تازه‌ای در این بازه پیدا نشد.")
        for i, it in enumerate(ss.get("suggestions", [])):
            with st.container(border=True):
                st.markdown(f"**{it['title']}**  \n{it['desc']}  \n_{it['source']} · {it['date']}_")
                if st.button(":material/add: افزودن به صف", key=f"sugg_add_{i}"):
                    ss.news_list.append({"title": it["title"], "desc": f"{it['desc']} ({it['source']}، {it['date']})",
                                         "icon": "📰", "status": "Pending", "ai": "", "research": [],
                                         "added": today_local().isoformat(), "week": current_week(),
                                         "url": it.get("url", "")})
                    ss.suggestions.pop(i)
                    st.rerun()
        if ss.get("sugg_sources"):
            st.markdown(ss["sugg_sources"])


def render():
    header("اخبار داغ هفته", "بررسی، تأیید یا ردِ خبرهای پیشنهادی")
    ensure_daily_news()
    render_workflow(show_script=True, nav=True, tabs=True)

    sections = approved_sections()
    if sections:
        if HAS_DOCX:
            st.download_button(":material/download: دانلود همهٔ اسکریپت‌ها (Word)", data=make_docx(sections),
                               file_name="scripts.docx", mime=DOCX_MIME, key="dl_word_all")
        else:
            st.info("برای خروجی Word، «python-docx» را به requirements.txt اضافه کنید.")

    _suggest_box()

    with st.form("add_news", clear_on_submit=True):
        t = st.text_input("عنوان خبر جدید")
        d = st.text_input("توضیح کوتاه")
        if st.form_submit_button("افزودن خبر") and t.strip():
            st.session_state.news_list.append(
                {"title": t.strip(), "desc": d.strip(), "icon": "📰", "status": "Pending", "ai": "", "research": [],
                                         "added": today_local().isoformat(), "week": current_week()})
            st.rerun()
