"""Self-contained Web Studio & Pop-up Assistant Frontend."""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Codebase Intelligent Assistant</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    :root {
      --bg-primary: #0f1117;
      --bg-secondary: #161922;
      --bg-card: #1c202d;
      --border-color: #2a3042;
      --text-primary: #f0f3f8;
      --text-muted: #8b949e;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --font-mono: 'Consolas', 'Fira Code', monospace;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-primary);
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      user-select: none;
    }

    /* Draggable header for PyWebView */
    .app-header {
      background-color: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      -webkit-app-region: drag;
      cursor: move;
    }
    .pywebview-drag-region { -webkit-app-region: drag; }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 14px;
      color: #fff;
    }
    .brand i { color: var(--accent); }

    .header-badges {
      display: flex;
      align-items: center;
      gap: 8px;
      -webkit-app-region: no-drag;
    }
    .badge {
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 12px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 5px;
    }
    .badge.active { color: var(--success); border-color: rgba(16, 185, 129, 0.4); }

    /* Navigation tabs */
    .nav-tabs {
      display: flex;
      background: var(--bg-secondary);
      border-bottom: 1px solid var(--border-color);
      padding: 0 16px;
      gap: 6px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 8px 14px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
    }
    .tab-btn:hover { color: var(--text-primary); }
    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
    }

    /* Main container */
    .app-body {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      position: relative;
    }

    .tab-content {
      display: none;
      flex: 1;
      flex-direction: column;
      overflow: hidden;
      padding: 16px;
    }
    .tab-content.active { display: flex; }

    /* Chat Messages */
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding-bottom: 12px;
      user-select: text;
    }

    .message {
      display: flex;
      gap: 10px;
      max-width: 90%;
      line-height: 1.5;
      font-size: 13.5px;
    }
    .message.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }
    .message.assistant {
      align-self: flex-start;
    }
    .msg-avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      flex-shrink: 0;
    }
    .message.user .msg-avatar { background: var(--accent); color: #fff; }
    .message.assistant .msg-avatar { background: var(--bg-card); color: var(--accent); border: 1px solid var(--border-color); }

    .msg-bubble {
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      padding: 10px 14px;
      border-radius: 8px;
    }
    .message.user .msg-bubble {
      background: rgba(99, 102, 241, 0.15);
      border-color: rgba(99, 102, 241, 0.4);
    }

    /* Tool Call Pills & Diff Containers */
    .tool-pill {
      background: rgba(42, 48, 66, 0.6);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 6px 10px;
      font-size: 11.5px;
      font-family: var(--font-mono);
      color: var(--text-muted);
      margin: 6px 0;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .tool-pill i { color: var(--accent); }

    .diff-container {
      background: #08090d;
      border: 1px solid var(--border-color);
      border-radius: 6px;
      margin: 8px 0;
      font-family: var(--font-mono);
      font-size: 12px;
      overflow-x: auto;
    }
    .diff-header {
      background: var(--bg-secondary);
      padding: 6px 12px;
      font-weight: 600;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .diff-content {
      padding: 8px;
      white-space: pre;
      line-height: 1.4;
    }
    .diff-add { color: #4ade80; background: rgba(74, 222, 128, 0.1); }
    .diff-del { color: #f87171; background: rgba(248, 113, 113, 0.1); }

    .diff-actions {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    .btn-apply {
      background: var(--success);
      color: #fff;
      border: none;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .btn-reject {
      background: var(--danger);
      color: #fff;
      border: none;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }

    /* Input area */
    .input-bar {
      padding: 12px 16px;
      background: var(--bg-secondary);
      border-top: 1px solid var(--border-color);
      display: flex;
      gap: 10px;
    }
    .input-bar textarea {
      flex: 1;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px 12px;
      color: var(--text-primary);
      font-size: 13px;
      resize: none;
      height: 42px;
      outline: none;
      font-family: inherit;
    }
    .input-bar textarea:focus { border-color: var(--accent); }
    .send-btn {
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 6px;
      width: 44px;
      height: 42px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 15px;
      transition: background 0.2s;
    }
    .send-btn:hover { background: var(--accent-hover); }

    /* Repo map & Git views */
    .code-view {
      flex: 1;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 12px;
      overflow-y: auto;
      white-space: pre-wrap;
      user-select: text;
    }
  </style>
</head>
<body>
  <!-- Draggable Header -->
  <div class="app-header pywebview-drag-region">
    <div class="brand">
      <i class="fa-solid fa-bolt"></i>
      <span>Codebase Assistant</span>
    </div>
    <div class="header-badges">
      <div class="badge" id="modelBadge"><i class="fa-solid fa-microchip"></i> <span id="modelName">Local Model</span></div>
      <div class="badge active" id="gitBadge"><i class="fa-solid fa-code-branch"></i> <span id="branchName">main</span></div>
    </div>
  </div>

  <!-- Navigation -->
  <div class="nav-tabs">
    <button class="tab-btn active" onclick="switchTab('chatTab')"><i class="fa-regular fa-comments"></i> Chat</button>
    <button class="tab-btn" onclick="switchTab('mapTab')"><i class="fa-solid fa-sitemap"></i> Repo Map</button>
    <button class="tab-btn" onclick="switchTab('gitTab')"><i class="fa-solid fa-code-commit"></i> Git Studio</button>
  </div>

  <!-- Content -->
  <div class="app-body">
    <!-- Chat Tab -->
    <div class="tab-content active" id="chatTab">
      <div class="chat-messages" id="chatMessages">
        <div class="message assistant">
          <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
          <div class="msg-bubble">
            <strong>Welcome to your Codebase Assistant!</strong><br>
            I am running completely offline. Ask me to explain the repository, find functions, propose optimizations, or edit code and run git commands.
          </div>
        </div>
      </div>
      <div class="input-bar">
        <textarea id="promptInput" placeholder="Ask a question or request a code change..." onkeydown="handleKeyDown(event)"></textarea>
        <button class="send-btn" onclick="sendMessage()"><i class="fa-solid fa-paper-plane"></i></button>
      </div>
    </div>

    <!-- Repo Map Tab -->
    <div class="tab-content" id="mapTab">
      <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 13px; font-weight: 600; color: var(--text-muted);">AST PageRank Repository Map</span>
        <button class="btn-apply" onclick="refreshRepoMap()" style="padding: 4px 8px; font-size: 11px;"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>
      <div class="code-view" id="repoMapContent">Loading repository map...</div>
    </div>

    <!-- Git Tab -->
    <div class="tab-content" id="gitTab">
      <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 13px; font-weight: 600; color: var(--text-muted);">Repository Working Tree Status</span>
        <button class="btn-apply" onclick="refreshGitStatus()" style="padding: 4px 8px; font-size: 11px;"><i class="fa-solid fa-rotate"></i> Refresh</button>
      </div>
      <div class="code-view" id="gitStatusContent">Loading git status...</div>
    </div>
  </div>

  <script>
    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.currentTarget.classList.add('active');
      document.getElementById(tabId).classList.add('active');

      if (tabId === 'mapTab') refreshRepoMap();
      if (tabId === 'gitTab') refreshGitStatus();
    }

    function handleKeyDown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }

    async function sendMessage() {
      const input = document.getElementById('promptInput');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';

      const chat = document.getElementById('chatMessages');
      chat.innerHTML += `
        <div class="message user">
          <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
          <div class="msg-bubble">${escapeHtml(text)}</div>
        </div>
      `;
      chat.scrollTop = chat.scrollHeight;

      // Loading bubble
      const loadingId = 'loading_' + Date.now();
      chat.innerHTML += `
        <div class="message assistant" id="${loadingId}">
          <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
          <div class="msg-bubble"><i class="fa-solid fa-spinner fa-spin"></i> Reasoning...</div>
        </div>
      `;
      chat.scrollTop = chat.scrollHeight;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: text })
        });
        const data = await res.json();
        const loadElem = document.getElementById(loadingId);
        if (loadElem) loadElem.remove();

        let toolPills = '';
        if (data.tools_executed) {
          data.tools_executed.forEach(t => {
            toolPills += `<div class="tool-pill"><i class="fa-solid fa-wrench"></i> Used tool: <strong>${t}</strong></div>`;
          });
        }

        let patchHtml = '';
        if (data.pending_patch) {
          patchHtml = `
            <div class="diff-container">
              <div class="diff-header">
                <span>Proposed Change: ${data.pending_patch.file_path}</span>
                <span class="badge" style="color: var(--warning)">Awaiting Confirmation</span>
              </div>
              <div class="diff-content">${formatDiff(data.pending_patch.diff)}</div>
            </div>
            <div class="diff-actions">
              <button class="btn-apply" onclick="confirmPatch('${data.pending_patch.patch_id}')"><i class="fa-solid fa-check"></i> Approve & Apply</button>
              <button class="btn-reject" onclick="rejectPatch('${data.pending_patch.patch_id}')"><i class="fa-solid fa-xmark"></i> Reject</button>
            </div>
          `;
        }

        chat.innerHTML += `
          <div class="message assistant">
            <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-bubble">
              ${toolPills}
              <div>${escapeHtml(data.response)}</div>
              ${patchHtml}
            </div>
          </div>
        `;
        chat.scrollTop = chat.scrollHeight;
      } catch (err) {
        document.getElementById(loadingId).remove();
        chat.innerHTML += `
          <div class="message assistant">
            <div class="msg-avatar"><i class="fa-solid fa-triangle-exclamation" style="color: var(--danger)"></i></div>
            <div class="msg-bubble" style="color: var(--danger)">Error: ${err.message}</div>
          </div>
        `;
      }
    }

    async function confirmPatch(patchId) {
      const res = await fetch(`/api/patches/${patchId}/confirm`, { method: 'POST' });
      const data = await res.json();
      alert(data.message || 'Patch applied successfully!');
    }

    async function rejectPatch(patchId) {
      const res = await fetch(`/api/patches/${patchId}/reject`, { method: 'POST' });
      const data = await res.json();
      alert('Patch rejected.');
    }

    async function refreshRepoMap() {
      const elem = document.getElementById('repoMapContent');
      elem.textContent = 'Generating PageRank outline...';
      const res = await fetch('/api/repo-map');
      const data = await res.json();
      elem.textContent = data.repo_map || 'No map available.';
    }

    async function refreshGitStatus() {
      const elem = document.getElementById('gitStatusContent');
      elem.textContent = 'Checking git status...';
      const res = await fetch('/api/git/status');
      const data = await res.json();
      elem.textContent = JSON.stringify(data, null, 2);
    }

    function formatDiff(diffText) {
      if (!diffText) return '';
      return diffText.split('\\n').map(line => {
        if (line.startsWith('+')) return `<span class="diff-add">${escapeHtml(line)}</span>`;
        if (line.startsWith('-')) return `<span class="diff-del">${escapeHtml(line)}</span>`;
        return escapeHtml(line);
      }).join('\\n');
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    // Load initial health
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        document.getElementById('modelName').textContent = data.model || 'Local Model';
        document.getElementById('branchName').textContent = data.git_branch || 'main';
      });
  </script>
</body>
</html>
"""
