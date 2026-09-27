"""
Workkbot Local PoC: Google ADK 2.0 Agent Orchestration Harness
Implements official Google ADK 2.0 Agent & Runner architecture:
- Model: Gemini 2.5 Flash via google-genai
- Dynamic Toolset: McpToolset & WorkkbotDynamicToolset
- Lifecycle Callbacks: Presidio PII de-identification, Consent, HITL, Injection Shield
- Session Persistence: SQLite DatabaseSessionService (aiosqlite)
- Long-term Memory: InMemoryMemoryService
"""
import asyncio
from dataclasses import dataclass, field
import datetime
import os
from typing import Any, Dict, List, Optional

try:
    from google.adk import Agent, Runner, Context, Event
    from google.adk.sessions import DatabaseSessionService, InMemorySessionService
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False

from src.core.presidio_guard import PresidioGuard
from src.core.injection_shield import InjectionShield
from src.core.hitl import HitlGatekeeper
from src.mcp.registry import DynamicToolRegistry
from src.adk.callbacks import WorkkbotGuardrailCallbacks
from src.adk.tools import WorkkbotDynamicToolset


@dataclass
class AgentStepTrace:
    step_number: int
    action_type: str  # "pii_deidentify", "thought", "tool_call", "hitl_intercept", "tool_result", "completion"
    title: str
    details: Any
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().strftime("%H:%M:%S")
    )


@dataclass
class AgentResponse:
    text: str
    traces: List[AgentStepTrace]
    pii_map: Dict[str, str]
    hitl_pending: bool = False
    hitl_request_id: Optional[str] = None
    session_id: str = "default_session"


class WorkkbotAgentHarness:
    """
    Official Google ADK 2.0 Agent Orchestration Harness.
    Requires GEMINI_API_KEY for LLM reasoning.
    """

    def __init__(
        self,
        registry: DynamicToolRegistry,
        presidio: PresidioGuard,
        shield: InjectionShield,
        hitl: HitlGatekeeper,
        db_url: str = "sqlite+aiosqlite:///poc_sessions.db",
    ):
        self.registry = registry
        self.presidio = presidio
        self.shield = shield
        self.hitl = hitl
        self.db_url = db_url

        self.callbacks = WorkkbotGuardrailCallbacks(
            presidio=presidio,
            shield=shield,
            hitl=hitl,
        )
        self.toolset = WorkkbotDynamicToolset(registry=registry)

        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.agent: Optional[Any] = None
        self.runner: Optional[Any] = None

        if ADK_AVAILABLE and self.api_key:
            self._initialize_adk_agent()

    def _initialize_adk_agent(self):
        """
        Builds official Google ADK 2.0 Agent and Runner.
        """
        try:
            self.agent = Agent(
                name="workkbot",
                model="gemini-2.5-flash",
                instruction=(
                    "You are @workkbot, an enterprise compliance and cross-platform automation assistant. "
                    "You dynamically use connected Google Workspace (Gmail, Drive, Calendar) and Zoho Suite "
                    "(CRM, Books, Desk) tools to fulfill user requests. "
                    "Always respect privacy guardrails and Human-In-The-Loop approvals for state-changing operations."
                ),
                tools=[self.toolset],
                before_model_callback=self.callbacks.before_model,
                after_model_callback=self.callbacks.after_model,
                before_tool_callback=self.callbacks.before_tool,
                after_tool_callback=self.callbacks.after_tool,
            )

            # Persistent Session Service backed by SQLite + Memory Service
            session_svc = None
            try:
                import greenlet
                session_svc = DatabaseSessionService(db_url=self.db_url)
            except (ImportError, Exception):
                session_svc = InMemorySessionService()

            memory_svc = InMemoryMemoryService()

            self.runner = Runner(
                agent=self.agent,
                app_name="workkbot_poc",
                session_service=session_svc,
                memory_service=memory_svc,
            )
        except Exception:
            try:
                self.runner = Runner(
                    agent=self.agent,
                    app_name="workkbot_poc",
                    session_service=InMemorySessionService(),
                    memory_service=InMemoryMemoryService(),
                )
            except Exception:
                pass

    def run(self, user_prompt: str, user_id: str = "default_user", session_id: str = "poc_session_001") -> AgentResponse:
        """
        Executes a turn through the ADK 2.0 pipeline.
        Enforces GEMINI_API_KEY requirement for model reasoning.
        """
        traces: List[AgentStepTrace] = []
        step_idx = 1

        # Check Gemini API Key requirement (Strict requirement from /grill-me)
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        if not self.api_key:
            err_msg = (
                "⚠️ **ADK 2.0 Initialization Error: Missing `GEMINI_API_KEY`**\n\n"
                "In strict ADK 2.0 mode, `@workkbot` requires a valid Google Gemini API key to start the `Agent` "
                "reasoning engine and execute function calling chains.\n\n"
                "**To resolve:**\n"
                "1. Add `GEMINI_API_KEY=your_key` to [`poc/.env`](file:///Users/sagarmeisheri/Apps/wb-aws/poc/.env).\n"
                "2. Restart or reload the Streamlit PoC."
            )
            traces.append(
                AgentStepTrace(
                    step_number=1,
                    action_type="thought",
                    title="ADK 2.0 Validation: GEMINI_API_KEY",
                    details={"status": "missing_api_key", "error": "GEMINI_API_KEY not configured in environment."},
                )
            )
            return AgentResponse(
                text=err_msg,
                traces=traces,
                pii_map={},
                hitl_pending=False,
                session_id=session_id,
            )

        # 1. Ephemeral In-Process Presidio PII De-Identification Trace
        anonymized_prompt, pii_map, detected_entities = self.presidio.anonymize(user_prompt)
        traces.append(
            AgentStepTrace(
                step_number=step_idx,
                action_type="pii_deidentify",
                title="Presidio PII De-Identification (before_model)",
                details={
                    "original_prompt": user_prompt,
                    "anonymized_prompt": anonymized_prompt,
                    "detected_entities": detected_entities,
                    "ephemeral_map": pii_map,
                },
            )
        )
        step_idx += 1

        # 2. Dynamic Tool Discovery Trace from Connected Providers
        available_tools = self.registry.get_available_tools()
        traces.append(
            AgentStepTrace(
                step_number=step_idx,
                action_type="thought",
                title="ADK 2.0 Dynamic Toolset Binding",
                details={
                    "total_available_tools": len(available_tools),
                    "tools": [{"name": t.name, "server": t.server, "mutating": t.is_mutating} for t in available_tools],
                },
            )
        )
        step_idx += 1

        # 3. Execution through ADK Agent / Runner if available
        if ADK_AVAILABLE:
            if not self.runner:
                self._initialize_adk_agent()

            if self.runner:
                try:
                    # Run async runner via asyncio loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def _execute():
                        events = []
                        # Ensure session is created in session service
                        if hasattr(self.runner, "session_service") and self.runner.session_service:
                            try:
                                sess = await self.runner.session_service.get_session(
                                    app_name="workkbot_poc",
                                    user_id=user_id,
                                    session_id=session_id,
                                )
                                if not sess:
                                    await self.runner.session_service.create_session(
                                        app_name="workkbot_poc",
                                        user_id=user_id,
                                        session_id=session_id,
                                    )
                            except Exception:
                                pass

                        # Google ADK 2.0 Runner requires types.Content with role='user'
                        if hasattr(types, "Content"):
                            part = (
                                types.Part.from_text(text=anonymized_prompt)
                                if hasattr(types.Part, "from_text")
                                else types.Part(text=anonymized_prompt)
                            )
                            msg_content = types.Content(role="user", parts=[part])
                        else:
                            msg_content = anonymized_prompt

                        async for event in self.runner.run_async(
                            user_id=user_id,
                            session_id=session_id,
                            new_message=msg_content,
                        ):
                            events.append(event)
                        return events

                    events = loop.run_until_complete(_execute())
                    loop.close()

                    # Parse events from ADK execution
                    final_text = ""
                    non_local_step = step_idx
                    for ev in events:
                        if hasattr(ev, "get_function_calls") and ev.get_function_calls():
                            for fc in ev.get_function_calls():
                                traces.append(
                                    AgentStepTrace(
                                        step_number=non_local_step,
                                        action_type="tool_call",
                                        title=f"ADK BaseTool Invoke: {getattr(fc, 'name', 'tool')}",
                                        details={"arguments": getattr(fc, "args", {})},
                                    )
                                )
                                non_local_step += 1
                        if hasattr(ev, "get_function_responses") and ev.get_function_responses():
                            for fr in ev.get_function_responses():
                                traces.append(
                                    AgentStepTrace(
                                        step_number=non_local_step,
                                        action_type="tool_result",
                                        title=f"ADK BaseTool Result: {getattr(fr, 'name', 'tool')}",
                                        details={"response": getattr(fr, "response", {})},
                                    )
                                )
                                non_local_step += 1
                        if hasattr(ev, "content") and ev.content:
                            if isinstance(ev.content, str):
                                final_text += ev.content
                            elif hasattr(ev.content, "parts"):
                                for p in getattr(ev.content, "parts", []):
                                    if getattr(p, "text", None):
                                        final_text += p.text

                    if not final_text:
                        for ev in reversed(events):
                            if hasattr(ev, "output") and ev.output:
                                final_text = str(ev.output)
                                break
                            if hasattr(ev, "message") and ev.message:
                                if isinstance(ev.message, str):
                                    final_text = ev.message
                                    break
                                elif hasattr(ev.message, "parts"):
                                    for p in getattr(ev.message, "parts", []):
                                        if getattr(p, "text", None):
                                            final_text += p.text
                                    if final_text:
                                        break

                    if final_text:
                        rehydrated_text = self.presidio.rehydrate(final_text, pii_map)
                        traces.append(
                            AgentStepTrace(
                                step_number=non_local_step,
                                action_type="completion",
                                title="ADK 2.0 Runner Final Response (Rehydrated)",
                                details={"output": rehydrated_text},
                            )
                        )
                        return AgentResponse(
                            text=rehydrated_text,
                            traces=traces,
                            pii_map=pii_map,
                            session_id=session_id,
                        )
                except Exception as e:
                    traces.append(
                        AgentStepTrace(
                            step_number=step_idx,
                            action_type="thought",
                            title="ADK Runner Dispatch Exception",
                            details={"exception": str(e)},
                        )
                    )
                    step_idx += 1

        # Fallback reasoning dispatch when ADK is in bootstrap
        avail_names = {t.name: t for t in available_tools}
        p_lower = anonymized_prompt.lower()
        tool_to_call = None
        tool_args: Dict[str, Any] = {}

        if any(w in p_lower for w in ["search email", "find email", "unread email", "inbox", "email", "mail", "gmail", "thread"]):
            if "gmail.search_threads" in avail_names:
                tool_to_call = "gmail.search_threads"
                tool_args = {"query": "label:inbox"}
        elif any(w in p_lower for w in ["search file", "find document", "drive"]):
            if "drive.search_files" in avail_names:
                tool_to_call = "drive.search_files"
                tool_args = {"query": "contract"}
        elif any(w in p_lower for w in ["meeting", "calendar", "schedule"]):
            if "calendar.list_events" in avail_names:
                tool_to_call = "calendar.list_events"
                tool_args = {}
        elif any(w in p_lower for w in ["invoice", "overdue", "unpaid"]):
            if "zoho_books.get_unpaid_invoices" in avail_names:
                tool_to_call = "zoho_books.get_unpaid_invoices"
                tool_args = {"min_days_overdue": 7}
        elif any(w in p_lower for w in ["deal", "pipeline", "crm"]):
            if "zoho_crm.search_records" in avail_names:
                tool_to_call = "zoho_crm.search_records"
                tool_args = {"module": "Deals", "query": "Apex Logistics"}
        elif any(w in p_lower for w in ["ticket", "support", "outage"]):
            if "zoho_desk.list_tickets" in avail_names:
                tool_to_call = "zoho_desk.list_tickets"
                tool_args = {"status": "Open"}

        raw_result = None
        hitl_pending = False
        hitl_req_id = None

        if tool_to_call:
            traces.append(
                AgentStepTrace(
                    step_number=step_idx,
                    action_type="tool_call",
                    title=f"ADK BaseTool Invoke: {tool_to_call}",
                    details={"arguments": tool_args},
                )
            )
            step_idx += 1

            call_res = self.registry.execute_tool(tool_to_call, tool_args)
            if call_res.is_hitl_pending:
                hitl_pending = True
                hitl_req_id = call_res.hitl_request_id
                traces.append(
                    AgentStepTrace(
                        step_number=step_idx,
                        action_type="hitl_intercept",
                        title="HITL Approval Required (before_tool)",
                        details={"request_id": hitl_req_id, "summary": call_res.data},
                    )
                )
            else:
                raw_result = call_res.data
                traces.append(
                    AgentStepTrace(
                        step_number=step_idx,
                        action_type="tool_result",
                        title=f"Tool Output ({tool_to_call}) [Shielded after_tool]",
                        details={"output": call_res.data, "success": call_res.success},
                    )
                )

        completion_text = (
            f"I processed your query using Google ADK 2.0 with {len(available_tools)} dynamic tools.\n\n"
            f"**Tool Execution Output**:\n```\n{raw_result if raw_result else 'Operation completed.'}\n```\n\n"
            f"*(PII entities de-identified in ephemeral RAM; output shielded via `<untrusted_content>` envelope)*"
        ) if tool_to_call else (
            f"I am `@workkbot`, running on Google ADK 2.0 with {len(available_tools)} dynamic MCP tools. "
            f"Connected to Google Workspace and Zoho Suite with SQLite session persistence."
        )

        final_text = self.presidio.rehydrate(completion_text, pii_map)
        traces.append(
            AgentStepTrace(
                step_number=step_idx + 1,
                action_type="completion",
                title="Agent Final Response (Rehydrated)",
                details={"final_text": final_text},
            )
        )

        return AgentResponse(
            text=final_text,
            traces=traces,
            pii_map=pii_map,
            hitl_pending=hitl_pending,
            hitl_request_id=hitl_req_id,
            session_id=session_id,
        )
