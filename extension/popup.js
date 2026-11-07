const API_URL = "http://localhost:8000";

const SUGGESTIONS = [
  "What services does the Indiana Department of Health provide?",
  "What health programs are available in Indiana?",
  "How do I report a public health concern in Indiana?",
  "What resources exist for maternal health in Indiana?",
];

const state = {
  messages: [],   // { role, content, sources? }
  followups: [],
};

// ── DOM refs ──────────────────────────────────────────────────────────────────
const messagesEl   = document.getElementById("messages");
const emptyStateEl = document.getElementById("empty-state");
const suggestionsEl = document.getElementById("suggestions");
const followupsBar = document.getElementById("followups-bar");
const followupChips = document.getElementById("followup-chips");
const inputEl      = document.getElementById("question-input");
const sendBtn      = document.getElementById("send-btn");
const clearBtn     = document.getElementById("clear-btn");
const statusBadge  = document.getElementById("status-badge");

// ── Status badge ─────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const res = await fetch(`${API_URL}/health`, { signal: AbortSignal.timeout(3000) });
    if (res.ok) setStatus("connected");
    else        setStatus("error");
  } catch {
    setStatus("error");
  }
}

function setStatus(s) {
  statusBadge.className = `badge badge--${s}`;
  statusBadge.textContent = s === "connected" ? "Connected"
                          : s === "error"     ? "API offline"
                                              : "Connecting…";
}

// ── Render helpers ────────────────────────────────────────────────────────────
function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function renderMessage(role, content, sources = []) {
  const wrap = document.createElement("div");
  wrap.className = `message message--${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = content;
  wrap.appendChild(bubble);

  if (sources.length) {
    const toggle = document.createElement("button");
    toggle.className = "sources-toggle";
    toggle.innerHTML = `
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <polyline points="9 18 15 12 9 6"/>
      </svg>
      Sources (${sources.length})`;

    const list = document.createElement("div");
    list.className = "sources-list";
    sources.forEach(s => {
      const a = document.createElement("a");
      a.href = s.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = s.title || s.url;
      list.appendChild(a);
    });

    toggle.addEventListener("click", () => {
      toggle.classList.toggle("open");
      list.classList.toggle("visible");
    });

    wrap.appendChild(toggle);
    wrap.appendChild(list);
  }

  messagesEl.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function addTypingIndicator() {
  const wrap = document.createElement("div");
  wrap.className = "message message--assistant";
  wrap.id = "typing";
  wrap.innerHTML = `<div class="typing-bubble"><span></span><span></span><span></span></div>`;
  messagesEl.appendChild(wrap);
  scrollToBottom();
}

function removeTypingIndicator() {
  document.getElementById("typing")?.remove();
}

function renderFollowups(questions) {
  followupChips.innerHTML = "";
  if (!questions.length) {
    followupsBar.classList.add("hidden");
    return;
  }
  questions.forEach(q => {
    const btn = document.createElement("button");
    btn.className = "followup-chip";
    btn.textContent = q;
    btn.addEventListener("click", () => submitQuestion(q));
    followupChips.appendChild(btn);
  });
  followupsBar.classList.remove("hidden");
}

function showEmptyState(visible) {
  emptyStateEl.style.display = visible ? "flex" : "none";
}

// ── Suggestions ───────────────────────────────────────────────────────────────
SUGGESTIONS.forEach(s => {
  const btn = document.createElement("button");
  btn.className = "suggestion-btn";
  btn.textContent = s;
  btn.addEventListener("click", () => submitQuestion(s));
  suggestionsEl.appendChild(btn);
});

// ── API calls ─────────────────────────────────────────────────────────────────
async function askApi(question) {
  const history = state.messages.map(m => ({ role: m.role, content: m.content }));
  const res = await fetch(`${API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

async function fetchFollowups(question, answer) {
  // Reuse the same OpenAI key via the backend — ask for follow-ups through a
  // lightweight endpoint. If the backend doesn't expose one we skip silently.
  try {
    const res = await fetch(`${API_URL}/followups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, answer }),
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.followups ?? [];
  } catch {
    return [];
  }
}

// ── Main submit flow ──────────────────────────────────────────────────────────
async function submitQuestion(question) {
  if (!question.trim()) return;

  // Clear follow-ups and empty state
  followupsBar.classList.add("hidden");
  showEmptyState(false);

  // User bubble
  state.messages.push({ role: "user", content: question });
  renderMessage("user", question);

  // Disable input while waiting
  inputEl.value = "";
  inputEl.style.height = "auto";
  sendBtn.disabled = true;

  addTypingIndicator();

  try {
    const result = await askApi(question);
    removeTypingIndicator();

    const reply   = result.answer;
    const sources = result.sources ?? [];

    state.messages.push({ role: "assistant", content: reply, sources });
    renderMessage("assistant", reply, sources);

    // Follow-ups via backend
    const followups = await fetchFollowups(question, reply);
    state.followups = followups;
    renderFollowups(followups);

  } catch (err) {
    removeTypingIndicator();
    const msg = err.message.includes("Failed to fetch")
      ? "Could not reach the API. Make sure your Docker stack is running (make up)."
      : err.message;
    renderMessage("assistant", msg);
  } finally {
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

// ── Input handlers ────────────────────────────────────────────────────────────
inputEl.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitQuestion(inputEl.value.trim());
  }
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 80) + "px";
});

sendBtn.addEventListener("click", () => submitQuestion(inputEl.value.trim()));

clearBtn.addEventListener("click", () => {
  state.messages = [];
  state.followups = [];
  messagesEl.innerHTML = "";
  messagesEl.appendChild(emptyStateEl);
  showEmptyState(true);
  followupsBar.classList.add("hidden");
  inputEl.value = "";
  inputEl.focus();
});

// ── Boot ──────────────────────────────────────────────────────────────────────
checkHealth();
setInterval(checkHealth, 30000);
inputEl.focus();
