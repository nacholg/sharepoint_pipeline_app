import html
from typing import Any
import re


def e(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def display_or_pending(value: Any, pending: str = "Pendiente") -> str:
    return e(value) if value not in (None, "") else e(pending)

def no_break_iso_date(value: Any, language: str = "es") -> str:
    if value in (None, ""):
        return ""

    text = str(value).strip()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year, month, day = text.split("-")

        month_maps = {
            "es": {
                "01": "Ene", "02": "Feb", "03": "Mar", "04": "Abr",
                "05": "May", "06": "Jun", "07": "Jul", "08": "Ago",
                "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dic",
            },
            "en": {
                "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
            },
            "pt": {
                "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
                "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
                "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
            },
        }

        month_map = month_maps.get(language, month_maps["es"])
        month_label = month_map.get(month, month)
        formatted = f"{day} {month_label} {year}"
        return html.escape(formatted)

    return html.escape(text)
