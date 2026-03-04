PYTHON ?= python
DOCKER_COMPOSE ?= docker compose
TEST_COMPOSE_ARGS ?= --profile minimal -f compose.yml -f docker-compose.test.yml

.PHONY: check test deploy-check docs-check test-backend test-backend-up test-backend-down

check:
	$(PYTHON) scripts/check_blueprint_language.py
	PYTHONPATH=src $(PYTHON) manage.py check

test:
	PYTHONPATH=src pytest -q

test-backend-up:
	$(DOCKER_COMPOSE) $(TEST_COMPOSE_ARGS) up -d --build postgis redis minio minio-init backend

test-backend:
	$(DOCKER_COMPOSE) $(TEST_COMPOSE_ARGS) up -d --build postgis redis minio minio-init backend
	$(DOCKER_COMPOSE) $(TEST_COMPOSE_ARGS) exec -T backend pytest -q

test-backend-down:
	$(DOCKER_COMPOSE) $(TEST_COMPOSE_ARGS) down --remove-orphans

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
