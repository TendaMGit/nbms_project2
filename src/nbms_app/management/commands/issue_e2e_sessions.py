from __future__ import annotations

import json
from importlib import import_module

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Issue deterministic authenticated sessions for e2e test users."

    def add_arguments(self, parser):
        parser.add_argument("--users", nargs="+", required=True, help="Usernames to issue authenticated sessions for.")
        parser.add_argument(
            "--pretty",
            action="store_true",
            help="Pretty-print JSON output.",
        )

    def handle(self, *args, **options):
        users = options["users"] or []
        User = get_user_model()
        missing = [username for username in users if not User.objects.filter(username=username).exists()]
        if missing:
            raise CommandError(f"Unknown username(s): {', '.join(missing)}")

        session_engine = import_module(settings.SESSION_ENGINE)
        SessionStore = session_engine.SessionStore

        payload = {}
        for username in users:
            user = User.objects.get(username=username)
            session = SessionStore()
            session["_auth_user_id"] = str(user.pk)
            session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
            session["_auth_user_hash"] = user.get_session_auth_hash()
            # Avoid one-time middleware rekey so e2e cookies stay valid across requests.
            session["_nbms_session_rekeyed"] = True
            session.save()
            payload[username] = session.session_key

        indent = 2 if options.get("pretty") else None
        self.stdout.write(json.dumps(payload, indent=indent, sort_keys=True))
