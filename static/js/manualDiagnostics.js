(function () {
    console.log("manualDiagnostics.js loaded");

    /**
     * Analyze the content of a single Monaco editor and set markers.
     * @param {monaco.editor.IStandaloneCodeEditor} editorInstance
     */
    function updateManualDiagnostics(editorInstance) {
        const model = editorInstance.getModel();
        if (!model) return;

        const markers = [];
        const code = model.getValue();
        const lines = code.split('\n');

        // Stacks to track positions of opening symbols.
        const parenStack = [];
        const braceStack = [];
        const bracketStack = [];

        lines.forEach((line, idx) => {
            const lineNumber = idx + 1;
            const trimmed = line.trim();

            // Missing semicolon diagnostics
            if (
                trimmed &&
                !trimmed.endsWith(';') &&
                !trimmed.endsWith('{') &&
                !trimmed.endsWith('}') &&
                !trimmed.startsWith('//') &&
                !trimmed.startsWith('*') &&
                !/^(if|for|while|switch|else)(\s*\(.*\))?$/.test(trimmed)
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

            // Unmatched symbol diagnostics
            for (let col = 0; col < line.length; col++) {
                const ch = line[col];
                const column = col + 1;
                switch (ch) {
                    case '(':
                        parenStack.push({line: lineNumber, column});
                        break;
                    case ')':
                        if (parenStack.length) parenStack.pop();
                        else markers.push(makeMarker(lineNumber, column, "Unmatched closing parenthesis.", monaco.MarkerSeverity.Error));
                        break;
                    case '{':
                        braceStack.push({line: lineNumber, column});
                        break;
                    case '}':
                        if (braceStack.length) braceStack.pop();
                        else markers.push(makeMarker(lineNumber, column, "Unmatched closing brace.", monaco.MarkerSeverity.Error));
                        break;
                    case '[':
                        bracketStack.push({line: lineNumber, column});
                        break;
                    case ']':
                        if (bracketStack.length) bracketStack.pop();
                        else markers.push(makeMarker(lineNumber, column, "Unmatched closing bracket.", monaco.MarkerSeverity.Error));
                        break;
                }
            }
        });

        // Any remaining opening symbols are unmatched
        parenStack.forEach(pos => markers.push(makeMarker(pos.line, pos.column, "Unmatched opening parenthesis.", monaco.MarkerSeverity.Error)));
        braceStack.forEach(pos => markers.push(makeMarker(pos.line, pos.column, "Unmatched opening brace.", monaco.MarkerSeverity.Error)));
        bracketStack.forEach(pos => markers.push(makeMarker(pos.line, pos.column, "Unmatched opening bracket.", monaco.MarkerSeverity.Error)));

        monaco.editor.setModelMarkers(editorInstance.getModel(), 'manualDiagnostics', markers);
    }

    /**
     * Helper to create a marker object
     */
    function makeMarker(line, col, message, severity) {
        return {
            startLineNumber: line,
            startColumn: col,
            endLineNumber: line,
            endColumn: col + 1,
            message,
            severity
        };
    }

    /**
     * Initialize manual diagnostics for multiple editors.
     * @param {Object<string, monaco.editor.IStandaloneCodeEditor>} editorsMap
     */
    function initManualDiagnostics(editorsMap) {
        if (!editorsMap || typeof editorsMap !== 'object') {
            console.warn("initManualDiagnostics: invalid editorsMap provided");
            return;
        }
        console.log("initManualDiagnostics called with editors:", Object.keys(editorsMap));
        Object.values(editorsMap).forEach(editorInstance => {
            editorInstance.onDidChangeModelContent(() => updateManualDiagnostics(editorInstance));
            updateManualDiagnostics(editorInstance);  // initial run
        });
    }

    // Expose globally
    window.initManualDiagnostics = initManualDiagnostics;
})();
