"""هوش مصنوعی برنامه (Gemini + Groq). بقیهٔ برنامه فقط از همین‌جا import می‌کند: `from core.ai import ...`

نقشهٔ فایل‌ها:
- config.py          تنظیمات: مدل‌ها، اولویت جست‌وجو، سقف مصرف
- gemini_models.py   مصرف روزانه، فهرست مدل‌ها، کلیدها، کنار گذاشتن موقت مدل‌های بی‌سهمیه
- gemini.py          فراخوانی Gemini (استریم، جست‌وجوی وب، لینک منابع) — ask_ai
- prompts_news.py    پرامپت‌های بررسی خبر / نظریه‌های توطئه / پرسش تکمیلی
- prompts_deep.py    پرامپت‌های سناریوی دیپ‌دایو
- prompts_suggest.py معیارها و پرامپت‌های پیشنهاد خبر روزانه
- research.py        تحقیق ترکیبی Groq ← Gemini (خبر، نظریه‌ها، دیپ‌دایو)
- suggest_news.py    پیشنهاد خبر روزانه
- deep_ideas.py      پیشنهاد هفتگی موضوع دیپ‌دایو (نمره‌دهی)
- diagnostics.py     وضعیت سهمیه و تست مدل‌ها
- text_utils.py      شباهت متن
"""
from core.ai.config import (ALLOW_FALLBACK, DAILY_REQUEST_LIMIT, MAX_ATTEMPTS_PER_CLICK,  # noqa: F401
                            MIN_SECONDS_BETWEEN_CALLS, PREFERRED_MODELS, SEARCH_PRIORITY, THINKING_BUDGET)
from core.ai.deep_ideas import DEEP_TYPE_FA, pick_top, suggest_deep_topics  # noqa: F401
from core.ai.diagnostics import blocked_count, diagnose, quota_status, reset_model_cache  # noqa: F401
from core.ai.gemini import ask_ai  # noqa: F401
from core.ai.gemini_models import _get_keys, usage_today  # noqa: F401
from core.ai.prompts_news import NEWS_STRUCTURE, STYLE_SAMPLE, build_followup_prompt  # noqa: F401
from core.ai.research import research_conspiracies, research_deep, research_news  # noqa: F401
from core.ai.suggest_news import suggest_news  # noqa: F401
from core.ai.text_utils import _similar  # noqa: F401
