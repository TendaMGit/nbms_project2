# NBMS Project 2 (Baseline)

This is a clean, portable baseline for the NBMS platform.

## Quickstart (local)

1) Create a virtual environment and install deps:

```
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

2) Create your `.env` file from the example:

```
copy .env.example .env
```

3) Run migrations and start the server:

```
python manage.py migrate
python manage.py runserver
```

4) Run tests:

```
python manage.py test
```

## Settings

- Dev settings: `config.settings.dev`
- Test settings: `config.settings.test`
- Prod settings: `config.settings.prod`

