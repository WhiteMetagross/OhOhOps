# Security Policy:

OhOhOps handles telemetry, source context, generated code, provider credentials,
and Docker execution. Treat every deployment as privileged infrastructure and
apply the controls in this policy before connecting production systems.

## Supported versions:

| Version or branch | Security support |
| --- | --- |
| `main` | Supported. |
| Older commits and untagged forks | Not supported. |

There are currently no published release branches. Security fixes are developed
against the latest commit on `main`.

## Reporting a vulnerability:

Use GitHub private vulnerability reporting or a GitHub Security Advisory for
this repository. Do not open a public issue for a suspected vulnerability.

Include the following information in the private report:

1. A concise description of the vulnerability and its security impact.
2. The affected commit, component, endpoint, configuration, or deployment mode.
3. Reproduction steps or a minimal proof of concept that does not expose live data.
4. Any required credentials, permissions, network access, or runtime assumptions.
5. A suggested mitigation, if one is known.

Remove API keys, database passwords, tokens, customer data, and private source
code from the report. If a credential has been exposed, revoke or rotate it
immediately and then report the exposure privately.

## Response process:

1. The maintainers will acknowledge a private report within five business days.
2. The report will be reproduced, triaged, and assigned a severity level.
3. A fix, mitigation, or configuration change will be prepared when appropriate.
4. The reporter will be included in coordinated disclosure decisions when contact information is provided.
5. Public disclosure will occur only after a mitigation is available or the maintainers determine that disclosure is necessary.

## Security scope:

The following areas are in scope:

1. Authentication, authorization, tenant namespace isolation, and API key handling.
2. FastAPI routes, Server Sent Events, webhook verification, and input validation.
3. Repository ingestion, archive extraction, path validation, and source handling.
4. Generated patch handling, sandbox boundaries, Docker execution, and deployment writes.
5. Secret exposure in source, logs, images, documentation, or generated artifacts.
6. Dependency vulnerabilities that affect the security of a supported deployment.

## Operational requirements:

1. Run the service only on trusted hosts and protect access to the Docker socket.
2. Use network isolated sandbox mode with explicit CPU, memory, and timeout limits.
3. Store secrets in environment variables or a secret manager, never in source control or `NEXT_PUBLIC_` variables.
4. Use separate, least privilege credentials for model providers, Pinecone, Supabase, and GitHub ingestion.
5. Review generated patches and deployment settings before enabling production automation.
6. Keep dependencies, container images, operating systems, and provider SDKs updated.
7. Rotate credentials immediately after accidental disclosure or suspected compromise.

## Security limitations:

OhOhOps can execute generated code and control Docker. Model checks, blocklists,
sandboxing, health checks, and rollback logic reduce risk but do not replace
human review or host level security controls. Their behavior depends on the
configured deployment mode, provider availability, credentials, and project
configuration. Validate these controls against the target environment before
using autonomous repair in production.

## Disclosure contact:

Use the repository's private GitHub security reporting channel as the primary
contact. Do not publish vulnerability details, exploit code, credentials, or
customer data in commits, issues, pull requests, discussions, or screenshots.
