"""Server-Sent Events (SSE) streaming helpers for real-time agent output."""

import json
from typing import Any, AsyncGenerator, Dict


async def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Formats payload as a valid SSE message string."""
    payload = json.dumps({"type": event_type, "data": data})
    return f"event: {event_type}\ndata: {payload}\n\n"
