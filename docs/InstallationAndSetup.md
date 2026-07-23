# Installation And Setup:

This document describes local development, offline demonstration, live provider configuration, and production deployment preparation.

## Requirements:

1. Windows, Linux, or macOS with Docker Desktop or an equivalent Docker Engine.
2. Git 2.40 or later.
3. At least 8 GB of memory for the complete backend image and browser checks.
4. PowerShell, Bash, or a compatible shell.
5. Node.js 20 only when running frontend checks outside Docker.
6. Python 3.12 only when running backend tools outside Docker.
7. A Docker daemon with permission to create network isolated sandbox containers.

## Clone:

```powershell
git clone https://github.com/WhiteMetagross/OhOhOps.git
Set-Location OhOhOps
```

## Local configuration:

Copy the example environment file and keep it ignored by Git.

```powershell
Copy-Item .env.example .env
```

For a local offline demonstration, use the following values in `.env`.

```env
DEPLOYMENT_MODE=local
CHROMA_HOST=chromadb
USE_MOCK_LLM=true
USE_LOCAL_EMBEDDINGS=false
SANDBOX_MODE=docker
OHOHOPS_API_KEY=ohohops-dev-key
OHOHOPS_WEBHOOK_SECRET=ohohops-dev-secret
```

Mock mode uses deterministic responses and does not transmit source code to a model provider. Docker mode still executes generated demonstration patches inside the configured sandbox.

## Start with Compose:

```powershell
docker compose up --build -d
docker compose ps
```

Open the dashboard at `http://localhost:3000`. The API health endpoint is `http://localhost:8000/api/v1/health`.

## Live Gemini configuration:

Set `GEMINI_API_KEY` for Gemini embeddings and chat, or use the separate `GEMINI_API_KEY_CHAT` and `GEMINI_API_KEY_SECURITY` variables when the two model roles need independent credentials. Keep `USE_MOCK_LLM=false` for live generation.

## Live Pinecone configuration:

Set `DEPLOYMENT_MODE=cloud` and `PINECONE_API_KEY`. The service creates the `ohohops-3072` serverless index when it does not exist. The configured cloud, region, cosine metric, and fixed dimension must match the account and index policy.

## Live Supabase configuration:

Set `SUPABASE_DB_URL` to the PostgreSQL session pooler URI from the Supabase Connect panel. The backend creates three tables idempotently and applies row level security. Use a database role that can create tables during the first boot. Never use the browser publishable key as the PostgreSQL password or backend database credential.

The backend uses port 5432 session pooler mode and disables asyncpg statement caching for pooler compatibility. A database password containing reserved URI characters must be percent encoded before use.

## RAGAS configuration:

RAGAS evaluation uses the configured model and retrieval context. Configure a live model, index representative source context, and run the one sample evaluation before scaling to a larger dataset. Fidelity scores are written to the ledger when the database is configured.

## Provider combinations:

1. Local mode with mock inference uses ChromaDB and deterministic embeddings.
2. Local mode with Gemini uses ChromaDB and Gemini embeddings.
3. Cloud mode with Gemini uses Pinecone and Gemini embeddings.
4. Cloud mode with OpenAI uses Pinecone and OpenAI embeddings.
5. Local FastEmbed mode uses ChromaDB and the 3072 dimension adapter.

## Frontend outside Docker:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` when the API is not at `http://127.0.0.1:8000`. The browser uses the configured API key fallback in local development and a namespace scoped key after onboarding.

## Backend outside Docker:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Outside Docker, use subprocess sandbox mode unless the local Docker socket is intentionally exposed to the process.

## Shutdown and cleanup:

Stop the stack with `docker compose down`. Add `-v` when removing local ChromaDB and sandbox volumes after a test run. Do not use broad recursive deletion commands against the workspace or host Docker data.

## Production checklist:

1. Rotate every credential that was used during testing.
2. Use a dedicated database role with the minimum schema privileges needed for migrations and writes.
3. Confirm Supabase row level security and public role denial.
4. Protect the Docker socket and isolate the host.
5. Set `SANDBOX_MODE=docker`, `SANDBOX_NETWORK_MODE=none`, memory, CPU, and timeout limits.
6. Keep `ENABLE_TELEMETRY_LOOP=false` until autonomous invocation has been reviewed.
7. Configure a real health command for the target service.
8. Verify rollback on a disposable project before enabling automatic deployment.
9. Keep `.env`, provider keys, database URIs, and generated raw tenant keys outside Git.
10. Monitor the operational ledger and provider usage.
