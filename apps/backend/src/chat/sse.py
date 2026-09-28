"""Cloud Run HTTP/2 Server-Sent Events (SSE) Formatter for @assistant-ui/react-google-adk (Spec 02, R02.2).

Converts ADK runner events into standard assistant-ui SSE chunks, including initial keep-alive
pings (: ping\\n\\n) to eliminate Cloud Load Balancing timeout drops.
"""
import json
import logging
from typing import AsyncIterator, Dict, Any

logger = logging.getLogger("workkbot.sse")


async def format_adk_sse_stream(
    event_generator: AsyncIterator[Dict[str, Any]],
    include_initial_ping: bool = True,
) -> AsyncIterator[str]:
    """
    Transforms ADK event stream into SSE wire format expected by @assistant-ui/react-google-adk.
    """
    # 1. Send initial keep-alive ping for Cloud Run HTTP/2 and Google Cloud Load Balancer
    if include_initial_ping:
        yield ": ping\n\n"

    try:
        async for event in event_generator:
            # Wire format per convertSdkEvent
            wire_event = {
                "id": event.get("id", ""),
                "turnComplete": event.get("turnComplete", False),
            }
            if "author" in event:
                wire_event["author"] = event["author"]
            if "branch" in event:
                wire_event["branch"] = event["branch"]
            if "content" in event:
                wire_event["content"] = event["content"]
            if "actions" in event:
                wire_event["actions"] = event["actions"]
            if "errorCode" in event:
                wire_event["errorCode"] = event["errorCode"]
            if "errorMessage" in event:
                wire_event["errorMessage"] = event["errorMessage"]

            data_str = json.dumps(wire_event)
            yield f"data: {data_str}\n\n"

    except Exception as e:
        logger.error("Exception during SSE streaming: %s", e)
        error_event = {
            "id": "",
            "errorCode": "STREAM_ERROR",
            "errorMessage": str(e),
            "turnComplete": True,
        }
        yield f"data: {json.dumps(error_event)}\n\n"
