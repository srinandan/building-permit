---
name: submit
description: Lint, test, and open a pull request for uncommitted changes in this repo.
---

# Submit Skill

Run this skill when you are ready to ship your changes. It walks through a fixed sequence: review what changed, lint each affected service, check for unused packages, run unit tests, then create a branch, push, and open a pull request.

---

## Step 1 — Review Uncommitted Changes

```bash
git diff --stat   # which files changed
git diff          # full diff for review
git status        # untracked files
```

Summarize what changed and which services are affected (`agent/`, `contractor-agent/`, `assessor-mcp-server/`, `agent-engine/`, `api/`, `frontend/`) before proceeding. Only run steps 2–4 for the services with changes.

---

## Step 2 — Lint Affected Services

**Python services** (`agent/`, `contractor-agent/`, `assessor-mcp-server/`, `agent-engine/`):
```bash
cd <service> && uv run ruff check .
```

**Go service** (`api/`):
```bash
cd api && go vet ./...
```

**Frontend** (`frontend/`):
```bash
cd frontend && npm run lint        # ESLint
cd frontend && npx tsc --noEmit   # type-check without emitting
```

Fix all errors before continuing. Warnings are acceptable but should be noted in the PR description.

---

## Step 3 — Check for Unused Packages

**Python services** — check that declared dependencies are actually imported:
```bash
cd <service> && uv run deptry .
```

If `deptry` is not installed, add it temporarily:
```bash
cd <service> && uv add --dev deptry && uv run deptry . && uv remove --dev deptry
```

**Go** — tidy and check for drift:
```bash
cd api && go mod tidy && git diff go.mod go.sum
```
Commit any changes to `go.mod`/`go.sum` before the main commit.

**Frontend** — check for unused npm packages:
```bash
cd frontend && npx depcheck
```

---

## Step 4 — Run Unit Tests

**Python services**:
```bash
cd agent && uv run pytest
cd contractor-agent && uv run pytest
cd assessor-mcp-server && uv run pytest
```

**Go**:
```bash
cd api && go test ./...
```

**Frontend**:
```bash
cd frontend && npm test -- --run   # Vitest, non-interactive
```

All tests must pass. If a test fails for a reason unrelated to your change, note it explicitly in the PR description rather than skipping it silently.

---

## Step 5 — Create Branch & Commit

Use a branch name that follows the pattern `<type>/<short-description>`:

```bash
git checkout -b feat/add-parcel-caching     # new feature
git checkout -b fix/cors-header             # bug fix
git checkout -b chore/update-deps           # maintenance
git checkout -b docs/update-spec            # documentation
```

Stage only the files you intentionally changed, then commit:

```bash
git add <file1> <file2> ...
git commit -m "<type>: <concise summary of what changed and why>"
```

---

## Step 6 — Push & Open Pull Request

```bash
git push -u origin <branch-name>
```

Open a pull request with:

- **Title:** `<type>: <short description>` (under 70 characters)
- **Body** covering:
  - **What changed** — one-paragraph summary
  - **Why** — motivation or issue being addressed
  - **Services affected** — list which directories have changes
  - **How to test locally** — exact commands a reviewer can run
  - **Deployment notes** — e.g., re-run `make setup` if RAG corpus changed, or update `agent/.env` if new env vars were added

### PR checklist

- [ ] Lint passes for all affected services
- [ ] No unused packages introduced
- [ ] All unit tests pass
- [ ] `plan/spec.md` and `plan/DESIGN.md` are not contradicted
- [ ] MCP tool signatures unchanged (or all callers updated)
- [ ] A2A agent card updated if endpoint paths changed
- [ ] Model Armor filter lists not weakened
