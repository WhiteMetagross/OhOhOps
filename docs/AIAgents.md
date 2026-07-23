# AI Agents:

OhOhOps is an agentic system with one orchestrated repair agent and supporting provider services. The word agent refers to a bounded graph operation with explicit input, output, and safety rules. It does not mean that a model can bypass the graph, execute arbitrary commands, or deploy without the configured controls.

![Repair state machine.](diagrams/StateMachine.png)

*Figure 1. StateMachineUml describes the conceptual states of an agent repair run.*

## Agent state:

The shared `AgentState` carries the current target file, discovered logs, project path, reproduction command, namespace, run identifier, source code, retrieved context, proposed patch, evaluation result, security decisions, sandbox output, retry count, deployment result, token usage, and latency. Nodes return partial state updates. LangGraph merges those updates and routes the next node.

## Agent nodes:

### Evaluation agent:

The evaluation node turns raw logs and telemetry into a repair question. It identifies the target, records evidence, and prepares the state for retrieval. It should not modify source files or execute commands.

### Context agent:

The context node queries ChromaDB or Pinecone through the vector store protocol. It uses AST aware chunks and namespace filtering. It returns relevant documents for the modification prompt and can stream a context grounded response through the Codebase Q&A endpoint.

### Modification agent:

The modification node requests a complete replacement file. The replacement format makes validation and rollback deterministic. The prompt includes the target, evidence, relevant context, coding constraints, and prior execution feedback when a retry occurs.

### Arbitration agents:

The arbitration node performs deterministic command and content safety checks, then asks two independently configured security models for decisions. A patch is clear only when the deterministic checks pass and both model decisions approve. A single denial ends the graph before sandbox execution.

### Sandbox agent:

The sandbox node invokes the configured subprocess or Docker strategy. Docker mode uses a network isolated container with bounded memory, CPU, and execution time. The node records standard output, standard error, exit code, and execution metadata.

### Deployment agent:

The deployment node applies a patch transaction, supervises the target process, and checks health. It finalizes the backup after a healthy result. It rolls back the original file when health verification fails and returns retry information to the graph.

## Agent routing:

1. Evaluation always routes to context retrieval.
2. Context retrieval always routes to modification.
3. Modification always routes to arbitration.
4. Arbitration routes to sandbox only after security clearance.
5. Arbitration routes to terminal completion after denial.
6. Sandbox routes to deployment on exit code zero.
7. Sandbox routes to modification when execution fails and retries remain.
8. Sandbox routes to terminal failure when the retry limit is reached.
9. Deployment routes to terminal completion after the deployment service returns.

## Prompt and model policy:

Model prompts must preserve the target file boundary, return complete file content, avoid unrelated changes, and respect the project language. Security prompts must judge command execution, network access, credential exposure, path traversal, destructive behavior, and scope expansion. Model output is evidence for a decision, not authority to skip deterministic checks.

## Mock and live behavior:

Mock mode uses deterministic model responses and deterministic embeddings so the graph can be tested without provider keys. Live mode selects Gemini, OpenAI, Anthropic, or OpenRouter according to configuration. Embedding output is normalized to 3072 values regardless of provider output size.

## Anomaly agent:

The PyOD Isolation Forest path consumes a bounded telemetry window and contamination setting. The background loop is disabled by default. When explicitly enabled, it can submit a repair graph after an anomalous observation with usable incident logs. This feature must be treated as a production automation switch.

## Safety invariants:

1. The graph cannot enter the sandbox without security clearance.
2. The sandbox cannot access the network in Docker mode.
3. The patch target must resolve inside the project directory.
4. The patch transaction keeps a backup until deployment health passes.
5. Retry count cannot exceed the configured maximum.
6. The ledger records terminal actions when the database is available.
7. Tenant namespace context is retained on protected requests.
8. Public Supabase roles cannot read agent audit tables.

## Human responsibility:

An operator remains responsible for the deployment policy, provider credentials, target process health command, sandbox image, rollback readiness, and review of generated changes. OhOhOps provides evidence and controlled automation. It is not a replacement for service ownership or change management.
