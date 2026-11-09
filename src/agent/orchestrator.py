"""Autonomous Agent Orchestrator managing multi-step ReAct loop and tool execution."""

import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.agent.llm_client import LLMClient
from src.agent.prompts import TOOL_DEFINITIONS
from src.agent.state import AgentState, ChatMessage, PendingPatch, ToolCall, ToolResult
from src.config import Settings, settings
from src.editor.file_manager import FileManager
from src.editor.patch_engine import PatchBlock, PatchEngine
from src.git_manager.git_ops import GitManager
from src.indexing.repo_map import RepoMapGenerator
from src.retrieval.bm25_search import BM25Retriever
from src.retrieval.hybrid_search import HybridRetriever
from src.retrieval.vector_search import VectorRetriever


class AgentOrchestrator:
    """Coordinates local LLM reasoning, code search, editing, git tools, and diff confirmation."""

    def __init__(self, workspace_dir: Optional[Path | str] = None, config: Optional[Settings] = None) -> None:
        self.config = config or settings
        self.workspace_dir = Path(workspace_dir or self.config.workspace_dir).resolve()

        self.llm = LLMClient(config=self.config)
        self.file_manager = FileManager(self.workspace_dir)
        self.git = GitManager(self.workspace_dir)
        self.repo_map_gen = RepoMapGenerator(self.workspace_dir)

        # Retrieval components (lazy loaded)
        self.bm25 = BM25Retriever()
        self._vector: Optional[VectorRetriever] = None
        self._hybrid: Optional[HybridRetriever] = None

    @property
    def vector(self) -> VectorRetriever:
        """Lazy-loaded VectorRetriever."""
        if self._vector is None:
            self._vector = VectorRetriever(self.config.chroma_db_dir, model_name=self.config.embedding_model)
        return self._vector

    @property
    def hybrid(self) -> HybridRetriever:
        """Lazy-loaded HybridRetriever."""
        if self._hybrid is None:
            self._hybrid = HybridRetriever(self.bm25, self.vector)
        return self._hybrid

    async def execute_tool(self, tool_call: ToolCall, state: AgentState) -> ToolResult:
        """Executes a single tool requested by the agent."""
        name = tool_call.name
        args = tool_call.arguments

        try:
            if name == "get_repo_map":
                out = self.repo_map_gen.generate_map(active_files=state.active_files)
                return ToolResult(call_id=tool_call.id, name=name, output=out)

            elif name == "search_code":
                query = args.get("query", "")
                top_k = int(args.get("top_k", 5))
                results = self.hybrid.search(query, top_k=top_k)
                if not results:
                    # Fallback to BM25 search
                    results = self.bm25.search(query, top_k=top_k)
                if not results:
                    return ToolResult(
                        call_id=tool_call.id,
                        name=name,
                        output=f"No matching code snippets found for query '{query}'.",
                    )
                formatted = []
                for r in results:
                    formatted.append(
                        f"--- {r.file_path}:{r.start_line}-{r.end_line} ({r.symbol_name}) ---\n{r.content}"
                    )
                return ToolResult(call_id=tool_call.id, name=name, output="\n\n".join(formatted))

            elif name == "read_file":
                rel_path = args.get("file_path", "")
                content = self.file_manager.read_file(rel_path)
                lines = content.splitlines()

                start = args.get("start_line")
                end = args.get("end_line")

                if start is not None or end is not None:
                    s_idx = max(0, (start or 1) - 1)
                    e_idx = end if end else len(lines)
                    sliced = lines[s_idx:e_idx]
                    numbered = [f"{s_idx + i + 1:4d} | {line}" for i, line in enumerate(sliced)]
                    output = "\n".join(numbered)
                else:
                    numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(lines)]
                    output = "\n".join(numbered)

                if rel_path not in state.active_files:
                    state.active_files.append(rel_path)

                return ToolResult(call_id=tool_call.id, name=name, output=output)

            elif name == "propose_edit":
                rel_path = args.get("file_path", "")
                patch_text = args.get("search_replace_text", "")
                blocks = PatchEngine.parse_search_replace_blocks(patch_text)

                if not blocks:
                    return ToolResult(
                        call_id=tool_call.id,
                        name=name,
                        output="Error: No valid <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE blocks found.",
                        is_error=True,
                    )

                original_content = self.file_manager.read_file(rel_path)
                patch_res = PatchEngine.apply_search_replace_blocks(
                    original_content, blocks, file_path=rel_path
                )

                if not patch_res.success:
                    return ToolResult(
                        call_id=tool_call.id,
                        name=name,
                        output=f"Patch failed: {patch_res.error_message}",
                        is_error=True,
                    )

                patch_id = f"patch_{uuid.uuid4().hex[:6]}"
                pending = PendingPatch(
                    patch_id=patch_id,
                    file_path=rel_path,
                    diff=patch_res.diff,
                    proposed_content=patch_res.diff,  # Will hold target content
                    original_content=original_content,
                )
                state.pending_patches[patch_id] = pending

                if not self.config.require_diff_confirmation:
                    # Apply directly
                    # Recompute target content
                    matched, modified_content = True, original_content
                    for b in blocks:
                        modified_content = modified_content.replace(b.search_block, b.replace_block, 1)
                    self.file_manager.write_file(rel_path, modified_content)
                    return ToolResult(
                        call_id=tool_call.id,
                        name=name,
                        output=f"Edit successfully applied to {rel_path}!\nUnified Diff:\n{patch_res.diff}",
                    )
                else:
                    return ToolResult(
                        call_id=tool_call.id,
                        name=name,
                        output=(
                            f"Proposed edit for '{rel_path}' generated [ID: {patch_id}]. "
                            f"Unified Diff generated. Awaiting user confirmation before modifying disk:\n\n{patch_res.diff}"
                        ),
                    )

            elif name == "git_status":
                status = self.git.get_status()
                out = (
                    f"Branch: {status.current_branch}\n"
                    f"Clean: {status.is_clean}\n"
                    f"Modified: {', '.join(status.modified) or 'None'}\n"
                    f"Staged: {', '.join(status.staged) or 'None'}\n"
                    f"Untracked: {', '.join(status.untracked) or 'None'}"
                )
                return ToolResult(call_id=tool_call.id, name=name, output=out)

            elif name == "git_diff":
                staged = bool(args.get("staged", False))
                file_path = args.get("file_path")
                diff = self.git.get_diff(staged=staged, file_path=file_path)
                return ToolResult(
                    call_id=tool_call.id,
                    name=name,
                    output=diff if diff else "No git changes detected.",
                )

            elif name == "git_commit":
                msg = args.get("message", "update: agent changes")
                status = self.git.get_status()
                to_stage = status.modified + status.untracked
                if to_stage:
                    self.git.stage_files(to_stage)
                commit_out = self.git.commit(msg)
                return ToolResult(call_id=tool_call.id, name=name, output=commit_out)

            elif name == "run_diagnostics":
                cmd = args.get("command", "pytest")
                res = subprocess.run(
                    cmd,
                    cwd=str(self.workspace_dir),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8",
                    errors="replace",
                )
                out = res.stdout if res.stdout else res.stderr
                return ToolResult(call_id=tool_call.id, name=name, output=out[:2000])

            else:
                return ToolResult(
                    call_id=tool_call.id,
                    name=name,
                    output=f"Unknown tool: {name}",
                    is_error=True,
                )

        except Exception as e:
            return ToolResult(
                call_id=tool_call.id,
                name=name,
                output=f"Tool execution failed: {e}",
                is_error=True,
            )

    async def step(self, state: AgentState) -> ChatMessage:
        """Executes a single reasoning step: calls LLM and processes tool invocations."""
        response = await self.llm.chat_completion(state.messages, tools=TOOL_DEFINITIONS)
        state.messages.append(response)
        state.iteration_count += 1

        if not response.tool_calls:
            state.is_complete = True
            return response

        # Execute tools
        for tc in response.tool_calls:
            res = await self.execute_tool(tc, state)
            state.messages.append(
                ChatMessage(
                    role="tool",
                    content=res.output,
                    tool_call_id=tc.id,
                )
            )

        if state.iteration_count >= state.max_iterations:
            state.is_complete = True

        return response

    def apply_pending_patch(self, state: AgentState, patch_id: str) -> bool:
        """Applies a confirmed pending patch to disk."""
        pending = state.pending_patches.get(patch_id)
        if not pending:
            return False

        # Apply using patch engine search/replace blocks or diff
        blocks = PatchEngine.parse_search_replace_blocks(pending.diff)
        current = self.file_manager.read_file(pending.file_path)

        res = PatchEngine.apply_search_replace_blocks(current, blocks, pending.file_path)
        if res.success:
            # Reconstruct modified
            mod = current
            for b in blocks:
                mod = mod.replace(b.search_block, b.replace_block, 1)
            self.file_manager.write_file(pending.file_path, mod)
            del state.pending_patches[patch_id]
            return True
        return False
