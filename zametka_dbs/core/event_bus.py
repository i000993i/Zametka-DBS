from collections import defaultdict
from typing import Callable, Any
import weakref
import logging

logger = logging.getLogger(__name__)

Callback = Callable[..., None]


class EventBus:
    """
    Central pub/sub event bus for inter-module communication.

    Modules subscribe to events they care about and emit events
    when something happens. This keeps modules decoupled.

    Usage:
        bus = EventBus()

        def on_file_opened(path):
            print(f"Opened: {path}")

        bus.subscribe("file:opened", on_file_opened)
        bus.emit("file:opened", path="/notes/test.md")
    """

    def __init__(self):
        self._subscribers: dict[str, list[weakref.ref]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callback) -> Callable:
        self._subscribers[event_type].append(weakref.ref(callback))
        logger.debug(f"Subscribed to '{event_type}': {callback.__name__}")

        def unsubscribe():
            self.unsubscribe(event_type, callback)

        return unsubscribe

    def unsubscribe(self, event_type: str, callback: Callback) -> None:
        self._subscribers[event_type] = [
            ref for ref in self._subscribers[event_type]
            if ref() is not None and ref() is not callback
        ]
        logger.debug(f"Unsubscribed from '{event_type}': {callback.__name__}")

    def emit(self, event_type: str, **data: Any) -> None:
        logger.debug(f"Event emitted: '{event_type}' data={data}")
        dead_refs = []
        for ref in self._subscribers.get(event_type, []):
            callback = ref()
            if callback is not None:
                try:
                    callback(event_type=event_type, **data)
                except Exception as e:
                    logger.error(
                        f"Error in handler '{callback.__name__}' "
                        f"for event '{event_type}': {e}"
                    )
            else:
                dead_refs.append(ref)
        for ref in dead_refs:
            self._subscribers[event_type].remove(ref)

    def clear(self) -> None:
        self._subscribers.clear()
        logger.debug("EventBus cleared all subscribers")

    @property
    def subscriber_count(self) -> int:
        return sum(len(refs) for refs in self._subscribers.values())


_bus_instance: EventBus | None = None


def get_bus() -> EventBus:
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance


def reset_bus() -> None:
    global _bus_instance
    _bus_instance = None


# Предопределённые типы событий
class Events:
    FILE_OPENED = "file:opened"
    FILE_CHANGED = "file:changed"
    FILE_CREATED = "file:created"
    FILE_DELETED = "file:deleted"
    FILE_RENAMED = "file:renamed"

    EDITOR_CURSOR_MOVED = "editor:cursor_moved"
    EDITOR_CONTENT_CHANGED = "editor:content_changed"
    EDITOR_ACTIVE_FILE_CHANGED = "editor:active_file_changed"

    VAULT_OPENED = "vault:opened"
    VAULT_CLOSED = "vault:closed"

    SEARCH_RESULTS = "search:results"
    SEARCH_STARTED = "search:started"

    PLUGIN_LOADED = "plugin:loaded"
    PLUGIN_UNLOADED = "plugin:unloaded"

    THEME_CHANGED = "theme:changed"
    CONFIG_CHANGED = "config:changed"

    APP_READY = "app:ready"
    APP_QUITTING = "app:quitting"
