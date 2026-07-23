# Testing:

OhOhOps uses layered verification. Unit tests isolate backend decisions. Container tests validate service wiring. Browser tests validate the user experience on desktop and mobile. Live provider checks validate the external model, Pinecone, Supabase, RAGAS, ChromaDB, and Docker boundaries.

![Repair activity flow.](diagrams/Activity.png)

*Figure 1. ActivityUml describes the decisions exercised by the repair and rollback tests.*

## Automated test matrix:

1. Backend unit tests cover 47 cases across anomaly detection, API behavior, graph routing, AST chunking, embeddings, security, ingestion, rollback, telemetry, and evaluation.
2. Frontend lint checks ESLint rules and Next.js conventions.
3. Frontend production build checks TypeScript, static generation, and standalone output.
4. Browser tests cover desktop dashboard rendering, mobile rendering, page navigation, footer attribution, backend health, theme persistence, and responsive overflow.
5. Sandbox tests execute Python, JavaScript, TypeScript, C, C++, and Go in network isolated containers.
6. Full stack smoke tests exercise health, mode, anomaly simulation, key verification, upload ingestion, file listing, SSE context, SSE graph, key creation, telemetry, deployment listing, and ledger reads.
7. Provider checks exercise live Gemini generation, dual model arbitration, Pinecone index and semantic retrieval, Chroma retrieval, and RAGAS metrics.
8. Database checks exercise Supabase schema creation, connection ping, insert, read, cleanup, row level security, and public access denial.

## Local unit tests:

Run the backend test image with the repository mounted into the test container.

```powershell
docker build --target test -t ohohops-backend-test backend
docker run --rm `
  -e DEPLOYMENT_MODE=local `
  -e CHROMA_HOST=chromadb `
  -v "${PWD}:/workspace" `
  -w /workspace/backend `
  ohohops-backend-test `
  python -m pytest --cov=app --cov-report=term-missing
```

The expected result is 47 passing tests. Coverage is informative rather than a release gate, because several provider and process branches require external services.

## Local Compose tests:

The test overlay supplies mock inference, deterministic embeddings, a test PostgreSQL service, ChromaDB, and test authentication values.

```powershell
docker compose -f docker-compose.yml -f docker-compose.test.yml up --build -d
docker compose -f docker-compose.yml -f docker-compose.test.yml ps
curl.exe --fail http://127.0.0.1:8000/api/v1/health
docker exec -e PYTHONPATH=/app ohohops-backend-1 python scripts/test_all_sandboxes.py
docker exec `
  -e PYTHONPATH=/app `
  -e OHOHOPS_API_KEY=ohohops-test-key `
  ohohops-backend-1 `
  python scripts/test_full_stack.py
Set-Location frontend
npm ci
npm run lint
npm run build
npm run test:e2e
```

The test overlay verifies that the explicit ledger row level security SQL also works on a plain PostgreSQL instance without Supabase specific roles.

## Browser coverage:

The Playwright suite runs six cases across desktop and mobile projects. The first case checks the dashboard heading, repair guarantees, and horizontal overflow. The second checks that light and dark theme state persists through reload. The third checks onboarding, settings, dashboard footer attribution, health, and the 3072 embedding dimension.

The configuration uses two workers to avoid local Windows socket exhaustion while preserving parallel desktop and mobile coverage. CI retries are enabled twice, while local runs fail immediately so a developer can see the first failure.

## Live provider checks:

Live checks must be run with credentials supplied through an ignored environment file or process environment. Do not commit credentials or print them in logs.

```powershell
docker compose up --build -d
docker exec -e PYTHONPATH=/app ohohops-backend-1 python scripts/test_vectorstore.py
docker exec -e PYTHONPATH=/app ohohops-backend-1 python scripts/test_nodes.py
docker exec -e PYTHONPATH=/app ohohops-backend-1 `
  python -m app.eval.ragas_suite --samples 1
```

Live provider checks can spend quota and can create indexes, collections, ledger tables, audit events, and test tenant keys. Use unique namespaces and remove test credentials after validation.

## Verified live results:

The current validated environment produced the following results.

1. Gemini model discovery and live patch generation passed.
2. Dual model arbitration with two model responses passed.
3. Pinecone index creation, 3072 dimension validation, upsert, and search passed.
4. Chroma AST indexed retrieval passed.
5. RAGAS faithfulness returned 1.0 and context recall returned 0.5 for the seeded sample.
6. Supabase schema, ping, insert, read, cleanup, and public access denial passed.
7. The full live ledger workflow passed through the dashboard.

## CI acceptance:

The GitHub Actions workflow has backend, frontend, and integration jobs. The integration job builds the complete Compose stack, waits for health, runs all six sandboxes, runs the full API smoke test, and runs the browser suite. A green CI run is required after source or documentation changes that affect code or test configuration.

## Negative and security tests:

1. Missing cloud Pinecone configuration fails settings validation.
2. Missing local Chroma host fails settings validation.
3. Invalid bearer keys are rejected.
4. Unsafe archive paths are rejected.
5. Patch targets outside the project root are rejected.
6. Security denial prevents sandbox execution.
7. Nonzero sandbox exit routes to retry or terminal failure.
8. Deployment health failure restores the original file.
9. Public Supabase roles cannot read ledger tables.

## Test data cleanup:

Local Compose data is removed with `docker compose down -v`. Live data must be removed by unique namespace and test event marker. Do not delete broad production records to clean a demonstration.
