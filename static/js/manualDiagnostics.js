// manualDiagnostics.js
(function () {
    console.log("manualDiagnostics.js loaded");

    function updateManualDiagnostics() {
        const model = window.editor && window.editor.getModel();
        if (!model) return;

        const markers = [];
        const code = model.getValue();
        const lines = code.split('\n');

        // Stacks to track positions of opening symbols.
        const parenStack = [];
        const braceStack = [];
        const bracketStack = [];

        lines.forEach((line, index) => {
            const lineNumber = index + 1;
            const trimmed = line.trim();

            // Check for a missing semicolon on lines that are non-empty, not comments,
            // and don't end with a semicolon or a block delimiter.
            if (
                trimmed &&
                !trimmed.endsWith(';') &&
                !trimmed.endsWith('{') &&
                !trimmed.endsWith('}') &&
                !trimmed.startsWith('//') &&      // ignore single-line comments
                !trimmed.startsWith('*') &&        // ignore block comment lines
                !/^(if|for|while|switch|else)(\s*\(.*\))?$/.test(trimmed) // ignore common control structures
            ) {
                markers.push({
                    startLineNumber: lineNumber,
                    startColumn: line.length,
                    endLineNumber: lineNumber,
                    endColumn: line.length + 1,
                    message: "Maybe missing a semicolon?",
                    severity: monaco.MarkerSeverity.Warning
                });
            }

            // Process each character to track opening and closing symbols.
            for (let col = 0; col < line.length; col++) {
                const ch = line[col];
                const column = col + 1; // Monaco uses 1-indexed columns
                if (ch === '(') {
                    parenStack.push({line: lineNumber, column: column});
                } else if (ch === ')') {
                    if (parenStack.length > 0) {
                        parenStack.pop();
                    } else {
                        markers.push({
                            startLineNumber: lineNumber,
                            startColumn: column,
                            endLineNumber: lineNumber,
                            endColumn: column + 1,
                            message: "Unmatched closing parenthesis.",
                            severity: monaco.MarkerSeverity.Error
                        });
                    }
                } else if (ch === '{') {
                    braceStack.push({line: lineNumber, column: column});
                } else if (ch === '}') {
                    if (braceStack.length > 0) {
                        braceStack.pop();
                    } else {
                        markers.push({
                            startLineNumber: lineNumber,
                            startColumn: column,
                            endLineNumber: lineNumber,
                            endColumn: column + 1,
                            message: "Unmatched closing brace.",
                            severity: monaco.MarkerSeverity.Error
                        });
                    }
                } else if (ch === '[') {
                    bracketStack.push({line: lineNumber, column: column});
                } else if (ch === ']') {
                    if (bracketStack.length > 0) {
                        bracketStack.pop();
                    } else {
                        markers.push({
                            startLineNumber: lineNumber,
                            startColumn: column,
                            endLineNumber: lineNumber,
                            endColumn: column + 1,
                            message: "Unmatched closing bracket.",
                            severity: monaco.MarkerSeverity.Error
                        });
                    }
                }
            }
        });

        // Any remaining opening symbols are unmatched.
        parenStack.forEach(pos => {
            markers.push({
                startLineNumber: pos.line,
                startColumn: pos.column,
                endLineNumber: pos.line,
                endColumn: pos.column + 1,
                message: "Unmatched opening parenthesis.",
                severity: monaco.MarkerSeverity.Error
            });
        });
        braceStack.forEach(pos => {
            markers.push({
                startLineNumber: pos.line,
                startColumn: pos.column,
                endLineNumber: pos.line,
                endColumn: pos.column + 1,
                message: "Unmatched opening brace.",
                severity: monaco.MarkerSeverity.Error
            });
        });
        bracketStack.forEach(pos => {
            markers.push({
                startLineNumber: pos.line,
                startColumn: pos.column,
                endLineNumber: pos.line,
                endColumn: pos.column + 1,
                message: "Unmatched opening bracket.",
                severity: monaco.MarkerSeverity.Error
            });
        });

        // Update the markers in the editor
        monaco.editor.setModelMarkers(model, 'manualDiagnostics', markers);
    }

    function initManualDiagnostics() {
        console.log("initManualDiagnostics called");
        if (window.editor && window.editor.onDidChangeModelContent) {
            console.log("Editor found:", window.editor);
            window.editor.onDidChangeModelContent(() => {
                updateManualDiagnostics();
            });
            // Run an initial check.
            updateManualDiagnostics();
        } else {
            console.log("Editor not ready, retrying...");
            setTimeout(initManualDiagnostics, 500);
        }
    }

    window.initManualDiagnostics = initManualDiagnostics;
})();
