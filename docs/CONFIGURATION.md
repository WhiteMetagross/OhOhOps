# Configuration:

## Self contained local mode:

Copy `.env.example` to `.env`. Keep `USE_MOCK_LLM=true`. This mode uses
deterministic offline model responses, deterministic 3072 value embeddings,
ChromaDB, and the real Docker sandbox.

## Real model mode:

Set `USE_MOCK_LLM=false`. Configure one chat provider plus enough credentials to
construct two distinct security model IDs.

Recommended provider diversity:

```dotenv
GEMINI_API_KEY_SECURITY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
```

OpenAI provides native 3072 dimensional embeddings through
`text-embedding-3-large`. Gemini and local embeddings are adapted to the fixed
storage width when their native output differs.

Provider setup:

1. [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
2. [Anthropic authentication](https://platform.claude.com/docs/en/manage-claude/authentication)
3. [OpenRouter quickstart](https://openrouter.ai/docs/quickstart)
4. [OpenAI API quickstart](https://platform.openai.com/docs/quickstart/make-your-first-api-request)

## Cloud vector storage:

Set `DEPLOYMENT_MODE=cloud` and `PINECONE_API_KEY`. OhOhOps creates the
`ohohops-3072` serverless index when absent.

1. [Create a Pinecone API key](https://docs.pinecone.io/reference/api/authentication)
2. [Pinecone index API](https://docs.pinecone.io/reference/api/2025-04/control-plane/create_index)

## Supabase ledger:

Set `SUPABASE_DB_URL` to the Postgres connection string shown by the Supabase
Connect panel. Use session pooler mode when the deployment network lacks IPv6.

[Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)

## Private GitHub ingestion:

Set `GITHUB_TOKEN` to a fine grained token with read access only to required
repositories. OhOhOps accepts only HTTPS github.com repository URLs and sends
the token through Git configuration without placing it in the URL.

## Production secrets:

Replace `OHOHOPS_API_KEY` and `OHOHOPS_WEBHOOK_SECRET` with separate random
values. Store all values in the deployment secret manager. Never expose provider
keys through `NEXT_PUBLIC_` variables.

## Sandbox limits:

The default Docker sandbox allows 256 MB of memory, half a CPU, no network, and
60 seconds per run. Set `SANDBOX_MEM_LIMIT` or `SANDBOX_TIMEOUT_SECONDS` when
large compilers or target projects require more capacity.
