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
| 1 | Learn the core Jenkins ideas and check the existing Jenkins setup | Partly done (nodes info still needed) |
| 2 | Install and check the plugins we need | Done (01/10/2026) |
| 3 | Store credentials (GitHub, Docker Hub) in Jenkins | Done (02/10/2026) – confirm both IDs exist |
| 4 | First "hello world" Jenkinsfile + Multibranch Pipeline job | In progress |
| 5 | Test stage (Django tests inside a Python 3.12 container) | Not started |
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
- How the Docker agent is set up (Cloud / permanent node / Docker socket on controller): Not a Docker Cloud (the "Docker" cloud plugin isn't installed). Waiting on the Nodes page.
- Node names and labels:
- Docker CLI available on the agent? (yes/no):
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
-

**Results from the "Inspect agent" stage**
- Node name:
- User:
- OS:
- `docker version` worked? (yes / error message):

**Errors faced**
| Error | Cause | Fix |
|-------|-------|-----|
| | | |

---

## Error index (all steps)

| Step | Error message (short) | Root cause | Fix |
|------|----------------------|-----------|-----|
