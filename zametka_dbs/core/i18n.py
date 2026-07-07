import json
import os
import logging

logger = logging.getLogger(__name__)

_TRANSLATIONS: dict[str, dict[str, str]] = {}
_CURRENT_LANG = "en"


def _load_lang(lang: str) -> dict[str, str]:
    path = os.path.join(
        os.path.dirname(__file__), "..", "..", "assets", "lang", f"{lang}.json"
    )
    path = os.path.normpath(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug("Loaded %d translations for '%s'", len(data), lang)
            return data
    except Exception as e:
        logger.warning("Failed to load translations for '%s': %s", lang, e)
        return {}


def set_language(lang: str):
    global _CURRENT_LANG, _TRANSLATIONS
    _CURRENT_LANG = lang
    _TRANSLATIONS = _load_lang(lang)


def current_language() -> str:
    return _CURRENT_LANG


def tr(key: str, *args, **kwargs) -> str:
    text = _TRANSLATIONS.get(key, key)
    if args:
        try:
            text = text.format(*args)
        except (IndexError, KeyError):
            pass
    return text
