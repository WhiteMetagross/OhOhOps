# Testing

## Automated matrix

Backend tests cover API routes, graph routing, anomaly detection, AST chunking,
embedding width, security voting, ZIP and path containment, sandbox behavior,
deployment commit, and rollback.

Frontend checks cover ESLint, TypeScript production build, desktop browser flow,
mobile browser flow, theme persistence, navigation, and responsive overflow.

Docker checks cover image builds, service health, ChromaDB connectivity, and
network isolated sandbox execution.

## Complete offline run

```powershell
docker build --target test -t ohohops-backend-test backend
docker run --rm `
  -e DEPLOYMENT_MODE=local `
  -e CHROMA_HOST=chromadb `
  -v "${PWD}:/workspace" `
  -w /workspace/backend `
  ohohops-backend-test `
  python -m pytest --cov=app --cov-report=term-missing

docker compose -f docker-compose.yml -f docker-compose.test.yml up --build -d
docker compose ps
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

## Live provider checks

After configuring real credentials:

```powershell
docker compose up --build -d
docker exec -e PYTHONPATH=/app ohohops-backend-1 python scripts/test_vectorstore.py
docker exec -e PYTHONPATH=/app ohohops-backend-1 python scripts/test_nodes.py
docker exec -e PYTHONPATH=/app ohohops-backend-1 `
  python -m app.eval.ragas_suite --samples 1
```

Live checks spend provider quota and can create Pinecone and Supabase data.
