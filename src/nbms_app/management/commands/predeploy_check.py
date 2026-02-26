import os

from django.core.management import BaseCommand, CommandError, call_command


class Command(BaseCommand):
    help = "Run production pre-deploy checks (env contract, check --deploy, migrate --check)."

    required_env_vars = (
        "DJANGO_SECRET_KEY",
        "DATABASE_URL",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
    )

    def add_arguments(self, parser):
        parser.add_argument("--skip-env-check", action="store_true", help="Skip required environment variable checks.")
        parser.add_argument("--skip-deploy-check", action="store_true", help="Skip Django check --deploy.")
        parser.add_argument("--skip-migrate-check", action="store_true", help="Skip migrate --check.")

    def handle(self, *args, **options):
        if not options["skip_env_check"]:
            self._validate_required_env_vars()

        if not options["skip_deploy_check"]:
            self.stdout.write("Running django deploy checks...")
            call_command("check", deploy=True)

        if not options["skip_migrate_check"]:
            self.stdout.write("Running migration drift checks...")
            self._run_migrate_check()

        self.stdout.write(self.style.SUCCESS("Pre-deploy checks passed."))

    def _validate_required_env_vars(self):
        missing = [name for name in self.required_env_vars if not (os.environ.get(name) or "").strip()]
        if missing:
            missing_list = ", ".join(missing)
            raise CommandError(f"Missing required environment variables: {missing_list}")

    def _run_migrate_check(self):
        try:
            call_command("migrate", check=True, verbosity=0, interactive=False)
        except SystemExit as exc:
            if exc.code not in (0, None):
                raise CommandError("Unapplied migrations detected by migrate --check.") from exc
        except CommandError as exc:
            raise CommandError(f"Migration check failed: {exc}") from exc
