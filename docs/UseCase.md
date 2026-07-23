# Use Cases:

This document defines the primary operational uses of OhOhOps. The actors are an SRE operator, a monitored service or daemon, configured model providers, the vector store, the sandbox runtime, and the operational ledger.

![Repair request sequence.](diagrams/Sequence.png)

*Figure 1. SequenceUml shows the request path from dashboard input to ledger recording.*

## Actors:

1. The SRE operator submits incidents, reviews context, observes graph progress, and approves the deployment posture.
2. The telemetry daemon sends metric observations, logs, source identifiers, and reproduction commands.
3. The FastAPI service authenticates requests, validates input, and coordinates the repair run.
4. The model providers generate patches and independent security decisions.
5. The vector store returns relevant source and operational context.
6. The Docker sandbox executes a candidate without network access.
7. The ledger stores audit events, tenant key hashes, and pending deployment records.

## UC-01: Configure local access:

### Goal:

Start a local demonstration without paid provider credentials.

### Preconditions:

1. Docker Desktop is running.
2. Git is installed.
3. The repository has been cloned.

### Main flow:

1. The operator copies `.env.example` to `.env`.
2. The operator selects local deployment mode and mock inference.
3. Docker Compose builds ChromaDB, the backend, and the frontend.
4. The operator opens the dashboard.
5. The health strip reports the local service state.

### Postconditions:

The operator can use the dashboard, local vector store, deterministic model path, and Docker sandbox without external provider quota.

## UC-02: Create and verify tenant access:

### Goal:

Create a namespace scoped key for the dashboard and telemetry daemon.

### Main flow:

1. The operator opens Setup.
2. The operator selects Managed service or Local Docker.
3. The operator enters a tenant namespace.
4. The dashboard sends a protected key generation request.
5. The backend creates a hash and returns the raw key once.
6. The operator verifies the key through the dashboard.
7. The dashboard stores the verified key for future requests.
8. The operator opens the operations workspace.

### Alternative flow:

If the key is invalid, expired, or generated with the wrong administrator credential, the dashboard displays a clear error and does not open the operations workspace.

### Postconditions:

The namespace is attached to protected requests, and the raw key is not persisted by the backend.

## UC-03: Ingest source context:

### Goal:

Make a repository or archive available to retrieval and repair operations.

### Main flow:

1. The operator selects GitHub URL, ZIP Upload, or Local Path.
2. The operator supplies the namespace and source input.
3. The backend validates archive entries and path containment.
4. The AST chunker parses supported languages and records file metadata.
5. The embedding adapter creates exactly 3072 values for every chunk.
6. The vector store upserts chunks under the namespace.
7. The ledger records the ingestion result.
8. The dashboard updates the available target file selector.

### Postconditions:

Relevant source context is searchable without mixing namespaces.

## UC-04: Investigate through Codebase Q&A:

### Goal:

Ask a focused question about source, retry behavior, security gates, or deployment logic.

### Main flow:

1. The operator enters a question and optional namespace.
2. The backend performs semantic retrieval.
3. The context node streams the model answer through SSE.
4. The backend records a RAG inference event.
5. The dashboard renders the response in the Codebase Q&A panel.

### Postconditions:

The operator receives a context grounded answer, and the request is represented in the audit trail when the ledger is configured.

## UC-05: Run a manual repair:

### Goal:

Diagnose and repair a known incident with explicit operator input.

### Main flow:

1. The operator supplies a target file, reproduction command, and crash logs.
2. The dashboard starts a graph run through the protected API.
3. The evaluation node creates the initial state.
4. The context node retrieves source and operational context.
5. The modification node proposes a complete replacement file.
6. The arbitration node performs static safety checks and requests two model decisions.
7. If both decisions clear the patch, the sandbox executes it with no network.
8. A successful sandbox routes to deployment.
9. The deployment node writes the patch transactionally and checks process health.
10. The dashboard receives node events and final status through SSE.
11. The ledger records the final action.

### Alternative flows:

1. Security denial ends the run with a blocked status.
2. A nonzero sandbox exit routes back to modification while retries remain.
3. A failed deployment restores the backup and either retries or ends with rollback.
4. A missing project directory ends the run with an actionable error.

## UC-06: Run proactive anomaly handling:

### Goal:

Detect abnormal telemetry and optionally start the repair graph.

### Main flow:

1. The daemon or operator sends CPU, memory, error rate, and log data.
2. The telemetry endpoint writes an event to the ledger.
3. PyOD evaluates the configured window and contamination threshold.
4. If the observation is anomalous and logs are available, the graph is queued.
5. The operator follows the same graph and safety states as a manual repair.

### Safety condition:

The background telemetry loop is disabled by default because enabling it can invoke real model and Docker work without an interactive operator action.

## UC-07: Review the operational ledger:

### Goal:

Inspect recent repair, telemetry, ingestion, key, and RAG events.

### Main flow:

1. The dashboard requests recent logs with a protected bearer key.
2. The backend reads the newest records from Supabase PostgreSQL.
3. The dashboard renders action, status, tokens, latency, and detail fields.
4. The operator can refresh the list after a new graph event.

### Security condition:

The public Supabase publishable key cannot read the ledger tables because row level security is enabled and public grants are revoked. The backend connects through the configured database URL.

## UC-08: Operate tenant daemon telemetry:

### Goal:

Run the supplied daemon against a deployed service.

### Main flow:

1. The operator downloads `frontend/public/ohohops_daemon.py`.
2. The operator supplies the server URL, project directory, and namespace scoped key.
3. The daemon sends metric and log observations at the configured interval.
4. The backend authenticates the key and associates events with the namespace.
5. The operator reviews telemetry and any queued repair in the dashboard.

## Acceptance criteria:

1. Every protected use case returns a clear authentication result.
2. Every repair run emits enough state for an operator to understand its outcome.
3. Every patch reaches execution only after security clearance.
4. Every sandbox failure respects the retry limit.
5. Every failed deployment has a rollback path.
6. Every tenant scoped record is isolated from other namespaces.
