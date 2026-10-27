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
| 0 | Check my machine; decide cluster tool, branch, scope, folder layout | Machine check done (15/10/2026): 8 CPUs, 15 GiB RAM, kind + kubectl already installed, existing `kind` cluster found. Decisions made 15/10/2026 (all as recommended). Done (15/10/2026): on `k8s-setup` (⚠️ see F7) |
| 1 | Concepts: cluster, node, control plane, Pod, `kubectl`, manifests, desired state | Done (15/10/2026): cluster anatomy, manifest anatomy (spec/status), labels and selectors |
| 2 | Write a kind config file and create the `portfolio` cluster (kind + kubectl already installed); kubectl contexts | Done (15/10/2026): cluster `portfolio`, 3 nodes Ready, 8000 → 30080. Open: commit (F10), old cluster (F11) |
| 3 | First Pod by hand (imperative), then the same Pod as a YAML manifest (declarative). Self-healing demo | Done (26/10/2026): imperative Pod, declarative Pod, Deployment self-healing. Open: pin image in practice files |
| 3½ | Mock interview 1: 10 questions on Steps 0–3 | Done (26–27/10/2026): score 5/10, bonus 🟡 (controllers placed after scheduler/kubelet). Revisit list in the interview section |
| 4 | A Namespace for the project | Done (27/10/2026): `portfolio` namespace, set as the context default |
| 5 | Configuration: ConfigMap (normal settings) and Secret (passwords), without committing secrets to git | **Current** (started 27/10/2026): Part A ConfigMap ✅, Part B Secret ✅ (27/10/2026); Part C env test given |
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
| spec / status | `spec` = what I want (I write it). `status` = what exists (Kubernetes writes it) |
| API group | The family an object type belongs to: `apps/v1` = group `apps`, version `v1`. Pods are in the core group (`v1`) |
| Label | A `key: value` sticker on an object, e.g. `app: nginx` |
| Selector | A search for labels. Deployments, ReplicaSets and Services find "their" Pods this way, not by name |
| Imperative / declarative | Commands one at a time vs a YAML file of the desired state applied with `kubectl apply -f`. My project = declarative |
| `pod-template-hash` | Label a ReplicaSet stamps on its Pods (also the middle of their names), so old and new ReplicaSets don't count each other's Pods |
| Port mapping (kind) | Docker publishing a port from my machine into a kind node container (`extraPortMappings`). Only settable at cluster creation |
| NodePort (preview) | A Service type that opens the same port (30000–32767) on every node and forwards it to the matching Pods |
| kubeconfig | The file `~/.kube/config` holding the address + credentials of every cluster kubectl knows |
| Context | One named entry in kubeconfig (cluster + user). The **current context** = the cluster every kubectl command goes to. kind names them `kind-<cluster name>` |
| Scheduler events | `describe pod` → Events: `Scheduled` (the scheduler picked a node), then `Pulling` / `Pulled` / `Created` / `Started` (that node's kubelet) |
| `port-forward` | A temporary tunnel from my machine straight into one Pod (`kubectl port-forward pod/<name> <my port>:<Pod port>`). For testing, not for real traffic |
| Taint / toleration | A taint is a "keep off" sign on a node; only Pods with a matching toleration may be scheduled there. The control plane is tainted |
| Pod CIDR | The IP range a node hands out to its Pods (`10.244.<node>.0/24` here) |
| `kubectl apply` | Declarative: "make the cluster match this file". Creates what's missing, updates what changed, leaves the rest alone |
| `--dry-run=server` | `kubectl apply --dry-run=server -f <file>`: the API server fully validates the manifest but stores nothing. My self-check before applying |
| `--dry-run` values | `none` = really do it (default). `client` = kubectl only builds/prints the object, no checks (good for generating YAML). `server` = the API server runs every check but saves nothing (good for verifying files) |
| `kubectl explain` / `api-resources` | Built-in lookup: `explain deployment` shows GROUP/VERSION and fields; `api-resources` lists every kind with its apiVersion and short name (`deploy`, `po`) |
| Namespace | A named group of objects inside one cluster. Deleting it deletes everything inside. `-n <ns>` = one command; `kubectl config set-context --current --namespace=<ns>` = my default |
| Cluster-wide vs namespaced | Nodes, Namespaces, PersistentVolumes belong to the whole cluster; Pods, Deployments, Services, ConfigMaps, Secrets, PVCs belong to one namespace |
| ConfigMap | An object holding ordinary settings as `data: KEY: "value"` (all values are text). Pods read it as environment variables or files |
| Short name vs flag | `cm` is a **short name** for the resource type `configmap` (not a flag). Flags start with dashes (`-n`, `--dry-run`). Shape: `kubectl <verb> <type> <name> <flags>`. Short names: `po` pods, `deploy`, `rs`, `cm`, `svc`, `ns`, `no` nodes, `pvc`; `secrets` has none. List: `kubectl api-resources` |
| Secret | Like a ConfigMap, for sensitive values. Only **base64-encoded**, not encrypted: keep it out of git and limit who can read it. `stringData` lets me write plain text; Kubernetes encodes it |
| CRD | Custom Resource Definition: adds a new object type to the cluster. kubectl mentions CRDs whenever it doesn't recognise a kind |

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

**Part C – branch setup (15/10/2026)**

Commands suggested by Claude:
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

What I actually did (read back from `git reflog`, ~12:03–12:04):

| # | Action | Result |
|---|---|---|
| 1 | One commit on `dev`: `8422b8a` "proper comments on the dockerfile" | Contains `DOCKER_LOG.md`, `JENKINS_LOG.md`, `K8S_LOG.md`, `portfolio/Dockerfile`. So this log is also on `dev` and `main` |
| 2 | `git switch main`, `git merge dev` (fast-forward `a3fef65` → `8422b8a`), pushed `dev` **and `main`** | Not in the suggested list. First time the multi-stage non-root Dockerfile and the Step 9 Jenkinsfile reach `main` → ⚠️ **F7** |
| 3 | `git switch -c k8s-setup` (from `main`, same commit `8422b8a`) | ✅ On `k8s-setup`. **Not pushed yet**: plan is to push it with the first file in Step 2 |
| – | `portfolio/entrypoint.sh` | Flag cleared by the checkouts; file is still LF ✅ (F1 not triggered) |

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

**Exercise 2 – read a real object (15/10/2026, read-only)**
```bash
kubectl get deployment nginx -o yaml
```

| Question | My answer | Notes |
|---|---|---|
| 1. `apiVersion`, `kind` | `apps/v1`, `Deployment` | ✅ `apps` = API group, `v1` = version. Same `apps` as the `.apps` in `deployment.apps/nginx` |
| 2. `spec.replicas` | 2 | ✅ desired |
| 3. `status.readyReplicas` | 2 | ✅ actual. spec = status → nothing for the controllers to fix |
| 4. Image in `spec.template` | `nginx` | ✅ **No tag = `nginx:latest`.** Lesson for my own manifests: always pin a tag (follow-up F8) |
| 5. `spec.selector.matchLabels` vs `spec.template.metadata.labels` | Both `app: nginx` | ✅ Identical, on purpose (see below) |

**Concept: labels and selectors (the glue of Kubernetes)**
- A **label** is a `key: value` sticker on an object (`app: nginx`).
- A **selector** is a search for stickers ("all Pods with `app: nginx`").
- The Deployment/ReplicaSet does **not** track its Pods by name. It counts the Pods that match its selector.
- The `template` stamps `app: nginx` on every Pod it creates, so the selector finds them. If the two didn't match, the API server would reject the Deployment.
- A **Service** finds its Pods the same way. That's how my `web` Service will find the Django Pods later.

**Exercise 3 – see the labels (15/10/2026, read-only)**
```bash
kubectl get pods --show-labels     # every Pod with its labels
kubectl get pods -l app=nginx      # only Pods matching a selector
```

| Question | My answer | Notes |
|---|---|---|
| 1. Which **extra** label do the nginx Pods have, and where have I seen its value? | ?? (didn't spot it) | **`pod-template-hash=69b9cdbbdd`**. Same value as the middle of the Pod names and the ReplicaSet's name. The ReplicaSet stamps it on every Pod it creates. During an update (Step 10) a Deployment runs an old and a new ReplicaSet side by side, and this label lets each one count only its own Pods |
| 2. Label on `kaushal` | `run: kaushal` | ✅ `kubectl run <name>` adds `run=<name>` automatically → `kaushal` was created **imperatively** with `kubectl run` |
| 3. Why is `kaushal` missing from `-l app=nginx`? | Labels don't match | ✅ A selector only returns objects carrying the exact label |

**Step 1 complete (15/10/2026).**

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| None yet | | |

---

### Step 2 – Write the kind config and create the `portfolio` cluster (started 15/10/2026)

**What and why**
Write one small YAML file that describes the whole cluster, then let kind build it. The cluster's
shape lives in git (declarative), so it can be deleted and rebuilt identically at any time.

**Concept: the kind config is not a Kubernetes object**
It borrows the Kubernetes look (`apiVersion` + `kind` at the top), but **kind** reads it, not the API server.
`kind: Cluster`, `apiVersion: kind.x-k8s.io/v1alpha4` (checked against the kind docs, 15/10/2026).

**Concept: port mappings**
A kind node is a Docker container, so Docker can publish a port from my machine into it.
Planned chain for Step 8: browser `localhost:8000` → WSL port 8000 → node container port 30080 → NodePort Service (nodePort 30080) → Django/nginx Pod.
kind rule: the mapping's `containerPort` **must equal** the Service's `nodePort`. Port mappings can **only** be set when the cluster is created.

**Concept: YAML in four rules**
1. Indent with spaces, never tabs (2 spaces per level by convention).
2. A setting is `key: value` (space after the colon).
3. A list item starts with `- `.
4. Indentation shows what belongs to what.

**Plan (Claude's suggestions)**

| Choice | Suggestion | Why | My choice |
|---|---|---|---|
| File | `k8s/kind-config.yaml` | Cluster setup lives in git next to the manifests | _pending_ |
| Cluster name | `name: portfolio` inside the file | Declarative; kubectl context will be `kind-portfolio` | _pending_ |
| Nodes | 1 `control-plane` + 2 `worker` | See the scheduler spread Pods; later see what happens when a node disappears. Each node = one more Docker container; 13 GiB free is plenty. Alternative: single node (simplest; kind's docs say most people don't need multi-node) | _pending_ |
| Port mapping | On the control-plane node: `containerPort: 30080`, `hostPort: 8000`, `listenAddress: "127.0.0.1"`, `protocol: TCP` | Needed for Step 8. `127.0.0.1` = only my own machine can connect | _pending_ |
| Node image | kind's default, not pinned | Simple for now. kind recommends pinning `kindest/node:<version>@sha256:<digest>` for repeatable clusters (optional later) | _pending_ |

**Pre-check (WSL, read-only; run by Claude via `wsl.exe`, 15/10/2026)**
```bash
docker ps --format '{{.Names}}: {{.Ports}}'   # which ports each container publishes
ss -ltn 'sport = :8000'                       # anything listening on 8000? header only = free
```

| Container / port | Published | Meaning |
|---|---|---|
| `kind-control-plane` (old cluster) | `127.0.0.1:34217->6443/tcp` | 6443 = the **API server**. kind published it on a random local port; this is the door `kubectl` uses for context `kind-kind`. The new cluster will get its own random port |
| `jenkins` | `0.0.0.0:8080->8080/tcp`, `50000/tcp` | Jenkins uses 8080 → good that the plan avoids it |
| Port 8000 | header only | ✅ **Free** |

**My file – review 1 (15/10/2026, 12:38, 237 bytes)**
```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: portfolio

nodes:
  - role: control-plane
    containerPort: 30080
    hostport: 8000
    listenAddress:"127.0.0.1"
    protocol: TCP
  - role: worker
  - role: worker
```

| Line | Problem | Rule / fix |
|---|---|---|
| 1–3, 5–6, 11–12 | ✅ Header, cluster name and node list correct. No tabs | – |
| 7–10 | The 4 port settings sit **directly on the node**. kind expects them **inside `extraPortMappings`**, which is a **list** (one item per mapping; a node can have several) | Add `extraPortMappings:` lined up with `role`, then one list item (`- `) holding the 4 settings |
| 8 | `hostport` | Keys are **case-sensitive**: `hostPort` |
| 9 | `listenAddress:"127.0.0.1"` has no space after the colon, so YAML doesn't see a key and a value | YAML rule 2: `listenAddress: "127.0.0.1"` |
| all | Windows line endings (CRLF) | Harmless for YAML (parsers accept CRLF). Different from `entrypoint.sh`, which `sh` executes line by line (F1) |

**Fix (15/10/2026): made by Claude at my request ("correct it")**. Only the control-plane item changed:
```yaml
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 8000
        listenAddress: "127.0.0.1"
        protocol: TCP
```

**Review 2 – checked by Claude**
- No tabs; CRLF line endings kept consistent on every line ✅
- Parsed with a real YAML parser (PyYAML in WSL). How kind sees the file:
  `nodes` = a list of **3** items → item 1 `{role: control-plane, extraPortMappings: [ {containerPort: 30080, hostPort: 8000, listenAddress: "127.0.0.1", protocol: TCP} ]}`, items 2–3 `{role: worker}` ✅
- Lesson: **indentation = structure.** The 4 settings are indented under the `- ` item, so they become **one** mapping inside the `extraPortMappings` list, which belongs to the control-plane node.

**Status:** file ready ✅.

**Create the cluster (15/10/2026, typed by me in WSL)**
```bash
cd /mnt/c/Users/KaushalRupakhetiRent/Desktop/portfolio-site
kind create cluster --config k8s/kind-config.yaml
kubectl get nodes -o wide
docker ps --format '{{.Names}}: {{.Ports}}'
```

| Prediction | My answer | Result |
|---|---|---|
| How many nodes, what names? | 3: `portfolio-control-plane`, `portfolio-worker`, `portfolio-worker2` | ✅ All 3 `Ready`, v1.37.0, containerd 2.3.4 |
| Which container shows port 8000? | The control plane | ✅ `portfolio-control-plane: 127.0.0.1:40551->6443/tcp, 127.0.0.1:8000->30080/tcp` |

**What the output shows**
- Workers show `ROLES <none>`: normal. Only the control plane gets a role label by default.
- Node IPs `172.20.0.3/.4/.5` sit on the same Docker network (`kind`) as the old cluster's node (`172.20.0.2`). Same network, but **separate clusters**.
- `portfolio-control-plane` publishes two ports: its **API server** (6443) on random local port 40551, and **my mapping** 8000 → 30080. The workers publish nothing; they're only reachable inside the Docker network.

**My question: "Why do `portfolio` and `kind` both have a control plane?"**
- Because there are now **two independent clusters** on my machine. kind names node containers `<cluster name>-<role>`:
  - `kind-control-plane` = the old cluster called `kind` (kept on purpose, decision 2A)
  - `portfolio-control-plane` (+ 2 workers) = the new cluster
- Every cluster has its **own** control plane: its own API server, etcd, scheduler and controllers. The two clusters don't know about each other and share nothing.
- kubectl talks to **one** cluster at a time. Which one is decided by the **current context** in my kubeconfig (`~/.kube/config`): `kind-kind` → `127.0.0.1:34217`, `kind-portfolio` → `127.0.0.1:40551`. `kind create cluster` switched it to `kind-portfolio` automatically (that's why `kubectl get nodes` showed the portfolio nodes).
- ⚠️ kind commands default to the cluster **named `kind`**. `kind delete cluster` with no `--name` deletes the **old** one. For the new cluster I must always add `--name portfolio`.

**Exercise 4 – two clusters, one kubectl (given 15/10/2026, read-only):** skipped by me ("next", 16/10/2026)
```bash
kubectl config get-contexts               # * = current context
kubectl get pods                          # current context (portfolio)
kubectl --context kind-kind get pods      # one command aimed at the old cluster
```

**State check (16/10/2026, run by Claude via `wsl.exe`, read-only)**

| Check | Result |
|---|---|
| `kind get clusters` | `kind`, `portfolio` → old cluster **still exists** |
| Current context | `* kind-portfolio` ✅ |
| `default` namespace in `portfolio` | Empty (answer to Exercise 4's prediction: "No resources found in default namespace") |
| Git | `k8s/` untracked, `K8S_LOG.md` modified → Step 2 work **not committed / pushed yet** (F10) |

**What changed after WSL restarted (cluster came back by itself ~23 min before the check)**
- **Node IPs swapped:** control plane 172.20.0.4 → .3, worker .3 → .5, worker2 .5 → .4. Docker hands out container IPs again on every start. Kubernetes copes because components find each other by name. Lesson: never hard-code a node or Pod IP.
- **Pod IPs** are `10.244.x.x` (each node gets its own `/24` slice). Pods using the node's network (kindnet, kube-proxy, control plane) show the node IP instead. Confirms F4: nginx's `allow 172.16.0.0/12` won't match Pod traffic.
- **kube-proxy restarts are high** (8, 8 and 15) while most Pods show 1. All Running now → F9, investigate with `logs --previous` / `describe` in Step 10.

**Decision now due:** delete the old `kind` cluster? (decision 2A said "keep until the new one works") _pending, not decided on 16/10_

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| First "verify" (15/10/2026): `k8s/kind-config.yaml` was **0 bytes** on disk | File created at 12:30 and open in VS Code, but the typed content wasn't saved yet (tools, Git and kind only see what's saved) | Save with Ctrl+S (or turn on File → Auto Save), then verify again |
| Review 1 of `k8s/kind-config.yaml`: port settings directly on the node, `hostport`, `listenAddress:"127.0.0.1"` | Missing the `extraPortMappings` list level; keys are case-sensitive; YAML needs a space after `:` | Corrected by Claude at my request; parsed OK (review 2) |

---

### Step 3 – First Pod: by hand, then as a manifest (started 16/10/2026)

**What and why**
Meet the Pod lifecycle with the simplest possible Pod (plain nginx), first with a command
(imperative), then as a YAML file (declarative). Learn the 5 everyday commands: `get`, `describe`,
`logs`, `port-forward`, `delete`. See that a bare Pod is **not** self-healing.

**Image:** `nginx:1.30.6-alpine`: an exact version (1.30 = nginx's current *stable* line; checked on Docker Hub 16/10/2026). Pinned on purpose (F8).

**Part A – imperative (given 16/10/2026):** _pending_ (port-forward uses 8081 because Jenkins owns 8080)
```bash
kubectl run hello --image=nginx:1.30.6-alpine   # create a Pod by command
kubectl get pods -o wide -w                     # watch it start; Ctrl+C to stop watching
kubectl describe pod hello                      # read the Events at the bottom
kubectl port-forward pod/hello 8081:80          # browse http://localhost:8081, then Ctrl+C
kubectl logs hello                              # the container's output (my visit should appear)
kubectl delete pod hello
kubectl get pods                                # is it coming back?
```
Predictions asked: (1) which node will it land on, and could it be the control plane? (2) what IP range? (3) will it come back after delete?

**Part A – result (26/10/2026):** I reported "everything worked" (page loaded through the tunnel). Outputs and predictions not pasted.
Claude's read-only check afterwards: 3 nodes Ready, `default` namespace empty → the deleted bare Pod did **not** come back.

**Answers to the predictions** (checked by Claude in the cluster, 26/10/2026)

| Node | Pod IP range (`spec.podCIDR`) | Taint |
|---|---|---|
| `portfolio-control-plane` | `10.244.0.0/24` | `node-role.kubernetes.io/control-plane` |
| `portfolio-worker` | `10.244.1.0/24` | none |
| `portfolio-worker2` | `10.244.2.0/24` | none |

1. **A worker, never the control plane.** The control plane carries a **taint**, a "keep off" sign. The scheduler only places a Pod on a tainted node if the Pod has a matching **toleration**. Normal Pods don't, so in a multi-node cluster they always go to the workers. (The control-plane's own Pods tolerate it.)
2. **`10.244.1.x` or `10.244.2.x`**, depending on the worker. Each node hands out IPs from its own `/24` slice.
3. **No.** A bare Pod has no owner (no ReplicaSet/Deployment watching it). Deleted = gone. Part C shows the opposite with a Deployment.

**Part B – declarative (given 26/10/2026):** _pending_
File `k8s/practice/hello-pod.yaml` (practice manifests kept apart from the real app manifests), written by me.

| Field | Value | Why |
|---|---|---|
| `apiVersion` | `v1` | Pods are in the **core** API group, so no `group/` prefix |
| `kind` | `Pod` | |
| `metadata.name` | `hello` | |
| `metadata.labels` | `app: hello` | My own label instead of `kubectl run`'s automatic `run: hello` |
| `spec.containers` | a **list** with one item: `name: nginx`, `image: nginx:1.30.6-alpine`, `ports` = a list with one item `containerPort: 80` | Same shape as my kind file: `nodes` list → item → `extraPortMappings` list → item |

Helper: `kubectl explain pod.spec.containers` = built-in documentation for any field.

```bash
kubectl apply -f k8s/practice/hello-pod.yaml           # create from the file
kubectl get pod hello -o wide --show-labels
kubectl apply -f k8s/practice/hello-pod.yaml           # same file again: what does it say?
# edit the file: add a second label  tier: practice   then:
kubectl apply -f k8s/practice/hello-pod.yaml           # what does it say now?
kubectl get pod hello --show-labels                    # did the Pod restart?
kubectl run hello --image=nginx:1.30.6-alpine --dry-run=client -o yaml   # compare with kubectl run's version (creates nothing)
kubectl delete -f k8s/practice/hello-pod.yaml          # delete by file
```
Predictions asked: (1) what does the second `apply` print? (2) does changing a label restart the Pod?

**My file – review 1 (26/10/2026, 11:21, saved as `k8s/practice/hello-pord.yaml`)**
```yaml
apiVersion: V1
kind: pod
metadata:
  name: hello-pod
  labels:
    app: hello
spec:
  containers:
    - name: hello-container
      image: nginx
      ports:
        - containerPort: 80
```
✅ **Structure is perfect**: every indent level and both lists (`containers` → item → `ports` → item) parse exactly as intended. Big improvement on the kind file.

Checked by Claude with a **server-side dry run** (the API server validates the file but stores nothing):
```bash
kubectl apply --dry-run=server -f k8s/practice/hello-pord.yaml
```
```
error: resource mapping not found for name: "hello-pod" namespace: "" from "k8s/practice/hello-pord.yaml": no matches for kind "pod" in version "V1"
ensure CRDs are installed first
```
`kubectl get pods` afterwards: still empty ✅ (dry run created nothing).

| Line | Problem | Fix | Must? |
|---|---|---|---|
| 1 | `V1` | `v1`: API versions are lowercase | **Must** |
| 2 | `pod` | `Pod`: kinds are written in CamelCase (`Pod`, `Deployment`, `ConfigMap`) | **Must** |
| 10 | `image: nginx` = `nginx:latest` | `nginx:1.30.6-alpine` (pin the tag, F8) | Should |
| file name | `hello-pord.yaml` (typo) | Rename to `hello-pod.yaml`, or use the real name in every command | Should |
| 4, 9 | `hello-pod`, `hello-container` instead of `hello`, `nginx` | ✅ Valid names, my choice. Just use `hello-pod` in the `get`/`delete` commands | – |
| end | No line break after the last line | Harmless. Optional: VS Code setting "Files: Insert Final Newline" | Optional |

**Reading the error:** kubectl looks up the pair (version `V1`, kind `pod`) in the API server's list of known types. No such pair exists, so it guesses I might be using a *custom* type that isn't installed yet (that's the "CRDs" hint: Custom Resource Definitions). Here it's only capital letters.

**New habit:** `kubectl apply --dry-run=server -f <file>` = verify a manifest myself before applying it.

**Part B – result (26/10/2026)**

| Prediction | My answer | Result |
|---|---|---|
| What does the second `apply` print (file unchanged)? | `unchanged` | ✅ `pod/hello-pod unchanged`. apply compares the file with the cluster and does nothing when they already match |
| Does changing a label restart the Pod? | No | ✅ `RESTARTS 0` after adding `tier: practice` |

Cluster state checked by Claude (11:30): `hello-pod  1/1 Running  0 restarts  10.244.2.5  portfolio-worker2  app=hello,tier=practice`. IP `10.244.2.5` is inside worker2's range `10.244.2.0/24` (Part A prediction 2 seen for real). `kubectl apply --dry-run=server` → `pod/hello-pod unchanged (server dry run)` ✅

File review 2 (`k8s/practice/hello-prod.yaml`): `v1` + `Pod` fixed ✅, `tier: practice` added ✅. Still open: `image: nginx` not pinned (F8), file name now `hello-prod` ("prod" reads like *production*; `hello-pod.yaml` suggested).

**Why a label change doesn't restart anything:** labels live in `metadata`, which is information *about* the Pod. The container only restarts when something it runs with changes. Most of a Pod's `spec` can't be changed at all after creation (e.g. `ports`); the API server rejects the edit. That's why real apps use a **Deployment**: to change a Pod, it creates new Pods and removes the old ones.

**Part C – a Deployment and self-healing (given 26/10/2026):** _pending_
File `k8s/practice/hello-deployment.yaml`, written by me.

| Field | Value |
|---|---|
| `apiVersion` / `kind` | `apps/v1` / `Deployment` |
| `metadata.name` | `hello` |
| `spec.replicas` | `3` |
| `spec.selector.matchLabels` | `app: hello` |
| `spec.template` | **My Pod's `metadata` (labels only, no name) + `spec`**, indented one level deeper. Labels must include `app: hello` (= the selector, Step 1) |
| image | `nginx:1.30.6-alpine` |

Key idea: `template` = a Pod manifest without `apiVersion`/`kind`. The Deployment stamps out Pods from it and names them itself.

```bash
kubectl delete -f k8s/practice/hello-prod.yaml                 # remove the bare Pod first (Part B step 5)
kubectl apply --dry-run=server -f k8s/practice/hello-deployment.yaml
kubectl apply -f k8s/practice/hello-deployment.yaml
kubectl get deploy,rs,pods -o wide
kubectl get pods -w                                             # 2nd terminal: leave it watching
kubectl delete pod <one hello-… Pod name>                       # 1st terminal
kubectl delete pods -l app=hello                                # all of them at once
kubectl get pods -o wide
kubectl delete -f k8s/practice/hello-deployment.yaml            # clean up: Deployment → RS → Pods all go
```
Predictions asked: (1) how do 3 Pods spread over the nodes? (2) after deleting one Pod, how many are there seconds later, and with which name? (3) what happens after deleting all of them?

**My file – review 1 (26/10/2026, 11:34), with the line-by-line explanation I asked for**
```yaml
apiVersion: v1                  # ⚠️ group + version. Deployments live in the "apps" group → must be apps/v1
kind: Deployment                # the type of object
metadata:                       # facts ABOUT the Deployment
  name: hello-deployment        # its name; the ReplicaSet and Pods get names built from it
spec:                           # OUTER spec = the Deployment's desired state
  replicas: 3                   # always keep 3 Pods
  selector:                     # how the Deployment recognises "its" Pods
    matchLabels:
      app: hello                # any Pod labelled app=hello counts
  template:                     # the blueprint for every Pod it creates (= a Pod manifest minus apiVersion/kind)
    metadata:
      labels:
        app: hello              # stamped on every new Pod; must match the selector
    spec:                       # INNER spec = the Pod's spec: what runs inside each Pod
      containers:               # a list: a Pod can hold several containers
        - name: hello-container # the container's name inside the Pod
          image: nginx          # ⚠️ unpinned = nginx:latest → nginx:1.30.6-alpine (F8)
          ports:
            - containerPort: 80 # documents that nginx listens on 80; opens/publishes nothing by itself
```
- ✅ Structure, indentation, selector = template labels, no tabs. Pod `name` correctly left out of the template.
- Trailing space after `template:` (line 10): harmless.
- **Two `spec`s:** outer (lines 5–19) = what the *Deployment* keeps true; inner (lines 14–19) = what each *Pod* runs.
- **Names after apply:** Deployment `hello-deployment` → ReplicaSet `hello-deployment-<hash>` → Pods `hello-deployment-<hash>-<random>` (Step 1 naming patterns).
- **`containerPort` ≠ Docker `-p`:** it's information for people and tools. Reaching the Pod from outside needs port-forward or a Service (Step 7–8).

Server dry run (by Claude):
```
error: resource mapping not found for name: "hello-deployment" namespace: "" from "k8s/practice/hello-deployment.yaml": no matches for kind "Deployment" in version "v1"
ensure CRDs are installed first
```
Same error family as Part B: the (version, kind) pair doesn't exist. `v1` is the **core** group (Pod, Service, ConfigMap…); Deployment is in **apps**.
Cluster at the same time: `No resources found` → the bare `hello-pod` was already deleted ✅ (Part C step 1 done).

**Part C – result (26/10/2026).** I fixed line 1 (`apps/v1`) and reported "done". Server dry run: `deployment.apps/hello-deployment created (server dry run)` ✅. Outputs/predictions not pasted; Claude rebuilt what happened from `kubectl get events`:

| Time (UTC) | What I did | What the cluster did |
|---|---|---|
| 11:43:56–11:44:03 | `kubectl apply -f hello-deployment.yaml` | ReplicaSet `hello-deployment-54958dc87f` created 3 Pods: `-5xm97` + `-6jcm4` on **worker2**, `-xc8hc` on **worker**. None on the control plane (taint) |
| 11:46:15 | Deleted `-5xm97` | **Same second:** RS `SuccessfulCreate` → new Pod `-bfhzt` (new name) on worker. Back to 3 ✅ self-healing |
| 11:46:48 | Deleted all (`-l app=hello`) | Same second: 3 new Pods `-wgxbq`, `-jpfz5` (worker2), `-lzkfn` (worker) ✅ |
| 11:47:30 | `kubectl delete -f hello-deployment.yaml` | All Pods stopped; Deployment → ReplicaSet → Pods removed together (owner chain) |

Answers to the Part C predictions: (1) spread over the **two workers only**; the scheduler balances but doesn't guarantee an exact split (here 2 + 1). (2) still **3**, the replacement has a **new name** (Pods are replaced, never revived). (3) all 3 come straight back; only deleting the **Deployment** makes them go away for good.

⚠️ Image still `nginx` (unpinned). The events show `Pulling image "nginx"` for **every** new Pod: with the `latest` tag, Kubernetes defaults to `imagePullPolicy: Always` (pull every time). A pinned tag defaults to `IfNotPresent` (reuse the copy already on the node). One more reason for F8.

**Step 3 complete (26/10/2026)**, apart from pinning the image in the two practice files.

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| Part B review 1: `no matches for kind "pod" in version "V1"` / `ensure CRDs are installed first` | `apiVersion: V1`, `kind: pod`: both case-sensitive | `v1`, `Pod`; self-check with `kubectl apply --dry-run=server -f` |
| Part C review 1: `no matches for kind "Deployment" in version "v1"` | Deployment is in the `apps` API group, not core `v1` | `apiVersion: apps/v1` |
| Part C review 2 (11:39) – kept for the record: same error again | I pasted Claude's **annotated** block into the file. It showed my original file plus notes, not a corrected version, so line 1 (`v1`) and line 17 (`nginx`) were unchanged. Claude's explanation didn't say that clearly | Change only the values before the `#`: line 1 → `apps/v1`, line 17 → `nginx:1.30.6-alpine`. Comments can stay (YAML ignores everything after `#`) |

---

### Mock interview 1 – Steps 0–3 (started 26/10/2026)

My request: 10 interview questions, one at a time, to confirm I understand the concepts and the commands so far before Step 4.
Verdicts: ✅ correct · 🟡 partly · ❌ missed. Model answers are in my words-to-learn, not to memorise.

| # | Topic | Question | My answer | Verdict | Model answer / what was missing |
|---|---|---|---|---|---|
| 1 | Desired state | Compose already restarts crashed containers (`restart: unless-stopped`). What does Kubernetes add? | "Kubernetes adds multiple points of failure… with replicas, even if one Pod restarts or is unhealthy, traffic is diverted to a healthy Pod" | 🟡 | ✅ Replicas + traffic only to healthy Pods is a real benefit (that part is Services + readiness probes, Steps 7–8). ⚠️ **Wording:** the term is "removes the **single point of failure** (SPOF)" / "adds **redundancy**". "Multiple points of failure" means the opposite. ❌ Missing the core idea: **desired state + reconciliation across many machines**. Compose restarts a container on the same host, and the host itself is the SPOF. Kubernetes keeps comparing desired vs actual: a crashed, deleted or unhealthy Pod is replaced, and if a whole **node** dies its Pods are recreated on another node. **Model answer:** "Compose restarts a container on one machine. Kubernetes stores the desired state and its controllers keep making reality match it across a cluster: failed or deleted Pods are replaced, even on another node if one dies, and with replicas behind a Service traffic only reaches healthy Pods." |
| 2 | Object chain | Explain each part of the Pod name `hello-deployment-54958dc87f-5xm97`. Which object created this Pod? | "hello is the name of the cluster, deployment is the name of the deployment, and the last part is the unique id of the Pod, which changes after each recreation" | 🟡 | ✅ `5xm97` = random suffix, unique per Pod; a replacement gets a new one (strictly: it's a **new** Pod, not the old one recreated). ❌ `hello-deployment` is **one** name, the Deployment's `metadata.name`. The cluster (`portfolio`) never appears in Pod names (it does appear in kind's **node container** names, e.g. `portfolio-worker`). ❌ Middle part `54958dc87f` missed = **`pod-template-hash`**, the ID of the **ReplicaSet** `hello-deployment-54958dc87f`; it changes only when the Pod template changes (e.g. new image). ❌ Creator not answered: the **ReplicaSet** created the Pod; the Deployment created the ReplicaSet. **Model answer:** "`hello-deployment` is the Deployment, `54958dc87f` is the pod-template-hash that names its ReplicaSet, `5xm97` is a random suffix for this one Pod. The ReplicaSet created it, and the Deployment owns the ReplicaSet." |
| 3 | Labels / selectors | The selector says `app: hello`. How does the ReplicaSet decide which Pods are its own? What happens if the template's labels say `app: web` while the selector still says `app: hello`? | "By the labels written under matchLabels. Since the value differed, the Pods created won't be under the same ReplicaSet" | 🟡 | ✅ Part 1: it counts the Pods whose **labels match its selector**, never by name. ❌ Part 2: **nothing is created at all.** The API server rejects the Deployment at `apply` time. Checked by Claude with a server dry run: `The Deployment "hello-deployment" is invalid: spec.template.metadata.labels: Invalid value: {"app":"web"}: selector does not match template labels`. **Why this rule exists:** the ReplicaSet would create a Pod labelled `app: web`, count 0 Pods matching `app: hello`, create another, and so on forever. **Model answer:** "The ReplicaSet counts Pods whose labels match its selector. If the template's labels don't match the selector, the API server rejects the Deployment, because the controller would never see the Pods it creates and would keep creating new ones." |
| 4 | Self-healing | In Part A you deleted a bare Pod, in Part C a Deployment's Pod. Why were the outcomes different? Which component noticed in Part C, and what exactly did it compare? | "In the first case there is no ReplicaSet to check for replicas; in the second, the ReplicaSet makes sure there's always a minimum number of Pods running. The ReplicaSet (under the Deployment) noticed, comparing desired state to current state" | ✅ | Two refinements: (1) **exactly**, not minimum: too few → create, too many → delete (e.g. scaling 3 → 2). (2) The ReplicaSet is an **object** (data stored in etcd); objects don't act. The **ReplicaSet controller**, a loop inside **kube-controller-manager** on the control plane, does the work. It compared `spec.replicas` (3) with the number of running Pods matching its selector (2) and created 1. **Model answer:** "The bare Pod had no owner, so nothing was watching it. The other Pod was owned by a ReplicaSet. The ReplicaSet controller in kube-controller-manager compared the desired count, 3, with the Pods matching its selector, 2, and created one more. It always keeps exactly the desired number." |
| 5 | Architecture | You run `kubectl apply -f hello-deployment.yaml`. Walk through what happens, component by component, until the nginx container runs on a worker | "I don't know this" | ❌ | Full walkthrough in the box below the table. **Interview tip:** never stop at "I don't know"; say the parts you do know (here: API server stores it, a controller creates Pods, scheduler picks a node, kubelet starts it). **Re-ask at the end as a bonus.** |
| 6 | Declarative | (1) Imperative vs declarative, using commands I ran as examples. (2) Every object has a `spec` and a `status`: who writes each? | "Imperative is what you type directly in the terminal without a YAML file; declarative is writing a YAML file and running a command to apply it. Imperative example: `kubectl run pod hello --image nginx`. The kube controller writes spec and status" | 🟡 | ✅ Part 1 mostly right. Sharper: **imperative = "do this action"**, **declarative = "make it look like this"** (Kubernetes works out create / update / nothing; the second apply printed `unchanged`). The file isn't the point: `kubectl create -f file.yaml` is still imperative (fails if it already exists). Exact command I ran: `kubectl run hello --image=nginx:1.30.6-alpine` (`run` always makes a Pod; an extra word `pod` would become the Pod's **name**). Declarative example missing: `kubectl apply -f k8s/practice/hello-deployment.yaml`. ❌ Part 2: **I** write the **spec** (through `kubectl apply` → API server). **Kubernetes** writes the **status**: the kubelet reports each Pod's status, controllers update their own object's status (e.g. a ReplicaSet's `readyReplicas`). Controllers *do* write specs, but only of objects they create (the ReplicaSet controller fills each Pod's spec from the template; the scheduler adds the node name). **Model answer:** "Imperative is giving orders, like `kubectl run hello --image=nginx:1.30.6-alpine`. Declarative is describing the end state in a file and running `kubectl apply -f`, so Kubernetes works out what to change. I write the spec, and Kubernetes writes the status: kubelets report Pod status and controllers update counts like readyReplicas." |
| 7 | Troubleshooting | `kubectl apply` fails with `no matches for kind "Deployment" in version "v1"`. (1) What does it mean? (2) Fix? (3) How to catch it before applying? (4) Which built-in command shows the right apiVersion for a kind? | "It's the version error. The apiVersion for Deployment is `app/v1`. We could have caught it with the `--dry-run=service` command" | 🟡 | Right ideas, but two one-letter slips and part 4 missing (Claude ran each on the cluster). (1) More precise: the cluster has no type called `Deployment` in the **core** group `v1`; Deployments live in the **apps** group. (2) ⚠️ `apps/v1`, plural. `app/v1` fails exactly the same way. (3) ⚠️ `--dry-run=server`: `--dry-run=service` gives `error: Invalid dry-run value (service). Must be "none", "server", or "client".` (4) Missing: **`kubectl explain deployment`** → `GROUP: apps · KIND: Deployment · VERSION: v1`, or **`kubectl api-resources`** → `deployments  deploy  apps/v1  true  Deployment` (also lists short names: `deploy`, `po`). **Model answer:** "The cluster has no Deployment type in the core v1 group, because Deployments are in the apps group. Fix it with apiVersion apps/v1. A server-side dry run would have caught it, and `kubectl explain deployment` or `kubectl api-resources` shows the right group and version." |
| 8 | Contexts | Two clusters on my laptop. (1) How does kubectl know which one a command goes to? (2) How do I check, and how do I aim one command at the other cluster? (3) Why check before `kubectl delete`? (4) Which kind command has a dangerous default here? | "From the context of the cluster; we can use `kubectl config set-cluster` to set the appropriate cluster. `kubectl config get-context` to know which cluster we are in. No idea" | 🟡 | Commands checked by Claude on the cluster. (1) ✅ "context" is right: every command goes to the **current context** in kubeconfig (`~/.kube/config`). ❌ `set-cluster` doesn't switch: it **writes a cluster entry** into kubeconfig ("Set a cluster entry in kubeconfig"). Switch with **`kubectl config use-context kind-kind`**. (2) 🟡 `get-context` → `error: unknown command "get-context"`; it's **`get-contexts`** (plural, `*` = current) or **`current-context`** (prints `kind-portfolio`). One command elsewhere: **`--context kind-kind`** (Exercise 4). (3) ❌ kubectl never asks "which cluster did you mean?": `delete` acts on the current context immediately; at work that's deleting production instead of a test cluster. (4) ❌ **kind commands default to the cluster named `kind`**: `kind delete cluster` with no `--name` deletes the **old** cluster; anything for the new one needs `--name portfolio`. **Model answer:** "kubectl sends every command to the current context in kubeconfig. `kubectl config current-context` shows it, `use-context` switches it, and `--context` aims a single command elsewhere. Check before deleting, because kubectl deletes from whichever cluster is current without asking. kind defaults to the cluster named kind, so `kind delete cluster` without --name would delete my old cluster." |
| 9 | Scheduling | (1) Why did none of the Part C Pods land on `portfolio-control-plane`? Name the mechanism. (2) They split 2 + 1 over the workers: is an even split guaranteed? (3) Some kube-system Pods (coredns) *do* run on the control plane: how are they allowed? | "Because the control plane never runs the workload, it acts as a manager. Not guaranteed: Pods are assigned to whichever worker is less loaded. Because it helps to manage nodes, such as mapping IPs to Pod names, but doesn't carry the actual workload" | 🟡 | Checked by Claude on both clusters. (1) 🟡 Right purpose, but **"never" is wrong** and the mechanism wasn't named. It's a **taint**: `node-role.kubernetes.io/control-plane=NoSchedule` on `portfolio-control-plane`. Counter-example: the **old** single-node cluster's `kind-control-plane` has **no taint**, and my `kaushal` Pod ran **on it** (kind removes the taint when there's only one node). (2) ✅ Not guaranteed: the scheduler filters nodes that fit, then scores them (free resources, spreading Pods of the same ReplicaSet, …) and picks the best; 2 + 1 is normal. (3) ❌ I described *what* coredns does (DNS: turns names into IPs), not *how it's allowed*: it has a matching **toleration** (`node-role.kubernetes.io/control-plane effect=NoSchedule`), and both coredns Pods run on `portfolio-control-plane`. (etcd, the API server etc. aren't scheduled at all: the kubelet starts them from files on the node = static Pods.) **Model answer:** "The control plane has a NoSchedule taint, so the scheduler keeps normal Pods off it. A single-node cluster removes the taint, which is why my old cluster ran Pods on its control plane. The split isn't guaranteed, because the scheduler scores nodes on free resources and spreading. System Pods like coredns carry a toleration for that taint, so they're allowed there." |
| 10 | Networking | (1) In the kind config, what do `hostPort: 8000` and `containerPort: 30080` each refer to, and why couldn't this be added to the old cluster? (2) Does `containerPort: 80` in my Pod file make nginx reachable from my browser? (3) How did I actually reach nginx in Part A? | "It maps the container default port to the host port. No, it doesn't. We should enable port forwarding to make it reachable, with `kubectl port-forward pod/hello 8081:80`" | 🟡 | (1) 🟡 Too vague, and the second half is missing. **`hostPort: 8000`** = the port on **my machine** (WSL, `127.0.0.1:8000`). **`containerPort: 30080`** = a port inside the **kind node container**, where a **NodePort Service** will listen in Step 8. It is not nginx's default port (80). Chain: browser `localhost:8000` → node `30080` → Service → Pod. Why not on the old cluster: kind does this with **Docker port publishing**, which Docker only sets when a container is **created**; the old node container already existed, so the cluster would have to be rebuilt. (2) ✅ No: `containerPort` only **documents** the port; it publishes nothing. (3) ✅ Exactly right: `kubectl port-forward pod/hello 8081:80` = a temporary tunnel from my port 8081 to the Pod's port 80 (8081 because Jenkins owns 8080). **Model answer:** "hostPort 8000 is on my machine; containerPort 30080 is inside the kind node, where a NodePort Service will listen. kind uses Docker port publishing, which can only be set when a container is created, so the old cluster would need rebuilding. containerPort 80 in a Pod only documents the port. In Part A I used kubectl port-forward pod/hello 8081:80." |
| Bonus | Architecture (Q5 again) | Put these in order and give each one line: kubelet, scheduler, API server, ReplicaSet controller, etcd, Deployment controller | (27/10/2026) "API server, etcd, scheduler, kubelet, Deployment controller, ReplicaSet controller" (order only, no one-liners) | 🟡 | ✅ API server → etcd correct. ❌ The two **controllers come before** the scheduler and kubelet: the scheduler can only place Pods that **exist**, and Pods are created by the ReplicaSet controller. **Rule of thumb: you can't place what doesn't exist, and you can't start what isn't placed.** Correct order: **API server** (checks + stores) → **etcd** (holds it) → **Deployment controller** (creates the ReplicaSet) → **ReplicaSet controller** (creates the Pods) → **scheduler** (picks a node) → **kubelet** (starts the container through containerd, reports status). Still on the revisit list |

**Concept: from `kubectl apply` to a running container (answer to Q5)**

| # | Component | What it does | Where I saw it |
|---|---|---|---|
| 1 | `kubectl` | Reads the current context from kubeconfig and sends the Deployment to that cluster's **API server** | `127.0.0.1:40551 → 6443` in `docker ps` |
| 2 | **API server** | Checks the object (valid? allowed?) and stores it in **etcd**. kubectl prints `created` **here**: nothing is running yet | The `apps/v1` and `selector does not match` rejections happen at this step |
| 3 | **Deployment controller** (in kube-controller-manager) | Sees a new Deployment with no ReplicaSet → creates ReplicaSet `hello-deployment-<hash>` | `kubectl get rs` |
| 4 | **ReplicaSet controller** (in kube-controller-manager) | Wants 3, counts 0 → creates 3 **Pod objects**. They have no node yet → `Pending` | Event `SuccessfulCreate` |
| 5 | **Scheduler** | Sees Pods with no node, skips the tainted control plane, picks a worker, writes the node name onto each Pod | Event `Scheduled … to portfolio-worker2` |
| 6 | **kubelet** on that worker | Sees a Pod assigned to its node → tells **containerd** to pull the image and start the container | Events `Pulling` → `Pulled` → `Created` → `Started` |
| 7 | kubelet → API server → etcd | Reports the Pod's **status** back; `kubectl get pods` now shows `Running` | `READY 1/1` |

- **Hub and spoke:** every component talks **only to the API server**. They never call each other; each one *watches* for changes and reacts. That's why one failing part doesn't break the others.
- **Each step is a small loop** comparing desired vs actual, the same idea as Q1 and Q4.

**Side question during Q8: "What do the values in dry run mean?" (26/10/2026)**

| Value | How far the request goes | Checks the object? | Saved? | Use it for |
|---|---|---|---|---|
| `none` (default) | All the way | Yes | **Yes**: the real thing | Normal commands |
| `client` | Stays in kubectl. It only asks the server which types exist | **No**: only builds and prints the object | No | Generating YAML: `kubectl run … --dry-run=client -o yaml` (Part B) |
| `server` | To the **API server**, which runs every check, fills in defaults, then throws the result away | **Yes**, exactly like a real apply | No | **Checking my files** before applying |

In Q5 terms: a server dry run stops at **step 2**, after the API server's checks but before etcd.

Proof on my cluster with the broken selector file from Q3 (run by Claude):
```
--dry-run=client → deployment.apps/hello-deployment created (dry run)        ← happily accepts a broken file
--dry-run=server → The Deployment "hello-deployment" is invalid: … `selector` does not match template `labels`
kubectl get deploy → No resources found                                      ← neither stored anything
```
**Takeaway:** `client` = "what would I send?", `server` = "would the cluster accept it?". To verify a manifest, always use `server`.

**Score after 10 questions (26/10/2026): 5 / 10** (✅ = 1, 🟡 = ½, ❌ = 0 → 1 ✅, 8 🟡, 1 ❌). Bonus re-ask of Q5 pending.

**Strengths**
- Self-healing reasoning: bare Pod vs ReplicaSet, desired vs current (Q4 ✅).
- The *idea* behind most answers was right: replicas and healthy traffic (Q1), labels decide ownership (Q3), declarative = file + apply (Q6), split not guaranteed (Q9), containerPort publishes nothing and port-forward (Q10).
- Honest "I don't know" instead of guessing (Q5).

**Pattern:** I know *what* happens, but often miss *which mechanism* does it and the *exact* name or command.

**Revisit before Step 4**

| Topic | Questions | What to drill |
|---|---|---|
| apply → running container: the 7 components in order | Q5 | The concept table above; say it out loud once |
| Exact spelling of commands and values | Q7, Q8 | `apps/v1`, `--dry-run=server`, `get-contexts`, `current-context`, `use-context`, `--context` |
| Name the mechanism | Q2, Q3, Q9 | `pod-template-hash` = ReplicaSet ID; selector ≠ labels → **rejected**; taint + toleration |
| Who writes what | Q6 | I write `spec`; kubelet and controllers write `status` |
| Cluster safety | Q8 | Check the context before `delete`; kind defaults to the cluster named `kind` |
| Port layers | Q10 | my machine (8000) → kind node (30080) → Service → Pod (80) |
| Vocabulary | Q1 | "removes the single point of failure", "redundancy" |

---

### Step 4 – A Namespace for the project (started 27/10/2026)

**What and why**
Give the portfolio app its own named area inside the cluster, so its objects stay apart from practice
objects and system parts. First real manifest of the app: `k8s/namespace.yaml`.

**Starting state (checked by Claude, 27/10/2026):** current context `kind-portfolio`, its NAMESPACE column empty (= `default`). Namespaces: `default`, `kube-node-lease`, `kube-public`, `kube-system`, `local-path-storage`. Only object in `default`: `service/kubernetes` (the API server's own Service). Git: still uncommitted (F10).

**Concept: namespaces**
- A namespace is a named group of objects inside **one** cluster. Names must be unique **within** a namespace, so `web` can exist in two namespaces at once.
- **Deleting a namespace deletes everything inside it.** Powerful for clean-up, dangerous by mistake.
- Not everything lives in a namespace. **Cluster-wide** objects: Nodes, Namespaces themselves, PersistentVolumes. **Namespaced:** Pods, Deployments, ReplicaSets, Services, ConfigMaps, Secrets, PersistentVolumeClaims. (`kubectl api-resources` → NAMESPACED column.)
- **DNS:** a Service is reachable as plain `web` from Pods in the **same** namespace, and as `web.portfolio` (full: `web.portfolio.svc.cluster.local`) from other namespaces. So `server web:8000` in `nginx.conf` and `DB_HOST=db` keep working **if** nginx, web and db share one namespace.

**Plan (Claude's suggestions)**

| Choice | Suggestion | Why | My choice |
|---|---|---|---|
| Namespace name | `portfolio` | Matches the cluster and project | _pending_ |
| File | `k8s/namespace.yaml` | First real app manifest, next to `kind-config.yaml` | _pending_ |
| Namespace in later manifests | Write `namespace: portfolio` in every manifest's `metadata` | The file then says where it belongs, so it can't land in the wrong namespace by accident | _pending (decide in Step 5)_ |

**Task (given 27/10/2026):** _pending_
1. Look up `apiVersion` and `kind` for a Namespace **myself** (Q7 lesson): `kubectl api-resources | grep -i namespace` or `kubectl explain namespace`.
2. Write `k8s/namespace.yaml`: only `apiVersion`, `kind`, `metadata.name`. A Namespace needs no `spec`.
3. Run:
```bash
kubectl apply --dry-run=server -f k8s/namespace.yaml
kubectl apply -f k8s/namespace.yaml
kubectl get ns
kubectl apply -f k8s/practice/hello-deployment.yaml -n portfolio   # put the practice app inside it
kubectl get pods                                                   # prediction 1
kubectl get pods -n portfolio
kubectl config set-context --current --namespace=portfolio         # make portfolio my default
kubectl config get-contexts                                        # NAMESPACE column
kubectl get pods                                                   # now?
kubectl delete -f k8s/practice/hello-deployment.yaml               # clean up (goes to portfolio now)
```
Predictions asked: (1) after applying into `portfolio`, what will a plain `kubectl get pods` show? (2) is a Namespace itself inside a namespace?

**Result (27/10/2026).** I reported "done"; predictions and outputs not pasted. Checked by Claude:

| Check | Result |
|---|---|
| `k8s/namespace.yaml` | `apiVersion: v1` · `kind: Namespace` · `metadata.name: portfolio` ✅ (looked up and written by me, correct first time) |
| `kubectl get ns` | `portfolio  Active  15m` ✅ |
| Context | `* kind-portfolio … NAMESPACE portfolio` ✅ default namespace switched |
| Events in `portfolio` | 08:38 practice Pods created there, 08:41 all deleted ✅ |
| `kubectl get all -n portfolio` | `No resources found` ✅ clean |
| Server dry run | `namespace/portfolio unchanged (server dry run)` ✅ |

Answers to the predictions: (1) `No resources found in default namespace.`: kubectl only looks in **one** namespace (the context's default) unless I add `-n` or `-A`. (2) **No.** Namespaces are cluster-wide (`kubectl api-resources` → NAMESPACED `false`).

Spotted in the events: the ReplicaSet hash was again **`54958dc87f`**, the same as on 26/10 in `default`. The hash is calculated from the **Pod template**, so an identical template gives an identical hash, whatever the day or namespace (Q2).

**Step 4 complete (27/10/2026).**

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| None | | |

---

### Step 5 – Configuration: ConfigMap and Secret (started 27/10/2026)

**What and why**
In Compose, one `.env` file fed both `web` and `db`. In Kubernetes, settings live **in the cluster** as objects:
a **ConfigMap** for ordinary settings and a **Secret** for passwords and keys. Pods read them as environment
variables (Step 6–7). Goal: the real secret values never reach git.

**What the app actually reads (checked by Claude in `settings.py`, 27/10/2026)**

| Variable | Default in code | Needed? |
|---|---|---|
| `SECRET_KEY` | none | **Required** (crash without it) |
| `ALLOWED_HOSTS` | none | **Required** |
| `DB_PASSWORD` | none | **Required** |
| `DEBUG` | `False` | Optional |
| `CSRF_TRUSTED_ORIGINS` | empty | Needed in Step 8 (see F13) |
| `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT` | `portfolio_db`, `portfolio_user`, `db`, `5432` | Optional, but written down explicitly is clearer |
| `EMAIL_*`, `EMAIL`, social URLs, `USE_S3` | console e-mail, empty, `False` | Not needed now |
| PostgreSQL image: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | – | Needed by the `db` container (Step 6) |
| `PORTFOLIO_IMAGE` | – | Compose only. In Kubernetes the image goes in the Deployment |
| `GRAFANA_PASSWORD`, `EMAIL_PASSWORD` | – | Monitoring / e-mail: later (Step 13) |

**Suggested split**

| ConfigMap `portfolio-config` (ordinary) | Secret `portfolio-secrets` (sensitive) |
|---|---|
| `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`, `POSTGRES_DB`, `POSTGRES_USER` | `SECRET_KEY`, `DB_PASSWORD`, `POSTGRES_PASSWORD` (same value as `DB_PASSWORD`) |

Same values under two names (`DB_*` for Django, `POSTGRES_*` for the PostgreSQL image), exactly like the Compose `.env`. Can be tidied in Step 7.

**Concepts**
- A ConfigMap has **`data`** instead of `spec`: a flat list of `KEY: value`.
- **Every value must be text.** YAML reads `False` as a true/false value and `5432` as a number, and the API server rejects both in a ConfigMap. Quote them: `"False"`, `"5432"`.
- A **Secret is not encrypted**, only **base64-encoded** (a reversible text format). Anyone allowed to read Secrets can decode them. The protection is: keep them out of git, and limit who can read them.

**Decisions**

| Question | Options | Claude's recommendation | My choice |
|---|---|---|---|
| `namespace:` in every manifest (from Step 4) | Yes / no (rely on `-n` or the context) | **Yes**: `namespace: portfolio` in `metadata` | ✅ Yes: I wrote it into `configmap.yaml` (27/10/2026) |
| How to create the Secret without committing it | **A.** `k8s/secret.yaml` (real values, written with `stringData`) **ignored by git**, plus a committed placeholder copy · **B.** Imperative `kubectl create secret generic … --from-literal=…` (nothing on disk; retype after every cluster rebuild) · **C.** Encrypted-secret tools (Sealed Secrets, SOPS): later | **A**: declarative, I learn the Secret format, nothing real in git | ✅ **A**, taken as the recommendation after I said "next" without choosing (27/10/2026). Switch to B if I object |

**Part A – ConfigMap (given 27/10/2026)**
File `k8s/configmap.yaml`, written by me: `apiVersion` + `kind` looked up myself, `metadata` (`name: portfolio-config`, `namespace: portfolio`), `data` with the 9 keys above. Suggested values: `DEBUG "False"`, `ALLOWED_HOSTS "localhost,127.0.0.1"`, `CSRF_TRUSTED_ORIGINS "http://localhost:8000"`, `DB_NAME`/`POSTGRES_DB portfolio_db`, `DB_USER`/`POSTGRES_USER portfolio_user`, `DB_HOST db`, `DB_PORT "5432"`.
```bash
kubectl apply --dry-run=server -f k8s/configmap.yaml
kubectl apply -f k8s/configmap.yaml
kubectl get configmap            # short name: cm
kubectl describe cm portfolio-config
```

**Part A – result (27/10/2026).** Written and applied by me. Checked by Claude: `configmap/portfolio-config unchanged (server dry run)`; `kubectl get cm -n portfolio` → `portfolio-config  DATA 9`. All values quoted, no tabs, `namespace: portfolio` ✅.

| Finding | Why it matters | Fix |
|---|---|---|
| ⚠️ Line 11: **`POSTGRESS_DB`** (double S) | The API server accepts **any** key name, so neither the dry run nor `apply` can catch it. The PostgreSQL image only reads `POSTGRES_DB`; with it missing, PostgreSQL names the database after `POSTGRES_USER` → it would create `portfolio_user`, while Django asks for `DB_NAME=portfolio_db` → `database "portfolio_db" does not exist` in Step 6–7 | Rename the key to `POSTGRES_DB`, then `kubectl apply` again (expect `configured`). The old key stays only if I don't re-apply the file |
| `kube-root-ca.crt` ConfigMap I didn't create | Kubernetes puts it in **every** namespace automatically: the cluster's certificate, so Pods can check they're really talking to the API server | Leave it alone |
| `describe` lists keys alphabetically | Not the order of my file. Purely display | – |

**Lesson:** validation checks the *shape* (is it a valid ConfigMap?), not the *meaning* (will PostgreSQL find the key it looks for?). Typos in key names only show up when the app runs.

**Part B – Secret (given 27/10/2026, option A):** _pending_

| # | Action | Why |
|---|---|---|
| 1 | Add `k8s/secret.yaml` to `.gitignore` **first** | If the file exists before the ignore rule, one `git add k8s` stages the real passwords |
| 2 | Write the placeholder copy **`k8s/secret.yaml.example`** (values like `change-me`) | Committed, so anyone (me after a rebuild) knows which keys are needed. The `.example` ending matters: `kubectl apply -f k8s/` only reads `.yaml`/`.yml`/`.json`, so the placeholders can never overwrite the real Secret |
| 3 | Copy it to `k8s/secret.yaml` and put the real values in | |
| 4 | Generate fresh values in WSL: `openssl rand -hex 32` (SECRET_KEY), `openssl rand -hex 16` (password, used for **both** `DB_PASSWORD` and `POSTGRES_PASSWORD`) | Hex = only 0–9 and a–f, so no character can confuse YAML. Never paste them into chat or this log |

Secret shape: `apiVersion` + `kind` (look up), `metadata` (`name: portfolio-secrets`, `namespace: portfolio`), `type: Opaque` (= a generic key/value Secret), and **`stringData`** (plain text; Kubernetes base64-encodes it into `data`).
```bash
git check-ignore -v k8s/secret.yaml        # must print the .gitignore rule; nothing = NOT ignored
git status --short                         # secret.yaml must NOT appear
kubectl apply --dry-run=server -f k8s/secret.yaml
kubectl apply -f k8s/secret.yaml
kubectl get secret
kubectl describe secret portfolio-secrets  # shows sizes, not values
kubectl get secret portfolio-secrets -o jsonpath='{.data.DB_PASSWORD}' | base64 -d; echo   # proves base64 ≠ encryption (don't paste the output)
```

**Verification 1 (27/10/2026, 09:26; checked by Claude, secret values never printed)**

| Check | Result |
|---|---|
| ConfigMap typo | ✅ Fixed and re-applied. Cluster keys now include `POSTGRES_DB`, and **`POSTGRESS_DB` is gone**: `kubectl apply` remembers what it applied last time (the `last-applied-configuration` annotation), so a key I delete from the file is deleted from the cluster too |
| My file names | `k8s/secrets.yaml` + `k8s/secrets.yaml.example` (plural): fine, the commands just use that name |
| `.gitignore` line 64 | ❌ **`.k8s/secrets.yaml`**: the leading dot means a folder called `.k8s`, which doesn't exist. `git check-ignore -v k8s/secrets.yaml` → nothing → **NOT ignored**; `git status` lists `?? k8s/secrets.yaml` |
| `secrets.yaml`, `secrets.yaml.example` | ❌ Both **0 bytes** (created 09:26, nothing written or saved yet). So no real value has been exposed |
| Secret in the cluster | Not created yet (`No resources found in portfolio namespace`) |

Fix order: (1) `.gitignore` → `k8s/secrets.yaml` (no leading dot), save, re-check until `check-ignore` prints the rule; (2) only then write the values into `secrets.yaml`.

**Verification 2 (27/10/2026):** `.gitignore` line 64 now `k8s/secrets.yaml` → `git check-ignore -v` prints `.gitignore:64:k8s/secrets.yaml` ✅ ignored. At my request ("give me contents for both the files") Claude gave the full contents of both files in chat, with **placeholders only**. Real values are generated by me with `openssl` and never shown to Claude.

**Part B – result (27/10/2026).** Files written and Secret applied by me. Checked by Claude with every value masked:

| Check | Result |
|---|---|
| `git check-ignore` / `git status` | `secrets.yaml` ignored ✅, not listed; `secrets.yaml.example` listed (to be committed) ✅ |
| `secrets.yaml` values | `SECRET_KEY` 64 hex chars, `DB_PASSWORD` 32, `POSTGRES_PASSWORD` 32, all real (no placeholder left) ✅ |
| Passwords match | `DB_PASSWORD == POSTGRES_PASSWORD`: yes ✅ |
| Cluster | `portfolio-secrets` · Type `Opaque` · `DB_PASSWORD 32 bytes`, `POSTGRES_PASSWORD 32 bytes`, `SECRET_KEY 64 bytes` ✅ |
| `secrets.yaml.example` | Placeholders only ✅ (`changeme`, plus a descriptive placeholder for `POSTGRES_PASSWORD`) |

**Part C – prove it (given 27/10/2026):** _pending_
File `k8s/practice/env-test.yaml`, written by me: a one-shot Pod in `portfolio` that prints the **names** of its environment variables (never the values), using image `busybox:1.38.0` (checked on Docker Hub).

New pieces:
```yaml
spec:
  restartPolicy: Never              # run once and stop (Pods default to Always = restart forever)
  containers:
    - name: env-test
      image: busybox:1.38.0
      command: ["sh", "-c", "env | sort | cut -d= -f1"]   # print variable NAMES only
      envFrom:                      # import EVERY key as an environment variable
        - configMapRef:
            name: portfolio-config
        - secretRef:
            name: portfolio-secrets
```
- `envFrom` = Compose's `env_file`: every key becomes a variable. (`env` + `valueFrom` picks single keys: Step 7.)
- `command` replaces the image's default command (like overriding `CMD` in Docker).
- **Env vars are read once, when the container starts.** Changing the ConfigMap later doesn't reach a running Pod until it's restarted.
```bash
kubectl apply --dry-run=server -f k8s/practice/env-test.yaml
kubectl apply -f k8s/practice/env-test.yaml
kubectl get pod env-test
kubectl logs env-test
kubectl delete -f k8s/practice/env-test.yaml
```
Predictions asked: (1) what STATUS will the Pod show after it finishes? (2) which variables will appear that I did **not** put in the ConfigMap or Secret?

**Errors**

| Error | Cause | Fix |
|-------|-------|-----|
| `POSTGRESS_DB` key in the ConfigMap (silent: dry run and apply both succeed) | Typo in a key name. The API server only checks shape, not meaning | Renamed to `POSTGRES_DB`, re-applied ✅ (old key removed automatically) |
| `.gitignore`: `.k8s/secrets.yaml` didn't ignore `k8s/secrets.yaml` | Leading dot = a different folder name (`.k8s`) | `k8s/secrets.yaml`; confirm with `git check-ignore -v` |

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
| F7 | ⚠️ `main` was pushed at `8422b8a` (15/10/2026): Jenkins runs Test, then waits at the production approval gate (60 min timeout, then aborts). If **approved**: `latest` becomes the non-root image and the production VM's cron pulls it. Old root-owned volumes → possible `permission denied`, `web` crash-loop, 502 (same risk as staging in Docker Step 6). `static_volume` is safe to recreate (collectstatic refills it). **`media_volume` holds uploads: change its owner to UID 1000, don't delete it.** Was the `main` push intended? _asked, pending_ | Step 0 Part C | Now |
| F8 | Pin image tags in my own manifests (`image: nginx` silently means `nginx:latest`). Decide `dev-latest` vs `dev-<commit>` for the portfolio image | Step 1 Ex. 2 | Step 7 / 10 |
| F9 | kube-proxy Pods restarted 8, 8 and 15 times in the new cluster (others ~1). Running now. Find out why | Step 2 state check | Step 10 (`logs --previous`, `describe`) |
| F10 | Step 2 work (`k8s/kind-config.yaml` + this log) not committed; `k8s-setup` not on GitHub yet | Step 2 | Any time: `git add k8s K8S_LOG.md`, commit, `git push -u origin k8s-setup` |
| F11 | Old `kind` cluster still running (uses memory; risk of using the wrong context). Delete with `kind delete cluster --name kind` once I decide | Step 2 | My decision |
| F12 | Kubernetes health checks (probes, Step 7) call Django with the **Pod IP** as host name. With `ALLOWED_HOSTS=localhost,127.0.0.1` Django answers `400 Bad Request` → the probe fails. Choose a probe type or Host header that works | Step 5 | Step 7 |
| F13 | nginx.conf sends `Host $host`, which drops the port. Browser at `localhost:8000` sends `Origin: http://localhost:8000` → Django's CSRF check can reject logins/forms with 403 unless `CSRF_TRUSTED_ORIGINS` contains it (or nginx uses `$http_host`). Verify in Step 8 | Step 5 | Step 8 |
| F14 | `k8s/kind-config.yaml` is not a Kubernetes object (kind reads it). Once more files live in `k8s/`, `kubectl apply -f k8s/` would fail on it. Move it (e.g. `k8s/cluster/`) or always apply files one by one | Step 5 | Step 7 |

---

## Error index (all steps)

| Step | Error message (short) | Root cause | Fix |
|------|----------------------|-----------|-----|
| 0 | `kind get cluster` → `ERROR: Subcommand is required` | Typo: subcommand is plural | `kind get clusters` |
| 2 | `k8s/kind-config.yaml` empty on disk | Not saved in VS Code | Ctrl+S |
| 2 | kind config review 1: settings outside `extraPortMappings`, `hostport`, no space after `listenAddress:` | Missing list level; case-sensitive keys; YAML `key: value` rule | Corrected by Claude at my request, parsed OK |
| 3 | `no matches for kind "pod" in version "V1"` + `ensure CRDs are installed first` | `apiVersion: V1` and `kind: pod`: both case-sensitive | `v1` and `Pod`; check with `kubectl apply --dry-run=server -f` |
| 3 | `no matches for kind "Deployment" in version "v1"` | Deployment lives in the `apps` group | `apiVersion: apps/v1` |
| 5 | `POSTGRESS_DB` (silent, no error message) | Key typo; API server checks shape, not meaning | `POSTGRES_DB`, re-apply |
| 5 | `git check-ignore` prints nothing for `k8s/secrets.yaml` | `.gitignore` had `.k8s/secrets.yaml` (leading dot) | `k8s/secrets.yaml` |
