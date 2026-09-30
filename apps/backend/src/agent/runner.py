"""Google ADK 2.0 In-Process Runner Singleton (Spec 02, R02.1 & R02.3).

Executes agent conversational turns through canonical google.adk.runners.Runner,
coordinates session persistence with Supabase PostgreSQL (public.adk_sessions, public.adk_events),
routes LLM generation with circuit-breaker failover, and handles ChatGPT-style event tree branching.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.genai import types

from src.agent.agent import core_agent
from src.agent.model_tier import ModelTier, model_router
from src.agent.session_service import WorkkbotEvent, session_service
from src.compliance.callbacks import pii_anonymize_callback
from src.compliance.session_pii_vault import session_pii_vault
from src.config import settings

logger = logging.getLogger("workkbot.runner")


class AdkRunnerSingleton:
    """Canonical in-process ADK Runner orchestrating streaming turns and event tree branching."""

    def __init__(self):
        self.agent = core_agent
        self.session_service = session_service
        self.model_router = model_router
        self._runner = Runner(
            agent=self.agent,
            session_service=self.session_service,
            app_name="workkbot",
            auto_create_session=True,
        )

    async def run_turn_stream(
        self,
        user_id: str,
        org_id: str,
        session_id: str,
        message: str,
        checkpoint_id: Optional[str] = None,
        model_preference: Optional[str] = None,
        state_delta: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Executes a conversational turn using canonical Google ADK 2.0.
        Supports checkpoint-based branching when checkpoint_id is provided.
        Streams real model outputs progressively via StreamingMode.SSE.
        """
        start_time = time.time()

        # 1. Ensure persistent session exists in Supabase
        await self.session_service.get_or_create_session(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            conversation_id=conversation_id,
            auth_token=auth_token,
        )

        branch_name = f"branch_{checkpoint_id[:8]}" if checkpoint_id else "main"

        # 2. Model routing with circuit-breaker evaluation
        active_model = self.model_router.get_route_model(model_preference)
        logger.info(
            "Routing turn session=%s model=%s (checkpoint=%s, branch=%s)",
            session_id,
            active_model,
            checkpoint_id,
            branch_name,
        )

        # 2b. Sanitize prompt text & register in ephemeral SessionPiiVault (Spec 03, R03.1b)
        sanitized_message, _ = pii_anonymize_callback(session_id, message)

        # 3. Prepare user message in canonical google.genai types.Content format with tokenized text
        new_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=sanitized_message)],
        )

        model_event_id = f"evt_{uuid.uuid4().hex[:12]}_m"
        # Cap total LLM calls to 3 (max 2 tool execution cycles + 1 final answer)
        run_config = RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=3)

        # 4. Set turn context for dynamic MCP tools resolution
        from src.mcp.google_tools import current_turn_context
        turn_ctx = {
            "user_id": user_id,
            "org_id": org_id,
            "session_id": session_id,
            "message": message,
            "auth_token": auth_token,
            "state_delta": state_delta or {},
            "tool_call_count": 0,
        }
        token_ctx_token = current_turn_context.set(turn_ctx)


        # 5. Execute turn via canonical Google ADK Runner with StreamingMode.SSE
        rehydrator = session_pii_vault.create_stream_rehydrator(session_id)
        received_partials = False
        last_event_id = model_event_id
        try:
            async for adk_event in self._runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message,
                state_delta=state_delta,
                run_config=run_config,
            ):
                if adk_event.author == "user":
                    continue

                eid = adk_event.id or model_event_id
                last_event_id = eid
                is_partial = getattr(adk_event, "partial", False)
                content = adk_event.content
                parts_data = []

                if content and hasattr(content, "parts"):
                    for part in content.parts:
                        part_dict = {}
                        if getattr(part, "thought", False):
                            thought_text = getattr(part, "text", "") or ""
                            part_dict = {"thought": True, "text": thought_text}
                        elif getattr(part, "function_call", None):
                            fc = part.function_call
                            part_dict = {
                                "functionCall": {
                                    "name": getattr(fc, "name", ""),
                                    "args": getattr(fc, "args", {}) or {},
                                    "id": getattr(fc, "id", None),
                                }
                            }
                        elif getattr(part, "function_response", None):
                            fr = part.function_response
                            part_dict = {
                                "functionResponse": {
                                    "name": getattr(fr, "name", ""),
                                    "response": getattr(fr, "response", {}) or {},
                                    "id": getattr(fr, "id", None),
                                }
                            }
                        elif getattr(part, "text", None):
                            text_str = part.text
                            # Rehydrate tokens in model response across SSE chunk boundaries (Spec 03, R03.1 Step 8)
                            rehydrated_text = rehydrator.process_chunk(text_str)
                            if rehydrated_text:
                                part_dict = {"text": rehydrated_text}
                        if part_dict:
                            parts_data.append(part_dict)


                if is_partial:
                    if parts_data:
                        received_partials = True
                        yield {
                            "id": eid,
                            "author": "model",
                            "branch": branch_name,
                            "content": {
                                "role": "model",
                                "parts": parts_data,
                            },
                            "turnComplete": False,
                        }
                else:
                    # Non-partial event: if no partials were received, stream this whole content
                    if not received_partials and parts_data:
                        yield {
                            "id": eid,
                            "author": "model",
                            "branch": branch_name,
                            "content": {
                                "role": "model",
                                "parts": parts_data,
                            },
                            "turnComplete": False,
                        }

            # Flush any remaining tail in rehydrator buffer
            flushed_tail = rehydrator.flush()
            if flushed_tail:
                yield {
                    "id": last_event_id,
                    "author": "model",
                    "branch": branch_name,
                    "content": {
                        "role": "model",
                        "parts": [{"text": flushed_tail}],
                    },
                    "turnComplete": False,
                }

            # Final completion event signifying turn complete
            self.model_router.record_success(active_model)
            yield {
                "id": last_event_id,
                "author": "model",
                "branch": branch_name,
                "content": {
                    "role": "model",
                    "parts": [],
                },
                "turnComplete": True,
            }

        except Exception as exc:
            logger.warning(
                "ADK live model stream returned exception for %s: %s", active_model, exc
            )
            # Record failure in model router to trigger circuit breaker if 429 / 503
            err_str = str(exc)
            if "429" in err_str or "quota" in err_str.lower():
                self.model_router.record_failure(active_model, is_rate_limit=True)
            elif "503" in err_str or "unavailable" in err_str.lower():
                self.model_router.record_failure(active_model, is_rate_limit=False)

            # Yield actual model error directly to caller
            yield {
                "id": model_event_id,
                "author": "model",
                "branch": branch_name,
                "content": {
                    "role": "model",
                    "parts": [{"text": f"Model error from {active_model}: {exc}"}],
                },
                "turnComplete": True,
                "errorCode": 500,
                "errorMessage": str(exc),
            }
        finally:
            current_turn_context.reset(token_ctx_token)

        duration = time.time() - start_time
        logger.info("Completed turn session=%s in %.3fs", session_id, duration)


runner_singleton = AdkRunnerSingleton()

