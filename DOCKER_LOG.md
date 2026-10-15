# Multi-stage Docker Build – Learning Log

A running record of turning `portfolio/Dockerfile` into a multi-stage build: what was done,
why, the errors hit and how each was fixed.

- **Started:** 06/10/2026
- **Branch:** `jenkins-setup` (Step 9 Jenkins changes still uncommitted, left as-is on purpose)
- **Goals:** (1) understand how multi-stage builds work, (2) smaller final image, (3) run the container as a non-root user
- **How we test:** build and run locally on Docker Desktop first, then let Jenkins build it
- **Rule:** never paste a token, password or API key into this log (same rule as `JENKINS_LOG.md`)

---

## Roadmap

| # | Step | Status |
|---|------|--------|
| 0 | Baseline: build the **current** image locally, record its size and layers | Done (06/10/2026): 751 MB disk / 205 MB compressed |
| 1 | Concepts: what a stage is, `FROM ... AS name`, `COPY --from=name` | Done (06/10/2026) |
| 2 | Write the **builder** stage (compilers + install packages into a virtual env) | Done (06/10/2026): venv = 138 MB, all packages present |
| 3 | Write the **runtime** stage (clean slim image, copy only the finished virtual env + app) | Done (06/10/2026): code reviewed |
| 4 | Build locally, compare size with Step 0, run the container and check it starts | Done (06/10/2026): 86.4 MB compressed, full site works. 2 errors fixed (CRLF, nginx DNS) |
| 5 | Run as a **non-root user** (and fix any file-permission problems) | Done (06/10/2026): runs as `appuser` (UID 1000), code read-only, site works |
| 6 | Build through Jenkins and confirm the pipeline still works | Done (06/10/2026): `dev` build SUCCESS, `dev-latest` pushed. Fixed Jenkins socket access after the switch to WSL Docker (`group_add` 0 → 986) |
| 7 | Wrap-up: review questions, final notes | **Current**: Dockerfile commented (06/10/2026) |

---

## Glossary (fill in as we go)

| Term | Meaning in my own words |
|------|-------------------------|
| Image | A read-only template (stack of layers) that containers are started from |
| Layer | The filesystem change made by one Dockerfile instruction (`RUN`, `COPY`…). Layers stack; size adds up |
| Build context | The folder sent to Docker at build time (last argument of `docker build`), filtered by `.dockerignore` |
| Stage | One `FROM` line and everything under it, up to the next `FROM`. Each stage starts from a fresh base |
| Builder stage | An early stage with the heavy tools (compilers, headers) used only to produce files. Thrown away afterwards |
| Runtime / final stage | The **last** stage. The only one that becomes the image that's tagged and pushed |
| `COPY --from` | `COPY --from=<stage> <src> <dest>`: copy files from another stage's filesystem instead of from my laptop |
| Base image (`slim`) | The image after `FROM`. `slim` = Debian with only the minimum packages, so a smaller start |
| Non-root user | A normal Linux user the app runs as, so a hacked app can't act as root inside the container |
| Virtual env (venv) | A self-contained folder with its own Python packages. Easy to move as one unit with `COPY --from` |
| Wheel | A pre-built Python package (`.whl`). If one exists for my Python/OS, pip installs it without compiling |

---

## Step log

### Step 0 – Baseline: measure the current image (06/10/2026)

**Why:** we can't say "the multi-stage build made it smaller" without a number from *before*.

**Starting Dockerfile (single-stage), as of 06/10/2026**
```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y     libpq-dev     gcc     && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
COPY . .
EXPOSE 8000
ENTRYPOINT ["sh", "entrypoint.sh"]
```

**Observations before starting**
- `gcc` + `libpq-dev` = tools for **compiling** code. In a single-stage image they stay in the final image even though the running app never uses them.
- The container currently runs as **root** (no `USER` line).

**Commands run** (WSL Ubuntu terminal, from inside `portfolio/`, so the context is `.`)
```bash
docker build -t portfolio:single-stage .
docker images portfolio:single-stage
docker history portfolio:single-stage
```
- `-t name:tag` = label the image so we can find and compare it later.
- Last argument = **build context** (the folder sent to Docker; `.dockerignore` filters it).
- `docker history` = one row per layer, newest at the top.

**Results**
| Measure | Value |
|---|---|
| `DISK USAGE` (space used on my laptop) | **751 MB** |
| `CONTENT SIZE` (compressed, roughly what is pushed to Docker Hub) | **205 MB** |
| Layer: `apt-get install libpq-dev gcc` | **224 MB** ← biggest |
| Layer: `pip install` | **187 MB** |
| Layer: `COPY . .` (our app code) | 0.3 MB |
| Base image `python:3.12-slim` (Debian + Python layers) | ~134 MB (87.7 + 41.4 + 4.94) |
| Sum of all layers (uncompressed) | ~545 MB |
| Build time | not recorded |

**What the numbers tell me**
- **Compilers (224 MB) are bigger than all our Python packages (187 MB)**, and the running app never uses them. A multi-stage build can leave this layer out.
- The app code itself is tiny (0.3 MB). Nearly all the size is tools and libraries.
- **Why 751 MB and not 545 MB?** Docker Desktop's newer image store keeps both the **compressed** download (205 MB) and the **unpacked** layers (~545 MB) on disk: 545 + 205 ≈ 750. *(Inferred from the numbers adding up, not from documentation.)*
- `<missing>` in the IMAGE column is normal: BuildKit doesn't give intermediate layers their own image IDs. It is **not** an error.
- To watch later: the `pip install` line has no `--no-cache-dir`, so pip's download cache may be stored inside that 187 MB layer.

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

---

### Step 1 – Concepts (06/10/2026)

**Key ideas**
1. **Stage** = a `FROM` line + everything below it until the next `FROM`. Each `FROM` starts from a clean base image.
2. **`FROM <image> AS <name>`** names a stage, so later stages can refer to it.
3. **`COPY --from=<name> <src> <dest>`** copies files out of an earlier stage (not from the build context).
4. **Only the last stage becomes the image.** Anything not copied into it with `COPY --from` is thrown away.
5. Install packages into **one folder (a venv, e.g. `/opt/venv`)** in the builder, so a single `COPY --from` moves all of them.

**Planned shape**
```
Stage 1: builder                        Stage 2: runtime (final)
python:3.12-slim                        python:3.12-slim (fresh)
+ gcc, libpq-dev (224 MB)               COPY --from=builder /opt/venv
+ pip install -> /opt/venv    ──────►   COPY . . (app code)
(thrown away)                           (tagged + pushed)
```

**Check questions (answered by Claude at my request)**

**Q1. If the builder installs `gcc`, why isn't it in the final image?**
The final image is built **only** from the last stage. That stage starts from a fresh `python:3.12-slim`, which has no `gcc`, and we never `COPY --from` the compiler. The builder stage's layers are used during the build and then dropped.

**Q2. In `COPY --from=builder /opt/venv /opt/venv`, where does each path point?**
- 1st `/opt/venv` = the **source**, the folder inside the **builder stage's** filesystem.
- 2nd `/opt/venv` = the **destination** inside the **current (final) stage**.
- Same path on both sides on purpose: a venv's scripts have their own path written into them, so it should stay at the same location.

**Q3. Without `gcc` in the final stage, what might the app still need at run time?**
- Separate "**build-time**" needs (compilers, `-dev` header packages) from "**run-time**" needs (the shared libraries that compiled code loads when it runs).
- `psycopg2` (the PostgreSQL driver) needs the PostgreSQL client library **libpq** at run time. Normally you'd install `libpq5` in the final stage.
- **But** we use **`psycopg2-binary`**, a pre-built wheel that **bundles its own copy of libpq** inside the package. So copying the venv should bring libpq with it, and the final stage shouldn't need any `apt-get install`.
- **To verify in Step 4**, not assume: run the container and confirm Django connects to PostgreSQL (`migrate` succeeds).
- Follow-up thought: if every package in `requirements.txt` has a ready-made wheel, `gcc`/`libpq-dev` may not be needed **even in the builder**. Decision to make in Step 2.

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

---

### Step 2 – Builder stage (06/10/2026)

**Decision: keep `gcc` + `libpq-dev` in the builder** (I asked Claude to pick the best option)
- Standard pattern, which matches my goal of learning the concept.
- Safer: if a package ever has no ready-made wheel (e.g. after a Python upgrade), pip can still compile it.
- Costs nothing in the final image, because the builder is thrown away.
- Possible later experiment: remove them and see whether pip still installs everything from wheels.

**Plan for this step**
- Add the builder stage at the **top** of `portfolio/Dockerfile`. Leave the old lines underneath **unchanged for now** (they get rewritten in Step 3).
- Build **only** the builder with `--target builder` and look inside it.

**Code (typed by me, reviewed by Claude: correct)**
```dockerfile
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev  \
        && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
```
- Change from the plan: I **removed the old single-stage lines** instead of leaving them below. That's fine: the builder is now the only (and last) stage, and the original is kept in Step 0 above and in git.
- Extra lines I added: the two `PYTHON...` `ENV` lines in the builder. Harmless; they only really matter in the final stage, where the app runs.

**Line-by-line notes**
- `FROM ... AS builder`: names the stage for `COPY --from=builder` later.
- `\` at the end of a line = the command continues on the next line.
- `--no-install-recommends`: only strictly required packages, so a faster build.
- `rm -rf /var/lib/apt/lists/*` in the **same** `RUN`: the apt index is never saved into a layer.
- `python -m venv /opt/venv`: all packages go into one folder, so it's easy to copy.
- `ENV PATH="/opt/venv/bin:$PATH"`: makes the venv's `pip`/`python` the default. `ENV` instead of `activate`, because each `RUN` is a new shell (same lesson as Jenkins Q2).
- `COPY requirements.txt .` before the code: the slow `pip install` layer is reused from cache when only code changes.
- `--no-cache-dir`: pip doesn't keep its download cache in the layer.
- Test one stage on its own: `docker build --target builder -t portfolio:builder .`

**Q (me): what is `--target`?**
- `--target <stage>` = build up to and including that stage, stop there, and tag **that** stage as the image.
- Without it, Docker builds to the **last** stage.
- Uses: debugging (check the builder on its own), checking what will be copied, picking special stages (e.g. `test`) in real projects.
- **Right now** there's only one stage, so `--target builder` = no flag at all. It only makes a difference once Step 3 adds the second stage.

**Q (me): explain the check commands**
- `docker run --rm portfolio:builder pip list`
  - `docker run` = start a **container** (a running copy) from an **image** (the template).
  - `--rm` = delete the container when it exits (otherwise stopped containers pile up in `docker ps -a`).
  - `portfolio:builder` = the image to use.
  - `pip list` = the command run **inside** the container, instead of the image's default. Thanks to `ENV PATH`, `pip` = `/opt/venv/bin/pip`, so it lists the **venv's** packages.
- `docker run --rm portfolio:builder du -sh /opt/venv`
  - `du` = disk usage, `-s` = one total, `-h` = human-readable (e.g. `150M`).
  - Tells me roughly how much the venv will add to the final image (compare with the 187 MB `pip install` layer in Step 0).
- The builder has no `ENTRYPOINT`/`CMD`, so whatever I type after the image name is what runs. The final stage will have an `ENTRYPOINT`, which changes how I test it (Step 4).

**Results**
| Measure | Value |
|---|---|
| `portfolio:builder` DISK USAGE | 651 MB (single-stage was 751 MB) |
| `portfolio:builder` CONTENT SIZE | 163 MB (single-stage was 205 MB) |
| `/opt/venv` size (`du -sh`) | **138 MB** (the single-stage `pip install` layer was 187 MB) |
| `pip list` | All 15 packages from `requirements.txt` + their dependencies (`botocore`, `s3transfer`, `jmespath`, `urllib3`, `python-dateutil`, `six`) + `pip 26.2.1` ✅ |

**What the numbers tell me**
- The packages really are in **`/opt/venv`**, so one `COPY --from` will move all of them.
- The builder is **already smaller** than the old image, although it still contains `gcc`. Probable reasons (not measured one by one): `--no-cache-dir` (no pip download cache in the layer) and `--no-install-recommends` (fewer apt extras).
- 138 MB = roughly what the Python packages will add to the **final** image.
- **Rough estimate** for the final image (uncompressed): base ~134 MB + venv 138 MB + code 0.3 MB ≈ **272 MB**, compared with ~545 MB before. To be confirmed in Step 4.
- Dependencies I didn't list myself (e.g. `botocore`) come in automatically because `boto3` needs them.

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| `docker run --rmi portfolio:bu…` (typo, didn't run) | Typed `--rmi` instead of `--rm`. `--rmi` is a `docker compose down` option, not a `docker run` one | Retyped with `--rm`. No harm done |

---

### Step 3 – Runtime (final) stage (06/10/2026)

**Q (me): why `FROM python:3.12-slim` and not a distroless image?**
- **Distroless** (`gcr.io/distroless/...`) = only the language runtime + libraries. **No shell, no apt, no pip, no `ls`/`cat`.** Smaller, fewer programs to attack, but very hard to debug.
- Why it doesn't fit **right now**:
  1. `ENTRYPOINT ["sh", "entrypoint.sh"]` needs `sh`, which distroless doesn't have, so the container wouldn't start. The startup logic (`sleep`, `migrate`, `collectstatic`, `exec gunicorn`) would need rewriting.
  2. Distroless Python = Debian's system Python, **not 3.12** (Debian 12 variant believed to be 3.11, *unverified*). A venv and compiled wheels built for 3.12 won't run on a different Python version, so the builder base would have to change too.
  3. Harder to look inside while learning (`docker exec ... sh` impossible).
  4. Google's README has (I believe) called the Python image *experimental*. *Unverified, check before using.*
- **Decision (06/10/2026):** stay on `python:3.12-slim`. Distroless **not** added to the roadmap ("slim is enough").
- **Rule learned:** builder and final stage must use the **same Python version, in the same location**, or the copied venv breaks.

**Full Dockerfile after Step 3 (typed by me, reviewed by Claude: correct)**
```dockerfile
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev  \
        && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------- Stage 2: runtime (final image) ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

EXPOSE 8000
ENTRYPOINT ["sh", "entrypoint.sh"]
```
- I removed the two `ENV PYTHON...` lines from the builder (they're only needed where the app runs). Good.

**Line-by-line notes (runtime stage)**
- 2nd `FROM` = **fresh start**: no `gcc`, no `libpq-dev`, nothing from the builder unless I copy it.
- Same base (`python:3.12-slim`) as the builder, because the venv links to `/usr/local/bin/python`.
- ⚠️ **`ENV` does NOT carry across stages.** `PATH` must be set again, or `entrypoint.sh` runs the system `python`/`gunicorn`, which have no packages (`ModuleNotFoundError` / `gunicorn: not found`).
- `PYTHONUNBUFFERED=1` = logs show up immediately in `docker logs`. `PYTHONDONTWRITEBYTECODE=1` = no `.pyc` files written at run time.
- `COPY --from=builder /opt/venv /opt/venv` = **the multi-stage line**. Only the venv crosses over.
- `COPY . .` = app code from my laptop (the build context, filtered by `.dockerignore`).
- Venv before code: the code changes more often, so the venv layer stays cached.
- No `USER` yet. The non-root user is Step 5 (one change at a time).

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

---

### Step 4 – Build, compare, run (06/10/2026)

#### 4a – Build and measure

**Commands**
```bash
docker build -t portfolio:multi-stage .          # no --target = build to the LAST stage
docker images portfolio
docker history portfolio:multi-stage
docker run --rm --entrypoint which portfolio:multi-stage gcc python gunicorn
```
- `--entrypoint which` = temporarily **replace** `sh entrypoint.sh` with another program, so I can look inside without starting the app (which would need a database).

**Results: before vs after**
| Measure | Single-stage (Step 0) | Multi-stage | Change |
|---|---|---|---|
| DISK USAGE | 751 MB | **365 MB** | **−386 MB (−51%)** |
| CONTENT SIZE (compressed, pushed to Docker Hub) | 205 MB | **86.4 MB** | **−119 MB (−58%)** |
| Compilers layer (`apt-get install gcc libpq-dev`) | 224 MB | **gone** | −224 MB |
| Python packages layer | 187 MB (`pip install`) | 144 MB (`COPY /opt/venv`) | −43 MB |
| App code (`COPY . .`) | 0.3 MB | 0.3 MB | same |

**Checks**
- `docker history`: **no `apt-get install gcc` layer** in the final image ✅. The only big new layer is `COPY /opt/venv` (144 MB).
- `which gcc` printed **nothing**, so the compiler isn't in the final image ✅
- `which python` → `/opt/venv/bin/python`, `which gunicorn` → `/opt/venv/bin/gunicorn`. The `PATH` line in the final stage works ✅

**Notes**
- **138M (`du`) vs 144 MB (`history`) is the same data in different units.** `du -h` uses MiB (1 MiB = 1,048,576 bytes); Docker uses MB (1,000,000 bytes). 138 MiB ≈ 145 MB.
- Numbers add up: layers ≈ 134 (base) + 144 (venv) + 0.3 (code) ≈ 278 MB unpacked, + 86 MB compressed ≈ **365 MB** disk usage (same pattern as Step 0).
- Step 2 estimate was ~272 MB unpacked. Actual ~278 MB, so close.
- The **compressed size** matters most for CI/CD: Jenkins pushes and the staging/prod VMs pull **~86 MB instead of ~205 MB** each deploy.

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

#### 4b – Run the full stack with docker compose

**Why:** 4a proved the image is **smaller**. 4b proves it **works**, especially the Step 1 prediction that `psycopg2-binary` brings its own libpq (so `migrate` against real PostgreSQL must succeed).

**Decision (06/10/2026):** run the **full** `docker-compose.yml` (db, web, nginx, prometheus, grafana) rather than a throwaway Postgres or SQLite.

**What compose needs (found by reading the files)**
- No `portfolio/.env` existed, so I create one with **dummy test values only** (never real secrets).
- `portfolio/.env` is **git-ignored** (`.gitignore` line 3) and **docker-ignored** (`.dockerignore`), so it can't be committed or baked into the image.
- `.env` does two jobs:
  1. **Compose itself** reads it to fill in `${...}` in the YAML: `PORTFOLIO_IMAGE` (which image `web` uses), `GRAFANA_PASSWORD`, `EMAIL`, `EMAIL_PASSWORD`, and `$POSTGRES_USER`/`$POSTGRES_DB` in the db healthcheck.
  2. `env_file: - .env` passes **all** of it into the `db` and `web` containers as environment variables.
- Required by `settings.py` (no default): `SECRET_KEY`, `ALLOWED_HOSTS`, `DB_PASSWORD`. `DB_HOST` defaults to `db` (= the compose service name).
- Postgres image needs `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and these must match Django's `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- Ports used on my laptop: **80** (nginx), **9090** (prometheus), **3000** (grafana).

**First run: `web` crash-loops, browser shows nginx `502 Bad Gateway`**
```
: not foundtrypoint.sh: 2:
web-1  | entrypoint.sh: 3: set: Illegal option -
(repeats)
```
- **Cause: Windows line endings (CRLF) in `entrypoint.sh`.**
  - `git config core.autocrlf` = `true`, so on **checkout on Windows** Git turns LF into CRLF.
  - `git ls-files --eol` showed `i/lf  w/crlf  portfolio/entrypoint.sh`: **LF in the repo, CRLF on my disk**.
  - `COPY . .` copied the CRLF file into the image. Linux `sh` reads the `\r` as part of each command:
    - empty line 2 → command `\r` → `not found`
    - line 3 `set -e\r` → `set: Illegal option -`
- **Why the log line looks scrambled:** the message contains `\r` (= "go back to the start of the line"), so the end of the line overwrites the beginning. Real text: `web-1 | entrypoint.sh: 2: \r: not found`.
- **Why it repeats:** `restart: unless-stopped` in compose keeps restarting the crashed container.
- **Why 502 Bad Gateway:** nginx is fine but forwards to `web:8000`, where nothing is listening (gunicorn never started).
- **Why Jenkins never hit this:** Jenkins checks out on **Linux**, so it gets LF.
- **Not caused by the multi-stage change.** The single-stage image built from this folder would fail the same way.

**Fix options considered**
| Option | Fixes | Downside |
|---|---|---|
| `.gitattributes` with `*.sh text eol=lf` | Root cause, every machine, permanently | One more file to commit |
| `RUN sed -i 's/\r$//' entrypoint.sh` in Dockerfile | Every build, however the file was checked out | Hides the cause; only that one file |
| **Convert the file to LF in VS Code** ← **chosen (06/10/2026)** | My copy, right now | ⚠️ **Can come back**: a fresh clone, or Git rewriting the file (e.g. some checkouts/branch switches), may turn it back to CRLF because `core.autocrlf=true` |

- If this error ever comes back: check `git ls-files --eol portfolio/entrypoint.sh`. If it shows `w/crlf`, convert again or switch to the `.gitattributes` fix.

**Fix applied**
1. VS Code → status bar `CRLF` → `LF` → save `entrypoint.sh`.
2. `docker build -t portfolio:multi-stage .` (builder `CACHED`; only `COPY . .` rebuilt).
3. `docker compose up -d --force-recreate web` = replace only the `web` container with one from the new image; the other 4 keep running.

**Second run: success ✅**
| Service | Status |
|---|---|
| db (`postgres:16-alpine`) | Up (**healthy**) |
| web (`portfolio:multi-stage`) | **Up**, no restarts |
| nginx | Up, port 80 |
| prometheus | Up, port 9090 |
| grafana | Up, port 3000 |

What `docker compose logs web` proves:
- **All 32 migrations `OK` against real PostgreSQL**, so `psycopg2-binary` brought its own libpq. **Step 1 prediction confirmed:** no `libpq-dev`/`libpq5` needed in the final stage.
- `140 static files copied to '/app/staticfiles'`: Django + collectstatic work from the venv.
- `Starting gunicorn 26.0.0` / `Listening at: http://0.0.0.0:8000` / 3 workers booted: `PATH` → `/opt/venv/bin/gunicorn` works.
**But the browser still showed `502 Bad Gateway`**

`docker compose logs nginx --tail 10`:
```
10:49:33 [notice] start worker process ...
10:50:35 [error] connect() failed (111: Connection refused) while connecting to upstream ... upstream: "http://127.0.53.53:8000/"
10:54:18 [error] ... same ...
```
- Claude's first guess: nginx cached the **old** web container's IP. **Partly wrong**: the upstream is **`127.0.53.53`**, not a container IP.
- **`127.0.53.53`** = a special warning address that internet DNS servers return for bare names that clash with a top-level domain. **`web` is one (`.web` is a TLD).**
- **What happened** (best explanation from the evidence):
  1. 10:49:33: nginx started and resolved `web` **once** (an `upstream { server web:8000; }` block is only resolved at startup).
  2. `web` was crash-looping (CRLF), so **Docker's internal DNS didn't know it** (it only answers for running containers) and passed the question to **normal internet DNS** → `127.0.53.53`.
  3. `127.0.0.0/8` = loopback, so nginx connected to **itself** on port 8000 → `Connection refused` → 502.
  4. Fixing `web` at 10:53 didn't help: nginx never looked the name up again.
- **Lesson:** after `web` restarts or is recreated, **restart nginx too**. Or make nginx start only after web is healthy (possible improvement later).
- Side issue: the terminal showed `>` = the shell was waiting for a closing quote (a stray `'` in the `docker inspect` command). **Ctrl+C** to escape.
- Fix: `docker compose restart nginx`. **Result: http://localhost loads fully, with all CSS ✅**

**Step 4 outcome**
- Multi-stage image = **−58% compressed / −51% on disk** and **works the same as before**: PostgreSQL migrations, collectstatic, gunicorn, nginx static files, page + CSS.
- Not checked: `git ls-files --eol portfolio/entrypoint.sh` output (should show `w/lf`). The app starting proves the image copy is LF.

- 📝 **Note for Step 5:** `Control socket listening at /root/.gunicorn/gunicorn.ctl`. **`/root/` proves the container is running as root.** When we switch to a non-root user, gunicorn won't be able to write into `/root/`, so watch this line.

---

### Step 5 – Non-root user (06/10/2026)

**Why**
- The container currently runs as **root** (gunicorn log: `/root/.gunicorn/gunicorn.ctl`).
- If the app is hacked, the attacker's code runs as root inside the container: full control, and an easier escape to the host. A normal user limits the damage.

**How**
- `RUN useradd ...` = create a normal user in the image.
- `USER <name>` = every later instruction **and the running container** use that user.

**What the app writes at run time (needs write permission)**
| Path | Written by |
|---|---|
| `/app/staticfiles` | `collectstatic` in `entrypoint.sh` |
| `/app/media` | user uploads (project images, CV) |
| `~/.gunicorn/` | gunicorn control socket, so the user needs a **home folder** |
- Everything else (`/app` code, `/opt/venv`) only needs **read**. Keeping it root-owned is **more secure** (the app can't change its own code).

**⚠️ Must decide before Step 6 (pushing to `dev`)**
- `static_volume` / `media_volume` on the **staging/prod VMs** were created by the **root** container, so their files are **root-owned**. A non-root container may get **permission denied** (crash-loop) there.
- `media_volume` contains **real uploads**, so it must **not** be deleted to fix this.
- Locally this is solved by starting with fresh volumes (`docker compose down -v`), which **deletes local test data only**.

**Decisions (06/10/2026)**
- User: **`appuser`, UID 1000** (fixed UID, so volume file ownership stays the same across rebuilds).
- Staging/prod VMs: `media_volume` holds **test data only**, so it's safe to **recreate the volumes** on the VMs when the non-root image is deployed (exact steps to plan in Step 6).

**Runtime stage after Step 5 (typed by me, reviewed by Claude: correct)**
```dockerfile
# ---------- Stage 2: runtime (final image) ----------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN mkdir -p /app/staticfiles /app/media \
    && chown appuser:appuser /app/staticfiles /app/media

USER appuser

EXPOSE 8000
ENTRYPOINT ["sh", "entrypoint.sh"]
```

**Line-by-line notes**
- `useradd --create-home --uid 1000 appuser`: a normal user with home `/home/appuser` (gunicorn's control socket needs it) and a fixed UID (Linux tracks ownership by **number**). A matching `appuser` group is created too. Placed early, so it's cached.
- `mkdir -p` is needed because `.dockerignore` excludes `staticfiles/` and `media/`, so they don't exist in the image.
- `chown appuser:appuser` **only** on the two folders the app writes to. Code and venv stay root-owned = read-only for the app.
- **New empty named volume** mounted on a folder → Docker first copies that folder's contents **and owner** from the image. So fresh volumes become appuser-owned; **old root-created volumes don't change**.
- `USER appuser` after the root-only commands, before `EXPOSE`/`ENTRYPOINT`. Applies to the running container.
- The builder stage stays root (it's thrown away).

**Test commands**
```bash
docker compose down -v                 # -v also DELETES named volumes (local test data only, never on a real server)
docker build -t portfolio:multi-stage .
docker compose up -d
docker compose ps
docker compose logs web --tail 15
docker compose exec web id             # exec = run a command inside the RUNNING container
docker compose exec web touch /app/hacked.txt   # supposed to FAIL
```

**Results ✅**
| Check | Result |
|---|---|
| `compose up` | 6 fresh volumes created; all 5 containers up; db healthy |
| Migrations + collectstatic | All `OK`, `140 static files copied`, so appuser **can write** `/app/staticfiles` |
| Gunicorn control socket | `/home/appuser/.gunicorn/gunicorn.ctl` (was `/root/...`) |
| `id` | `uid=1000(appuser) gid=1000(appuser) groups=1000(appuser)` |
| `touch /app/hacked.txt` | `Permission denied`, so the app **can't change its own code** |
| Browser http://localhost | Page loads with full CSS |
| nginx 502? | No: `web` was running (not crash-looping) when nginx started, so the name resolved correctly first time |

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

---

### Step 6 – Through Jenkins to staging (06/10/2026)

**Facts that shape this step**
- The Jenkinsfile only runs `docker build` on **`dev`** (staging) and **`main`** (production). On `jenkins-setup` only the Test stage runs, so it **doesn't** test the Dockerfile.
- Pushing to `dev` → Jenkins pushes `iamkaushal20/portfolio:dev-latest` → the staging VM's cron pulls it. The VM's **old root-owned volumes** would make the non-root container crash-loop (permission denied on `/app/staticfiles`).
- Jenkins checks out on **Linux**, so `entrypoint.sh` gets LF there (no CRLF problem).

**Decisions (06/10/2026)**
- Test by **merging to `dev`** (a real end-to-end staging deploy).
- **One commit** containing everything: Step 9 Jenkins work + Dockerfile + `DOCKER_LOG.md`.

**Pre-commit check (Claude, 06/10/2026)**
| File | Status | Note |
|---|---|---|
| `portfolio/Dockerfile` | modified | multi-stage + non-root |
| `DOCKER_LOG.md` | new | this log |
| `Jenkinsfile`, `JENKINS_LOG.md` | modified | Step 9 work |
| `portfolio/portfolio_pages/templates/add_project.html` | modified | ⚠️ only change: `remove.` → `remove..` (double full stop), probably left over from the trigger test |
| `portfolio/entrypoint.sh` | shows `M` but **no content diff** | Git only noticed the file was re-saved. Line endings: `i/lf w/lf` ✅. Git warns `LF will be replaced by CRLF the next time Git touches it`, which confirms the local fix is fragile |
| `portfolio/.env` | not listed | git-ignored ✅ (test values stay local) |

**Decision (06/10/2026): scope of Step 6 = confirm the Jenkins pipeline runs successfully. Staging VM checks skipped.**
- `add_project.html` change (`remove..`) kept as-is.
- ⚠️ **Known risk accepted:** the staging VM's cron will pull the new `dev-latest`. Its **old root-owned volumes** may make `web` crash-loop (permission denied) → staging shows 502. Test data only. Fix if it happens: recreate the volumes on the VM (`docker compose down -v`, then `up -d` **on the VM**). Jenkins will still be green, because it only builds and pushes.
- Open questions left for later: the staging VM's cron command, and whether staging/prod share one VM.

**Commands (typed by me)**
```bash
# 1. Commit everything on jenkins-setup and push
git add DOCKER_LOG.md JENKINS_LOG.md Jenkinsfile portfolio/Dockerfile portfolio/portfolio_pages/templates/add_project.html
git commit -m "Multi-stage non-root Dockerfile + Jenkins step 9 tidy-up"
git push

# 2. Merge into dev and push (this triggers the staging build)
git switch dev
git pull origin dev
git merge jenkins-setup
git push origin dev
git switch jenkins-setup
```

**Results**

**`dev` build (commit `2109dba`): FAILURE ❌, before the Dockerfile was even used**
```
[Pipeline] { (Test)
+ docker inspect -f . python:3.12
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
+ docker pull python:3.12
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
Stage "Deploy staging" skipped due to earlier failure(s)
...
Finished: FAILURE
```
- Git, the commit, the merge and the polling trigger all worked: Jenkins checked out `2109dba` with my commit message ✅
- It failed in the **Test** stage, at the very first Docker command (checking for the `python:3.12` image). **The Dockerfile was never reached.** Not caused by the multi-stage change.
- **Meaning:** the Jenkins container's user (`jenkins`, UID 1000) is **not allowed to use the Docker socket** `/var/run/docker.sock`, the "phone line" from the Jenkins container to Docker Desktop's engine. It worked on 02/10/2026, so something changed since then.
- How socket access was originally granted was **not recorded** in `JENKINS_LOG.md`. Diagnosing first.
- **Root cause (likely): I switched from Docker Desktop to Docker Engine inside WSL Ubuntu.**
  - Docker Desktop's socket setup let the container's `jenkins` user (UID 1000) in.
  - The WSL engine creates the socket the standard Linux way: owner `root`, group `docker`, mode `660` = only root and members of the `docker` group.
  - The `jenkins` user in the container is **not** in that group → `permission denied`.
  - Linux checks **numbers (GIDs)**, not names. The Jenkins container needs the **GID** of WSL's `docker` group (e.g. via `--group-add <GID>` when the container is created).
  - (This also explains why Claude's Windows-side `docker ps` couldn't find Docker Desktop's engine.)
- Diagnostics requested: `getent group docker`, `ls -ln /var/run/docker.sock`, `docker exec <jenkins> id`, `docker inspect` (User/GroupAdd/Binds/Ports), plus how Jenkins was started (`docker run` or compose).

**Diagnostics: results so far**
| Command (in WSL) | Output | Meaning |
|---|---|---|
| `getent group docker` | `docker:x:986:kaushal20` | WSL `docker` group = **GID 986**; my user is a member |
| `ls -ln /var/run/docker.sock` | `srw-rw---- 1 0 986 ... Oct 6 08:21` | `s` = socket. Owner UID **0** (root), group **986**, `rw-rw----` = only root and group 986 can use it. Created 08:21 today (engine start) |
| `docker ps` | `jenkins  my-jenkins  Up 4 hours` | Container **name = `jenkins`**, **image = `my-jenkins`** (a custom image), running on the WSL engine |

- **Lesson: `<name>` in instructions is a placeholder.** Replace it **including the `< >`**. In bash, `<` = read from a file and `>` = write to a file, which is why `docker exec <jenkins> id` gave `jenkins: No such file or directory` and `... <jenkins>` gave `syntax error near unexpected token 'newline'`.
- **Container name ≠ image name.** `docker exec`/`inspect` need the **name** (`jenkins`), not the image (`my-jenkins`) → `No such container: my-jenkins`.

| Command | Output | Meaning |
|---|---|---|
| `docker exec jenkins id` | `uid=1000(jenkins) gid=1000(jenkins) groups=1000(jenkins),0(root)` | Jenkins user is in groups **1000 and 0**, **not 986** |
| `docker inspect ... jenkins` | `User=jenkins GroupAdd=[0] Binds=[jenkins_home:/var/jenkins_home:rw /var/run/docker.sock:/var/run/docker.sock:rw] Ports=8080→8080` | Created with **`--group-add 0`**; data in the **named volume `jenkins_home`**; socket mounted; port 8080 |

**✅ Root cause confirmed**
- With **Docker Desktop**, the socket's group was (inferred) **0**, and Jenkins was given `--group-add 0`, so it worked.
- With the **WSL engine**, the socket's group is **986**. Jenkins is in 1000 and 0 only → `permission denied`.

**Fix options**
| Option | Pros | Cons |
|---|---|---|
| **Re-create the container with `--group-add 986`** ← **chosen (06/10/2026)** | Permanent, minimal access (only Jenkins gets it) | Container must be re-created with exactly the same settings |
| `sudo chmod 666 /var/run/docker.sock` | One command | **Security hole** (anyone can control Docker = root); lost on every engine restart |

**Condition from me: the `jenkins_home` volume must be preserved.**
- A **named volume** exists separately from containers. Stop, rename and `rm` of a container **do not delete it**. Only `docker volume rm jenkins_home` (or `compose down -v`) would.
- Plan: **back up** the volume to a file → stop → **rename** the old container to `jenkins-old` (rollback, not deleted) → create a new `jenkins` with the same settings + `--group-add 986`, using the **same volume**.
- ⚠️ `986` is the GID of **this** WSL install's `docker` group. If Docker is reinstalled, check `getent group docker` again.
- Still to collect: restart policy, network, env vars (`-e`), volume list.

**Remaining settings collected**
| Command | Output | Meaning |
|---|---|---|
| Restart / Network | `Restart=on-failure Network=jenkins_default` | Restarts only on a crash. Network name `<project>_default` = **compose naming**, so Jenkins was probably started by a **compose project called `jenkins`** |
| Env vars | `JENKINS_HOME`, `JAVA_HOME`, `JENKINS_VERSION=2.580.1`, `JENKINS_SLAVE_AGENT_PORT=50000`, etc. | All defaults from the Jenkins image. **No custom `-e`, no secrets** |
| `docker volume ls` | `jenkins_home` present | Named volume exists ✅ |

- **If it's compose:** the fix = add `group_add: ["986"]` to the compose file and let compose re-create the container (same volume). Better than a hand-typed `docker run`, which would drift from the compose file.
- Confirming via compose labels: `com.docker.compose.project`, `...project.working_dir`, `...project.config_files`.

**✅ Confirmed: Jenkins is managed by compose**, file `Desktop/jenkins/docker-compose.yml` (builds image `my-jenkins`, container `jenkins`, `restart: on-failure`, port 8080, socket mount).
- The file had:
  ```yaml
  group_add:
    - "0"        # written for Docker Desktop's socket (group 0)
  ```
- And `volumes: jenkins_home: name: jenkins_home`, a **fixed volume name**, so compose re-uses the **same** volume on re-create. Data safe.
- **Fix = change `"0"` → `"986"`**, then `docker compose up -d` in `Desktop/jenkins`.
- **Plan change:** no `jenkins-old` rename. Compose tracks containers by **labels**, not names, so a renamed copy would confuse it. Backup = a `.tgz` of the volume; rollback = set `"0"` again and `up -d`.

**Fix commands (typed by me)**
```bash
cd /mnt/c/Users/KaushalRupakhetiRent/Desktop/jenkins
docker compose stop                     # stop only, removes nothing
docker run --rm -v jenkins_home:/data:ro -v "$HOME":/backup alpine \
  tar czf /backup/jenkins_home_backup_2026-10-06.tgz -C /data .
ls -lh ~/jenkins_home_backup_2026-10-06.tgz
# then edit docker-compose.yml: group_add "0" -> "986"
```
- `:ro` = mount the volume read-only, so the backup can't change it.
- `tar czf` = create a gzip-compressed archive. `-C /data .` = everything inside `/data`.
- Restore, if ever needed: `docker run --rm -v jenkins_home:/data -v "$HOME":/backup alpine tar xzf /backup/jenkins_home_backup_2026-10-06.tgz -C /data`

**Done (06/10/2026)**
- Backup: `/home/kaushal20/jenkins_home_backup_2026-10-06.tgz`, **581 MB** ✅ (owned by `root` because `alpine` ran as root, so deleting it needs `sudo rm`).
- Compose edited (reviewed: correct):
  ```yaml
  # Add the 'jenkins' user to the group that owns /var/run/docker.sock.
  # Docker Engine in WSL: group 'docker' = GID 986 (check: getent group docker).
  # (Was "0" when using Docker Desktop.)
  group_add:
    - "986"
  ```

**Next: re-create and check**
```bash
docker compose up -d                      # in Desktop/jenkins; NO --build
docker exec jenkins id                    # expect groups=1000(jenkins),986
docker exec jenkins docker ps             # Docker CLI inside Jenkins can reach the engine
```
- Why **no `--build`**: the image `my-jenkins` already exists. `--build` would rebuild it from the Dockerfile and could pull a **newer Jenkins version**, which is a second change at the same time. One change at a time.

**Results ✅ socket access fixed**
| Check | Output |
|---|---|
| `docker compose up -d` | `Container jenkins Started`. The new ID `d987e6e73707` (created 11 s earlier) shows it **was** re-created, although compose only said "Started" |
| `docker exec jenkins id` | `groups=1000(jenkins),986`, so the jenkins user is now in the socket's group (no name shown, because the group has no name inside the container; only the number matters) |
| `docker exec jenkins docker ps` | Lists all containers, so **the Docker CLI inside Jenkins reaches the WSL engine** (was `permission denied`) |
- Still to check: Jenkins UI data intact (login, `portfolio-site` job + history), then re-run the `dev` build.

**`dev` build re-run (Build Now, commit `2109dba`): `Finished: SUCCESS` ✅**
| Look for | Seen in console | ✅ |
|---|---|---|
| Jenkins data survived | `Started by user kaushal Rupakheti`, `using credential github-creds`, `dockerhub-creds` login worked, same workspace | ✅ volume preserved |
| Socket fix in a real pipeline | `docker inspect` / `docker pull python:3.12` worked (no `permission denied`) | ✅ |
| `error: no such object: python:3.12` | **Not an error**: the WSL engine has an **empty image cache**, so it pulled the image once. Next builds will skip the pull | ✅ |
| Build context | `transferring context: 157.14kB` | ✅ `.dockerignore` still working |
| Both stages built | `[builder 1/6]`…`[builder 6/6]` and `[stage-1 2/6]`…`[stage-1 6/6]` | ✅ |
| Multi-stage copy | `#13 [stage-1 4/6] COPY --from=builder /opt/venv /opt/venv` | ✅ |
| Non-root | `[stage-1 2/6] RUN useradd --create-home --uid 1000 appuser`, `[stage-1 6/6] ... chown appuser:appuser` | ✅ |
| Pushes | `dev-latest: digest: sha256:84dedd…` and `dev-2109dba…: digest: sha256:84dedd…` (**same digest** = same image, two tags) | ✅ |
| Production skipped | `Stage "Deploy production" skipped due to when conditional` | ✅ correct on `dev` |
| Logout | Post Actions → `Removing login credentials` | ✅ |

**Things worth noticing in the log**
- **Stages build in parallel.** `#7 [stage-1 2/6] RUN useradd` finished **while** `#6 [builder 2/6] apt-get install` was still running. BuildKit sees that the runtime stage doesn't need the builder **until** `COPY --from=builder`, so it starts the independent steps early. Another multi-stage benefit: faster builds.
- **`stage-1`** = BuildKit's automatic name for my **unnamed** second stage (stages are numbered from 0: `builder` = stage 0).
- **Nothing was `CACHED`**, because the WSL engine is new and has no build cache yet. The next `dev` build should show `CACHED` for most builder steps.
- **Second push: `Layer already exists`** everywhere. Docker Hub already had every layer from the first tag, so the second tag cost almost nothing.
- **`debconf: unable to initialize frontend: Dialog ...`** = apt has no keyboard/screen inside a build, so it falls back to non-interactive mode. **Harmless warnings.** (Optional tidy-up: `ENV DEBIAN_FRONTEND=noninteractive` in the builder, or prefix the apt command with it.)
- `Timeout set to expire in 1 hr 0 min` appears even though production was skipped. The `options { timeout }` wrapper starts before the `when` check decides to skip. Harmless.

**Still open (outside Jenkins)**
- ⚠️ Staging VM: its cron will now pull the new non-root `dev-latest`. If the site shows 502 / `web` crash-loops with permission denied → recreate the volumes **on the VM** (test data only).
- `main` (production) not run yet. When merged, the approval prompt will appear first.

---

### Step 7 – Wrap-up (06/10/2026)

**Comments added to `portfolio/Dockerfile`** (by Claude at my request)
- Header block: what each stage does, why only the last stage ships, and the "same base image in both stages" rule.
- One short comment per section explaining **why** (not just what): apt minimal install, venv + `ENV PATH`, layer-cache order, `--no-cache-dir`, `ENV` not carrying across stages, fixed UID, the writable folders + volume ownership, `USER`, and the LF line-ending requirement for `entrypoint.sh`.
- **No instruction changed.** Checked by comparing all non-comment lines with the committed version: `INSTRUCTIONS IDENTICAL`. So the image builds exactly the same (only the Dockerfile layer metadata changes).
- Not committed yet (I run git myself).
- Side note: `Post Actions` still ran `docker logout` → `Removing login credentials` even after the failure. **Step 9 `post { always }` is confirmed working** ✅ (logout only touches a local file, so it doesn't need the socket).

---

## Error index (all steps)

| Step | Error message (short) | Root cause | Fix |
|------|----------------------|-----------|-----|
| 4b | `entrypoint.sh: 3: set: Illegal option -`, `: not found`, nginx `502 Bad Gateway` | `core.autocrlf=true` checked out `entrypoint.sh` with CRLF on Windows; `COPY . .` put it in the image; `sh` reads `\r` as part of commands | Converted `entrypoint.sh` to LF in VS Code, rebuilt, `docker compose up -d --force-recreate web`. ⚠️ Local fix only; can return on a fresh clone (permanent fix = `.gitattributes` `*.sh text eol=lf`) |
| 4b | Still `502`; nginx log `upstream: "http://127.0.53.53:8000/"`, `111: Connection refused` | nginx resolves `web` only at startup; `web` was down then, so internet DNS answered `127.0.53.53` (TLD-clash warning address) | `docker compose restart nginx`. Page + CSS load ✅ |
| 6 | Jenkins `dev` build: `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock` | Switched Docker Desktop → Docker Engine in WSL. Socket is now group **986**; Jenkins compose had `group_add: "0"` (Docker Desktop's socket group) | Backed up `jenkins_home` (581 MB .tgz); `Desktop/jenkins/docker-compose.yml` `group_add` → `"986"`; `docker compose up -d` (no `--build`). Re-run: SUCCESS ✅ |
| 6 | `<jenkins>`: `No such file or directory` / `syntax error near unexpected token 'newline'` | Typed the placeholder `<...>` literally; `<` `>` are bash redirections | Use the real name without `< >` |
| 6 | `No such container: my-jenkins` | Used the **image** name; `docker exec` needs the **container** name | `docker exec jenkins ...` |
