# Architecture

## Repair graph

1. Evaluation converts incident evidence into an actionable problem.
2. Context retrieval queries the selected vector store.
3. Modification produces a complete replacement file.
4. Arbitration requires deterministic checks plus two unanimous model votes.
5. Sandbox executes the patch in a network isolated container.
6. Deployment applies the patch transactionally and verifies process health.

Failed sandbox runs return to modification until the configured retry limit.
Failed deployment health checks restore the original file and restart the prior
version.

## Runtime modes

Local mode uses ChromaDB and Docker. Cloud mode uses Pinecone and a tenant daemon.
The daemon reports telemetry, receives approved patches, supervises the target
process, and performs rollback when the patched process fails.

## Data boundaries

Provider credentials stay in environment variables. Vector namespaces isolate
ingested projects. Supabase stores audit events, tenant key hashes, and pending
deployments when configured. Raw tenant keys are returned once and never stored.
