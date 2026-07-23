# Security

## Reporting

Report suspected vulnerabilities privately through GitHub Security Advisories.
Do not open a public issue containing credentials, exploit details, or customer
data.

## Operational boundaries

OhOhOps can execute generated code and control Docker. Run it only on trusted
hosts. Protect the Docker socket, use scoped provider keys, set spending limits,
and keep production secrets outside source control.

Generated patches require deterministic blocklist approval plus unanimous votes
from two model configurations. Sandbox containers have no network access and use
CPU, memory, and time limits. Deployment writes are transactional and restore
the prior file when health verification fails.

## Supported versions

Security fixes target the latest commit on `main`.
