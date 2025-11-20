import logging
from typing import Any, Callable, Dict, List

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_name: str, callback: Callable):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def emit(self, event_name: str, data: Any = None, **kwargs):
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                try:
                    # Pass data if it's a single dictionary, or merge kwargs if provided
                    if data is None and kwargs:
                        callback(kwargs)
                    elif isinstance(data, dict) and kwargs:
                        combined = {**data, **kwargs}
                        callback(combined)
                    elif data is not None:
                        callback(data)
                    else:
                        callback({})
                except Exception as e:
                    logging.error(f"Error in event handler for {event_name}: {e}")

