PYTHON ?= python

.PHONY: check test deploy-check docs-check

check:
	$(PYTHON) scripts/check_blueprint_language.py
	PYTHONPATH=src $(PYTHON) manage.py check

test:
	PYTHONPATH=src pytest -q

docs-check:
	$(PYTHON) scripts/check_blueprint_language.py

deploy-check:
	PYTHONPATH=src \
	DJANGO_SETTINGS_MODULE=config.settings.prod \
	DJANGO_READ_DOT_ENV_FILE=0 \
	DJANGO_SECRET_KEY=$${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY is required} \
	DATABASE_URL=$${DATABASE_URL:?DATABASE_URL is required} \
	DJANGO_ALLOWED_HOSTS=$${DJANGO_ALLOWED_HOSTS:?DJANGO_ALLOWED_HOSTS is required} \
	DJANGO_CSRF_TRUSTED_ORIGINS=$${DJANGO_CSRF_TRUSTED_ORIGINS:?DJANGO_CSRF_TRUSTED_ORIGINS is required} \
	$(PYTHON) manage.py predeploy_check
