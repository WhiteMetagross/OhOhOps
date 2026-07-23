# Usage:

OhOhOps is used from the browser dashboard. The normal operator path is Setup, access verification, source synchronization, incident submission, graph observation, and ledger review.

## Open the dashboard:

Start the Docker stack and open `http://localhost:3000`. The root route redirects to Setup. Operations opens the dashboard. Setup opens onboarding. The footer on every page identifies Mridankan Mandal, RedZapdos123, and WhiteMetagross.

## Select a theme:

Use the theme button in the primary navigation. The control switches between light and dark Sunfire palettes, updates the document color scheme, and persists the value across reloads. The same control is available on the dashboard, onboarding page, and settings page.

## Configure access:

1. Open Setup.
2. Select Managed service for a namespace key workflow or Local Docker for a Compose workflow.
3. Enter a namespace such as `production` or `visual-demo`.
4. Select Generate key.
5. Copy the raw key because it is shown once.
6. Select Verify key.
7. Select Open operations workspace after verification succeeds.

The backend stores only a hash of the raw key. Use a unique namespace for each tenant and do not place raw keys in source control, screenshots intended for public distribution, or issue reports.

## Synchronize source:

The Sync Workspace panel supports three input modes.

1. GitHub URL accepts a public or token authorized repository URL.
2. ZIP Upload accepts a source archive after containment and file validation.
3. Local Path accepts a path available to the backend process.

Enter a namespace and run ingestion. The backend parses supported source files with Tree Sitter, creates AST aware chunks, normalizes vectors to 3072 values, and stores chunks in the selected vector store. The target file selector updates after successful ingestion.

## Ask Codebase Q&A:

Enter a question such as `Where are retry limits and security gates defined?` and an optional namespace. Select Ask. The backend retrieves relevant context and streams the answer through SSE. The response is intended for investigation and should be reviewed against the cited source context.

## Run a manual repair:

1. Select Manual Triage in Anomaly Control.
2. Select a target file after ingestion or provide a valid target in the request.
3. Enter a reproduction command.
4. Paste crash logs or incident evidence.
5. Select Run repair graph.
6. Observe the six graph stages and live agent output.
7. Review the proposed file, security gate checklist, sandbox output, deployment evidence, and final outcome.

The graph displays Evaluation, Context retrieval, Code modification, Dual model consensus, Docker sandbox, and Deployment. The dashboard also shows tokens, latency, retry cycles, and outcome when the run completes.

## Understand outcomes:

1. A cleared patch reaches the sandbox.
2. A security denial stops the graph before execution.
3. A nonzero sandbox exit returns to modification while retries remain.
4. A successful sandbox result enters deployment.
5. A failed deployment restores the original file.
6. A retry limit ends the run with a terminal failure.
7. Ledger status shows the audit result when Supabase is configured.

## Use proactive sentinel:

Select Proactive Sentinel only when telemetry-driven automation is intended. The endpoint records CPU, memory, error rate, logs, target file, and reproduction command. The optional background telemetry loop is disabled by default and must be enabled through configuration for autonomous invocation.

## Review telemetry:

Telemetry Pulse charts CPU and error rate values returned by the backend. Anomaly Control can refresh available files and filter operations by namespace. The chart is a monitoring view and does not by itself authorize a repair.

## Review the ledger:

Operational Ledger lists recent action, status, token, latency, and detail fields. Use Refresh after a graph or telemetry event. A missing or unavailable ledger is shown as a degraded state rather than causing the dashboard to crash. Public Supabase access is denied by the database schema, so ledger reads must pass through the authenticated backend.

## Manage keys:

Settings provides tenant key generation, service access guidance, and credential inventory. Generate keys for a defined namespace and label. Revoke keys that are no longer used. Treat a raw key as compromised if it appears in a terminal log, screenshot, issue, or chat message.

## Run the daemon:

Download the daemon from `frontend/public/ohohops_daemon.py` or the Settings page instructions. Start it with a namespace scoped key, server URL, and project directory. Confirm that telemetry appears in the dashboard and that the namespace is correct before enabling repair automation.

## Operational limits:

1. Keep Docker sandbox network mode set to `none` for production execution.
2. Keep memory, CPU, and timeout values bounded.
3. Keep model credentials scoped to the smallest provider permissions.
4. Use mock mode for documentation and UI work that does not require external inference.
5. Use a disposable project when testing deployment and rollback.
6. Review generated patches before enabling automatic deployment.
