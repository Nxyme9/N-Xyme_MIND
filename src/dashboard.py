"""Dashboard — Performance dashboard data"""

import logging, time
from typing import Dict, List

logger = logging.getLogger(__name__)


class Dashboard:
    def __init__(self):
        self._widgets: Dict[str, dict] = {}
        self._data: Dict[str, List] = {}

    def add_widget(self, name: str, widget_type: str, title: str, max_points: int = 100):
        self._widgets[name] = {"type": widget_type, "title": title, "max_points": max_points}
        self._data[name] = []

    def update(self, widget: str, value):
        if widget in self._data:
            self._data[widget].append({"value": value, "time": time.time()})
            max_points = self._widgets[widget]["max_points"]
            if len(self._data[widget]) > max_points:
                self._data[widget] = self._data[widget][-max_points:]

    def get_data(self, widget: str) -> List:
        return self._data.get(widget, [])

    def get_all(self) -> Dict:
        return {
            "widgets": self._widgets,
            "data": {k: v[-10:] for k, v in self._data.items()},
        }
