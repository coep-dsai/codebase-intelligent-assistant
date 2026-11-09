# 🤝 Contributing to Codebase Intelligent Assistant

Thank you for contributing to Codebase Intelligent Assistant! This project is designed to be highly modular, strictly typed, and developer-friendly so any team member can easily build new features on top of the core architecture.

---

## 🛠️ Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/coep-dsai/codebase-intelligent-assistant.git
   cd codebase-intelligent-assistant
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux / macOS:
   source .venv/bin/activate
   ```

3. **Install the package in editable mode with development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

---

## 📏 Coding Standards & Best Practices

1. **No Sloppy Workarounds or Incomplete TODOs:** Every function and module must be fully implemented, tested, and documented.
2. **Strict Static Typing:** Always provide complete type annotations for all function parameters and return values.
3. **Defensive Error Handling:** Catch and handle system errors, model timeouts, syntax issues, and file system boundaries gracefully without crashing the agent.
4. **Unit Tests for Every Feature:** Every new component in `src/` must have a corresponding test file in `tests/test_<component>.py`.

---

## 🧩 How to Add a New Agent Tool

1. **Define the Tool Function Schema in `src/agent/prompts.py`:**
   Add your tool to `TOOL_DEFINITIONS`:
   ```python
   {
       "type": "function",
       "function": {
           "name": "my_new_tool",
           "description": "Explains what this tool does clearly to the local LLM.",
           "parameters": {
               "type": "object",
               "properties": {
                   "arg_name": {"type": "string", "description": "Parameter explanation."}
               },
               "required": ["arg_name"]
           }
       }
   }
   ```

2. **Implement Tool Execution in `src/agent/orchestrator.py`:**
   In `execute_tool()`:
   ```python
   elif name == "my_new_tool":
       val = args.get("arg_name")
       result_text = do_something(val)
       return ToolResult(call_id=tool_call.id, name=name, output=result_text)
   ```

3. **Add Automated Unit Tests in `tests/`:**
   Ensure your tool's behavior is verified with automated tests.

---

## 🌐 How to Add a New Programming Language

1. Install the corresponding pre-compiled Tree-sitter package:
   ```bash
   pip install tree-sitter-<language>
   ```
2. Register the module and file extensions in `src/indexing/ast_parser.py`:
   - Add module to `LANGUAGE_MODULES`: `"ruby": "tree_sitter_ruby"`
   - Add file extensions to `EXTENSION_TO_LANGUAGE`: `".rb": "ruby"`
3. Add a test case in `tests/test_ast_parser.py`.

---

## 🧪 Testing & Linting

Before pushing code or opening pull requests:

```bash
# Run the test suite
pytest

# Format and check code style with Ruff
ruff check src tests

# Verify static typing with MyPy
mypy src
```
