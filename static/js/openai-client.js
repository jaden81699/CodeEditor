let aiContext = {};

function getCSRFToken() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : "";
}

function getRespondUrl() {
  return document.querySelector('meta[name="ai-respond-url"]')?.content || "/ai/respond/";
}

export function supported() { return true; }

export async function initLLM({ onProgress } = {}) {
  onProgress?.({ progress: 1, text: "Ready" });
}

export async function getAIResponse(userInput, context = {}) {
  // context may include: attemptNo, questionId, mode, history (array of {role,text})
  const ctx = (context && typeof context === "object") ? context : {};
  const rawHistory = Array.isArray(ctx.history) ? ctx.history : [];

  const history = rawHistory
    .filter(m => m && typeof m === "object")
    .map(m => ({
      role: (String(m.role || "").toLowerCase() === "assistant") ? "assistant" : "user",
      text: String(m.text || "").slice(0, 4000),
    }))
    .filter(m => m.text.trim().length > 0)
    .slice(-4);

  const payload = {
    text: String(userInput || ""),
    attempt_no: ctx.attemptNo ?? aiContext.attemptNo ?? null,
    question_id: ctx.questionId ?? aiContext.questionId ?? null,
    mode: ctx.mode ?? aiContext.mode ?? null,
    history,
  };

  const r = await fetch(getRespondUrl(), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCSRFToken(),
    },
    body: JSON.stringify(payload),
  });

  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `Request failed (${r.status})`);
  return data.text || "";
}

export function setAIContext(next = {}) {
  if (next && typeof next === "object") {
    aiContext = { ...aiContext, ...next };
  }
}
export async function resetWebLLM() { location.reload(); }
