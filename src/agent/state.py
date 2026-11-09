"""State definitions and message data structures for the Agent runtime."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    """Represents an agent's request to execute an external tool."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolResult:
    """Outcome of a tool execution."""

    call_id: str
    name: str
    output: str
    is_error: bool = False


@dataclass
class ChatMessage:
    """Standardized chat message structure compatible with Ollama and OpenAI."""

    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class PendingPatch:
    """Represents a code modification awaiting user confirmation."""

    patch_id: str
    file_path: str
    diff: str
    proposed_content: str
    original_content: str
    created_at: float = field(default_factory=time.time)


@dataclass
class AgentState:
    """Mutable runtime state for a multi-step agent interaction."""

    messages: List[ChatMessage] = field(default_factory=list)
    active_files: List[str] = field(default_factory=list)
    pending_patches: Dict[str, PendingPatch] = field(default_factory=dict)
    iteration_count: int = 0
    max_iterations: int = 12
    is_complete: bool = False
    last_error: Optional[str] = None
