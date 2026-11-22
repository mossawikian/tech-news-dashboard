"""کارت «تقویم محتوا»."""
import calendar
import datetime as dt

import streamlit as st

from core.helpers import MONTHS_FA, WEEKDAYS_FA, H, esc, fa
from core.tz import today_local


def render_calendar():
    ss = st.session_state
    y, m = ss.cal_year, ss.cal_month
    today_iso = today_local().isoformat()
    with st.container(border=True):
        H('<div class="card-title">تقویم محتوا</div>')
        with st.container(key="keep_cal_nav"):
            c_prev, c_mid, c_next = st.columns(3)
            prev = c_prev.button("→", key="cal_prev")
            c_mid.markdown(f'<div style="text-align:center;font-weight:700;padding-top:.4rem">'
                           f'{MONTHS_FA[m - 1]} {fa(y)}</div>', unsafe_allow_html=True)
            nxt = c_next.button("←", key="cal_next")
        if prev:
            ss.cal_year, ss.cal_month = (y - 1, 12) if m == 1 else (y, m - 1)
            st.rerun()
        if nxt:
            ss.cal_year, ss.cal_month = (y + 1, 1) if m == 12 else (y, m + 1)
            st.rerun()

        cells = []
        for week in calendar.Calendar(firstweekday=5).monthdayscalendar(y, m):
            for d in week:
                if d == 0:
                    cells.append('<div class="cell"></div>')
                    continue
                iso = f"{y:04d}-{m:02d}-{d:02d}"
                evs = [e for e in ss.events if e["date"] == iso]
                cls = "cell" + (" today" if iso == today_iso else "") + (" has" if evs else "")
                tip = esc(" | ".join(e["title"] for e in evs))
                cells.append(f'<div class="{cls}" title="{tip}">{fa(d)}{"<i></i>" if evs else ""}</div>')
        head = "".join(f'<div class="wd">{d}</div>' for d in WEEKDAYS_FA)
        H(f'<div class="cal-grid">{head}{"".join(cells)}</div>')

        month_prefix = f"{y:04d}-{m:02d}"
        month_events = [e for e in ss.events if e["date"].startswith(month_prefix)]
        for i, ev in enumerate(sorted(month_events, key=lambda e: e["date"])):
            if st.button(f":material/delete: {fa(ev['date'])} — {ev['title']}", key=f"del_{i}"):
                ss.events.remove(ev)
                st.rerun()
