"""منطقهٔ زمانی برنامه. سرور Streamlit Cloud به وقت UTC کار می‌کند؛ اگر از date.today() استفاده شود،
«امروز» ساعت ۰۵:۰۰ صبح به وقت پاکستان عوض می‌شود نه ۰۰:۰۰. همهٔ تاریخ‌ها و ساعت‌های برنامه از اینجا می‌آیند.
برای منطقهٔ دیگر، متغیر محیطی APP_TIMEZONE را بگذارید (مثلاً Asia/Kabul)."""
import datetime as dt
import os
from zoneinfo import ZoneInfo

try:
    TZ = ZoneInfo(os.environ.get("APP_TIMEZONE", "").strip() or "Asia/Karachi")
except Exception:  # noqa: BLE001
    TZ = ZoneInfo("Asia/Karachi")


def now_local():
    return dt.datetime.now(TZ)


def now_naive():
    """ساعت محلی بدون tzinfo (برای مقایسه با زمان‌های ذخیره‌شده در داده)."""
    return now_local().replace(tzinfo=None)


def today_local():
    return now_local().date()
