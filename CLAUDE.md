# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A Django-based personal portfolio site. Single Django project (`portfolio`) with a single app (`portfolio_pages`) that holds all models, views, forms, and templates. Runs behind Gunicorn + Nginx in Docker Compose, with Prometheus/Grafana for monitoring.

All Django code lives under `portfolio/` (i.e. `portfolio/portfolio/` is the project package and `portfolio/portfolio_pages/` is the app) — commands below assume you've `cd`'d into `e:\portfolio_site\portfolio`.

## Commands

Run from `portfolio/` (where `manage.py` lives), using the project's `.venv`:

```
python manage.py runserver              # dev server
python manage.py migrate                # apply migrations
python manage.py makemigrations         # create migrations after model changes
python manage.py createsuperuser        # create an admin/login user
python manage.py collectstatic --noinput
```

Tests (`portfolio_pages/tests.py`, uses Django's `TestCase`):

```
python manage.py test
python manage.py test portfolio_pages
python manage.py test portfolio_pages.tests.Smoketest
python manage.py test portfolio_pages.tests.Smoketest.test_homepage_loads
```

Tests need `TEST_DB=sqlite` in the environment to fall back to SQLite instead of Postgres (see Settings below):

```
TEST_DB=sqlite python manage.py test
```

Docker (production-style stack: db + web + nginx + prometheus + grafana):

```
docker compose up -d --build
docker compose logs -f web
```

`entrypoint.sh` runs on container start: waits briefly for Postgres, runs `migrate`, runs `collectstatic`, then execs Gunicorn (`portfolio.wsgi:application`, 3 workers).

There is no configured linter/formatter in this repo — don't assume one.

## Architecture

**Settings (`portfolio/portfolio/settings.py`)** — all secrets/config come from `.env` via `python-decouple` (`config(...)`), not hardcoded. Key env-driven values: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, DB connection vars, email vars, `LINKEDIN_URL`/`FACEBOOK_URL`/`INSTAGRAM_URL`/`GITHUB_URL`/`EMAIL`. `.env` is gitignored; check `.env` locally for the full var list before adding new settings.

Database selection is env-driven, not settings-file-driven: if `TEST_DB=sqlite` is set, it uses `db.sqlite3`; otherwise it connects to Postgres using the `DB_*` config vars. This is how local/test runs avoid needing Postgres.

A custom context processor (`portfolio_pages/context_processors.py::social_links`) injects social links into every template's context — this is why templates can reference `{{ LINKEDIN_URL }}`, `{{ Github }}`, etc. without views passing them explicitly.

`django_prometheus` wraps every request (`PrometheusBeforeMiddleware`/`PrometheusAfterMiddleware` are first/last in `MIDDLEWARE`) and exposes `/metrics`, scraped by the `prometheus` container per `monitoring/prometheus.yml`.

**URLs** — `portfolio/portfolio/urls.py` mounts the app at `/portfolio_pages/` and redirects `/` there; it also wires up `/admin/`, media file serving, and `django_prometheus.urls`. All actual page routes are in `portfolio_pages/urls.py` (index, contact, projects, skills, add/edit/delete for skills and projects, resume, login/logout).

**Models (`portfolio_pages/models.py`)** — `MY_Project` has a one-to-many `ProjectImage` (`related_name='images'`) and `Projecttech_stack` (`related_name='tech_stack'`, a plain CharField per tag rather than a M2M/tags table). Both `MY_Project` and `My_skill` are owned by a `User` FK (default `pk=1`) and gated by `@login_required` in views — there is no per-object permission system beyond "must be the owning user" (enforced via `get_object_or_404(..., user=request.user)` in each edit/delete view). `Contact` stores contact-form submissions directly in the DB (admin can view but not add/edit, see `admin.py`). `CV` holds the resume file shown on `/resume/`.

**Views/forms pattern** — Add/edit views for skills and projects share one template each (`add_skill.html`, `add_project.html`) driven by whether an `instance` is passed to the form; `add_project` additionally hand-parses `tech_stack` from a comma-separated string in `request.POST` (not a model field on `Add_ProjectForm`) and manually creates `Projecttech_stack` rows, and separately loops `request.FILES.getlist("images")` to create `ProjectImage` rows — this multi-image/tag handling lives in the view, not the form.

**Auth** — Uses Django's built-in `authenticate`/`login`/`logout` directly in `portfolio_pages/views.py::user_login`/`user_logout` (no `django-allauth` or DRF). Login template is `portfolio/templates/registration/login.html` (project-level templates dir), everything else is app-level templates in `portfolio_pages/templates/`.

**Static/media split** — Two static locations: `portfolio/static/` (project-level, currently minimal) and `portfolio_pages/static/` (app CSS, one file per page under `static/pages/`). `collectstatic` merges these into `staticfiles/`, served by Nginx directly (`location /static/`) in Docker; `MEDIA_ROOT` (`media/`) is also served directly by Nginx (`location /media/`), bypassing Django for both static and media in production.

**Nginx (`nginx/nginx.conf`)** — reverse proxies everything except `/static/` and `/media/` to the `web` (Gunicorn) container; `/nginx_status` (stub_status) is restricted to the Docker-internal `172.16.0.0/12` range only.

## Known rough edges

- `requirements.txt` is UTF-16 encoded (likely from a Windows tool) — re-save as UTF-8 if editing it by hand causes issues, or edit via a tool that round-trips the encoding correctly.
- `add_project.html` (template) and `nginx.conf` currently have uncommitted local changes — check `git diff` before assuming their on-disk state matches HEAD.
