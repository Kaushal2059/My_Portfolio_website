# Jenkins CI/CD – Learning Log

A running record of everything done while moving the portfolio-site CI/CD from
GitHub Actions to Jenkins: what was done, why, the errors hit and how each was fixed.

- **Started:** 30/09/2026
- **Goal:** Rebuild the pipeline from `.github/workflows/deploy.yml` in Jenkins (AWS job left out for now)
- **Environments:** Staging (`dev` branch → `portfolio:dev-latest`) and Production (`main` branch → `portfolio:latest`)
- **Setup:** Jenkins running in Docker, with Docker used as the build agent
- **Deploy targets:** Local VM(s) that pull new images from Docker Hub with cron

---

## Roadmap

| # | Step | Status |
|---|------|--------|
| 1 | Learn the core Jenkins ideas and check the existing Jenkins setup | Done (02/10/2026) |
| 2 | Install and check the plugins we need | Done (01/10/2026) |
| 3 | Store credentials (GitHub, Docker Hub) in Jenkins | Done (02/10/2026) – confirm both IDs exist |
| 4 | First "hello world" Jenkinsfile + Multibranch Pipeline job | Done (02/10/2026) |
| 5 | Test stage (Django tests inside a Python 3.12 container) | Done (02/10/2026) – 4/4 tests pass |
| 6 | Staging stage (build + push `dev-*` image on `dev` branch) | In progress |
| 7 | Production stage (build + push `latest` image on `main`, with manual approval) | Not started |
| 8 | Automatic triggers (GitHub webhook / polling) | Not started |
| 9 | Tidy up (post actions, cleanup, decide what to do with GitHub Actions) | Not started |

---

## Glossary (fill in as we go)

| Term | Meaning in my own words |
|------|-------------------------|
| Controller | |
| Agent / Node | |
| Executor | |
| Label | |
| Job / Project | |
| Multibranch Pipeline | |
| Jenkinsfile | |
| Stage / Step | |
| Workspace | |
| Credentials | |
| Credential ID | |
| Plugin | |

---

## Step log

### Step 1 – Core ideas and checking the environment (30/09/2026 – 01/10/2026)

**Notes**

- **Controller** = the Jenkins server (web UI at `http://localhost:8080`). Stores jobs, config and history, and schedules builds. It should not do heavy build work itself.
- **Agent / node** = the machine or container that actually runs the build. The controller sends work to agents.
- **Executor** = one build slot on an agent (2 executors = 2 builds at the same time).
- **Label** = a tag on an agent (e.g. `docker`). A pipeline asks for a label and Jenkins picks a matching agent.
- **Multibranch Pipeline job** = scans the Git repo, finds every branch that has a `Jenkinsfile`, and builds each branch on its own. This is how we get staging on `dev` and production on `main`.
- **Jenkinsfile** = the pipeline written as code in the repo (the Jenkins version of `deploy.yml`).
- **Stage** = a named group of work ("Test", "Deploy Staging"). **Step** = a single command inside a stage (`sh '...'`).
- **Workspace** = the folder on the agent where the code is checked out for a build.
- **Credentials** = Jenkins' safe store for secrets (the Jenkins version of GitHub Secrets).
- **Plugin** = an add-on. Almost every Jenkins feature (Git, Docker, Pipeline) comes from a plugin.

**GitHub Actions → Jenkins mapping**

| GitHub Actions | Jenkins |
|---|---|
| `.github/workflows/deploy.yml` | `Jenkinsfile` at repo root |
| `jobs:` | `stages { stage('...') { } }` |
| `runs-on: ubuntu-latest` | `agent { ... }` |
| `steps: - run:` | `steps { sh '...' }` |
| `needs: test` | Stages run in order by default |
| `if: github.ref == 'refs/heads/dev'` | `when { branch 'dev' }` |
| `secrets.X` | `credentials('id')` / `withCredentials` |
| `env:` | `environment { }` |
| `on: push` | Webhook or polling trigger |
| `actions/checkout` | `checkout scm` (automatic in Multibranch jobs) |

**Key difference:** GitHub gives a fresh VM with tools already installed for every run. In Jenkins **we** provide the machines, so the agent must have the tools we need (e.g. the Docker CLI).

**Environment findings**
- Jenkins version:
- Jenkins container name / image:
- How the Docker agent is set up (Cloud / permanent node / Docker socket on controller): **Docker socket on the controller ("Docker-outside-of-Docker")**. The Jenkins container has the Docker CLI and talks to **Docker Desktop's** engine on my laptop. No separate agent node. (Confirmed from build #2 log, 02/10/2026.)
- Node names and labels: `built-in` (the controller itself)
- Docker CLI available on the agent? (yes/no): **Yes**. Client 29.8.1 → Server Docker Desktop 4.93.0 (Engine 29.8.1)
- Staging / production servers: local VM(s)
- Do staging and production share one VM or use two?:
- How the VM gets new images (cron pulling from Docker Hub?):

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None so far | | |

---

### Step 2 – Plugins (01/10/2026)

**What I did**
- Went to **Manage Jenkins → Plugins → Installed plugins** and searched for each required plugin.

**Plugins confirmed installed**

| Plugin | Version | Why we need it |
|---|---|---|
| Pipeline | 608.v67378e9d3db_1 | Lets Jenkins run a `Jenkinsfile` at all |
| Pipeline: Declarative | 2.2293.v6e7193cec599 | The simple `pipeline { stages { ... } }` syntax we'll use |
| Pipeline Graph View | 1041.v107d70db_b_1a_f | Shows each build as a picture of its stages |
| Git plugin / Git client | 5.10.1 / 6.6.1 | Clones the repo |
| GitHub Branch Source | 1983.vfa_27ed961853 | Multibranch jobs that read branches from GitHub |
| GitHub plugin | 1.47.0 | GitHub webhook triggers (Step 8) |
| Credentials Binding | 728.v902a_273b_8947 | `withCredentials { }` to use secrets safely in steps |
| Docker Pipeline | 653.v2f2c08eff0ec | `agent { docker { image '...' } }` and `docker.build()` / `docker.withRegistry()` |
| Docker Commons | 477.v289085a_b_6896 | Shared code that Docker Pipeline needs |

**Notes**
- **Greyed-out "Enabled" toggle** = another plugin depends on this one, so Jenkins won't let you switch it off. That's normal.
- **Health score** (e.g. 74 for Docker Pipeline) = a rough sign of how well the plugin is maintained. It doesn't mean something is broken.
- **"Up for adoption"** = the original maintainer has stepped back and is looking for a new one. The plugin still works fine and is very widely used.
- **"Docker" (cloud) plugin is NOT installed.** That plugin would let Jenkins start a new agent container for every build. We don't need it: Docker Pipeline can run each stage inside a container (e.g. `python:3.12`), as long as the agent can run `docker` commands.

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

---

### Step 3 – Credentials (01/10/2026)

**Notes**
- Secrets **never** go in the Jenkinsfile or the repo. They live in Jenkins and are looked up by their **ID**.
- **Scope "Global"** = any job can use it. **Scope "System"** = only Jenkins itself can use it (e.g. for agent connections), not pipelines. We want **Global**.
- Use **access tokens**, not real passwords. A token can be limited and revoked without changing your password.
- Jenkins masks credentials in build logs (they show as `****`).
- **Newer Jenkins UI:** "Add Credentials" first asks you to **pick a type**, then click **Next** to see the form (older versions had a "Kind" dropdown instead).
- **"Treat username as secret"**: leave this unticked for Docker Hub and GitHub. Usernames aren't secret, and masking them makes logs hard to read (`****/portfolio:latest`).

**Credential types, and when to use each**

| Type | Use for |
|---|---|
| Username with password | Username + password/token logins (Docker Hub, GitHub) |
| GitHub App | Organisation-level GitHub integration with higher rate limits |
| SSH Username with private key | SSH to servers, or `git@github.com:` clones |
| Secret file | A whole file (`.env`, kubeconfig) |
| Secret text | A single value with no username (API key, Slack token) |
| X.509 / Certificate | Certificate auth (e.g. remote Docker daemon over TLS) |

**GitHub fine-grained token – how it was created (02/10/2026)**
- GitHub → Settings → Developer settings → Personal access tokens → **Fine-grained tokens** → Generate new token.
- **Repository access:** *Only select repositories* → portfolio repo.
- Newer GitHub UI: Permissions → **+ Add permissions** → search and tick each one → then set its access level in the row's dropdown.

| Permission | Access | Why |
|---|---|---|
| Contents | Read-only | Clone code, read `Jenkinsfile` |
| Metadata | Read-only (mandatory, auto-added) | Branch names, basic repo info |
| Commit statuses | Read and write | Jenkins posts ✅/❌ on commits |

- Expiration: 90 days. **When it expires:** generate a new token and update the `github-creds` password in Jenkins.
- **Principle of least privilege:** give a token only the access it needs. Never tick *Administration*.

**Credentials created**

| ID | Kind | Used for |
|---|---|---|
| `dockerhub-creds` | Username with password (password = Docker Hub access token) | Pushing images |
| `github-creds` | Username with password (password = GitHub personal access token) | Scanning branches / cloning |

**What I did**
-

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| | | |

---

### Step 4 – First Jenkinsfile + Multibranch Pipeline job (02/10/2026)

**Notes**
- A **Jenkinsfile** lives at the repo root. A Multibranch job only builds branches that **contain** a Jenkinsfile. Branches without one show "Does not meet criteria", which is expected.
- We work on a separate branch, `jenkins-setup`, so `main` and `dev` aren't affected. GitHub Actions only runs on `main`, `dev` and `aws-deployment`, so it ignores this branch.
- **Declarative pipeline skeleton:**
  ```groovy
  pipeline {          // everything goes inside this
      agent any       // where to run (any free agent)
      stages {        // list of stages, run in order
          stage('Name') {
              steps { echo '...'; sh '...' }
          }
      }
  }
  ```
- `echo` = a Jenkins step that prints to the log. `sh` = runs a shell command on the agent (Linux). On a Windows agent it would be `bat`.
- Useful built-in variables: `env.BRANCH_NAME`, `env.BUILD_NUMBER`, `NODE_NAME`, `WORKSPACE`, `GIT_COMMIT`.
- `"..."` (double quotes) lets Groovy fill in `${...}` values. `'''...'''` (triple single quotes) passes the text to the shell unchanged, so the **shell** expands `$NODE_NAME`.
- **Scan Repository** = Jenkins checks GitHub for branches with a Jenkinsfile and creates a sub-job for each one.
- **Console Output** = the full build log. Always the first place to look when something fails.

**Job settings used**

| Setting | Value |
|---|---|
| Job name | `portfolio-site` |
| Type | Multibranch Pipeline |
| Branch source | GitHub, credentials `github-creds` |
| Repository URL | `https://github.com/Kaushal2059/My_Portfolio_website.git` |
| Build mode / Script path | by Jenkinsfile / `Jenkinsfile` |

**Git / GitHub setup for the Jenkins branch (02/10/2026)**

| Term | Meaning |
|---|---|
| Remote | A named link from my local repo to a repo on GitHub |
| `origin` | The default name for that remote (just a nickname for the URL) |
| Branch | A separate line of work. Changes on it don't affect `main` until merged. |
| Upstream (`-u`) | Links my local branch to the GitHub branch, so plain `git push` / `git pull` work afterwards |
| `fetch` vs `pull` | `fetch` = download info about GitHub's branches and change nothing locally. `pull` = fetch **and** merge into my current branch. |

| # | Command | What it does |
|---|---|---|
| 1 | `git remote -v` | Shows where `origin` points |
| 1a | `git remote add origin <url>` | Only if there is **no** origin yet |
| 1b | `git remote set-url origin <url>` | Only if origin points to the **wrong** repo |
| 2 | `git fetch origin` | Gets the latest list of branches from GitHub |
| 3 | `git switch main` then `git pull origin main` | Start from the latest `main` |
| 4 | `git switch -c jenkins-setup` | Create the new branch and move onto it |
| 5 | `git status` | Check what's changed or untracked |
| 6 | `git add Jenkinsfile JENKINS_LOG.md` | Stage only these two files |
| 7 | `git commit -m "..."` | Save a snapshot locally |
| 8 | `git push -u origin jenkins-setup` | Upload the branch to GitHub and set its upstream |
| 9 | `git branch -vv` | Check the branch tracks `origin/jenkins-setup` |

- New untracked files (Jenkinsfile, log) move with you when you create a branch. They belong to no branch until committed.
- Pushing uses **my own** GitHub login (Git Credential Manager may open a browser). The `github-creds` token is only for **Jenkins**.

**What I did**
- Created branch `jenkins-setup` from `main`, committed `Jenkinsfile` + `JENKINS_LOG.md`, pushed to GitHub (after fixing the 403 error below).
- Created the `portfolio-site` Multibranch Pipeline job. The scan found `jenkins-setup` and ran it.
- **Builds #1 and #2 both passed ✅**: Checkout SCM, Hello, Inspect agent, Check Docker all green (02/10/2026).

**Notes: finding my way around the Jenkins UI**
- Pages are nested: **Multibranch job** (`portfolio-site`) → **branch job** (`jenkins-setup`) → **build** (`#2`).
- **Console Output is only on a build's page.** Click the build number (e.g. `#2`) in the Builds list, then **Console Output**. Direct URL pattern: `http://localhost:8080/job/<job>/job/<branch>/<build>/console`.
- Clicking a cell in **Stage View** → **Logs** shows the log for just that stage.
- **Declarative: Checkout SCM** = a stage Jenkins adds automatically to clone the branch (like `actions/checkout`). SCM = Source Code Management (Git).
- **"No Changes"** = the build ran on the same commit as the previous build.
- **Build Now** = re-run the pipeline on the latest commit of that branch.

**Results from the "Inspect agent" stage**
- Node name: `built-in`. The build ran on the **controller** (log line: `Running on Jenkins in /var/jenkins_home/workspace/portfolio-site_jenkins-setup`)
- User: `jenkins`
- OS: Linux, hostname `020b376d6ed9` (a container ID, which proves Jenkins itself runs inside a container)
- `docker version` worked? (yes / error message): **Yes ✅**. Client 29.8.1, Server = Docker Desktop 4.93.0
- Token check: log shows `Connecting to https://api.github.com using Kaushal2059/******`, so `github-creds` is on the **personal** account ✅
- `GitHub has been notified of this commit's build result` = the *Commit statuses* permission works (✅ next to the commit on GitHub).

**How to read a Jenkins console log**
- `[Pipeline] stage` / `{ (Name)` = a stage starting. `// stage` = that stage ending.
- `+ command` = the exact shell command being run (like `set -x`). The lines below it are its output.
- `****` = a masked credential.
- Last line `Finished: SUCCESS` / `FAILURE` / `ABORTED` = the overall result.

**My setup in one picture: Docker-outside-of-Docker (DooD)**
```
Laptop (Windows) ── Docker Desktop engine
   ├── container: Jenkins controller (has docker CLI, socket mounted)
   │       └── "docker run python:3.12" → asks Docker Desktop
   └── container: python:3.12 (a *sibling* of Jenkins, not inside it)
```
- Containers Jenkins starts are **siblings** on Docker Desktop, not children inside the Jenkins container.
- ⚠️ Builds run on the **built-in node**. Fine for learning. In real teams, builds go to separate agents so a bad build can't damage the controller. (Possible improvement later.)

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| `git push` → `remote: Permission to Kaushal2059/My_Portfolio_website.git denied to Kaushal-rentalbux` / `403` (02/10/2026) | Windows had saved the login for my **work** GitHub account (`Kaushal-rentalbux`) and used it for every push to github.com. That account has no write access to my **personal** repo (`Kaushal2059`). | **Chosen fix:** added `Kaushal-rentalbux` as a **collaborator** on the repo (repo Settings → Collaborators → Add people), accepted the invite while logged in as `Kaushal-rentalbux`, then pushed again. *(Alternative not used: put `Kaushal2059@` in the remote URL and sign in as the personal account.)* **Result: ✅ pushed `jenkins-setup` successfully (02/10/2026).** |

**Lessons from the 403 error**
- **403 = Forbidden.** GitHub knows who you are but won't let you do this. (**401** would mean "I don't know who you are".)
- The message names the account that was used (`denied to <account>`). Read it closely, because it often shows the wrong account is logged in.
- Git Credential Manager saves **one login per host** (github.com) by default. With two GitHub accounts, put the username in the remote URL so each repo uses the right one.
- **Collaborator** on a personal repo = full **write** access (push, branches). Personal repos have no finer roles; only organisation repos have Read/Triage/Write/Maintain/Admin.
- The invite must be **accepted** by the invited account before the access works.
- **Fine-grained tokens can't reach collaborator repos.** A fine-grained token only covers repos **owned** by the token's account. A token made on `Kaushal-rentalbux` can't select `Kaushal2059/My_Portfolio_website`, so the Jenkins token must be made on `Kaushal2059` (or be a classic token with `repo` scope).
- **Green squares (contribution graph)** go to the account whose **verified email matches the commit's author email**, not to the account that pushed. They only count once the commit is on the **default branch** (`main`). So: push with `Kaushal-rentalbux`, but set this repo's `user.email` to the email of `Kaushal2059` (or its `...@users.noreply.github.com` address) to get credit on the personal profile. Check with `git log -1 --format="%an <%ae>"`.
- Also check commit identity per repo: `git config user.name` / `git config user.email` (without `--global`, this sets them for this repo only).

---

### Step 5 – Test stage: Django tests in a Python 3.12 container (02/10/2026)

**Notes**
- **A stage can have its own `agent`.** `agent { docker { image 'python:3.12' } }` = start a `python:3.12` container and run this stage's steps inside it. That replaces `runs-on: ubuntu-latest` + `actions/setup-python`.
- **`reuseNode true`** = use the same node and **workspace** as the top-level `agent any`, so the container sees the code that's already checked out.
- **How the container gets my code (DooD):** Docker Pipeline notices Jenkins is running inside a container and starts the Python container with `--volumes-from <jenkins container>`, so both share `/var/jenkins_home`. In the log, look for a line like `Jenkins seems to be running inside container ...`.
- The container runs as the **jenkins user (UID 1000)**, not root, so `pip install` into the system Python would fail with *Permission denied*. Fix: create a **virtualenv** (`.venv`) inside the workspace.
- **`environment { }`** = environment variables for the stage (like `env:` in GitHub Actions). Only for **non-secret** values. Real secrets come from Credentials (Step 6).
- **`dir('portfolio') { }`** = run steps inside a sub-folder (like `working-directory: portfolio`).
- Each `sh` step is a **new shell**, so `cd` or `source` in one `sh` doesn't carry over to the next. That's why venv activation and the commands sit in the **same** `sh '''...'''` block.
- The first run is slower because Docker has to download `python:3.12` (~1 GB). Later runs reuse the cached image.

**GitHub Actions → Jenkins (test job)**

| GitHub Actions | Jenkins |
|---|---|
| `runs-on: ubuntu-latest` + `setup-python@v5` (3.12) | `agent { docker { image 'python:3.12' } }` |
| `defaults.run.working-directory: portfolio` | `dir('portfolio') { }` |
| `env:` | `environment { }` |
| `pip install -r requirements.txt` | same, inside a venv |
| `python manage.py test --verbosity=2` | same |

**What I did**
- Decided to **write the Jenkinsfile myself**, with explanations line by line (02/10/2026). Building it in 3 parts:
  - Part 1: Test stage with a Docker agent, running only `python --version`
  - Part 2: add `environment { }` with the test values
  - Part 3: `dir('portfolio')` + venv + install + `manage.py test`

**Result**
- **Part 1 ✅ – build #3 (02/10/2026):** `python --version` → `Python 3.12.15` inside the container. Commit `59be5b3` "test docker as a agent".
- **Part 2 ✅: build #5 (02/10/2026):** printed `TEST_DB is sqlite and DEBUG is True`. `docker inspect` returned `.` (image cached), so **no pull** and a much faster build. `[Pipeline] withEnv` = the `environment { }` block being applied.
- **Part 3 ✅: build #6 (02/10/2026), commit `815ad58`:** venv created, all packages installed, **4 tests ran, all OK** (`test_admin_page_loads`, `test_authenticated_admin`, `test_database_works`, `test_homepage_loads`) on in-memory SQLite. `Finished: SUCCESS`.
- Tests run / passed: **4 / 4**
- **Step 5 complete: Jenkins now does everything the GitHub `test` job did.**

**Notes from the build #6 log**
- Jenkins runs `sh` with **tracing** (`+ command` before each line). The long block after `. .venv/bin/activate` is the activate script's own commands. The key line: `PATH=.../.venv/bin:...`. Activating = putting the venv's `bin` first in PATH.
- `WARNING: The directory '/.cache/pip' ... not writable ... cache has been disabled`: harmless. UID 1000 has no user/home inside `python:3.12`, so `HOME=/` and pip can't write its cache. Result: packages are re-downloaded every build. *Possible improvement later: set `PIP_CACHE_DIR` (or `HOME`) to a folder in the workspace.*
- `Applying sessions.0001_initial...test_admin_page_loads ... ok` on one line: stdout and stderr mixed in the log. Not an error.
- If any test fails, `manage.py test` exits non-zero, so Jenkins marks the stage red and the build FAILURE automatically.

**Final Step 5 Jenkinsfile structure**
```
pipeline
 ├── agent any
 └── stages
      └── stage('Test')
           ├── agent { docker { image 'python:3.12'; reuseNode true } }
           ├── environment { 14 dummy test variables }
           └── steps
                ├── sh 'python --version'
                └── dir('portfolio') { sh ''' venv → pip install → manage.py test ''' }
```

**Notes: Docker container lifecycle in a build (from build #3 log)**
| Log line | Meaning |
|---|---|
| `docker inspect -f . python:3.12` → `error: no such object` | "Do I have this image locally?" No. **Not a failure**, just a check. |
| `docker pull python:3.12` | Download it (first time only, then cached) |
| `Jenkins seems to be running inside container ...` | DooD detected, so it uses `--volumes-from` |
| `docker run -t -d -u 1000:1000 -w <workspace> --volumes-from <jenkins> -e ... python:3.12 cat` | Start the container in the background, as UID 1000 (jenkins, **not root**), in my workspace, sharing Jenkins' disks. `cat` keeps it alive. |
| `+ python --version` | My step, run inside the container via `docker exec` |
| `docker stop` / `docker rm -f --volumes` | Container deleted after the stage, so every build starts fresh |

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| *(caught in review, 02/10/2026)* `dcocker {`. Would fail before any stage with `Invalid agent type "dcocker"` | Typo in the agent type. Allowed types: `any`, `none`, `label`, `docker`, `dockerfile` | Spell it `docker` |
| *(caught in review)* `steps { }` written **inside** `agent { }`. Would fail with `Invalid config option "steps"...` | `agent` = *where* to run, `steps` = *what* to run. They are **siblings** inside `stage`, not nested | Close `agent { }` right after `docker { }`, then open `steps { }` |
| *(caught in review, Part 2)* `SECRET_KEY` defined **twice** in `environment { }` | Typed the example line, then pasted the full list underneath it | Delete the duplicate. Each variable name only once. |
| *(caught in review, Part 3)* `dir(...) { sh ... }` written **directly in the stage**, outside `steps { }`. Would fail: `Unknown stage section "dir"... steps in a stage must be in a 'steps' block` | `dir` and `sh` are **steps**. A stage can only directly contain **sections** (`agent`, `environment`, `steps`, `when`, `post`) | Move the `dir` block **inside** `steps { }` |
| *(caught in review, Part 3)* `dir('portfoliio')` | Typo. **`dir()` silently creates a missing folder**, so the error would only show later: `Could not open requirements file: [Errno 2] No such file or directory` | Spell it `portfolio`, exactly as in the repo |
| *(caught in review, Part 3)* Old check lines (`echo TEST_DB...`) left in `steps` | Added the new code instead of **replacing** the old | Remove the leftover lines |
| **Build #4 FAILED (02/10/2026):** `MultipleCompilationErrorsException: startup failed: WorkflowScript: 18: Duplicate environment variable name: "SECRET_KEY"` | Pushed commit `12cc58a` **before** fixing the duplicate. Jenkins builds what's on **GitHub**, not my local file. | Fixed locally (deleted the duplicate), then committed and pushed again. **Result: ✅ build #5 passed (commit `b30b9ed`).** |
| *(caught in review)* `sh 'pytjhon --version'`. Would fail at runtime: `pytjhon: not found`, `exit code 127` | Typo in a shell command. Jenkins doesn't check what's inside `sh '...'` | Spell it `python` |

**Lessons**
- **Two kinds of errors:** structure/syntax errors (Jenkinsfile grammar) fail **before** the build starts, while command errors inside `sh` fail **during** the build, when that step runs.
- **Exit code 127** = command not found.
- **Reading a Groovy compile error:** only the first lines matter. `WorkflowScript` = my Jenkinsfile, `NN:` / `@ line NN, column NN` = location, then the message in plain English, and `^` points at the spot. The `at org.codehaus...` / `at hudson...` lines are a Java stack trace and can be ignored.
- A compile error has **no `[Pipeline] stage` lines at all**. Nothing ran, not even Checkout SCM.
- **Sections vs steps:** *sections* (`agent`, `environment`, `steps`, `when`, `post`) go directly in a `stage`. *Steps* (`sh`, `echo`, `dir`, `withCredentials`) must be inside `steps { }`.
- `dir('x')` **creates** folder `x` if it doesn't exist, so a typo there fails later with a misleading error. When a file "isn't found", check the folder name first.
- **Jenkins builds what's pushed to GitHub, not my local file.** Habit: run `git diff --staged` (or ask for a review) before every push.
- Correct stage layout:
  ```
  stage('X')
   ├── agent { docker { image '...'; reuseNode true } }
   ├── environment { }   (optional)
   └── steps { }
  ```
- **Pipeline Syntax → Declarative Directive Generator** (left menu of any pipeline job) generates correct blocks.
- Indent 4 spaces per level so every `}` lines up under the line that opened it.
- **Indentation doesn't change the structure in Groovy; only braces do.** Second attempt: I moved `steps {` to the left, but the `}` closing `agent` was still *after* `steps`, so `steps` was still inside `agent`. Fix: move that `}` to **before** `steps {`. Check by tracing which block each `}` closes. *(Fixed by Claude at my request, 02/10/2026; also removed a trailing space after `reuseNode true` and an empty line inside `steps`.)*
- Keep comments up to date when code changes (the header still said "Step 4 – Hello world").

---

### Step 6 – Staging: build + push `dev-*` image on the `dev` branch (02/10/2026)

**Plan (built in parts)**
- Part 1: add a `Deploy Staging` stage with a `when { branch 'dev' }` condition and just an `echo`. See it get **skipped** on `jenkins-setup`.
- Part 2: `docker build` with the two staging tags.
- Part 3: `withCredentials` + `docker login` + `docker push`.
- Part 4: merge to `dev` so the stage really runs, then check Docker Hub.

**Notes**
- **`when { }`** = a condition on a stage. If it's false, the stage is **skipped** (grey in Stage View, log line `Stage "..." skipped due to when conditional`). It's the Jenkins version of `if: github.ref == 'refs/heads/dev'`.
- **`branch 'dev'`** compares against `env.BRANCH_NAME`, which only exists in **Multibranch** jobs.
- The staging stage has **no `agent` of its own**, so it runs on the top-level `agent any` (the built-in node), which has the **Docker CLI**. That's what we need for `docker build` / `docker push`. The `python:3.12` container from the Test stage has no Docker CLI.
- Stages run in order. If `Test` fails, the build stops and `Deploy Staging` never runs. That's the Jenkins version of `needs: test`.

**Notes: Part 2 (docker build)**
- `docker build -t A -t B <context>`: each `-t` adds a **tag** (name:version) to the same image. `<context>` = the folder sent to Docker, which must contain the `Dockerfile` (ours: `portfolio`, same as `context: portfolio` in GitHub Actions).
- Image name format for Docker Hub: **`<dockerhub-username>/<repo>:<tag>`**. Must be **lowercase**.
- The Docker Hub username isn't a secret, so it can go in `environment { IMAGE_NAME = '...' }`. Only the **token** must stay in Credentials.
- `${IMAGE_NAME}` and `${GIT_COMMIT}` inside **single quotes** are expanded by the **shell**. Braces make clear where the variable name ends.
- DooD and `docker build`: the Docker CLI in the Jenkins container **uploads the context folder** to Docker Desktop, so local paths work fine.
- **Replay** (build page → *Replay*) re-runs a build with an **edited Jenkinsfile, without committing**. Great for experiments. The edit only lives in that one build.

**Notes: Part 3 (login + push with a real secret)**
- **`withCredentials([...]) { }`** = a **step** (so it goes inside `steps`) that fetches a credential by **ID**, puts it into env variables **only inside its braces**, and **masks** the values in the log (`****`).
- **`usernamePassword(credentialsId:, usernameVariable:, passwordVariable:)`** = for a *Username with password* credential. I choose the variable names.
- **`echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin`**: the token goes in through **stdin**, never on the command line (`-p` would expose it in process lists and Docker would warn).
- **Single quotes** around the `sh` script, so the **shell** expands `$DOCKER_PASS`. Double quotes would make Groovy paste the secret into the command, and Jenkins warns: *"insecure interpolation of sensitive variables"*.
- **`docker logout`** at the end: `docker login` saves the token in `/var/jenkins_home/.docker/config.json` (inside the Jenkins container), where it would **stay after the build**. Logging out removes it. *(A failed push would skip the logout, so `post { always { } }` is the robust fix, in Step 9.)*
- A `docker push` of the second tag uploads nothing new: every layer says `Layer already exists`.
- ⚠️ **Never test a push to `dev-latest` from a non-dev branch.** The staging VM's cron pulls `dev-latest` within ~5 minutes, so you'd deploy the wrong code to staging.

**Notes: Part 4 from the command line (GitHub CLI `gh`)**
| Task | Command |
|---|---|
| Install (once) | `winget install --id GitHub.cli`, reopen the terminal, then `gh auth login` (GitHub.com → HTTPS → browser, as `Kaushal-rentalbux`) and `gh auth status` |
| See PR + base branch | `gh pr view jenkins-setup` or `gh pr view jenkins-setup --json number,baseRefName,headRefName,mergeable` |
| Change base to `dev` | `gh pr edit jenkins-setup --base dev` |
| Commit count | `gh pr view jenkins-setup --json baseRefName,commits --jq "{base: .baseRefName, commits: (.commits \| length)}"` |
| Disable / enable workflow | `gh workflow disable "CI/CD Pipeline"` / `gh workflow enable "CI/CD Pipeline"`; check with `gh workflow list --all` |
| Merge (keep branch) | `gh pr merge jenkins-setup --merge` (no `--delete-branch`) |
| Check `dev` | `git fetch origin`, `git log --oneline -3 origin/dev`, `git show origin/dev:Jenkinsfile` |
| Trigger Jenkins scan | `curl.exe -X POST -u "USER:API_TOKEN" "http://localhost:8080/job/portfolio-site/build?delay=0"` (for Multibranch, `/build` = scan). API token: my name → Security → API Token. |
- `mergeable: UNKNOWN` = GitHub hasn't finished the merge check yet (the spinner in the web UI).

**Notes: merging into `dev` locally with Git Bash (no PR needed)**
| # | Command | Why |
|---|---|---|
| 0 | *Disable the GitHub workflow first* | Pushing to `dev` triggers GitHub Actions, just like merging a PR |
| 1 | `git switch jenkins-setup`, `git status`, then commit + `git push` if anything changed | Only merge finished, committed work |
| 2 | `git fetch origin` | Get the latest branch info |
| 3 | `git switch dev` | No local `dev` yet, so Git creates one **tracking `origin/dev`** |
| 4 | `git merge jenkins-setup` | Likely **Fast-forward**: `dev` has no commits of its own, so Git just moves the pointer forward. `--no-ff` forces a merge commit. |
| 5 | `git log --oneline -5`, `ls Jenkinsfile` | Check before pushing |
| 6 | `git push origin dev` | Publish |
| 7 | `git switch jenkins-setup` | Go back so new edits don't land on `dev` |
- **Fast-forward** = no new commit, the branch pointer just moves ahead. Only possible when the target has nothing the source lacks.
- After a local merge, an open PR **into `dev`** is marked *Merged* automatically. A PR **into `main`** should be **closed without merging**.
- In PowerShell, use **`curl.exe`**, because `curl` is an alias for `Invoke-WebRequest`.
- A Jenkins API token is a password. Never paste or commit it.

**What I did**
- Part 1 written (when + echo). Not pushed yet. Planning to push Parts 1 + 2 together.
- Part 2 written **correctly on the first try** (02/10/2026): `environment { IMAGE_NAME = 'iamkaushal20/portfolio' }` + `sh 'docker build -t ${IMAGE_NAME}:dev-latest -t ${IMAGE_NAME}:dev-${GIT_COMMIT} portfolio'`.
- ⚠️ Check: `iamkaushal20` must match the username in `dockerhub-creds`, or the push in Part 3 will fail with `denied: requested access to the resource is denied`.
- Part 3 written **correctly on the first try** (02/10/2026): `withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', ...)])` around `sh '''` login (`--password-stdin`) → push `dev-latest` → push `dev-${GIT_COMMIT}` → logout `'''`. Single quotes, inside `steps`, braces balanced. Not pushed yet.
- Found before Part 4: `dev` is **7 commits behind `main`** and has nothing of its own. Merging `jenkins-setup` (based on `main`) into `dev` will also bring those 7 commits (S3 media, AWS job, home page changes, settings.py edits), so **staging will get the same app code as `main`**.
- **Decision (02/10/2026): Option A.** Temporarily **disable the GitHub Actions workflow** (Actions → CI/CD Pipeline → ⋯ → Disable workflow) so that only Jenkins pushes `dev-latest` during the test. Re-enable or retire it in Step 9.

- **Part 2 ✅ tested with Replay** (build #10, replay of #9, 02/10/2026). Changed `branch 'dev'` → `branch 'jenkins-setup'` **in the Replay editor only**. Both stages green. Image built and tagged `iamkaushal20/portfolio:dev-latest` and `:dev-b30b9ed59caef5b5f2687706aaf2ccf868ac5089`.
- **Replay re-uses the commit of the replayed build** (here `b30b9ed`). Only the Jenkinsfile text is swapped for what I pasted.

**Notes from the build #10 log**
- `debconf: unable to initialize frontend: Dialog ... falling back to Noninteractive`: `apt-get` in the Dockerfile has no screen, so it falls back. Harmless.
- `WARNING: Running pip as the 'root' user`: comes from the **Dockerfile**, not Jenkins. Common in containers.

**`docker images` after build #10 (before the `.venv` fix)**
| Tag | ID | Disk usage | Content size |
|---|---|---|---|
| `dev-b30b9ed…` | `50eae3e672c6` | 950MB | 252MB |
| `dev-latest` | `50eae3e672c6` | 950MB | 252MB |
- **Same ID on both rows**, which proves one image with two tags. The ID matches `exporting manifest list sha256:50eae3e672c6…` in the build log.
- **Content size** = compressed layers (what gets pushed and pulled). **Disk usage** = unpacked size, stored once.
- **Baseline: 252MB content.** Compare after the `.venv/` fix.
- `.gitignore` (Git: what gets committed) and `.dockerignore` (Docker: what goes in the build context) are **independent**. The image fix needs `.dockerignore`.

**Q: Why do both tags show the same IMAGE ID?**
- A **tag is a label pointing to an image**, not a copy. One build, one image, two names. The IMAGE ID is a fingerprint of the content.
- The second tag uses **almost no disk space** (just metadata), even though `docker images` shows the full size on both rows.
- On push, the second tag uploads nothing new (`Layer already exists`).
- On the next build, `dev-latest` **moves** to the new image, while `dev-<commit>` stays on the old one. That's what makes **rollback** possible.

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| *(caught in review, Part 1)* `steps { }` written **inside** `when { }` | Same pattern as `steps` inside `agent` in Step 5. `when` only holds **conditions**. `steps` is its sibling. | Close `when` right after `branch 'dev'`, then open `steps` |
| *(caught in review)* Extra `script { docker.build("portfolio:latest") }` directly in the stage | Jumped ahead. `script` is a **step** (must be in `steps`). `latest` is the **production** tag. No `<dockerhub-user>/` prefix. | Removed. Build is done properly in Part 2 with `dev-latest` / `dev-<commit>` tags. |
| **Found in build #10 log:** `transferring context: 106.32MB`, far too big for a small Django app | The **Test stage creates `portfolio/.venv`** (~100 MB) in the **shared workspace**. `docker build ... portfolio` sends it as context. `.dockerignore` excludes `venv/` but **not `.venv/`**, and `COPY . .` puts it **inside the image**. (Never happened on GitHub Actions: each job had its own fresh VM.) | Add `.venv/` to `portfolio/.dockerignore`. Check: next build's `transferring context:` should be a few MB. *(First attempt saved as `.vnev/`, a typo that would match nothing. Corrected to `.venv/` by Claude at my request, 02/10/2026. `.gitignore` already had `.venv/` on line 5.)* Result: _(fill in after next build)_ |
| PR page stuck on **"Checking for the ability to merge automatically…"** (02/10/2026) | GitHub's background mergeability check. The page often just doesn't refresh. Not Jenkins-related. | Refresh the page (F5). If still stuck, check githubstatus.com. Result: _(fill in)_ |
| PR showed **only 7 commits** (all mine), but `dev` is 7 behind `main`, so a PR into `dev` should show ~14 | Probably opened with **base = `main`** (GitHub's default) instead of `dev` | Check "wants to merge into ___". If `main`: **Edit → change base to `dev`**. Never merge this into `main` (production). Result: _(fill in)_ |
| *(caught in review)* One `}` too many at the end of the file | Brace count off after the extra block | After the last stage's `}` there must be exactly **2**: `stages`, then `pipeline` |
| | *Fixed `when` myself. Claude removed the `script` block and the extra `}` at my request (02/10/2026).* | |

**Lessons**
- `when`, `agent`, `environment`, `steps`, `post` are all **siblings** directly inside a stage. None of them goes inside another.
- **Habit:** type `{` and its `}` together, then fill in the middle. That stops one block from swallowing the next.
- Pushing the wrong tag is dangerous: `latest` from `dev` would be pulled by the **production** VM's cron.
- **In Jenkins, all stages share one workspace** (unlike GitHub Actions jobs, which each get a new VM). Files one stage creates (`.venv`, build output) are seen by later stages, including `docker build`.
- **Read `transferring context: NN MB`** in every `docker build` log. A big number means unwanted files are getting into the build. Fix them with `.dockerignore`.
- `venv/` and `.venv/` are **different names**. `.dockerignore` matches exactly.
- **Always check a PR's base branch** ("wants to merge into ___"). GitHub defaults to `main`. Sanity check: does the commit count match what you expect?
- **✓ / ✗ next to commits on GitHub** = Jenkins commit statuses (the *Commit statuses* permission from Step 3). Each shows the **latest** build of that commit, so a later failed build or replay on the same commit replaces an earlier ✓. A commit Jenkins hasn't built yet has no mark.

---

## Review questions & answers (02/10/2026)

**Q1 (Step 4): `"${env.BRANCH_NAME}"` vs `'''$NODE_NAME'''`. Who fills in the value?**
- Double quotes: **Groovy/Jenkins** fills it in *before* the step runs, so the shell receives finished text.
- Single quotes: Groovy passes the text unchanged, and the **shell** expands `$NODE_NAME` from its environment.
- **Security rule:** secrets in `sh` → **always single quotes**. Double quotes paste the secret into the command text (Jenkins warns: *"A secret was passed to sh using Groovy String interpolation, which is insecure"*).

**Q2 (Step 5): Why can't `. .venv/bin/activate` and `pip install` be separate `sh` steps?**
- Every `sh` step is a **new shell process**. Activation only changes `PATH` in that shell, and the change is lost when the step ends.
- The next `sh` would use the **system pip** as UID 1000 (not root), so the install fails. Tests would then hit `ModuleNotFoundError: No module named 'django'`.
- Rule: shell state (`cd`, `export`, `activate`) only lasts within one `sh`. Use `dir()` and `environment {}` / `withEnv` for things that must carry across steps.

**Q3 (Step 3 → 6): Where does the real Docker Hub token go?**
- In the **Jenkins Credentials store** (ID `dockerhub-creds`), never in the Jenkinsfile or repo.
- The Jenkinsfile refers to it **by ID only**:
  - `withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) { ... }`, or
  - `environment { DOCKERHUB = credentials('dockerhub-creds') }` → creates `DOCKERHUB_USR` and `DOCKERHUB_PSW`.
- Values exist only inside that block and are **masked** in logs. Log in with `--password-stdin` so the token stays off the command line.

**Q4 (Step 6 Part 3): What if the username in `IMAGE_NAME` doesn't match the `dockerhub-creds` username?**
- My answer: the push fails. ✅
- Detail: `docker build` ✅ (any local name is allowed), `docker login` ✅ (the credentials are valid), **`docker push` ❌** `denied: requested access to the resource is denied`. That's **authorisation** (no permission to that namespace), not authentication. Same idea as the git `403` in Step 4.
- Jenkins runs `sh` with **`-e`** (stop at the first failure), so **`docker logout` is skipped** and the token stays in `/var/jenkins_home/.docker/config.json`. Fix in Step 9: `post { always { sh 'docker logout' } }`.

**Still open: Step 5 Part 1:** what happens if `reuseNode true` is removed? *(Answer in Step 6 or 9.)*

---

## Error index (all steps)

| Step | Error message (short) | Root cause | Fix |
|------|----------------------|-----------|-----|
| 4 | `git push` 403 – permission denied to `Kaushal-rentalbux` | Saved work GitHub login used for personal repo | Added `Kaushal-rentalbux` as a repo collaborator and accepted the invite |
| 6 | `transferring context: 106.32MB` (build #10) | Test stage's `.venv` in shared workspace, not in `.dockerignore`, so it was copied into the image | Add `.venv/` to `portfolio/.dockerignore` |
| 5 | `Duplicate environment variable name: "SECRET_KEY"` (build #4) | Same variable twice in `environment { }`, pushed before fixing | Remove the duplicate, commit, push |
