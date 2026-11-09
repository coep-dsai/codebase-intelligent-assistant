"""Asynchronous LLM Client for Ollama and OpenAI-compatible local inference servers."""

import json
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from src.agent.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS
from src.agent.state import ChatMessage, ToolCall
from src.config import Settings, settings
from src.editor.patch_engine import PatchEngine


class LLMClient:
    """Handles communication with local models via Ollama or OpenAI-compatible REST APIs."""

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config = config or settings
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-loaded async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def close(self) -> None:
        """Closes the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _format_messages_for_ollama(
        self, messages: List[ChatMessage]
    ) -> List[Dict[str, Any]]:
        """Converts internal ChatMessage instances to Ollama chat format."""
        formatted: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)

        return formatted

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatMessage:
        """Sends a non-streaming chat completion request and returns the assistant's response."""
        if tools is None:
            tools = TOOL_DEFINITIONS

        if self.config.llm_provider == "ollama":
            url = f"{self.config.ollama_base_url.rstrip('/')}/api/chat"
            payload: Dict[str, Any] = {
                "model": self.config.llm_model,
                "messages": self._format_messages_for_ollama(messages),
                "stream": False,
                "options": {
                    "temperature": self.config.llm_temperature,
                    "num_ctx": self.config.llm_context_window,
                },
            }
            if tools:
                payload["tools"] = tools

            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                msg_data = data.get("message", {})
                content = msg_data.get("content", "")
                raw_tools = msg_data.get("tool_calls", [])

                tool_calls: List[ToolCall] = []
                for rt in raw_tools:
                    func = rt.get("function", {})
                    call_id = f"call_{uuid.uuid4().hex[:8]}"
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    tool_calls.append(
                        ToolCall(id=call_id, name=func.get("name", ""), arguments=args)
                    )

                # Fallback: check if content contains SEARCH/REPLACE blocks directly
                if not tool_calls and "<<<<<<< SEARCH" in content:
                    blocks = PatchEngine.parse_search_replace_blocks(content)
                    if blocks:
                        # Extract first mentioned file or default
                        tool_calls.append(
                            ToolCall(
                                id=f"call_{uuid.uuid4().hex[:8]}",
                                name="propose_edit",
                                arguments={
                                    "file_path": "",
                                    "search_replace_text": content,
                                },
                            )
                        )

                return ChatMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls if tool_calls else None,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return ChatMessage(
                        role="assistant",
                        content=(
                            f"Model '{self.config.llm_model}' was not found in Ollama.\n\n"
                            f"To fix this, either:\n"
                            f"1. Download it by running: `ollama pull {self.config.llm_model}`\n"
                            f"2. Or update `LLM_MODEL` in `.env` to a model you already have (e.g. `qwen2.5-coder:1.5b` or `llama3.2:3b`)."
                        ),
                    )
                return ChatMessage(
                    role="assistant",
                    content=f"Error connecting to local LLM ({self.config.llm_model} at {url}): {e}",
                )
            except Exception as e:
                return ChatMessage(
                    role="assistant",
                    content=f"Error connecting to local LLM ({self.config.llm_model} at {url}): {e}",
                )

        else:
            # OpenAI-compatible local endpoint (vLLM / LM Studio / llama.cpp)
            url = f"{self.config.openai_compatible_url.rstrip('/')}/chat/completions"
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": self.config.llm_model,
                "messages": self._format_messages_for_ollama(messages),
                "temperature": self.config.llm_temperature,
                "max_tokens": self.config.llm_max_tokens,
            }
            if tools:
                payload["tools"] = tools

            try:
                response = await self.client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                choice = data["choices"][0]["message"]
                content = choice.get("content", "")
                raw_tools = choice.get("tool_calls", [])

                tool_calls = []
                for rt in raw_tools:
                    func = rt.get("function", {})
                    args = json.loads(func.get("arguments", "{}"))
                    tool_calls.append(
                        ToolCall(id=rt.get("id", ""), name=func.get("name", ""), arguments=args)
                    )

                return ChatMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls if tool_calls else None,
                )
            except Exception as e:
                return ChatMessage(
                    role="assistant",
                    content=f"Error connecting to local OpenAI-compatible endpoint ({url}): {e}",
                )
