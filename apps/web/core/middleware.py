from __future__ import annotations

from threading import Lock

from django.core.management import call_command


class AutoMigrateMiddleware:
    _lock = Lock()
    _migrated = False

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._ensure_migrated()
        return self.get_response(request)

    @classmethod
    def _ensure_migrated(cls) -> None:
        if cls._migrated:
            return
        with cls._lock:
            if cls._migrated:
                return
            call_command("migrate", interactive=False, verbosity=0)
            cls._migrated = True

