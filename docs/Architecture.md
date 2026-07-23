# Architecture:

OhOhOps is organized as a safety oriented, event visible SRE control plane. The dashboard is the operator surface. FastAPI is the boundary for authentication, ingestion, telemetry, graph execution, Server Sent Events, tenant keys, deployment acknowledgement, and ledger reads. LangGraph coordinates the repair state. The provider layer abstracts models and vector stores while preserving a fixed 3072 value embedding contract.

![Logical architecture of OhOhOps.](diagrams/Architecture.png)

*Figure 1. ArchitectureUml shows the main application layers, storage boundaries, and external model providers.*

## Architectural objectives:

1. Keep incident evidence, retrieved context, generated patches, security decisions, execution evidence, and deployment outcomes observable.
2. Make unsafe execution difficult by requiring security clearance before a patch can reach the sandbox.
3. Keep provider choices replaceable through typed configuration and adapter interfaces.
4. Allow local demonstrations without paid credentials through deterministic mock models, ChromaDB, and Docker.
5. Preserve a durable operational record when Supabase PostgreSQL is configured.
6. Keep retrieval namespaces separate so one tenant does not receive another tenant's source context.
7. Make failed patches recoverable through atomic file writes, backups, health checks, and rollback.

## Runtime layers:

### Presentation layer:

The Next.js App Router renders the dashboard, onboarding page, and settings page. The global layout provides the OhOhOps brand header, creator attribution, theme persistence, and navigation. The theme system stores the selected light or dark Sunfire theme in browser storage and applies the value before hydration to avoid a visible flash.

The dashboard is divided into health status, repair guarantees, scorecard metrics, source synchronization, graph trace, telemetry pulse, anomaly control, live agent output, Codebase Q&A, and the operational ledger. The browser client uses REST for normal requests and an SSE stream for graph progress.

### API layer:

FastAPI exposes versioned routes under `/api/v1`. The routes validate request schemas, enforce bearer authentication where required, attach the tenant namespace to authenticated requests, and delegate work to application services. Health reports model, arbitration, embeddings, vector store, Docker, and ledger status.

### Orchestration layer:

The LangGraph orchestrator registers six nodes.

1. `evaluation_node` converts incident logs and telemetry into an actionable agent state.
2. `context_node` retrieves relevant source and operational context.
3. `modification_node` produces a complete replacement file rather than an unbounded textual suggestion.
4. `arbitration_node` runs deterministic checks and two model security decisions.
5. `sandbox_node` executes the candidate in the configured isolated environment.
6. `deployment_node` applies the approved file, supervises the target process, and records the result.

The graph has two conditional decisions. Security denial ends the run. A successful sandbox routes to deployment. A failed sandbox routes back to modification while the retry budget remains, and ends the run after the configured limit.

### Data and provider layer:

The vector store protocol provides asynchronous upsert, semantic search, and unique file discovery. Local mode instantiates ChromaDB through its HTTP client. Cloud mode instantiates Pinecone and creates the `ohohops-3072` serverless index if it is absent. Both modes use the same fixed dimension embedding adapter.

The embedding adapter pads short vectors with zeros and folds longer vectors deterministically into the target dimension. Providers include Gemini, OpenAI, FastEmbed, and deterministic mock embeddings. This removes a hidden dimension mismatch between providers and index configuration.

The ledger uses asyncpg with statement caching disabled for pooler compatibility. It creates `operational_logs`, `api_keys`, and `pending_deployments` idempotently. Row level security is enabled explicitly, and `anon` and `authenticated` table privileges are revoked when those Supabase roles exist.

### Execution layer:

The sandbox service supports subprocess mode for rapid local development and Docker mode for production isolation. Docker mode uses `network=none`, a memory limit, a CPU limit, and a timeout. Project paths and patch targets are resolved and checked against the project root before a transaction begins.

## Modes:

### Local mode:

Local mode requires `CHROMA_HOST`. It is intended for the Docker Compose stack and offline demonstrations. The default test overlay starts ChromaDB, PostgreSQL, FastAPI, and Next.js together. Mock inference and deterministic embeddings allow the graph to execute without external model quota.

### Cloud mode:

Cloud mode requires `PINECONE_API_KEY`. The API can also use a Supabase database URL, real model providers, a GitHub token for private source ingestion, and the tenant daemon. The cloud path keeps the same graph semantics while replacing local vector storage and process supervision integrations.

## Security boundaries:

1. Optional credentials load only from environment variables or an ignored `.env` file.
2. Tenant API keys are returned once, while only hashes are persisted.
3. Protected routes require a development admin key or a verified namespace scoped tenant key.
4. Source archives and paths are checked for traversal and unsafe extraction.
5. The arbitration gate must clear before sandbox execution.
6. The sandbox has no network access in Docker mode.
7. Patch writes use a temporary file and atomic replacement.
8. Deployment failure restores the backup before retry or termination.
9. Supabase public roles cannot read the operational tables.

## Failure semantics:

Optional provider failure is reported by health and logs while the service remains available where safe. Required deployment mode configuration fails at startup. Ledger failure is non critical to the repair path and is logged without crashing the run. Patch failure is critical to deployment and is routed through rollback or retry logic. Every terminal result is intended to be visible in the SSE stream and the ledger.

## Extension points:

New model providers can implement the existing chat or embedding selection path. New vector stores can implement the `VectorStore` protocol. New restart strategies can be registered under `services/restart_strategies`. New dashboard panels can consume typed API clients without changing graph state. This separation makes provider experiments possible without rewriting the orchestration contract.
