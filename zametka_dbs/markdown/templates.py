"""
Template engine for Daily Notes and note templates.

Переменные шаблона:
  {{date}}       — 2026-06-23
  {{time}}       — 14:30
  {{datetime}}   — 2026-06-23 14:30
  {{title}}      — Заголовок заметки
  {{weekday}}    — Tuesday
  {{weekday_ru}} — Вторник
  {{month}}      — June
  {{month_ru}}   — Июнь
  {{year}}       — 2026
  {{iso_week}}   — 26
"""

import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

WEEKDAYS_RU = [
    "Понедельник", "Вторник", "Среда",
    "Четверг", "Пятница", "Суббота", "Воскресенье",
]

MONTHS_RU = [
    "", "Января", "Февраля", "Марта", "Апреля", "Мая", "Июня",
    "Июля", "Августа", "Сентября", "Октября", "Ноября", "Декабря",
]


DEFAULT_DAILY_TEMPLATE = """# {{date}}

**{{weekday_ru}}, {{month}} {{year}}**

## Tasks

- [ ]

## Notes


"""

DEFAULT_NOTE_TEMPLATE = """# {{title}}

Created: {{datetime}}

## Notes


"""


def render_template(template: str, title: str = "", date: datetime = None) -> str:
    if date is None:
        date = datetime.now()

    wd = date.weekday()
    vars_map = {
        "{{date}}": date.strftime("%Y-%m-%d"),
        "{{time}}": date.strftime("%H:%M"),
        "{{datetime}}": date.strftime("%Y-%m-%d %H:%M"),
        "{{title}}": title,
        "{{weekday}}": date.strftime("%A"),
        "{{weekday_ru}}": WEEKDAYS_RU[wd],
        "{{month}}": date.strftime("%B"),
        "{{month_ru}}": MONTHS_RU[date.month],
        "{{year}}": date.strftime("%Y"),
        "{{iso_week}}": date.strftime("%V"),
        "{{day}}": date.strftime("%d"),
        "{{hour}}": date.strftime("%H"),
        "{{minute}}": date.strftime("%M"),
    }

    result = template
    for var, value in vars_map.items():
        result = result.replace(var, value)
    return result


def daily_note_path(vault_path: str, date: datetime = None) -> str:
    if date is None:
        date = datetime.now()
    filename = date.strftime("%Y-%m-%d") + ".md"
    # Place in a Daily Notes subfolder if it exists, otherwise root
    daily_dir = os.path.join(vault_path, "Daily Notes")
    if os.path.isdir(daily_dir):
        return os.path.join(daily_dir, filename)
    return os.path.join(vault_path, filename)


def create_daily_note(vault_path: str, date: datetime = None,
                      template: str = None) -> str:
    if template is None:
        template = DEFAULT_DAILY_TEMPLATE
    path = daily_note_path(vault_path, date)
    if os.path.exists(path):
        return path
    content = render_template(template, title="Daily Note", date=date)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Created daily note: {path}")
    return path


def create_note_from_template(vault_path: str, title: str,
                              template: str = None) -> str:
    if template is None:
        template = DEFAULT_NOTE_TEMPLATE
    filename = title.strip().replace(" ", "-") + ".md"
    path = os.path.join(vault_path, filename)
    if os.path.exists(path):
        base, ext = os.path.splitext(filename)
        i = 1
        while os.path.exists(os.path.join(vault_path, f"{base}-{i}{ext}")):
            i += 1
        path = os.path.join(vault_path, f"{base}-{i}{ext}")
    content = render_template(template, title=title)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Created note: {path}")
    return path
