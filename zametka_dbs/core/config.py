import json
import logging
import os

logger = logging.getLogger(__name__)

try:
    from zametka_core import Config as RustConfig
    _HAS_RUST = True
except ImportError:
    _HAS_RUST = False


class _PyConfig:
    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Zametka")
        self._path = os.path.join(config_dir, "config.json")
        self._data = {}
        self._load()

    def _load(self):
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
                self._data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")

    def get(self, key, default=None):
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    def set(self, key, value):
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            if k not in d:
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self._save()


class Config:
    def __init__(self, config_dir=None):
        if _HAS_RUST:
            self._inner = RustConfig(config_dir)
        else:
            logger.info("Using Python config backend")
            self._inner = _PyConfig(config_dir)

    def get(self, key, default=None):
        if _HAS_RUST:
            val = self._inner.get(key, None)
            if val == "" and default is not None:
                return default
            keys = key.split(".")
            last = keys[-1]
            if last in ("enabled", "word_wrap", "show_line_numbers", "auto_render"):
                if val == "":
                    return default if default is not None else False
                return val.lower() == "true"
            if last in ("font_size", "tab_size", "sidebar_width", "max_results"):
                if val == "":
                    return default if default is not None else 0
                try:
                    return int(float(val))
                except ValueError:
                    return default
            if last in ("preview_width_ratio", "line_height"):
                if val == "":
                    return default if default is not None else 0.0
                try:
                    return float(val)
                except ValueError:
                    return default
            if isinstance(default, list):
                if val and val.startswith("["):
                    try:
                        return json.loads(val)
                    except json.JSONDecodeError:
                        pass
                return default if default is not None else []
            return val if val != "" else (default if default is not None else "")
        val = self._inner.get(key, None)
        if val is None:
            return default
        keys = key.split(".")
        last = keys[-1]
        if last in ("enabled", "word_wrap", "show_line_numbers", "auto_render"):
            return bool(val) if isinstance(val, bool) else str(val).lower() == "true"
        if last in ("font_size", "tab_size", "sidebar_width", "max_results"):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default
        if last in ("preview_width_ratio", "line_height"):
            try:
                return float(val)
            except (ValueError, TypeError):
                return default
        return val

    def set(self, key, value):
        if _HAS_RUST:
            if isinstance(value, (list, dict)):
                self._inner.set(key, json.dumps(value, ensure_ascii=False))
            else:
                self._inner.set(key, str(value))
        else:
            self._inner.set(key, value)


_config_instance = None


def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
