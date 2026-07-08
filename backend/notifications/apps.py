import os
import sys

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        if os.environ.get("DISABLE_INPROCESS_SCHEDULER") == "true":
            return

        argv = sys.argv
        is_manage_command = bool(argv) and argv[0].endswith("manage.py")
        command = argv[1] if is_manage_command and len(argv) > 1 else None

        if is_manage_command:
            # Only ever start under `runserver` (or gunicorn/uvicorn in
            # production, where argv[0] won't be manage.py at all) — never
            # during migrate/shell/test/send_daily_verse itself/etc.
            if command != "runserver":
                return
            # `runserver`'s autoreloader spawns a watcher parent process
            # (RUN_MAIN unset) plus the actual worker child (RUN_MAIN="true")
            # — only start in the child, or it'd run twice.
            if os.environ.get("RUN_MAIN") != "true":
                return

        from .scheduler import start_scheduler

        start_scheduler()
