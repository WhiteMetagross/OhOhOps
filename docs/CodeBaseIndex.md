# Codebase Index:

This index maps the production files in OhOhOps to their responsibilities. It is intended to help a new maintainer locate behavior before making a change.

## Root files:

1. `ReadMe.md` is the detailed public project overview, visual gallery, quick start, and capability summary.
2. `docker-compose.yml` defines the local backend, frontend, ChromaDB, volumes, health checks, and provider environment wiring.
3. `docker-compose.test.yml` adds mock inference, deterministic embeddings, test PostgreSQL, and test credentials for integration checks.
4. `.env.example` documents configurable environment variables without real secrets.
5. `SECURITY.md` describes security expectations for Docker, provider keys, and generated patches.
6. `render.yaml` describes the backend cloud service configuration.
7. `vercel.json` describes frontend deployment metadata.
8. `runtime.txt` records the runtime selection used by deployment tooling.

## Backend application:

### Application and configuration:

1. `backend/app/main.py` creates the FastAPI application and attaches the API router.
2. `backend/app/core/config.py` defines typed settings, provider selection, deployment mode validation, and safety limits.
3. `backend/app/core/lifespan.py` initializes Pinecone, the ledger, patch store, Docker client, and optional telemetry task.
4. `backend/app/core/schemas.py` defines request, response, graph state, telemetry, ledger, and tenant key schemas.
5. `backend/app/core/logging.py` configures structured application logging.
6. `backend/app/core/limiter.py` defines request rate limiting.

### API routes:

1. `backend/app/api/v1/health.py` reports application and dependency status.
2. `backend/app/api/v1/system.py` reports deployment mode.
3. `backend/app/api/v1/ingest.py` handles GitHub, ZIP, local path, and file listing operations.
4. `backend/app/api/v1/context.py` streams retrieval grounded answers.
5. `backend/app/api/v1/graph.py` starts and streams repair graph execution.
6. `backend/app/api/v1/anomaly.py` exposes anomaly simulation and control.
7. `backend/app/api/v1/telemetry.py` receives daemon telemetry and queues optional repairs.
8. `backend/app/api/v1/deployments.py` acknowledges and lists pending deployment records.
9. `backend/app/api/v1/keys.py` creates, verifies, lists, and revokes namespace keys.
10. `backend/app/api/v1/ledger.py` returns recent operational events.

### Graph:

1. `backend/app/graph/orchestrator.py` compiles the six node LangGraph workflow.
2. `backend/app/graph/routing.py` implements security, retry, and deployment routing.
3. `backend/app/graph/nodes/evaluation_node.py` normalizes incident evidence.
4. `backend/app/graph/nodes/context_node.py` retrieves context.
5. `backend/app/graph/nodes/modification_node.py` generates complete replacement files.
6. `backend/app/graph/nodes/arbitration_node.py` executes deterministic and dual model security checks.
7. `backend/app/graph/nodes/sandbox_node.py` executes the candidate patch.
8. `backend/app/graph/nodes/deployment_node.py` applies and supervises the patch.

### Services:

1. `backend/app/services/embeddings.py` provides deterministic, Gemini, OpenAI, and FastEmbed adapters with dimension normalization.
2. `backend/app/services/vectorstore.py` provides the Pinecone implementation and vector protocol.
3. `backend/app/services/vectorstore_chroma.py` provides the local ChromaDB implementation.
4. `backend/app/services/ast_chunker.py` parses supported languages into retrieval chunks.
5. `backend/app/services/ingestion.py` validates, extracts, parses, embeds, and indexes source files.
6. `backend/app/services/ledger.py` manages Supabase PostgreSQL schema, RLS, audit writes, and reads.
7. `backend/app/services/api_keys.py` manages tenant key hashes and namespace lookup.
8. `backend/app/services/patch_store.py` stores pending daemon deployment records.
9. `backend/app/services/deployment_patch.py` provides transactional patch, backup, rollback, and finalization operations.
10. `backend/app/services/sandbox.py` runs subprocess or Docker sandbox jobs.
11. `backend/app/services/process_manager.py` supervises target processes and health checks.
12. `backend/app/services/restart_strategies` contains process, subprocess, Docker, and daemon restart strategies.
13. `backend/app/services/llm.py` selects chat and security model providers.

### Security:

1. `backend/app/security/auth.py` validates administrator and tenant bearer keys.
2. `backend/app/security/blocklist.py` rejects unsafe command patterns.

### Evaluation:

1. `backend/app/eval/dataset_builder.py` builds evaluation samples.
2. `backend/app/eval/ragas_suite.py` runs RAGAS faithfulness and context recall evaluation.
3. `backend/app/eval/fixtures/seed_questions.json` contains seed questions for evaluation.

### Backend tools and tests:

1. `backend/scripts/test_nodes.py` checks evaluation, retrieval, model generation, and sandbox behavior.
2. `backend/scripts/test_vectorstore.py` checks live Pinecone or local vector behavior.
3. `backend/scripts/test_all_sandboxes.py` checks six language runtimes and network isolation.
4. `backend/scripts/test_full_stack.py` checks the complete API and graph path.
5. `backend/tests/conftest.py` provides isolated fixtures and mocks.
6. `backend/tests/test_ast_embeddings_and_rollback.py` covers AST, dimension, patch, and rollback behavior.
7. `backend/tests/test_security.py` covers arbitration and command safety.
8. `backend/tests/test_ingestion_security.py` covers archive and path validation.
9. `backend/tests/test_token_and_telemetry.py` covers telemetry and token accounting.

## Frontend application:

### Pages:

1. `frontend/src/app/layout.tsx` defines metadata, theme bootstrapping, global navigation, and creator footer.
2. `frontend/src/app/page.tsx` redirects the root route to onboarding.
3. `frontend/src/app/onboarding/page.tsx` provides deployment selection, tenant key generation, verification, and local setup guidance.
4. `frontend/src/app/dashboard/page.tsx` composes the operations workspace and graph stream.
5. `frontend/src/app/settings/page.tsx` provides key administration and daemon guidance.
6. `frontend/src/app/globals.css` defines Sunfire colors, liquid glass surfaces, typography, responsive rules, and light and dark variables.

### Components:

1. `BrandHeader.tsx` renders the brand, page context, navigation, and theme toggle.
2. `ThemeToggle.tsx` persists light and dark theme state.
3. `HealthStrip.tsx` renders dependency status.
4. `NodeStatusPanel.tsx` renders the six repair stages.
5. `RunForm.tsx` captures repair input.
6. `IncidentPanel.tsx` renders live agent output and patch evidence.
7. `SreScorecard.tsx` renders tokens, latency, retries, and outcome.
8. `TelemetryChart.tsx` renders metric trends.
9. `ContextPanel.tsx` renders Codebase Q&A.
10. `LedgerHistory.tsx` renders operational history.
11. `IngestPanel.tsx` handles source synchronization.
12. `StatusBanner.tsx` renders operation status messages.
13. `TerminalLog.tsx` renders sandbox and deployment text.

### Frontend libraries:

1. `frontend/src/lib/authKey.ts` stores and resolves browser bearer keys.
2. `frontend/src/lib/config.ts` defines API base URL and development key fallback.
3. `frontend/src/lib/sseClient.ts` parses Server Sent Events.
4. `frontend/src/lib/contextClient.ts` handles context requests.
5. `frontend/src/lib/keysClient.ts` handles tenant key operations.
6. `frontend/src/lib/systemClient.ts` handles health and mode requests.
7. `frontend/src/hooks/useGraphStream.ts` connects graph events to React state.

## Verification assets:

1. `frontend/e2e/dashboard.spec.ts` defines desktop and mobile browser checks.
2. `docs/diagrams` contains compiled PlantUML PNG diagrams without source files.
3. `visuals` contains ThisCase screenshots of pages, states, themes, and responsive layouts.
