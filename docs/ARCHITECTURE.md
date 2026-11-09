# 🏛️ Architecture & Technical Specification

This document details the internal design, mathematical formulations, and engineering decisions behind the **Codebase Intelligent Assistant**.

---

## 1. Code Intelligence: AST Parsing & Tag Extraction

Rather than treating code as raw text or slicing tokens arbitrarily across boundaries, our engine uses **Tree-sitter** concrete syntax tree (CST) grammars (`src/indexing/ast_parser.py`).

### Extracted Metadata
For every supported source file, the parser extracts:
- **Definitions (`def`):** Function declarations, method definitions, classes, interfaces, structs.
- **Signatures:** Parameter lists, return types, and docstrings.
- **References (`ref`):** Call sites and identifier references.

---

## 2. Personalized PageRank Repository Map

Large codebases exceed local LLM context budgets if fed naively. We implement a graph-based token budgeting system (`src/indexing/repo_map.py`) inspired by PageRank:

1. **Bipartite Relationship Graph:**
   - **Nodes:** Codebase source files $F = \{f_1, f_2, \dots, f_n\}$ and symbols $S = \{s_1, s_2, \dots, s_m\}$.
   - **Edges:** A directed edge exists from file $f_i$ to $f_j$ if file $f_i$ references a symbol defined in $f_j$.

2. **Power Iteration with Personalization Vector:**
   For a damping factor $\alpha = 0.85$ and personalization vector $\mathbf{p}$:
   $$\mathbf{r}^{(t+1)} = \alpha \left( \mathbf{A} \mathbf{r}^{(t)} + \frac{\sum_{i \in \text{dangling}} r_i^{(t)}}{N} \mathbf{1} \right) + (1 - \alpha) \mathbf{p}$$
   - When the user is actively working on a set of files $A \subset F$, $\mathbf{p}$ is biased toward those active files:
     $$p_i = \begin{cases} \frac{1}{|A|} & \text{if } f_i \in A \\ 0 & \text{otherwise} \end{cases}$$
   - This prioritizes structurally dependent and tightly-coupled files for the LLM.

3. **Hierarchical Token Budget Packing:**
   High-ranking files and their high-priority definitions are formatted into a clean outline until the target token limit is reached.

---

## 3. Hybrid Retrieval: BM25 + Dense Vectors + RRF

To maximize search accuracy across both conceptual questions ("Where is user authentication handled?") and precise identifiers (`get_user_by_id`), we combine lexical and semantic retrievers:

### BM25Okapi Lexical Search (`src/retrieval/bm25_search.py`)
- Code-aware tokenizer splits `snake_case`, `camelCase`, and dot-separated identifiers.
- Scores frequency and inverse document frequency of identifiers.

### FastEmbed Dense Vector Search (`src/retrieval/vector_search.py`)
- Uses `BAAI/bge-small-en-v1.5` running locally via ONNX Runtime on the CPU.
- Preserves 100% of GPU VRAM for the local LLM.
- Persisted in ChromaDB with cosine distance metric.

### Reciprocal Rank Fusion (RRF) (`src/retrieval/hybrid_search.py`)
Combines ranking from both retrievers without requiring fragile score normalization:
$$RRF(d) = \sum_{m \in \{dense, bm25\}} \frac{w_m}{k + r_m(d)}$$
where $k = 60$ and $r_m(d)$ is the 1-based rank of document $d$ in retriever $m$.

---

## 4. Industrial-Grade Patch Engine (`src/editor/patch_engine.py`)

Local coding models (e.g. Qwen 2.5 Coder 7B/14B) excel at structured block edits. Our patch engine provides three layers of resilience:

1. **Exact Block Matching:** Matches exact lines inside `<<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE`.
2. **Whitespace-Tolerant Fuzzy Matching:** If leading spaces or indentation tabs vary slightly, performs normalized line-slice matching to find the exact anchor in the source file.
3. **Pre-Flight Syntax Validation:** Runs `ast.parse` (or language equivalent) on the patched content before touching disk. If a patch introduces a syntax error, it is rejected automatically and the model is prompted with the syntax error.
4. **Atomic Writes & Safe Backups:** Uses temporary files with atomic OS replacement (`Path.replace`) and writes backups to `.codebase_agent/backups/`.

---

## 5. Incremental Delta Indexing (`src/indexing/delta_indexer.py`)

Re-indexing an entire repository on every change is inefficient. Our delta indexer:
- Computes SHA-256 hashes of file contents stored in `.codebase_agent/metadata_cache.db` (SQLite).
- On each scan, detects added, modified, and deleted files in milliseconds.
- Only parses and embeds files whose content hash changed.

---

## 6. Floating Pop-up & Web Studio Architecture

- **Backend:** FastAPI with ASGI async request handling and Server-Sent Events (SSE).
- **Desktop Window:** Native floating overlay built with `pywebview` on Windows with `on_top=True`, draggable headers (`.pywebview-drag-region`), and responsive dark-mode styling.
- **Web App:** Embedded single-page application at `/` featuring interactive chat, side-by-side unified diff review, and Git status dashboard.
