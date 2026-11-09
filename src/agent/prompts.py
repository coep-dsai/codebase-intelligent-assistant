"""System prompts and tool schemas for the codebase assistant agent."""

from typing import Any, Dict, List

SYSTEM_PROMPT = """You are the Codebase Intelligent Assistant, an expert local AI software engineer and pair programmer.
You help developers understand, explore, optimize, implement, and refactor code inside their repository with full Git version control.

Key Operating Rules:
1. Ground your answers in the actual source code. Never hallucinate functions or file paths. Always use tools like `get_repo_map`, `search_code`, or `read_file` to inspect the code first.
2. When making modifications or proposing new features:
   - Always read the target file first to see the exact indentation and surrounding context.
   - Use the `propose_edit` tool with clear, exact SEARCH/REPLACE blocks.
   - Follow this format for each edit block:
     <<<<<<< SEARCH
     [exact lines to replace]
     =======
     [new replacement lines]
     >>>>>>> REPLACE
3. Ensure all proposed edits preserve syntax and adhere to existing code style and types.
4. When performing Git tasks, check `git_status` first, propose changes, and use `git_commit` with clean conventional commit messages.
5. Be concise and professional. After performing actions, summarize what was changed and suggest next steps or test commands.
"""

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_repo_map",
            "description": "Returns a compact, token-budgeted architectural outline of the repository showing key classes, functions, and files ranked by PageRank.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Performs hybrid RRF search (semantic vector + BM25 keyword search) over the repository codebase to find relevant code snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language or keyword query describing what you are searching for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of code snippets to return (default: 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads the text content of a file within the workspace. Supports reading full files or specific line slices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative file path from workspace root.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional starting line number (1-based).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional ending line number (inclusive).",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_edit",
            "description": "Proposes a code modification to a file using SEARCH/REPLACE blocks. Generates a unified diff for user review before writing to disk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Relative path of the file to modify.",
                    },
                    "search_replace_text": {
                        "type": "string",
                        "description": "One or more <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE blocks.",
                    },
                },
                "required": ["file_path", "search_replace_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Checks the Git status of the repository, returning current branch, modified, staged, and untracked files.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Returns the current git diff of working tree changes or staged changes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "staged": {
                        "type": "boolean",
                        "description": "Whether to view staged changes instead of unstaged changes.",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Optional file path to limit the diff to.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "Stages all modified/added files and creates a new Git commit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Conventional commit message (e.g., 'feat: add user auth endpoint').",
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_diagnostics",
            "description": "Runs tests or syntax checks in the repository workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Test command to execute, e.g., 'pytest tests/test_parser.py'.",
                    },
                },
                "required": ["command"],
            },
        },
    },
]
