import os
from dotenv import load_dotenv

load_dotenv()


class AppState:
    def __init__(self):
        self.token: str | None = None
        self.user: dict | None = None
        self.api_base: str = os.getenv("API_BASE_URL", "http://localhost:8001/api/v1")
        self.ws_base: str = os.getenv("WS_BASE_URL", "ws://localhost:8001")
        self._media_base_url: str = os.getenv("MEDIA_BASE_URL", "")
        self._unread_count: int = 0
        self._unread_listeners: list = []
        self._notification_listeners: list = []
        self.last_employee_tab: int = 0
        self.last_manager_tab: int = 0

    @property
    def is_authenticated(self) -> bool:
        return self.token is not None

    @property
    def is_manager(self) -> bool:
        return bool(self.user and self.user.get("role") in ("manager", "admin"))

    @property
    def is_employee(self) -> bool:
        return bool(self.user and self.user.get("role") == "employee")

    @property
    def unread_count(self) -> int:
        return self._unread_count

    @unread_count.setter
    def unread_count(self, value: int):
        self._unread_count = value
        for listener in self._unread_listeners:
            try:
                listener(value)
            except Exception:
                pass

    def add_unread_listener(self, fn):
        self._unread_listeners.append(fn)

    def remove_unread_listener(self, fn):
        self._unread_listeners = [l for l in self._unread_listeners if l != fn]

    def set_unread_listener(self, fn):
        """Replace all listeners with a single one (prevents leak across route rebuilds)."""
        self._unread_listeners = [fn] if fn else []

    def set_notification_listener(self, fn):
        self._notification_listeners = [fn] if fn else []

    def dispatch_notification(self, data: dict):
        for listener in self._notification_listeners:
            try:
                listener(data)
            except Exception:
                pass

    def logout(self):
        self.token = None
        self.user = None
        self._unread_count = 0
        self._unread_listeners.clear()
        self._notification_listeners.clear()
        self.last_employee_tab = 0
        self.last_manager_tab = 0

    @property
    def display_name(self) -> str:
        return self.user.get("name", "Usuário") if self.user else "Usuário"

    @property
    def department_id(self) -> int | None:
        return self.user.get("department_id") if self.user else None

    @property
    def media_base(self) -> str:
        if self._media_base_url:
            return self._media_base_url
        return self.api_base.removesuffix("/api/v1")


app_state = AppState()
