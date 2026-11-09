"""FastAPI application providing REST endpoints and serving the Web Studio & Pop-up UI."""

from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.agent.orchestrator import AgentOrchestrator
from src.agent.state import AgentState, ChatMessage
from src.analysis.call_graph import CallGraphAnalyzer
from src.config import settings
from src.server.web_ui import INDEX_HTML

app = FastAPI(
    title="Codebase Intelligent Assistant",
    description="Offline, private, local agent for codebase exploration and editing",
    version="0.1.0",
)

# Enable CORS for local cross-origin development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Runtime lazy singletons
_orchestrator: Optional[AgentOrchestrator] = None
_active_state: Optional[AgentState] = None
_call_graph_analyzer: Optional[CallGraphAnalyzer] = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


def get_active_state() -> AgentState:
    global _active_state
    if _active_state is None:
        _active_state = AgentState()
    return _active_state


def get_call_graph_analyzer() -> CallGraphAnalyzer:
    global _call_graph_analyzer
    if _call_graph_analyzer is None:
        _call_graph_analyzer = CallGraphAnalyzer(settings.workspace_dir)
    return _call_graph_analyzer


class ChatRequest(BaseModel):
    prompt: str


class CommitRequest(BaseModel):
    message: str


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> str:
    """Serves the Web Studio and Pop-up user interface."""
    return INDEX_HTML


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """Returns runtime health status and configuration info."""
    orc = get_orchestrator()
    git_branch = orc.git.get_current_branch()
    return {
        "status": "healthy",
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "workspace": str(settings.workspace_dir),
        "git_branch": git_branch,
    }


@app.post("/api/chat")
async def chat_interaction(req: ChatRequest) -> Dict[str, Any]:
    """Executes a multi-step agent reasoning interaction."""
    orc = get_orchestrator()
    state = get_active_state()

    user_msg = ChatMessage(role="user", content=req.prompt)
    state.messages.append(user_msg)

    # Step the agent
    response = await orc.step(state)

    # Gather any executed tool names in this turn
    tools_executed: List[str] = []
    if response.tool_calls:
        tools_executed = [tc.name for tc in response.tool_calls]

    # Check for pending patch
    pending_patch = None
    if state.pending_patches:
        # Get the latest pending patch
        latest_id = list(state.pending_patches.keys())[-1]
        p = state.pending_patches[latest_id]
        pending_patch = {
            "patch_id": p.patch_id,
            "file_path": p.file_path,
            "diff": p.diff,
        }

    return {
        "response": response.content,
        "tools_executed": tools_executed,
        "pending_patch": pending_patch,
        "is_complete": state.is_complete,
    }


@app.get("/api/repo-map")
async def get_repo_map() -> Dict[str, Any]:
    """Generates and returns the latest PageRank repository outline."""
    orc = get_orchestrator()
    state = get_active_state()
    repo_map = orc.repo_map_gen.generate_map(active_files=state.active_files)
    return {"repo_map": repo_map}


@app.get("/api/git/status")
async def get_git_status() -> Dict[str, Any]:
    """Returns current git status."""
    orc = get_orchestrator()
    status = orc.git.get_status()
    return {
        "branch": status.current_branch,
        "is_clean": status.is_clean,
        "modified": status.modified,
        "staged": status.staged,
        "untracked": status.untracked,
        "deleted": status.deleted,
    }


@app.get("/api/git/diff")
async def get_git_diff(staged: bool = False, file_path: Optional[str] = None) -> Dict[str, Any]:
    """Returns git diff."""
    orc = get_orchestrator()
    diff = orc.git.get_diff(staged=staged, file_path=file_path)
    return {"diff": diff}


@app.post("/api/git/commit")
async def create_git_commit(req: CommitRequest) -> Dict[str, Any]:
    """Stages changes and creates a git commit."""
    orc = get_orchestrator()
    status = orc.git.get_status()
    to_stage = status.modified + status.untracked
    if to_stage:
        orc.git.stage_files(to_stage)
    out = orc.git.commit(req.message)
    return {"output": out}


@app.get("/api/graph")
async def get_call_graph() -> Dict[str, Any]:
    """Extracts and returns the symbol call graph."""
    analyzer = get_call_graph_analyzer()
    graph_data = analyzer.build_graph()
    return {
        "nodes": graph_data.nodes,
        "edges": graph_data.edges,
    }


@app.post("/api/patches/{patch_id}/confirm")
async def confirm_patch(patch_id: str) -> Dict[str, Any]:
    """Confirms and writes a pending patch to disk."""
    orc = get_orchestrator()
    state = get_active_state()
    success = orc.apply_pending_patch(state, patch_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to apply patch or patch ID not found.")
    return {"status": "applied", "message": f"Patch {patch_id} successfully written to disk."}


@app.post("/api/patches/{patch_id}/reject")
async def reject_patch(patch_id: str) -> Dict[str, Any]:
    """Rejects and discards a pending patch."""
    state = get_active_state()
    if patch_id in state.pending_patches:
        del state.pending_patches[patch_id]
        return {"status": "rejected", "message": f"Patch {patch_id} was discarded."}
    raise HTTPException(status_code=404, detail="Patch ID not found.")
