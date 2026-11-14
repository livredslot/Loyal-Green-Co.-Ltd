# Loyal Green factory system

A simple system for Loyal Green Co., Ltd to manage raw materials, production, repacking, stock, sales, cost and gross profit. The design and decisions are in the [requirements & design document](https://claude.ai/artifact/9FPmyhBvKo9iQAzzqx8FkP).

Built with Django and PostgreSQL. It runs on a laptop with SQLite for development and on AWS with Docker for the real system.

## Run it on the laptop (Windows, PowerShell)

The Python environment lives outside OneDrive, in `%USERPROFILE%\.venvs\loyal-green`.

First time only:

```powershell
python -m venv $env:USERPROFILE\.venvs\loyal-green
& $env:USERPROFILE\.venvs\loyal-green\Scripts\python.exe -m pip install -r requirements.txt
& $env:USERPROFILE\.venvs\loyal-green\Scripts\python.exe manage.py migrate
& $env:USERPROFILE\.venvs\loyal-green\Scripts\python.exe manage.py createsuperuser
```

Every time:

```powershell
& $env:USERPROFILE\.venvs\loyal-green\Scripts\python.exe manage.py runserver
```

Then open http://127.0.0.1:8000 and log in. Company details, users and roles are under **Setup** (the admin site).

Run the tests:

```powershell
& $env:USERPROFILE\.venvs\loyal-green\Scripts\python.exe manage.py test
```

## Roles

Five roles are created automatically: Director, Sales Manager, Production Lead, Warehouse Lead, Accountant. Give each user one role in Setup → Users → Groups. Costs and profit are hidden from the Warehouse Lead.

## Run it on the server

Copy `.env.example` to `.env`, fill it in, then:

```bash
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Caddy gets the HTTPS certificate for `SITE_DOMAIN` automatically.
