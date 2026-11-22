"""جریان کاری اخبار: کارت هر خبر، دسته‌بندی و فهرست هفته."""
import datetime as dt
import time

import streamlit as st

from components.research_box import add_version, manual_box, research_block
from components.script_box import script_box
from components.week_nav import week_nav, week_range
from core.ai import research_news
from core.helpers import H, chip, esc, fa, svg
from core.state import WEEKDAY_FA, current_week, now_str
from core.tz import today_local


def news_item(idx, item, show_script=False):
    status = item["status"]
    date_line = ""
    if status in ("Approved", "Rejected"):
        verb = "تأیید" if status == "Approved" else "رد"
        decided = item.get("decided", "")
        when = fa(decided) if decided else "ثبت نشده (یک‌بار دیگر دکمهٔ «" + verb + "» را بزنید)"
        date_line = f'<div class="muted" style="margin-top:4px">تاریخ {verb}: {when}</div>'
    push_chip = '<span class="chip chip-push">🔔 پیشنهاد اعلان</span>' if item.get("push") else ""
    with st.container(key=f"newscard_{idx}_{status}"):
        H('<div class="news-head">'
          f'<div class="avatar">{svg("news", 22)}</div>'
          f'<div><div class="news-title">{esc(item["title"])} {chip(status)}{push_chip}</div>'
          f'<div class="news-desc">{esc(item["desc"])}</div>{date_line}</div></div>')

        with st.container(key=f"keep_news_{idx}"):
            b_ok, b_no, b_ai = st.columns(3)
            ok = b_ok.button(":material/check: تأیید", key=f"app_{idx}", type="primary")
            no = b_no.button(":material/close: رد", key=f"rej_{idx}")
            ai = b_ai.button(":material/search: بررسی" if not item.get("research") else ":material/folder_open: تحقیق ثبت‌شده", key=f"rev_{idx}")
        if ok:
            item["status"], item["decided"] = "Approved", now_str()
            st.rerun()
        if no:
            item["status"], item["decided"] = "Rejected", now_str()
            st.rerun()
        has_research = bool(item.get("research"))
        redo_key = f"_redo_{idx}"
        if ai and has_research:
            # تحقیق قبلاً انجام شده؛ بدون تأیید، درخواست تازه‌ای مصرف نمی‌شود
            st.session_state[redo_key] = True
        if has_research and st.session_state.get(redo_key):
            st.info("برای این خبر قبلاً تحقیق انجام شده و نسخه‌های آن پایین‌تر هست. "
                    "بررسی مجدد یک درخواست جدید از سهمیه مصرف می‌کند.")
            c_yes, c_no = st.columns(2)
            go = c_yes.button(":material/replay: بله، نسخهٔ جدید بساز", key=f"redo_yes_{idx}", type="primary")
            if c_no.button("انصراف", key=f"redo_no_{idx}"):
                st.session_state[redo_key] = False
                st.rerun()
            if not go:
                ai = False
            else:
                st.session_state[redo_key] = False
                ai = True
        if ai:
            t0 = time.time()
            text = research_news(item["title"], item["desc"])
            if text:
                add_version(item, "بررسی مجدد" if has_research else "", text, round(time.time() - t0, 1))
                if item["status"] == "Pending":
                    item["status"] = "Reviewing"
                st.rerun()
        manual_box(idx, item)
        research_block(idx, item)

        if show_script and item["status"] == "Approved":
            script_box(idx, item)


def _day_label(iso):
    try:
        d = dt.date.fromisoformat(iso)
        return f"{svg('calendar', 16)} {WEEKDAY_FA[d.weekday()]} {fa(iso)}" + (" · امروز" if d == today_local() else "")
    except ValueError:
        return "—"


def _indices(week):
    """شمارهٔ خبرهای یک هفته؛ جدیدترین روز اول، و خبرهای روزهای قبل پایین‌تر."""
    news = st.session_state.news_list
    idxs = [i for i, n in enumerate(news) if n.get("week") == week]
    return sorted(idxs, key=lambda i: news[i].get("added", ""), reverse=True)  # مرتب‌سازی پایدار است


def _render_items(idxs, show_script):
    news, last_day = st.session_state.news_list, None
    for i in idxs:
        day = news[i].get("added", "")
        if day != last_day:
            H(f'<div class="day-label">{_day_label(day)}</div>')
            last_day = day
        news_item(i, news[i], show_script)


TAB_DEFS = [("done", "check_circle", "تأیید شده", lambda s: s == "Approved"),
            ("rej", "cancel", "رد شده", lambda s: s == "Rejected"),
            ("wait", "hourglass_empty", "در انتظار", lambda s: s not in ("Approved", "Rejected"))]


def render_workflow(show_script=False, nav=False, tabs=False):
    """جریان کاری. با nav=True بالای کارت کلید «هفتهٔ قبل / هفتهٔ بعد» هست و هفتهٔ جاری پیش‌فرض است.
    با tabs=True خبرها در سه دستهٔ «تأیید شده / رد شده / در انتظار» با شمارنده می‌آیند (خبرِ «در حال بررسی» هم
    در انتظار است؛ اگر بعد از بررسی رد شود، به «رد شده» می‌رود). انتخاب دسته با کلید ثابت حفظ می‌شود."""
    news = st.session_state.news_list
    with st.container(border=True):
        week, off = week_nav(week_range) if nav else (current_week(), 0)
        idxs = _indices(week)
        week_news = [news[i] for i in idxs]
        total = len(week_news)
        count = lambda s: sum(1 for n in week_news if n["status"] == s)  # noqa: E731
        done = count("Approved")
        pct = round(done / total * 100) if total else 0
        if not nav:
            H('<div class="card-title">اخبار هفتهٔ جاری</div>')
        waiting = total - done - count("Rejected")
        H('<div class="sum-row"><div>'
          f'<div class="sum-t">{fa(done)} از {fa(total)} خبر تأیید شده</div>'
          f'<div class="muted">{fa(count("Rejected"))} رد شده · {fa(waiting)} در انتظار</div></div>'
          f'<div class="progress"><div style="width:{pct}%"></div></div></div>')
        if not tabs:
            if not idxs:
                st.caption("خبری برای این هفته نیست.")
            _render_items(idxs, show_script)
            return
        by_key = {k: [i for i in idxs if m(news[i]["status"])] for k, _ic, _lb, m in TAB_DEFS}
        labels = {k: f":material/{ic}: {lb}  ·  {fa(len(by_key[k]))}" for k, ic, lb, _m in TAB_DEFS}
        keys = [d[0] for d in TAB_DEFS]
        if hasattr(st, "segmented_control"):
            pick = st.segmented_control("دسته", keys, default="done", key="news_tab",
                                        format_func=lambda k: labels[k], label_visibility="collapsed") or "done"
        else:  # نسخه‌های قدیمی‌تر Streamlit
            pick = st.radio("دسته", keys, key="news_tab", horizontal=True,
                            format_func=lambda k: labels[k], label_visibility="collapsed")
        if not by_key[pick]:
            st.caption("خبری در این دسته نیست.")
        _render_items(by_key[pick], show_script)
