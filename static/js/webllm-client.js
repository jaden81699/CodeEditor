if (navigator.storage?.persist) navigator.storage.persist().catch(() => {
});

// Minimal WebLLM ES module wrapper (uses Llama-3.2-3B-Instruct-q4f32_1-MLC)
let engine = null;                 // holds the WebLLM engine instance after initialization
let inflight = null;               // tracks a currently-running generation Promise to serialize requests

// === Telemetry helpers ===
function getCSRFCookie() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
}

function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCSRFCookie() || "";
}

const TELEMETRY_URL =
    document.querySelector('meta[name="ai-telemetry-url"]')?.content || "/ai/telemetry/";

const TELEMETRY_ON = true; // flip to false to disable quickly

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

const DEFAULT_MODEL = "Llama-3.2-3B-Instruct-q4f32_1-MLC"; // default model id to load in the browser
const DEFAULT_GEN = {max_tokens: 1000, temperature: 0.2}; // default generation parameters for responses

export function supported() {
    // returns true if WebGPU is available (required by WebLLM); false otherwise
    return typeof navigator !== "undefined" && "gpu" in navigator;
}

export async function initLLM({modelId = "Llama-3.2-1B-Instruct-q4f32_1-MLC", onProgress} = {}) {
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

export async function askAI(messages, gen = {}) {
    // Ensure the engine is ready (lazy initialization)
    if (!engine) await initLLM();
    // Serialize calls: if another request is running, wait for it to finish
    if (inflight) await inflight;

    // --- NEW: capture context and user prompt length (no content) ---
    const ctx = (window.aiContext || {});
    const userMsg = [...(messages || [])].reverse().find(m => m.role === "user")?.content || "";
    postTelemetry("ai_prompt", {
        attempt_no: ctx.attemptNo ?? null,
        question_id: ctx.questionId ?? null,
        model_id: DEFAULT_MODEL,                 // or engine?.getModelId?.()
        prompt_chars: userMsg.length,
        client_ts: new Date().toISOString()
    });

    // Merge default generation settings with any overrides from the caller
    const params = {...DEFAULT_GEN, ...gen, messages};
    // Kick off a completion request; the API is OpenAI-like
    const task = engine.chat.completions.create(params);
    inflight = task; // remember the running Promise to block overlapping calls
    try {
        const res = await task; // wait for model output
        // Return the text of the first choice (standard OpenAI-style response)
        const text = res?.choices?.[0]?.message?.content ?? "";

        // --- NEW: log reply length (no content) ---
        postTelemetry("ai_reply", {
            attempt_no: ctx.attemptNo ?? null,
            question_id: ctx.questionId ?? null,
            model_id: DEFAULT_MODEL,
            reply_chars: (text || "").length,
            client_ts: new Date().toISOString()
        });

        return text;
    } catch (err) {
        // (Optional) log failures
        postTelemetry("ai_reply", {
            attempt_no: ctx.attemptNo ?? null,
            question_id: ctx.questionId ?? null,
            model_id: DEFAULT_MODEL,
            reply_chars: null,
            error: String(err && err.message || err),
            client_ts: new Date().toISOString()
        });
        throw err;
    } finally {
        inflight = null; // clear lock whether it succeeded or threw
    }
}

export function cancelAI() {
    // Try to interrupt the current generation if supported by this engine build
    if (engine && typeof engine.interruptGenerate === "function") {
        engine.interruptGenerate();
    }
}

export function unloadLLM() {
    // Drop references so the engine can be GC'd; (full reset usually needs a reload)
    engine = null;
    inflight = null;
}

async function deleteDB(name) {
    return new Promise(res => {
        const req = indexedDB.deleteDatabase(name);
        req.onblocked = req.onerror = req.onsuccess = () => res();
    });
}

async function resetWebLLM() {
    // WebLLM/MLC commonly use these DB names (safe to attempt deleting all):
    await deleteDB('webllm');
    await deleteDB('mlc-webgpu-cache');
    await deleteDB('mlc-webgpu-temp');

    // Optional: clear Cache Storage (if you’ve used it)
    if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.map(k => caches.delete(k)));
    }

    // Optional: any app-local flags
    localStorage.removeItem('webllm_app_config');

    location.reload(); // start a brand new download on next init
}

document.getElementById('reset-ai-cache')?.addEventListener('click', resetWebLLM);

document.addEventListener('DOMContentLoaded', () => {
    const compTab = document.getElementById('pills-compiler-tab');
    const aiTab = document.getElementById('pills-ai-tool-tab');

    function resetCompilerLayout() {
        const body = document.querySelector('#pills-compiler #compiler-card .card-body')
            || document.querySelector('#compiler-card .card-body')
            || document.querySelector('#pills-compiler .card .card-body');

        if (body) {
            // Clear any inline sizes that might have been set earlier
            ['height', 'maxHeight', 'minHeight', 'overflow'].forEach(p => body.style.removeProperty(p));
        }

        // Monaco needs a layout when its container becomes visible again
        requestAnimationFrame(() => {
            const editors = Object.values(window.editors || {});
            editors.forEach(ed => {
                try {
                    ed?.layout?.();
                } catch (_) {
                }
            });
        });
    }

    // When the compiler tab becomes visible
    compTab?.addEventListener('shown.bs.tab', resetCompilerLayout);

    // Also run once on first load if compiler starts active
    if (compTab?.classList.contains('active')) resetCompilerLayout();

    // Optional: only size the AI card (not every .card) when AI tab is shown
    function sizeAiCard() {
        const aiCard = document.getElementById('ai-card');
        if (!aiCard) return;
        const navH = document.querySelector('nav.navbar')?.offsetHeight || 0;
        const pad = 24;
        aiCard.style.maxHeight = Math.max(320, window.innerHeight - navH - pad) + 'px';
    }

    aiTab?.addEventListener('shown.bs.tab', sizeAiCard);
    window.addEventListener('resize', () => {
        if (aiTab?.classList.contains('active')) sizeAiCard();
    });
});

(function () {
    async function getAIResponse(userInput) {
        if (!window.webllm || !window.webllm.supported()) {
            return "This browser doesn't support WebGPU; please try an updated Chrome/Edge/Safari, or switch to the compiler hints.";
        }

        /*const anyEditor = Object.values(window.editors || {})[0];
        const code = anyEditor?.getValue?.() ?? "";
        const failing = window.lastFailingTests || "";*/

        const messages = [
            {
                role: "system",
                content:
                    "You are a teaching assistant. First list 1–3 likely root causes tied to the failing tests. " +
                    "Then propose a small patch (≤5 lines) with line refs. Do not output full solutions.",
            },
            {
                role: "user",
                content:
                    `Question:\n${userInput}`
            },
        ];

        return await window.webllm.askAI(messages, {max_tokens: 180, temperature: 0.2});
    }

    // expose to the page
    window.getAIResponse = getAIResponse;
})();
