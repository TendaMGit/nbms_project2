# Beginner's Guide to Running NBMS Project 2 Locally (Windows)

This guide will help you set up and run the **NBMS Project 2** on your local Windows machine. It is designed to avoid complex GIS installations.

## Prerequisites

1. **Imstall Docker Desktop**: [Download here](https://www.docker.com/products/docker-desktop/).
    - Ensure it is running.
2. **Install Python 3.12+**: [Download here](https://www.python.org/downloads/).
    - Check the box "Add Python to PATH" during installation.
3. **Install Git**: [Download here](https://git-scm.com/download/win).

## Step 1: Clone the Repository

Open PowerShell or Command Prompt and run:

```powershell
git clone https://github.com/TendaMGit/nbms_project2.git
cd nbms_project2
```

## Step 2: Configure Environment

We need to tell the project to run in "Non-GIS" mode to avoid installing OSGeo4W.

1. Copy the `.env` template:

    ```powershell
    copy .env .env.local
    ```

    *(Note: The project uses `.env` by default, but you might have modified it directly. Ensure you have a `.env` file).*

2. **Edit your `.env` file** using Notepad or VS Code:
    - Set `ENABLE_GIS=false`
    - Set `DJANGO_DB_ENGINE=django.db.backends.postgresql`

## Step 3: Install Dependencies

Install the required Python packages:

```powershell
python -m pip install -r requirements-dev.txt
```

## Step 4: Start Infrastructure (Docker)

We use Docker to run the database (PostgreSQL/PostGIS) and Redis.

```powershell
docker compose -f docker/docker-compose.yml --env-file .env up -d
```

Check if containers are running:

```powershell
docker ps
```

*You should see `nbms_postgis`, `nbms_redis`, and `nbms_geoserver` in the list.*

## Step 5: Setup Database

Run the following commands to set up the database schema:

```powershell
python manage.py migrate
```

## Step 6: Run the Server

Start the Django development server:

```powershell
python manage.py runserver
```

Open your browser to: **[http://localhost:8000](http://localhost:8000)**

## Troubleshooting

### "500 Internal Server Error" or "ProgrammingError"

If you see a database error about missing columns, your database might be out of sync. You can reset it (warning: this deletes local data):

1. Stop the server (Ctrl+C).
2. Reset the database container:

    ```powershell
    docker compose -f docker/docker-compose.yml down
    docker volume rm docker_postgis_data
    docker compose -f docker/docker-compose.yml --env-file .env up -d
    ```

3. Run migrations again:

    ```powershell
    python manage.py migrate
    ```

### "Port already allocated"

If Docker says port 5432 is taken, stop any other Postgres instances:

```powershell
docker stop nbms_project-db-1
docker rm nbms_project-db-1
```
