# OhOhOps:

OhOhOps is an autonomous SRE control plane for incident detection, code context retrieval, patch generation, security arbitration, isolated execution, and controlled recovery. It provides a FastAPI backend, a six node LangGraph repair cycle, a Next.js Sunfire dashboard, ChromaDB local retrieval, Pinecone cloud retrieval, optional Supabase PostgreSQL audit storage, and RAGAS evaluation support.

The project is created and maintained by Mridankan Mandal through [RedZapdos123](https://github.com/RedZapdos123) and [WhiteMetagross](https://github.com/WhiteMetagross).

## Purpose:

OhOhOps reduces the manual effort required to investigate a production incident while preserving explicit safety boundaries. The agent first evaluates evidence, retrieves relevant code context, proposes a complete replacement patch, requests two model security votes, runs the patch inside a network isolated Docker sandbox, and deploys only after the configured checks pass. A failed deployment restores the prior file through a transactional rollback.

## Capability summary:

1. Six node cyclic LangGraph repair workflow.
2. PyOD Isolation Forest anomaly detection over a configurable telemetry window.
3. Tree Sitter AST aware chunking for Python, JavaScript, TypeScript, TSX, C, C++, and Go.
4. ChromaDB local retrieval and Pinecone cloud retrieval with namespace isolation.
5. A fixed 3072 value embedding contract independent of the configured provider dimension.
6. Dual model security arbitration with unanimous clearance before sandbox execution.
7. Network isolated Docker sandbox execution with memory, CPU, timeout, and retry limits.
8. Transactional patch deployment with backup, health verification, rollback, and retry routing.
9. FastAPI REST endpoints and Server Sent Events for live repair progress.
10. Supabase PostgreSQL operational ledger with explicit row level security and public grant revocation.
11. Next.js dashboard with Sunfire light and dark themes, responsive layouts, tenant key onboarding, telemetry, graph trace, RAG queries, and audit history.

## Visual gallery:

The following captures were taken from the running local Docker stack. The captures include authenticated live ledger data, the six stage repair trace, the responsive mobile layout, both Sunfire themes, onboarding, and settings.

![Dashboard light mode showing the operations workspace, health strip, repair trace, telemetry, and ledger.](visuals/DashboardLightMode.png)

*Figure 1. DashboardLightMode shows the primary operations workspace in the light Sunfire theme.*

![Dashboard dark mode showing the operations workspace and repair stages.](visuals/DashboardDarkMode.png)

*Figure 2. DashboardDarkMode shows the authenticated dashboard in the dark Sunfire theme.*

![Dashboard repair workflow while the graph is executing.](visuals/DashboardRepairWorkflowWorking.png)

*Figure 3. DashboardRepairWorkflowWorking shows the live repair stream while evaluation, context retrieval, modification, arbitration, sandbox, and deployment events are being emitted.*

![Dashboard repair workflow after graph execution.](visuals/DashboardRepairWorkflowComplete.png)

*Figure 4. DashboardRepairWorkflowComplete shows the completed incident analysis, proposed file, security gate, deployment evidence, and ledger result.*

![Dashboard in the light responsive mobile layout.](visuals/DashboardMobileLightMode.png)

*Figure 5. DashboardMobileLightMode demonstrates the stacked mobile layout in the light theme.*

![Dashboard in the dark responsive mobile layout.](visuals/DashboardMobileDarkMode.png)

*Figure 6. DashboardMobileDarkMode demonstrates the stacked mobile layout in the dark theme.*

![Onboarding page in dark mode.](visuals/OnboardingDarkMode.png)

*Figure 7. OnboardingDarkMode shows deployment selection and namespace access setup.*

![Onboarding page in light mode.](visuals/OnboardingLightMode.png)

*Figure 8. OnboardingLightMode shows the light theme setup experience.*

![Onboarding page with the generated tenant key redacted for publication.](visuals/OnboardingKeyGeneratedRedacted.png)

*Figure 9. OnboardingKeyGeneratedRedacted shows the one time generated tenant credential state with the credential value redacted.*

![Onboarding page after access verification with the credential redacted for publication.](visuals/OnboardingAccessVerifiedRedacted.png)

*Figure 10. OnboardingAccessVerifiedRedacted shows successful namespace verification before opening operations, with the credential value redacted.*

![Onboarding local Docker mode in dark theme.](visuals/OnboardingLocalDockerDarkMode.png)

*Figure 11. OnboardingLocalDockerDarkMode shows the local Compose deployment instructions.*

![Onboarding local Docker mode in light theme.](visuals/OnboardingLocalDockerLightMode.png)

*Figure 12. OnboardingLocalDockerLightMode shows the same deployment instructions in light mode.*

![Settings page in dark mode.](visuals/SettingsDarkMode.png)

*Figure 13. SettingsDarkMode shows tenant key administration and daemon connection guidance.*

![Settings page in light mode.](visuals/SettingsLightMode.png)

*Figure 14. SettingsLightMode shows the settings page in the light theme.*

## Architecture diagrams:

![Logical architecture of OhOhOps.](docs/diagrams/Architecture.png)

*Figure 15. ArchitectureUml describes the application layers and external provider boundaries.*

![Docker and cloud deployment topology.](docs/diagrams/Deployment.png)

*Figure 16. DeploymentUml describes the local containers, volumes, sandbox boundary, and cloud services.*

![Repair request sequence.](docs/diagrams/Sequence.png)

*Figure 17. SequenceUml describes a repair request from dashboard submission through ledger recording.*

![Repair activity flow.](docs/diagrams/Activity.png)

*Figure 18. ActivityUml describes detection, arbitration, sandbox execution, deployment, rollback, and retry decisions.*

![Repair state machine.](docs/diagrams/StateMachine.png)

*Figure 19. StateMachineUml describes the durable conceptual states of a repair run.*

## Repository map:

1. `backend/app` contains the FastAPI service, graph nodes, providers, security controls, storage services, and schemas.
2. `backend/tests` contains unit and integration oriented backend tests.
3. `backend/scripts` contains live node, sandbox, vector store, and full stack smoke checks.
4. `frontend/src` contains the Next.js App Router pages, dashboard components, clients, and theme system.
5. `frontend/e2e` contains desktop, mobile, navigation, health, and theme persistence tests.
6. `docs` contains architecture, use cases, system design, testing, installation, usage, code index, and agent documentation.
7. `docs/diagrams` contains compiled PlantUML PNG diagrams only. PlantUML source is intentionally not committed.
8. `visuals` contains descriptive ThisCase PNG captures of the running website.

## Quick start:

Requirements are Docker Desktop and Git. Copy `.env.example` to `.env`, keep mock mode enabled for an offline demonstration, and start the stack.

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Open `http://localhost:3000`. The local demonstration uses deterministic mock inference, ChromaDB, Docker sandbox execution, and the development API key. Configure real model, Pinecone, and Supabase values only when the corresponding live features are needed.

## Verification:

The complete setup and validation instructions are in the following documents.

1. [Architecture](docs/Architecture.md).
2. [Use cases](docs/UseCase.md).
3. [System design](docs/SystemDesign.md).
4. [Testing](docs/Testing.md).
5. [Installation and setup](docs/InstallationAndSetup.md).
6. [Usage](docs/Usage.md).
7. [Codebase index](docs/CodeBaseIndex.md).
8. [AI agents](docs/AIAgents.md).
9. [Configuration](docs/CONFIGURATION.md).
10. [Security policy](SECURITY.md).

## Safety notice:

OhOhOps can control Docker and apply generated patches. Protect the Docker socket, scope provider credentials, use network isolated sandbox mode for production, keep automatic deployment disabled until health checks match the target service, and never commit `.env` or provider credentials.

## License:

MIT. Copyright 2026 Mridankan Mandal.
