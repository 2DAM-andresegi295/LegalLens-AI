from __future__ import annotations

from django.core.management import call_command
from django.core.management.commands.runserver import Command as RunserverCommand


class Command(RunserverCommand):
    def inner_run(self, *args, **options):
        call_command("migrate", interactive=False, verbosity=0)
        return super().inner_run(*args, **options)

