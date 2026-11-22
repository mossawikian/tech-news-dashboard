"""CSS — جریان کاری اخبار: دسته‌ها، کارت خبر، ورودی‌ها، برچسب وضعیت، نشانگر سهمیه."""
CSS_NEWS = """
/* جریان کاری */
.sum-row { display: flex; align-items: center; gap: 18px; margin: 6px 0 14px; }
.sum-t { font-weight: 700; font-size: .98rem; }
.progress { flex: 1; max-width: 280px; height: 5px; border-radius: 99px; background: var(--line); overflow: hidden; }
.progress > div { height: 100%; border-radius: 99px; background: var(--grad); }
.day-label { display: flex; align-items: center; gap: 7px; color: var(--muted); font-size: .8rem; margin: 14px 0 8px; }

/* دسته‌بندی خبرها (کنترل قرصی) */
[class*="st-key-news_tab"] { margin-bottom: 6px; }
[class*="st-key-news_tab"] button { border-radius: 10px; font-weight: 600; }

/* کارت خبر */
[class*="st-key-newscard_"] {
    position: relative; background: var(--card2); border: 1px solid var(--line);
    border-radius: var(--r); padding: 16px 18px 14px; gap: .7rem; margin-bottom: 4px;
}
[class*="st-key-newscard_"]::before {
    content: ""; position: absolute; right: 0; top: 16px; bottom: 16px; width: 3px;
    border-radius: 3px; background: var(--faint);
}
[class*="st-key-newscard_"][class*="_Reviewing"]::before { background: var(--warn); }
[class*="st-key-newscard_"][class*="_Approved"]::before { background: var(--ok); }
[class*="st-key-newscard_"][class*="_Rejected"]::before { background: var(--bad); }
.news-head { display: flex; gap: 14px; align-items: flex-start; }
.news-title { font-weight: 700; font-size: 1rem; color: var(--text); line-height: 1.8; }
.news-desc { color: var(--muted); font-size: .88rem; margin-top: 4px; line-height: 1.9; }
.avatar {
    width: 42px; height: 42px; border-radius: 12px; flex: 0 0 auto;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft); color: var(--accent-ink);
}

/* ورودی‌ها و بازشوها */
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div, textarea {
    background: rgba(255,255,255,.05) !important; border-radius: var(--rs) !important;
}
[data-baseweb="input"] input, [data-baseweb="base-input"] input, textarea {
    color: var(--text) !important; -webkit-text-fill-color: var(--text);
}
[data-testid="stExpander"] details {
    background: rgba(255,255,255,.035); border: 1px solid var(--line) !important; border-radius: var(--rs);
}
[data-testid="stExpander"] summary { font-weight: 600; color: var(--muted); }
[data-testid="stAlert"] { border-radius: var(--rs); }

/* برچسب وضعیت */
.chip { display: inline-block; white-space: nowrap; font-size: .7rem; padding: 2px 10px; border-radius: 99px;
        margin-right: 8px; font-weight: 600; vertical-align: middle; }
.chip-pending { background: rgba(255,255,255,.07); color: var(--muted); border: 1px solid var(--line); }
.chip-review { background: var(--warn-soft); color: var(--warn); }
.chip-done { background: var(--ok-soft); color: var(--ok); }
.chip-rej { background: var(--bad-soft); color: var(--bad); }

/* نشانگر سهمیه (سایدبار) */
.qbox { border: 1px solid var(--line); border-radius: var(--r); padding: 12px 14px; margin: 14px 0 10px;
        background: var(--card); font-size: .8rem; direction: rtl; }
.q-head { display: flex; justify-content: space-between; color: var(--muted); }
.q-head b { color: var(--text); }
.q-bar { height: 5px; border-radius: 5px; background: var(--line); margin: 9px 0; overflow: hidden; }
.q-fill { height: 100%; border-radius: 5px; }
.q-fill.ok { background: var(--grad); } .q-fill.warn { background: var(--warn); } .q-fill.bad { background: var(--bad); }
.q-state { color: var(--muted); display: flex; align-items: center; gap: 7px; }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.dot.ok { background: var(--ok); box-shadow: 0 0 0 3px var(--ok-soft); }
.dot.warn { background: var(--warn); box-shadow: 0 0 0 3px var(--warn-soft); }
.q-row { display: flex; flex-direction: column; margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--line); }
.q-row span { color: var(--faint); font-size: .72rem; }


/* نسخه‌های تحقیق: راست‌چین کامل + هر نسخه یک رنگ (مرز، پس‌زمینه و نوار «پایان نسخه») */
[class*="st-key-newscard_"] [data-testid="stMarkdownContainer"],
[class*="st-key-newscard_"] [data-testid="stExpanderDetails"],
[class*="st-key-newscard_"] [data-testid="stCaptionContainer"] { direction: rtl !important; text-align: right !important; }
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] { direction: rtl !important; text-align: right !important; line-height: 2; }
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] ul,
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] ol { direction: rtl !important; padding-right: 1.6rem !important; padding-left: 0 !important; margin-right: 0 !important; }
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] li { direction: rtl !important; text-align: right !important; }
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] blockquote { border-right: 3px solid var(--vc); border-left: none; padding-right: 12px; padding-left: 0; }
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] h2,
[class*="st-key-ver_"] [data-testid="stMarkdownContainer"] h3 { text-align: right !important; color: var(--vc); }
[class*="st-key-ver_"] { margin: 10px 0; }
[class*="st-key-ver_"] [data-testid="stExpander"] details {
    background: var(--vc-soft) !important; border: 1px solid var(--vc) !important;
    border-right: 5px solid var(--vc) !important; border-radius: var(--rs);
}
[class*="st-key-ver_"] [data-testid="stExpander"] summary,
[class*="st-key-ver_"] [data-testid="stExpander"] summary p { color: var(--vc) !important; font-weight: 700; direction: rtl; }
[class*="st-key-ver_"] [data-testid="stExpanderDetails"] { border-top: 1px dashed var(--vc); padding-top: 12px; }
.ver-end { margin-top: 16px; padding-top: 8px; border-top: 3px solid var(--vc); color: var(--vc);
           text-align: center; font-size: .8rem; font-weight: 700; }
[class*="clr0x"] { --vc: #38bdf8; --vc-soft: rgba(56,189,248,.08); }
[class*="clr1x"] { --vc: #a78bfa; --vc-soft: rgba(167,139,250,.08); }
[class*="clr2x"] { --vc: #fb923c; --vc-soft: rgba(251,146,60,.08); }
[class*="clr3x"] { --vc: #34d399; --vc-soft: rgba(52,211,153,.08); }
[class*="clr4x"] { --vc: #fbbf24; --vc-soft: rgba(251,191,36,.08); }
[class*="clr5x"] { --vc: #fb7185; --vc-soft: rgba(251,113,133,.08); }

[class*="st-key-newscard_"] [data-testid="stCode"] { direction: ltr !important; text-align: left !important; }

/* برچسب «پیشنهاد اعلان» */
.chip-push { background: var(--accent-soft); color: var(--accent-ink); }
"""
