# OhOhOps

![OhOhOps phoenix logo](frontend/public/ohohops-logo.png)

OhOhOps is an autonomous SRE control plane for detecting incidents, retrieving
code context, generating repairs, validating patches, and recovering services.

Created and maintained by Mridankan Mandal through
[WhiteMetagross](https://github.com/WhiteMetagross) and
[RedZapdos123](https://github.com/RedZapdos123).

## Capabilities

1. Six node cyclic LangGraph repair workflow
2. PyOD Isolation Forest anomaly detection
3. Tree Sitter AST chunking for six sandbox languages
4. Pinecone cloud storage and ChromaDB local storage
5. Fixed 3072 value embedding contract
6. Unanimous dual model security arbitration
7. Network isolated Docker sandbox execution
8. Transactional deployment with automatic rollback
9. SSE streaming FastAPI API and Next.js dashboard
10. Optional Supabase ledger and RAGAS evaluation
11. Persistent light and dark sunfire themes

## Local start

Requirements:

1. Docker Desktop
2. Git

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Open `http://localhost:3000`.

Default example configuration uses deterministic mock models with real ChromaDB
and Docker. It needs no paid provider. Set `USE_MOCK_LLM=false` and configure
real providers before production use.

## Verification

```powershell
docker build --target test -t ohohops-backend-test backend
docker run --rm `
  -e DEPLOYMENT_MODE=local `
  -e CHROMA_HOST=chromadb `
  -v "${PWD}:/workspace" `
  -w /workspace/backend `
  ohohops-backend-test `
  python -m pytest --cov=app --cov-report=term-missing

Set-Location frontend
npm ci
npm run lint
npm run build
npm run test:e2e
```

Full setup and test matrices:

1. [Configuration](docs/CONFIGURATION.md)
2. [Testing](docs/TESTING.md)
3. [Architecture](docs/ARCHITECTURE.md)
4. [Security policy](SECURITY.md)

## Production warning

OhOhOps controls Docker and may apply generated patches. Protect the Docker
socket, scope all provider keys, keep automatic deployment disabled until health
checks match the target service, and never commit `.env`.

## License

MIT. Copyright 2026 Mridankan Mandal.
