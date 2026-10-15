# Kubernetes – Learning Log

A running record of moving the portfolio site onto Kubernetes, one step at a time: what I did,
why, my notes, every error I hit, how I fixed it, and what is left to follow up.

- **Started:** 13/10/2026
- **Level at start:** complete beginner to Kubernetes (comfortable with Docker, Compose and Jenkins, see `DOCKER_LOG.md` and `JENKINS_LOG.md`)
- **Goals:** (1) understand the core Kubernetes concepts by using them, (2) run the portfolio site on a local cluster, (3) learn to operate it: logs, scaling, updates, rollbacks
- **Cluster tool:** kind. A new, dedicated cluster called `portfolio`, created from a kind config file I write (decided 15/10/2026). The old `kind` cluster is kept for now.
- **Branch:** `k8s-setup`, created from `dev` after committing the Docker Step 7 work (decided 15/10/2026)
- **Manifests folder:** `k8s/` at the repo root
- **Rule:** I write every manifest and run every command (including git) myself. Claude guides, explains, reviews and keeps this log.
- **Rule:** never paste a token, password, API key or real Secret value into this log (same rule as the Docker and Jenkins logs).

---

## Roadmap (updated 15/10/2026 after the Step 0 decisions)

| # | Step | Status |
|---|------|--------|
| 0 | Check my machine; decide cluster tool, branch, scope, folder layout | Machine check done (15/10/2026): 8 CPUs, 15 GiB RAM, kind + kubectl already installed, existing `kind` cluster found. Decisions made 15/10/2026 (all as recommended). **Branch setup pending** |
| 1 | Concepts: cluster, node, control plane, Pod, `kubectl`, manifests, desired state | **Current** (started 15/10/2026): cluster anatomy done; manifest anatomy exercise given |
| 2 | Write a kind config file and create the `portfolio` cluster (kind + kubectl already installed); kubectl contexts | |
| 3 | First Pod by hand (imperative), then the same Pod as a YAML manifest (declarative). Self-healing demo | |
| 4 | A Namespace for the project | |
| 5 | Configuration: ConfigMap (normal settings) and Secret (passwords), without committing secrets to git | |
| 6 | Database: PersistentVolumeClaim + PostgreSQL + Service | |
| 7 | Django app: Deployment + Service; readiness/liveness probes (the Kubernetes answer to `depends_on`/`healthcheck`) | |
| 8 | Reach the site from my browser: port-forward, NodePort, then nginx / Ingress; static and media files | |
| 9 | Security: non-root `securityContext`, `fsGroup` for volume ownership | |
| 10 | Day-2 operations: logs, describe, events, scaling, rolling update to a new image tag, rollback | |
| 11 | Database migrations as a Job (fix the race when several web Pods start at once) | |
| 12 | Resources: CPU/memory requests and limits | |
| 13 | Optional: Prometheus + Grafana in the cluster, Jenkins deploying to the cluster, Kustomize/Helm | |
| 14 | Wrap-up: review questions, final notes | |

---

## Compose → Kubernetes map for this project

A preview only. Each row gets its own step and explanation later.

| `docker-compose.yml` today | Kubernetes object(s) | Why it changes |
|---|---|---|
| A service (`web`, `db`, `nginx`) | **Deployment** (or **StatefulSet** for the database) that manages **Pods** | A Pod is the smallest thing Kubernetes runs (one or more containers). The Deployment keeps the requested number of Pods alive |
| Service name used as a hostname (`web:8000` in `nginx.conf`, `DB_HOST`) | **Service** object with the same name | Stable name + IP even while Pods are replaced. It exists even when no Pod is running, so no repeat of the `127.0.53.53` nginx problem from Docker Step 4b |
| `.env` / `env_file` | **ConfigMap** (normal settings) + **Secret** (passwords, `SECRET_KEY`) | Settings live in the cluster and are injected as environment variables |
| Named volumes (`postgres_data`, `media_volume`, …) | **PersistentVolumeClaim** (PVC) | Storage that outlives any single Pod |
| Bind-mounted config files (`nginx.conf`, `prometheus.yml`) | **ConfigMap** mounted as a file | A cluster has no "folder next to the compose file" |
| `ports: "80:80"` | `kubectl port-forward`, **NodePort** Service, or **Ingress** | Different ways for outside traffic to reach the cluster |
| `depends_on` + `healthcheck` | **readiness / liveness probes** | Kubernetes has no start order. Pods retry until what they need answers |
| `restart: unless-stopped` | Built in | Controllers always restart or replace failed Pods |
| `logging:` size options | Built in (`kubectl logs`, log rotation on the node) | |

---

## Glossary (fill in as we go)

| Term | Meaning in my own words |
|------|-------------------------|
| Kubernetes (K8s) | A system that runs containers on one or more machines and keeps checking that what is running matches what I asked for |
| Desired state | What I *want* running, written in YAML. Kubernetes keeps comparing it with what *is* running and fixes any difference |
| Cluster | A group of machines (nodes) that Kubernetes manages as one |
| Node | One machine in the cluster. In kind, each node is a Docker container (e.g. `kind-control-plane`) |
| Control plane | The "brain": stores the desired state, decides which node runs what, and runs the check-and-fix loops |
| kind | "Kubernetes IN Docker": a tool that builds a whole cluster out of Docker containers on my laptop |
| `kubectl` | The command-line tool I use to talk to the cluster (read objects, create them, delete them) |
| Namespace | A named group that keeps objects apart, a bit like a folder. `-A` = show all namespaces |
| Pod | The smallest thing Kubernetes runs: one or more containers that share an IP and can share storage |
| Deployment | Keeps N identical Pods running and handles updates. Works through a ReplicaSet |
| ReplicaSet | The object that actually keeps the Pod count right. A Deployment creates one per version of the Pod template |
| DaemonSet | Runs exactly one copy of a Pod on every node (e.g. network and proxy helpers) |
| kubelet | The agent on each node that starts and watches the containers. Not a Pod itself |
| containerd | The container runtime inside each node. Kubernetes uses it instead of Docker |

---

## Step log

### Step 0 – Check my machine and make the starting decisions (13/10/2026)

**What and why**
Before installing anything: find out what my machine can give a cluster (CPU, memory, disk), what is
already installed, and decide the cluster tool, branch, scope and folder layout.

**Facts found before starting** (checked by Claude, read-only)
- Repo is on `dev`, last commit `2109dba` (multi-stage non-root Dockerfile).
- Uncommitted on `dev`: Docker Step 7 work (`DOCKER_LOG.md`, `JENKINS_LOG.md`, comments in `portfolio/Dockerfile`). `portfolio/entrypoint.sh` shows as modified but only its line endings differ.
- Docker Hub repo `iamkaushal20/portfolio` is **public** (anonymous API call returned 200; tags include `latest` and `dev-latest`). So the cluster can pull the image **without** login credentials (no `imagePullSecret` needed).
- The image runs as non-root `appuser` (UID 1000) and writes only to `/app/staticfiles` and `/app/media`. Matters for volume permissions later (Step 9).
- `entrypoint.sh` runs `migrate` + `collectstatic` on every container start. Fine with one Pod, risky with several (Step 11).

**Part A – machine check: commands I ran (WSL Ubuntu, 13/10/2026)**
```bash
uname -m                      # CPU type
free -h                       # memory WSL can use
df -h ~                       # free disk
docker version --format 'Docker server {{.Server.Version}}'
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
kubectl version --client
minikube version
kind version
```

**Part A – results**

| Check | Result | Good enough? |
|---|---|---|
| CPU type | `x86_64` (= amd64 downloads) | ✅ |
| CPU count (`nproc`, run in Part B) | 8 | ✅ |
| Memory | 15 GiB total, 13 GiB available, 4 GiB swap | ✅ plenty (a local cluster needs ~2 GiB) |
| Disk | 944 GB free | ✅ |
| Docker Engine | 29.8.2 | ✅ |
| Running containers | `jenkins` (`my-jenkins`) and **`kind-control-plane`** (`kindest/node:v1.37.0`), both up 5 hours | ⚠️ **a kind cluster already exists** |
| `kubectl` | client v1.37.0 (Kustomize v5.8.1 built in) | ✅ already installed |
| `minikube` | not installed | – |
| `kind` | v0.33.0 | ✅ already installed |

**What the surprise means**
- **kind** = "Kubernetes IN Docker". Every Kubernetes **node** is a Docker container. `kind-control-plane` is the only node of a cluster called `kind` (kind names node containers `<cluster-name>-control-plane`; `kind` is the default cluster name).
- That single node does **both** jobs: it runs the **control plane** (the brain) and my workloads (the muscle). In production these are separate machines.
- It existed before this session. Where it came from and whether anything on it matters: _asked, pending_.
- `kubectl` v1.37.0 matches the cluster's v1.37.0. kubectl is supported within one minor version of the cluster, so no problem there.
- **Recommendation changed** from minikube to **kind**: already installed and working with Docker Engine in WSL, so nothing new to install.
- kind can only add **port mappings** (laptop port → cluster) when a cluster is **created**. We'll want one for Ingress in Step 8, so Claude suggests a new cluster created from a kind config file that I write.

**Part B – look inside the existing cluster (read-only, 15/10/2026)**
```bash
nproc                              # 8
kind get clusters                  # kind
kubectl config current-context     # kind-kind
kubectl get nodes -o wide
kubectl get pods -A
```

| Check | Result |
|---|---|
| kind clusters | One, called `kind` |
| kubectl context | `kind-kind` (kind always names the context `kind-<cluster name>`) |
| Node | `kind-control-plane`: Ready, role `control-plane`, age 7d, v1.37.0, IP 172.20.0.2, OS Debian 13 (trixie), kernel = the WSL2 kernel, runtime `containerd://2.3.4` |
| Namespaces with Pods | `default`, `kube-system`, `local-path-storage` |
| My own objects in `default` | Bare Pod `kaushal` (6d22h old) and 2 Pods from an `nginx` Deployment (2d1h old). All three run the same image (image ID `ca5e66f340c76`, the nginx image). Who created them: not confirmed, and not needed now because the old cluster is kept as it is |

Notes on what this output means are in Step 1 below.

**Decisions**

| Question | Options discussed | My choice |
|---|---|---|
| Local cluster tool | **kind**: new dedicated cluster from a config file I write (Claude's revised recommendation) / reuse the existing `kind` cluster / install minikube as first suggested | ✅ New kind cluster `portfolio` from my own config file (15/10/2026) |
| Existing `kind` cluster | Keep it until the new one works, or delete it now | ✅ Keep it for now, decide later (15/10/2026) |
| Branch | Commit the Docker Step 7 work on `dev`, then a new branch `k8s-setup` from `dev` / work directly on `dev` | ✅ Commit on `dev`, then `k8s-setup` (15/10/2026) |
| First-pass scope | `web` + `db` first, then `nginx`, monitoring optional at the end / everything at once | ✅ `web` + `db` first, then `nginx`; monitoring optional (15/10/2026) |
| Folder for manifests | `k8s/` at the repo root | ✅ `k8s/` (15/10/2026) |
| Log file | `K8S_LOG.md` at the repo root, separate from the Docker/Jenkins logs | ✅ Keep `K8S_LOG.md` (15/10/2026) |

**Part C – branch setup (commands given 15/10/2026, typed by me):** _pending_
```bash
git status
git add DOCKER_LOG.md JENKINS_LOG.md portfolio/Dockerfile portfolio/entrypoint.sh
git commit -m "Docker step 7: comment the Dockerfile, update logs"
git push origin dev                  # my choice: starts a Jenkins staging build
git switch -c k8s-setup
git add K8S_LOG.md
git commit -m "Start Kubernetes learning log"
git push -u origin k8s-setup         # Jenkins will discover the branch and run only the Test stage
```
- `portfolio/entrypoint.sh` shows as modified, but its content is identical (index and working copy are both LF). Only Git's line-ending bookkeeping flags it. Adding it clears the flag and adds no change to the commit. The `LF will be replaced by CRLF` warning is follow-up F1.

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| `kind get cluster` → usage text + `ERROR: Subcommand is required` | Typo: the subcommand is plural (`clusters`). `kind get` only knows `clusters`, `nodes`, `kubeconfig` | Retyped as `kind get clusters`. No harm done |

---

### Step 1 – Concepts (started 15/10/2026)

**Prediction exercise:** "If nobody ever deployed anything, would `kubectl get pods -A` be empty?"
**Answer: No.** Kubernetes runs its own control plane as Pods in the `kube-system` namespace.

**Anatomy of my cluster** (from `kubectl get pods -A`)

| Pod(s) | Namespace | Brain or muscle? | Job |
|---|---|---|---|
| `kube-apiserver-…` | kube-system | Brain | The front door. `kubectl` and every other part only ever talk to the API server |
| `etcd-…` | kube-system | Brain | The cluster's database: stores the desired state and the current state |
| `kube-scheduler-…` | kube-system | Brain | Picks which node each new Pod runs on |
| `kube-controller-manager-…` | kube-system | Brain | Runs the check-and-fix loops (e.g. "nginx Deployment wants 2 Pods, only 1 exists → create 1") |
| `kube-proxy-…` | kube-system | Muscle (one per node) | Sends traffic addressed to a Service on to one of its Pods |
| `kindnet-…` | kube-system | Muscle (one per node) | kind's network plugin (CNI): gives every Pod its own IP |
| `coredns-…` (×2) | kube-system | Add-on | The cluster's DNS: turns a Service name like `web` into an address |
| `local-path-provisioner-…` | local-path-storage | Add-on | Creates a folder on the node when a PersistentVolumeClaim asks for storage. PostgreSQL will use it in Step 6 |

Not in the list: the **kubelet**, the agent on every node that actually starts the containers. It runs
as a normal program on the node, not as a Pod, so `kubectl get pods` can't show it.

**Reading Pod names: who made this Pod?**

| Name pattern | Example from my cluster | Made by |
|---|---|---|
| `<name>-<node name>` | `etcd-kind-control-plane` | A **static Pod**: started by the kubelet straight from a file on the node. Used for the control plane |
| `<name>-<hash>-<5 random>` | `nginx-69b9cdbbdd-h8l6q` | A **Deployment**, through a **ReplicaSet** (the hash = the ReplicaSet) |
| `<name>-<5 random>` | `kube-proxy-scpxg`, `kindnet-p5cr9` | Here: a **DaemonSet** (one Pod per node) |
| Just `<name>` | `kaushal` | Created directly by hand. Nothing recreates it if it is deleted |

**Reading the RESTARTS column**
- Every Pod showed `11 (82s ago)`: same count, same moment → not app crashes. The whole node container restarted ~82 s earlier, most likely because WSL/Docker had just started. 11 restarts in 7 days ≈ 11 WSL/laptop starts.
- `local-path-provisioner` showed `19 (45s ago)`: it restarted again **after** everything else came back. Most likely it started before the API server was ready, failed, and Kubernetes kept restarting it until it worked. Expect the same from Django when PostgreSQL isn't ready yet (follow-up F3).

**Node = a container; my Pods = containers inside it**
- `CONTAINER-RUNTIME containerd://2.3.4`: inside the node, Kubernetes uses **containerd**, not my WSL Docker.
- So `docker ps` in WSL shows only the node container. The Pods' containers live inside it, and their images are pulled by containerd inside the node.
- `KERNEL-VERSION …microsoft-standard-WSL2`: containers share the host's kernel, so the node reports the WSL kernel.

**Exercise 1 – the chain and the node's containers (15/10/2026, read-only)**
```bash
kubectl get deployments,replicasets,pods     # the Deployment → ReplicaSet → Pods chain
docker exec kind-control-plane crictl ps     # the containers inside the node, as containerd sees them
```

| What I saw | What it means |
|---|---|
| `deployment.apps/nginx 2/2` → `replicaset.apps/nginx-69b9cdbbdd` → `pod/nginx-69b9cdbbdd-h8l6q`, `-k6whh` | ✅ The ReplicaSet's name is the middle of the Pod names. Deployment creates the ReplicaSet; the ReplicaSet creates the Pods |
| ReplicaSet `DESIRED 2  CURRENT 2  READY 2` | Desired state and actual state side by side. If a Pod died, CURRENT would drop to 1 and the ReplicaSet would create a new Pod to get back to 2 |
| `.apps` after `deployment` / `replicaset` | The API group these objects belong to (Pods are in the core group, so no suffix) |
| RESTARTS: `kaushal` 11, nginx Pods 6 | The nginx Pods are younger, so they lived through fewer node restarts. Confirms "restarts = node restarts", not crashes |
| `crictl ps` lists etcd, kube-apiserver, scheduler, … | The brain is just ordinary containers running on the node |
| `crictl` `ATTEMPT` column | The same number as kubectl's RESTARTS |
| `local-path-provisioner` CREATED 7 min ago, everything else 8 min | ✅ Confirms it came back last (it retried after the API server was up) |
| `kaushal` and both nginx containers share image ID `ca5e66f340c76` | `kaushal` runs the same nginx image |

**Concept: imperative vs declarative**
- **Imperative** = give orders one command at a time (`kubectl run …`, `kubectl create deployment …`). Fast, but nothing is written down.
- **Declarative** = write the desired state in a YAML file and hand it over with `kubectl apply -f <file>`. Kubernetes works out what to change. The file lives in git, like my Dockerfile and Jenkinsfile. **The portfolio project will be declarative.**

**Concept: the parts of every Kubernetes object**
- I write four top-level fields: `apiVersion`, `kind`, `metadata`, `spec`.
- Kubernetes adds a fifth, `status`. **`spec` = desired state, `status` = actual state.** The controllers' job is to make `status` match `spec`.

**Exercise 2 – read a real object (given 15/10/2026, read-only):** _pending_
```bash
kubectl get deployment nginx -o yaml
```
Find: (1) `apiVersion` and `kind`, (2) `spec.replicas`, (3) `status.readyReplicas`, (4) the image under `spec.template`, (5) compare `spec.selector.matchLabels` with `spec.template.metadata.labels`. What do I notice?

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| None yet | | |

---

## Follow-ups (open items)

| # | Item | Raised in | Planned for |
|---|------|-----------|-------------|
| F1 | `entrypoint.sh` line endings: permanent fix (`.gitattributes` with `*.sh text eol=lf`) still not done (from `DOCKER_LOG.md`). Only bites if I build the image from my Windows checkout; Jenkins builds on Linux | Docker Step 4b | Before Step 7 if I build locally |
| F2 | `migrate` runs inside every web Pod at start-up | Step 0 | Step 11 |
| F3 | `sleep 2` "wait for database" in `entrypoint.sh` | Step 0 | Step 7: watch how Kubernetes restarts handle a database that isn't ready |
| F4 | nginx `/nginx_status` only allows `172.16.0.0/12` (the Docker network). Pod IPs in a cluster use a different range | Step 0 | Step 8 / 13 |
| F5 | `prom/prometheus:latest`, `grafana/grafana:latest`: pin versions before running them in the cluster | Step 0 | Step 13 |
| F6 | Static + media files are shared between `web` and `nginx` through named volumes. Kubernetes needs a different design for that | Step 0 | Step 8 |

---

## Error index (all steps)

| Step | Error message (short) | Root cause | Fix |
|------|----------------------|-----------|-----|
| 0 | `kind get cluster` → `ERROR: Subcommand is required` | Typo: subcommand is plural | `kind get clusters` |
