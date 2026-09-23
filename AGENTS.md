# AI First — shared development instructions

This file is the single source of truth for both Codex and Claude Code. `CLAUDE.md`
must remain a symbolic link to this file so the instructions cannot drift.

## Goal and constraints

- Build a judge-ready agentic AI prototype for hackalem.ai in a five-hour window.
- Optimize for a reliable end-to-end demo and clear user value before extra features.
- Track: Kazakhtelecom special track.
- Case: compare organizational regulations and structures before/after a reorganization,
  detect lost, duplicated, added, moved, or materially changed functions, and produce
  an evidence-backed conclusion with references to document clauses.
- Never claim a feature in README or the demo unless it works in the current branch.
- Commit and push a working checkpoint every 30–40 minutes. Before each checkpoint,
  run the fastest relevant verification and keep commits focused.

## Required stack

- Backend: Python 3.12, FastAPI, Pydantic.
- Frontend: Vue 3, Quasar, TypeScript.
- Data: PostgreSQL with pgvector when semantic retrieval is required.
- Delivery: Docker Compose; frontend uses a multi-stage Node build and nginx runtime.
- Configuration: `.back_env`, `.front_env`, and `.env` are local-only. Commit matching
  `.example` files with safe defaults and no secrets.

## Architecture principles

- Keep one explicit orchestrator and a small number of tools; introduce multiple agents
  only where independent roles produce observable value.
- Store run state and important decisions so a run can be inspected and reproduced.
- Make LLM outputs structured and validate them with Pydantic before business logic.
- Ground factual answers in retrieved context and return source references.
- Put deterministic checks before an LLM evaluator; use model-based evaluation only
  for criteria that cannot be checked reliably in code.
- Add timeouts, bounded retries, and a useful error state for every external API.
- Keep provider access behind a small adapter so OpenAI and NVIDIA models can be
  switched by configuration.

## Definition of done

- `docker compose up --build` starts the complete project from a clean clone.
- Health checks pass and the main user journey works without manual database changes.
- The UI exposes progress, final output, sources, and recoverable errors.
- At least one happy-path integration test covers the core scenario.
- README describes the actual problem, implemented features, architecture, setup,
  demo flow, limitations, and required environment variables.
- No secrets, local env files, generated caches, or build artifacts are tracked.

## Collaboration

- Inspect existing changes before editing; do not overwrite another agent's work.
- Prefer small modules with clear ownership boundaries to reduce merge conflicts.
- When changing an API contract, update backend schema, frontend types, examples, and
  tests in the same change.
- Record meaningful architecture decisions briefly in README or `docs/decisions/`.
