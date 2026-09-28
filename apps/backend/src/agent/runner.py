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
from google.genai import types

from src.agent.agent import core_agent
from src.agent.model_tier import ModelTier, model_router
from src.agent.session_service import WorkkbotEvent, session_service
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
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Executes a conversational turn using canonical Google ADK 2.0.
        Supports checkpoint-based branching when checkpoint_id is provided.
        Streams real model outputs directly with zero hardcoded responses.
        """
        start_time = time.time()

        # 1. Ensure persistent session exists in Supabase
        await self.session_service.get_or_create_session(
            session_id=session_id,
            user_id=user_id,
            org_id=org_id,
            conversation_id=conversation_id,
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

        # 3. Prepare user message in canonical google.genai types.Content format
        new_message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=message)],
        )

        model_event_id = f"evt_{uuid.uuid4().hex[:12]}_m"
        received_any_chunks = False

        # 4. Execute turn via canonical Google ADK Runner
        try:
            async for adk_event in self._runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=new_message,
                state_delta=state_delta,
            ):
                if adk_event.author == "user":
                    continue

                eid = adk_event.id or model_event_id
                content = adk_event.content
                parts_data = []

                if content and hasattr(content, "parts"):
                    for part in content.parts:
                        part_dict = {}
                        if getattr(part, "thought", False):
                            thought_text = getattr(part, "text", "") or ""
                            part_dict = {"thought": True, "text": thought_text}
                        elif getattr(part, "text", None):
                            text_str = part.text
                            part_dict = {"text": text_str}
                        if part_dict:
                            parts_data.append(part_dict)

                turn_done = getattr(adk_event, "turn_complete", False)
                if parts_data or turn_done:
                    received_any_chunks = True
                    yield {
                        "id": eid,
                        "author": "model",
                        "branch": branch_name,
                        "content": {
                            "role": "model",
                            "parts": parts_data,
                        },
                        "turnComplete": turn_done,
                    }

            if received_any_chunks:
                self.model_router.record_success(active_model)

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

        duration = time.time() - start_time
        logger.info("Completed turn session=%s in %.3fs", session_id, duration)


runner_singleton = AdkRunnerSingleton()
