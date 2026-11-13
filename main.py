"""
یادآور تولد شمسی (Persian Birthday Reminder)
Python + Flet + jdatetime + flet-android-notifications
"""
import json
import os
from datetime import datetime, time, timedelta

import flet as ft
import jdatetime

try:
    from flet_android_notifications import FletAndroidNotifications
except Exception:  # اجرا روی دسکتاپ بدون پکیج نوتیفیکیشن
    FletAndroidNotifications = None

# ---------------------------------------------------------------- تنظیمات
PINK_BG = ft.Colors.PINK_50
PINK_MAIN = ft.Colors.PINK_700
NOTIFY_HOUR = 9          # ساعت ارسال نوتیفیکیشن
YEARS_AHEAD = 5          # چند سال آینده از قبل زمان‌بندی شود
DATA_DIR = os.getenv("FLET_APP_STORAGE_DATA", ".")
DATA_FILE = os.path.join(DATA_DIR, "birthdays.json")

MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


# ---------------------------------------------------------------- ذخیره‌سازی
def load_people() -> list[dict]:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_people(people: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(people, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- منطق تاریخ
def max_days(month: int) -> int:
    return 31 if month <= 6 else 30


def upcoming_occurrences(day: int, month: int, count: int = YEARS_AHEAD) -> list[datetime]:
    """
    زمان‌های بعدی نوتیفیکیشن (میلادی) برای یک تولد شمسی.
    - اگر تاریخ امسال گذشته باشد → سال بعد
    - اگر امروز باشد و ساعت ۹ نگذشته باشد → همین امروز ساعت ۹
    - اگر امروز باشد ولی ساعت ۹ گذشته باشد → چند ثانیه بعد (همین امروز)
    """
    now = datetime.now()
    j_year = jdatetime.date.fromgregorian(date=now.date()).year
    result: list[datetime] = []
    year = j_year
    while len(result) < count and year < j_year + count + 3:
        try:
            jd = jdatetime.date(year, month, day)
        except ValueError:      # ۳۰ اسفند در سال غیرکبیسه
            jd = jdatetime.date(year, month, 29)
        when = datetime.combine(jd.togregorian(), time(NOTIFY_HOUR, 0))
        if when > now:
            result.append(when)
        elif when.date() == now.date() and not result:
            result.append(now + timedelta(seconds=10))
        year += 1
    return result


# ---------------------------------------------------------------- برنامه
async def main(page: ft.Page):
    page.title = "یادآور تولد شمسی"
    page.bgcolor = PINK_BG
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=PINK_MAIN)
    try:
        page.rtl = True
    except Exception:
        pass
    page.appbar = ft.AppBar(
        title=ft.Text("🎂 یادآور تولد شمسی", color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        center_title=True,
        bgcolor=PINK_MAIN,
    )

    notifications = FletAndroidNotifications() if FletAndroidNotifications else None
    state = {"schedule_mode": "inexact_allow_while_idle", "notif_ok": False}
    people = load_people()

    # ---------- نوتیفیکیشن
    async def setup_permissions() -> str:
        if notifications is None:
            return "نوتیفیکیشن فقط روی اندروید فعال است."
        try:
            granted = await notifications.request_permissions()
            state["notif_ok"] = bool(granted)
            if not granted:
                return "مجوز نوتیفیکیشن داده نشد؛ از تنظیمات گوشی فعالش کنید."
            can_exact = await notifications.can_schedule_exact_notifications()
            if not can_exact:
                can_exact = await notifications.request_exact_alarm_permission()
            state["schedule_mode"] = (
                "exact_allow_while_idle" if can_exact else "inexact_allow_while_idle"
            )
            return "" if can_exact else "مجوز Alarm دقیق داده نشد؛ زمان نوتیفیکیشن ممکن است کمی تأخیر داشته باشد."
        except Exception as ex:  # روی دسکتاپ یا خطای پلتفرم
            return f"خطا در تنظیم نوتیفیکیشن: {ex}"

    async def cancel_person(pid: int) -> None:
        if notifications is None:
            return
        for k in range(YEARS_AHEAD):
            try:
                await notifications.cancel(notification_id=pid * 10 + k)
            except Exception:
                pass

    async def schedule_person(p: dict) -> None:
        if notifications is None or not state["notif_ok"]:
            return
        await cancel_person(p["id"])
        for k, when in enumerate(upcoming_occurrences(p["day"], p["month"])):
            try:
                await notifications.schedule_notification(
                    notification_id=p["id"] * 10 + k,
                    title="🎂 تولد یادت نره!",
                    body=f"امروز تولد {p['name']} است 🎉",
                    scheduled_time=when,
                    schedule_mode=state["schedule_mode"],
                )
            except Exception as ex:
                status.value = f"خطا در زمان‌بندی: {ex}"
                status.color = ft.Colors.RED_700

    # ---------- UI
    status = ft.Text("", size=13, color=ft.Colors.GREY_800, text_align=ft.TextAlign.RIGHT)

    name_field = ft.TextField(
        label="نام",
        rtl=True,
        text_align=ft.TextAlign.RIGHT,
        border_color=PINK_MAIN,
        focused_border_color=PINK_MAIN,
        bgcolor=ft.Colors.WHITE,
    )
    day_dd = ft.Dropdown(
        label="روز",
        expand=True,
        border_color=PINK_MAIN,
        bgcolor=ft.Colors.WHITE,
        options=[ft.DropdownOption(key=str(i), text=str(i)) for i in range(1, 32)],
    )
    month_dd = ft.Dropdown(
        label="ماه",
        expand=True,
        border_color=PINK_MAIN,
        bgcolor=ft.Colors.WHITE,
        options=[ft.DropdownOption(key=str(i + 1), text=m) for i, m in enumerate(MONTHS)],
    )
    list_view = ft.ListView(expand=True, spacing=8, padding=ft.Padding.only(top=8) if hasattr(ft, "Padding") else 8)

    def make_delete(pid: int):
        async def handler(e):
            await cancel_person(pid)
            people[:] = [x for x in people if x["id"] != pid]
            save_people(people)
            render()
            status.value = "حذف شد."
            status.color = ft.Colors.GREY_800
            page.update()
        return handler

    def render():
        list_view.controls.clear()
        if not people:
            list_view.controls.append(
                ft.Container(
                    content=ft.Text("هنوز تولدی ثبت نشده است 🎈", color=ft.Colors.GREY_600),
                    alignment=ft.Alignment.CENTER if hasattr(ft, "Alignment") else None,
                    padding=24,
                )
            )
        for p in sorted(people, key=lambda x: (x["month"], x["day"])):
            list_view.controls.append(
                ft.Card(
                    content=ft.ListTile(
                        leading=ft.Icon(ft.Icons.CAKE, color=PINK_MAIN),
                        title=ft.Text(p["name"], weight=ft.FontWeight.BOLD),
                        subtitle=ft.Text(f"{p['day']} {MONTHS[p['month'] - 1]}"),
                        trailing=ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=PINK_MAIN,
                            on_click=make_delete(p["id"]),
                        ),
                    )
                )
            )

    async def add_person(e):
        name = (name_field.value or "").strip()
        if not name or not day_dd.value or not month_dd.value:
            status.value = "نام، روز و ماه را کامل وارد کنید."
            status.color = ft.Colors.RED_700
            page.update()
            return
        day, month = int(day_dd.value), int(month_dd.value)
        if day > max_days(month):
            status.value = f"{MONTHS[month - 1]} بیش از {max_days(month)} روز ندارد."
            status.color = ft.Colors.RED_700
            page.update()
            return

        new_id = max((p["id"] for p in people), default=0) + 1
        person = {"id": new_id, "name": name, "day": day, "month": month}
        people.append(person)
        save_people(people)

        msg = await setup_permissions()      # اگر قبلاً مجوز داده شده باشد، دیالوگی نمایش داده نمی‌شود
        await schedule_person(person)

        name_field.value = ""
        day_dd.value = None
        month_dd.value = None
        status.value = msg or f"تولد {name} ثبت شد ✅"
        status.color = ft.Colors.RED_700 if msg else ft.Colors.GREEN_800
        render()
        page.update()

    add_btn = ft.Button(
        content="ثبت تولد",
        icon=ft.Icons.ADD,
        on_click=add_person,
        bgcolor=PINK_MAIN,
        color=ft.Colors.WHITE,
        height=48,
    )

    page.add(
        ft.Column(
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Column(
                            controls=[
                                name_field,
                                ft.Row([day_dd, month_dd], spacing=12),
                                add_btn,
                                status,
                            ],
                            spacing=12,
                        ),
                    )
                ),
                ft.Text("تولدهای ثبت‌شده", size=18, weight=ft.FontWeight.BOLD, color=PINK_MAIN),
                list_view,
            ],
        )
    )
    render()
    page.update()

    # ---------- هنگام شروع: مجوزها + زمان‌بندی مجدد همه تولدها
    msg = await setup_permissions()
    if msg:
        status.value = msg
        status.color = ft.Colors.RED_700
    for p in people:
        await schedule_person(p)
    page.update()


ft.run(main)
