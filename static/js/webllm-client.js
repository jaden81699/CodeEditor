// webllm-client.js
if (navigator.storage?.persist) navigator.storage.persist().catch(() => {
});

// ---------------- Telemetry helpers ----------------
function getCSRFCookie() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCSRFCookie() || "";
}

const TELEMETRY_URL = document.querySelector('meta[name="ai-telemetry-url"]')?.content || "/ai/telemetry/";
let TELEMETRY_ON = true;

async function postTelemetry(event, payload = {}) {
    if (!TELEMETRY_ON) return;
    try {
        const csrf = getCSRFToken();
        const resp = await fetch(TELEMETRY_URL, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                ...(csrf ? {"X-CSRFToken": csrf} : {})
            },
            body: JSON.stringify({event, ...payload})
        });
        if (!resp.ok) {
            const txt = await resp.text().catch(() => "");
            console.warn("[ai_telemetry] HTTP", resp.status, txt);
        }
    } catch (e) {
        console.error("[ai_telemetry] network error", e);
    }
}

// ---------------- WebLLM core ----------------
let engine = null;
let inflight = null;

const DEFAULT_MODEL = "Llama-3.2-1B-Instruct-q4f32_1-MLC";
const DEFAULT_GEN = {max_tokens: 1000, temperature: 0.2};

// shared app context (attempt/question)
let aiCtx = {attemptNo: null, questionId: null};

// Public helpers
export function supported() {
    return typeof navigator !== "undefined" && "gpu" in navigator;
}

export function setAIContext(next) {
    aiCtx = {...aiCtx, ...next};
}

export function getModelId() {
    return engine?.getModelId?.() || DEFAULT_MODEL;
}

export function setTelemetryEnabled(on) {
    TELEMETRY_ON = !!on;
}

export async function initLLM({modelId = DEFAULT_MODEL, onProgress} = {}) {
    if (engine) return engine;
    const {CreateMLCEngine} = await import("https://esm.run/@mlc-ai/web-llm");
    engine = await CreateMLCEngine(modelId, {
        initProgressCallback: (p) => {
            onProgress?.(p);
            document.dispatchEvent(new CustomEvent("webllm:progress", {detail: p}));
        },
    });
    return engine;
}

// ---- Main API you call from the page ----
export async function getAIResponse(userInput, gen = {}) {
    if (!supported()) {
        return "This browser doesn't support WebGPU; please try an updated Chrome/Edge/Safari, or switch to the compiler hints.";
    }
    if (!engine) await initLLM();
    if (inflight) await inflight;

    const messages = [
        {
            role: "system",
            content:
                "You are a teaching assistant. First list 1–3 likely root causes tied to the failing tests. " +
                "Then propose a small patch (≤5 lines) with line refs. Do not output full solutions.",
        },
        {role: "user", content: String(userInput)},
    ];

    // one id to correlate prompt/reply (optional but helpful for dedupe)
    const client_msg_id = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;

    // Telemetry (prompt) — send text so server can hash; it truncates to 4k anyway
    await postTelemetry("ai_prompt", {
        attempt_no: aiCtx.attemptNo ?? null,
        question_id: aiCtx.questionId ?? null,
        model_id: getModelId(),
        prompt: String(userInput).slice(0, 4000),
        client_ts: new Date().toISOString(),
        client_msg_id
    });

    const params = {...DEFAULT_GEN, ...gen, messages};
    const task = engine.chat.completions.create(params);
    inflight = task;

    try {
        const res = await task;
        const text = res?.choices?.[0]?.message?.content ?? "";

        await postTelemetry("ai_reply", {
            attempt_no: aiCtx.attemptNo ?? null,
            question_id: aiCtx.questionId ?? null,
            model_id: getModelId(),
            reply: text.slice(0, 4000),
            client_ts: new Date().toISOString(),
            client_msg_id
        });

        return text;
    } catch (err) {
        await postTelemetry("ai_reply", {
            attempt_no: aiCtx.attemptNo ?? null,
            question_id: aiCtx.questionId ?? null,
            model_id: getModelId(),
            error: String(err?.message || err),
            client_ts: new Date().toISOString(),
            client_msg_id
        });
        throw err;
    } finally {
        inflight = null;
    }
}

export function cancelAI() {
    if (engine && typeof engine.interruptGenerate === "function") engine.interruptGenerate();
}

export function unloadLLM() {
    engine = null;
    inflight = null;
}

// Cache reset (unchanged)
async function deleteDB(name) {
    return new Promise(res => {
        const req = indexedDB.deleteDatabase(name);
        req.onblocked = req.onerror = req.onsuccess = () => res();
    });
}

export async function resetWebLLM() {
    await deleteDB('webllm');
    await deleteDB('mlc-webgpu-cache');
    await deleteDB('mlc-webgpu-temp');
    if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
    }
    localStorage.removeItem('webllm_app_config');
    location.reload();
}
