# AI First — development instructions

Shared instructions for contributors, Codex and Claude Code. `CLAUDE.md` must remain
a symbolic link to this file. Product capabilities, setup and limitations belong
in README.md; verification evidence belongs in docs/VALIDATION.md.

## Project and current implementation

- Hackalem.ai, Kazakhtelecom case: compare organizational regulations before/after
  reorganization; expose changes, possible losses, duplication and conflicts of
  interest with source references and a reviewable conclusion.
- Backend: Python 3.12, FastAPI, Pydantic. Frontend: Vue 3, Quasar, TypeScript.
- Delivery: Docker Compose; frontend builds with Node 22 and runs on nginx.
- PostgreSQL stores analyses and checkpoints in JSONB. The image includes pgvector,
  but retrieval, embeddings and RAG are not implemented.
- OpenAI is the implemented provider. NVIDIA/provider switching is not implemented.
- One explicit Python orchestrator coordinates extraction, matching, analysis,
  evidence validation, model criticism and bounded revision/rollback.

## Correctness and scope

- Prioritize the working end-to-end flow; avoid last-minute architectural expansion.
- Never claim capabilities or successful checks that are absent from the current code.
- Validate structured model output with Pydantic and verify evidence in code.
- Preserve unresolved sources and mappings. Missing output is not proof of a lost
  function; an exact quotation is not proof of correct semantic interpretation.
- The critic must review published conclusions and guarded mapping statuses.
- Do not hide warnings, replace real API failures with demo data, or describe coverage
  and model scores as measured accuracy. Mock mode must remain explicitly marked.
- Keep timeouts, bounded retries and recoverable errors for external calls.
- Live model tests cost money: run only within the user's approved scope.

## Collaboration and repository hygiene

- Inspect git status before editing; preserve other contributors' changes.
- Keep commits focused; stage explicit files rather than unrelated ongoing work.
- During active hackathon work, commit and push verified checkpoints every 30–40 minutes.
- Keep `.back_env`, `.front_env`, `.env`, uploaded documents and customer results out
  of Git. Maintain safe `.example` files; do not print secrets in logs or tool output.
- Do not track caches, node_modules, builds or local design exports.
- Do not remove Docker data volumes or rewrite saved results to improve a demo.
- Keep backend schema, frontend types, contract examples and tests aligned when
  changing an API. Record meaningful architecture decisions in docs/decisions/.

## Verification and handoff

- Backend, from backend/: install `.[dev]`, then `python -m pytest -q` and
  `ruff check app tests`. `TEST_DATABASE_URL` enables isolated PostgreSQL tests.
- Frontend, from frontend/: `npm ci`, `npm test`, `npm run build`.
- `docker compose up --build -d --wait` must start frontend, backend and database.
  Check health and the real API path through frontend nginx, not only mock data.
- Preserve stored analyses across ordinary container recreation. Clearly distinguish
  automated tests, saved-result UI checks and live model runs in the handoff.
- README must describe the actual problem, implemented features, architecture,
  environment setup, demo flow and material limitations, without unsupported claims.
