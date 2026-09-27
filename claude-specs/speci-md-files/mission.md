# Constitution: Mission & Non-Negotiable Boundaries

## 1. Project Vision
An internal, ChatGPT-style AI assistant for a single organization of under 100 employees: SSO-gated chat with persistent memory, connected internal tools via MCP, generative Artifacts, and admin governance — built on Google ADK 2.0 as the agentic harness, sized for low operating cost and low ops burden rather than hyperscale.

## 2. Target Audience & Personas
- **Primary Persona**: Employee end user. Chats via web or mobile, uses connected tools (Slack, Drive, internal ticketing) through the assistant, generates and views Artifacts (charts, small tools, files), expects the assistant to remember durable facts/preferences across sessions.
- **Secondary Persona / Stakeholder**: Org admin / IT-security reviewer. Manages user roles and tool connections, approves critical/write-action requests via the HITL gateway, reviews the audit log, manages the skill/plugin catalog, and owns the security review that gates rollout.

## 3. Product Scope & Core Capabilities
- **Chat**: Streaming web + native mobile chat UI, message edit/regenerate (branching), SSO login only.
- **Tools**: MCP-connected internal and third-party tools, per-role permissioning, human approval for critical/write actions.
- **Memory**: Episodic (transcript), semantic (durable facts/preferences), and procedural (team workflow conventions, authored as skills) memory classes.
- **Skills & plugins**: On-demand, versioned instruction bundles; the highest-value ones may graduate into dedicated ADK sub-agents.
- **Artifacts**: Sandboxed code execution and generative UI (charts, small interactive tools, generated files), rendered in an isolated origin.
- **Admin console**: User/role management, tool-connection management, skill catalog management, usage/cost dashboards, audit log, HITL approval queue.

## 4. Non-Negotiable Boundaries & Constraints
- **Boundary 1 (Security / Safety)**: No public sign-up — SSO/OIDC via the org's existing IdP only. All tool OAuth tokens encrypted at rest. Every write-capable tool call requires human approval via the HITL gateway before execution. Every tool invocation and every approval decision is written to an immutable audit log. Generated Artifacts execute only inside a sandboxed, network-restricted environment and render only in an isolated origin, never the main app's origin.
- **Boundary 2 (Performance / Scale)**: Architecture is explicitly sized for under 100 concurrent seats. No distributed infrastructure (service mesh, sharded databases, multi-region active-active) is to be introduced pre-emptively; a single managed Postgres primary is the target until there is measured evidence it can't keep up.
- **Boundary 3 (Compliance / Governance)**: Row-level org scoping (`org_id` + Postgres RLS) on every table from day one, even with a single tenant. Model provider stays swappable (Anthropic/OpenAI/Gemini) — no architectural decision may silently lock the system to one cloud vendor.
- **Out of Scope (v1)**: Multi-tenant resale/hosting of this platform for other organizations; agent-to-agent (A2A) federation with agents outside this deployment; self-hosted/fine-tuned model inference; a fully native (Swift/Kotlin) mobile rewrite.
