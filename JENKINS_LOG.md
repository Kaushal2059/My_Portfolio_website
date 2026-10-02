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
| 5 | Test stage (Django tests inside a Python 3.12 container) | In progress |
| 6 | Staging stage (build + push `dev-*` image on `dev` branch) | Not started |
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
- Tests run / passed: (Part 3)

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
| *(caught in review)* `sh 'pytjhon --version'`. Would fail at runtime: `pytjhon: not found`, `exit code 127` | Typo in a shell command. Jenkins doesn't check what's inside `sh '...'` | Spell it `python` |

**Lessons**
- **Two kinds of errors:** structure/syntax errors (Jenkinsfile grammar) fail **before** the build starts, while command errors inside `sh` fail **during** the build, when that step runs.
- **Exit code 127** = command not found.
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

## Error index (all steps)

| Step | Error message (short) | Root cause | Fix |
|------|----------------------|-----------|-----|
| 4 | `git push` 403 – permission denied to `Kaushal-rentalbux` | Saved work GitHub login used for personal repo | Added `Kaushal-rentalbux` as a repo collaborator and accepted the invite |
