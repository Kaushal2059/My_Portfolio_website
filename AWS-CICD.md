# AWS CI/CD — Phase 9 Running Log

This is the build log for **Phase 9** of the AWS deployment plan (see [`cloud_architecture.md`](cloud_architecture.md) for the target-state design and [`cloud_implementation_steps.md`](cloud_implementation_steps.md) for Phases 0-8, which are done). Phase 9 wires up GitHub Actions so pushes to `main` automatically build, push to ECR, and deploy to the live EC2 instance.

Logged here, in order: every step taken, every decision and its reasoning, every error hit and how it was fixed, and every question asked/answered along the way. Treat this the same way as `cloud_implementation_steps.md` — append, don't rewrite history.

## How we're working together (same ground rules as Phases 0-8)

- One step at a time. Claude explains the why, gives exact commands/config, user executes AWS Console/CLI steps themselves and reports back.
- Claude asks before making any judgment call, rather than assuming.
- Paste full error text, not paraphrases, when something breaks.
- Billable-resource teardown reminders still apply at session end (EC2, RDS, ALB).

## Locked-in decisions for Phase 9

Asked up front via AskUserQuestion before writing any config:

| Decision | Choice | Why |
|---|---|---|
| AWS resource state (this session) | **Still live** from last session | No need to recreate EC2/RDS/ALB before testing the pipeline. |
| GitHub → AWS auth | **OIDC federation** (not IAM user access keys) | No long-lived AWS credentials stored in GitHub at all — GitHub issues a short-lived token per workflow run, an IAM role trusts it. Real current industry-standard practice; nothing to leak or rotate. |
| Deploy mechanism | **SSM Run Command** (not SSH) | AWS Systems Manager runs the deploy commands over AWS's own control plane — no SSH port, no `.pem` key involved in CI. |
| Branch scope | **Only `main` → AWS.** `dev` stays on its existing Docker Hub → staging-VM flow, untouched. | There's only one EC2 instance in this design (no separate staging box), so redirecting `dev` too would need a second environment — out of scope for now. |
| Feature branch name | `aws-deployment` | Git branch names can't contain spaces; kebab-case matches the existing `main`/`dev` convention. |

Repo: `Kaushal2059/My_Portfolio_website` (from `git remote -v`) — this is what the OIDC trust policy gets scoped to.

## Log

*(Entries appended below as each step happens — newest at the bottom.)*
