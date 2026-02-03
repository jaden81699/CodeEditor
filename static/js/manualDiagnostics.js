// manualDiagnostics.9plus.js
//
// Lightweight, heuristic diagnostics for Monaco without a Java parser.
//
// Goals:
// - Catch *real* bracket/brace/paren mismatches (ignoring strings/comments).
// - Provide low-noise "possible missing semicolon" warnings.
// - Be fast enough to run on each change via debouncing.
// - Never crash if Monaco isn't ready yet.
//
// Usage:
//   1) Load this file after Monaco loader (can be before Monaco is ready).
//   2) After editors are created: window.initManualDiagnostics(window.editors);
//
// Notes:
// - This is NOT a Java compiler. Diagnostics are heuristic.
// - Unmatched delimiter errors are high confidence.
// - Semicolon warnings are low confidence; we avoid common false positives.

(function () {
  "use strict";

  console.log("manualDiagnostics.9plus.js loaded");

  const OWNER = "manualDiagnostics";
  const DEFAULT_DEBOUNCE_MS = 180;

  // --------------------------
  // Utilities
  // --------------------------

  function safeMonaco() {
    return typeof window !== "undefined" && window.monaco ? window.monaco : null;
  }

  function clampColumn(lineText, col) {
    // Monaco columns are 1-based; allow placing at end+1.
    const max = (lineText ? lineText.length : 0) + 1;
    if (col < 1) return 1;
    if (col > max) return max;
    return col;
  }

  function makeMarker(line, col, message, severity, lineText) {
    const c1 = clampColumn(lineText || "", col);
    return {
      startLineNumber: line,
      startColumn: c1,
      endLineNumber: line,
      endColumn: clampColumn(lineText || "", c1 + 1),
      message,
      severity,
    };
  }

  function debounce(fn, wait) {
    let t = null;
    return function (...args) {
      if (t) clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  // --------------------------
  // Core scan: delimiter matching, plus per-line metadata
  // --------------------------

  /**
   * Scan code once, char-by-char, tracking strings/comments to avoid false delimiter errors.
   * Returns:
   *   - markers (unmatched delimiters, unterminated comment/string/char)
   *   - lineInfo: for each line:
   *       - lineText
   *       - firstMeaningfulCol
   *       - firstMeaningfulChar
   *       - lastMeaningfulCol
   *       - lastMeaningfulChar
   *       - hasMeaningfulCode
   */
  function analyze(code) {
    const m = safeMonaco();
    const Severity = m ? m.MarkerSeverity : null;

    const markers = [];
    const lines = code.split("\n");
    const lineInfo = lines.map((t) => ({
      lineText: t,
      firstMeaningfulCol: null,
      firstMeaningfulChar: null,
      lastMeaningfulCol: null,
      lastMeaningfulChar: null,
      hasMeaningfulCode: false,
    }));

    // stacks store { line, col }
    const parenStack = [];
    const braceStack = [];
    const bracketStack = [];

    let inLineComment = false;
    let inBlockComment = false;
    let inString = false; // "
    let inChar = false;   // '
    let escape = false;

    // Where did we enter a multi-line construct?
    let blockCommentStart = null;
    let stringStart = null;
    let charStart = null;

    let line = 1;
    let col = 0;

    // helper to note meaningful chars per line outside strings/comments
    function noteMeaningful(ch, lineNo, colNo) {
      const info = lineInfo[lineNo - 1];
      if (!info) return;
      if (ch && ch.trim() !== "") {
        if (info.firstMeaningfulCol == null) {
          info.firstMeaningfulCol = colNo;
          info.firstMeaningfulChar = ch;
        }
        info.lastMeaningfulCol = colNo;
        info.lastMeaningfulChar = ch;
        info.hasMeaningfulCode = true;
      }
    }

    for (let i = 0; i < code.length; i++) {
      const ch = code[i];
      const next = i + 1 < code.length ? code[i + 1] : "";

      if (ch === "\n") {
        inLineComment = false;
        line += 1;
        col = 0;
        escape = false;
        continue;
      }
      col += 1;

      // Inside line comment: ignore everything until newline
      if (inLineComment) continue;

      // Inside block comment: look for end
      if (inBlockComment) {
        if (ch === "*" && next === "/") {
          inBlockComment = false;
          i += 1; // consume '/'
          col += 1;
        }
        continue;
      }

      // Inside string literal
      if (inString) {
        if (escape) {
          escape = false;
          continue;
        }
        if (ch === "\\") {
          escape = true;
          continue;
        }
        if (ch === "\"") {
          inString = false;
        }
        continue;
      }

      // Inside char literal
      if (inChar) {
        if (escape) {
          escape = false;
          continue;
        }
        if (ch === "\\") {
          escape = true;
          continue;
        }
        if (ch === "'") {
          inChar = false;
        }
        continue;
      }

      // Normal mode: detect start of comments/strings/chars first
      if (ch === "/" && next === "/") {
        inLineComment = true;
        i += 1;
        col += 1;
        continue;
      }
      if (ch === "/" && next === "*") {
        inBlockComment = true;
        blockCommentStart = { line, col };
        i += 1;
        col += 1;
        continue;
      }
      if (ch === "\"") {
        inString = true;
        stringStart = { line, col };
        continue;
      }
      if (ch === "'") {
        inChar = true;
        charStart = { line, col };
        continue;
      }

      // Record meaningful chars outside strings/comments
      noteMeaningful(ch, line, col);

      // Delimiter matching
      switch (ch) {
        case "(":
          parenStack.push({ line, col });
          break;
        case ")":
          if (parenStack.length) parenStack.pop();
          else if (Severity) markers.push(makeMarker(line, col, "Unmatched closing parenthesis ')'.", Severity.Error, lineInfo[line - 1].lineText));
          break;
        case "{":
          braceStack.push({ line, col });
          break;
        case "}":
          if (braceStack.length) braceStack.pop();
          else if (Severity) markers.push(makeMarker(line, col, "Unmatched closing brace '}'.", Severity.Error, lineInfo[line - 1].lineText));
          break;
        case "[":
          bracketStack.push({ line, col });
          break;
        case "]":
          if (bracketStack.length) bracketStack.pop();
          else if (Severity) markers.push(makeMarker(line, col, "Unmatched closing bracket ']'.", Severity.Error, lineInfo[line - 1].lineText));
          break;
      }
    }

    // Unmatched openings
    if (Severity) {
      for (const pos of parenStack) markers.push(makeMarker(pos.line, pos.col, "Unmatched opening parenthesis '('.", Severity.Error, lineInfo[pos.line - 1].lineText));
      for (const pos of braceStack) markers.push(makeMarker(pos.line, pos.col, "Unmatched opening brace '{'.", Severity.Error, lineInfo[pos.line - 1].lineText));
      for (const pos of bracketStack) markers.push(makeMarker(pos.line, pos.col, "Unmatched opening bracket '['.", Severity.Error, lineInfo[pos.line - 1].lineText));

      // Unterminated comment/string/char (lower confidence than delimiter mismatch)
      if (inBlockComment && blockCommentStart) {
        markers.push(makeMarker(blockCommentStart.line, blockCommentStart.col, "Unterminated block comment (missing '*/').", Severity.Warning, lineInfo[blockCommentStart.line - 1].lineText));
      }
      if (inString && stringStart) {
        markers.push(makeMarker(stringStart.line, stringStart.col, "Unterminated string literal (missing closing \").", Severity.Warning, lineInfo[stringStart.line - 1].lineText));
      }
      if (inChar && charStart) {
        markers.push(makeMarker(charStart.line, charStart.col, "Unterminated character literal (missing closing ').", Severity.Warning, lineInfo[charStart.line - 1].lineText));
      }
    }

    return { markers, lineInfo };
  }

  // --------------------------
  // Semicolon heuristic (low confidence)
  // --------------------------

  function shouldCheckSemicolon(trimmed) {
    if (!trimmed) return false;
    if (trimmed.startsWith("//")) return false;
    if (trimmed.startsWith("*")) return false;
    if (trimmed.startsWith("/*")) return false;

    // Top-level declarations / directives
    if (/^(package|import)\b/.test(trimmed)) return false;

    // Type declarations
    if (/^(class|interface|enum|record)\b/.test(trimmed)) return false;

    // Annotations
    if (/^@\w+/.test(trimmed)) return false;

    // Control statements that do not require ';' on the same line
    if (/^(if|for|while|switch|else|do|try|catch|finally|synchronized)\b/.test(trimmed)) return false;

    // Method / constructor headers often end with ')' and are followed by '{' on same or next line.
    // We'll handle the "next line starts with '{'" case later.
    return true;
  }

  // A line that ends in one of these is very likely part of a continued expression.
  const NON_TERMINAL_TAIL = new Set([
    ",", ".", "+", "-", "*", "/", "%", "&", "|", "^", "!", "?", "=", "<", ">", "(", "[",
  ]);

  function addSemicolonWarnings(markers, lineInfo) {
    const m = safeMonaco();
    if (!m) return;
    const Severity = m.MarkerSeverity;

    for (let i = 0; i < lineInfo.length; i++) {
      const info = lineInfo[i];
      const lineNo = i + 1;
      const text = info.lineText || "";
      const trimmed = text.trim();

      if (!info.hasMeaningfulCode) continue;
      if (!shouldCheckSemicolon(trimmed)) continue;

      const lastCh = info.lastMeaningfulChar;
      if (!lastCh) continue;

      // Already ends with valid terminators
      if (lastCh === ";" || lastCh === "{" || lastCh === "}" || lastCh === ":" ) continue;

      // Continued expression likely
      if (NON_TERMINAL_TAIL.has(lastCh)) continue;

      // If line ends with ')' and next meaningful char is '{', likely method/ctor declaration on next line
      if (lastCh === ")") {
        const next = lineInfo[i + 1];
        if (next && next.firstMeaningfulChar === "{") continue;
      }

      // Ignore lines that look like a method signature on the same line:
      // e.g., "public int f(int x)" or "void f() throws X"
      if (/\)\s*(throws\s+[\w.<>,\s]+)?\s*$/.test(trimmed) &&
          /^(public|private|protected|static|final|abstract|synchronized|native|strictfp|default)\b/.test(trimmed)) {
        continue;
      }

      // Marker near end of line (at last meaningful char)
      const col = info.lastMeaningfulCol || (text.length + 1);
      markers.push(makeMarker(lineNo, col, "Possible missing semicolon ';'.", Severity.Warning, text));
    }
  }

  // --------------------------
  // Public API
  // --------------------------

  /**
   * Analyze the content of a single Monaco editor and set markers.
   * @param {monaco.editor.IStandaloneCodeEditor} editorInstance
   * @param {{ debounceMs?: number }} [opts]
   */
  function attachManualDiagnostics(editorInstance, opts) {
    const m = safeMonaco();
    if (!m || !m.editor || !editorInstance) return null;

    const debounceMs = (opts && typeof opts.debounceMs === "number") ? opts.debounceMs : DEFAULT_DEBOUNCE_MS;

    const run = () => {
      const mm = safeMonaco();
      if (!mm || !mm.editor) return;

      const model = editorInstance.getModel();
      if (!model) return;

      const code = model.getValue();
      const { markers, lineInfo } = analyze(code);

      // Add semicolon warnings (low confidence)
      addSemicolonWarnings(markers, lineInfo);

      mm.editor.setModelMarkers(model, OWNER, markers);
    };

    const debouncedRun = debounce(run, debounceMs);

    // initial run + on change
    debouncedRun();
    const disposable = editorInstance.onDidChangeModelContent(debouncedRun);

    return { dispose: () => { try { disposable.dispose(); } catch (_) {} } };
  }

  /**
   * Initialize manual diagnostics for multiple editors.
   * @param {Object<string, monaco.editor.IStandaloneCodeEditor>} editorsMap
   * @param {{ debounceMs?: number }} [opts]
   */
  function initManualDiagnostics(editorsMap, opts) {
    const m = safeMonaco();
    if (!m || !m.editor) {
      console.warn("initManualDiagnostics: Monaco not ready yet. Call this after editor creation.");
      return;
    }

    if (!editorsMap || typeof editorsMap !== "object") {
      console.warn("initManualDiagnostics: invalid editorsMap provided");
      return;
    }

    // Dispose previous attachments to avoid duplicate listeners on hot reload
    if (window.__manualDiagDisposables && Array.isArray(window.__manualDiagDisposables)) {
      for (const d of window.__manualDiagDisposables) {
        try { d.dispose(); } catch (_) {}
      }
    }

    const keys = Object.keys(editorsMap);
    console.log("initManualDiagnostics called with editors:", keys);

    window.__manualDiagDisposables = [];
    for (const k of keys) {
      const ed = editorsMap[k];
      const disp = attachManualDiagnostics(ed, opts);
      if (disp) window.__manualDiagDisposables.push(disp);
    }
  }

  // Expose globally
  window.initManualDiagnostics = initManualDiagnostics;
  window.attachManualDiagnostics = attachManualDiagnostics;
})();
