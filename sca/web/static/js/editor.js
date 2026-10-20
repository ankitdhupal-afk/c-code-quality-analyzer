/**
 * CodeMirror 5 Editor Integration Module with Inline Markers and Gutter Tooltips.
 */

let editor = null;
let currentMarks = [];
let tooltipEl = null;

const STORAGE_CODE_KEY = "sca_editor_code";
const DEFAULT_CODE = `int main() {
    int x;
    return 0;
}
`;

export function initEditor(onRunRequested, onCodeChanged) {
  const textarea = document.getElementById("code-editor");

  // Restore saved code or default
  let initialCode = DEFAULT_CODE;
  try {
    const saved = localStorage.getItem(STORAGE_CODE_KEY);
    if (saved !== null && saved.trim()) {
      initialCode = saved;
    }
  } catch (e) {}

  textarea.value = initialCode;

  // Initialize CodeMirror 5
  editor = window.CodeMirror.fromTextArea(textarea, {
    mode: "text/x-csrc",
    lineNumbers: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    gutters: ["CodeMirror-linenumbers", "sca-gutter-markers"],
    tabSize: 4,
    indentUnit: 4,
    indentWithTabs: false,
    lineWrapping: false,
    extraKeys: {
      "Ctrl-Enter": () => onRunRequested && onRunRequested(),
      "Cmd-Enter": () => onRunRequested && onRunRequested(),
    },
  });

  // Cursor activity tracking
  editor.on("cursorActivity", () => {
    const cursor = editor.getCursor();
    const posEl = document.getElementById("cursor-pos");
    if (posEl) {
      posEl.textContent = `Ln ${cursor.line + 1}, Col ${cursor.ch + 1}`;
    }
  });

  // Code modification listener
  editor.on("change", () => {
    try {
      localStorage.setItem(STORAGE_CODE_KEY, editor.getValue());
    } catch (e) {}

    // Show stale results badge if markers were active
    if (currentMarks.length > 0) {
      const staleBadge = document.getElementById("stale-badge");
      if (staleBadge) staleBadge.style.display = "inline-block";
    }

    if (onCodeChanged) onCodeChanged();
  });

  // Tooltip element
  tooltipEl = document.createElement("div");
  tooltipEl.className = "sca-tooltip";
  document.body.appendChild(tooltipEl);

  return editor;
}

export function getCode() {
  return editor ? editor.getValue() : "";
}

export function setCode(newCode) {
  if (editor) {
    editor.setValue(newCode);
    clearMarkers();
  }
}

export function resetCode() {
  setCode(DEFAULT_CODE);
}

export function clearMarkers() {
  if (!editor) return;

  // Clear text marks
  currentMarks.forEach(m => m.clear());
  currentMarks = [];

  // Clear gutter markers
  editor.clearGutter("sca-gutter-markers");

  const staleBadge = document.getElementById("stale-badge");
  if (staleBadge) staleBadge.style.display = "none";
}

export function setDiagnosticsMarkers(diagnostics, recommendations = []) {
  if (!editor) return;
  clearMarkers();

  // Create lookup for recommendations by line and rule_id
  const recLookup = {};
  for (const r of recommendations) {
    const key = `${r.line}:${r.rule_id}`;
    recLookup[key] = r;
  }

  // Group diagnostics by line for gutter markers
  const lineDiags = {};

  for (const d of diagnostics) {
    const line = d.line;
    if (!lineDiags[line]) lineDiags[line] = [];
    lineDiags[line].push(d);

    // Add wavy underline mark
    const startLine = Math.max(0, d.line - 1);
    const startCol = Math.max(0, (d.col || 1) - 1);
    const endLine = Math.max(0, (d.end_line || d.line) - 1);
    const endCol = Math.max(startCol + 1, (d.end_col || startCol + 4));

    const markClass = `sca-mark-${d.severity || "warning"}`;
    try {
      const mark = editor.markText(
        { line: startLine, ch: startCol },
        { line: endLine, ch: endCol },
        { className: markClass }
      );
      currentMarks.push(mark);
    } catch (e) {}
  }

  // Add gutter markers
  for (const [lineStr, diags] of Object.entries(lineDiags)) {
    const lineNum = parseInt(lineStr, 10);
    const primaryDiag = diags[0];
    const severity = primaryDiag.severity || "warning";

    const marker = document.createElement("div");
    marker.className = `sca-gutter-marker marker-${severity}`;
    marker.textContent = severity === "error" ? "!" : (severity === "warning" ? "▲" : "i");

    // Tooltip data
    const rec = recLookup[`${lineNum}:${primaryDiag.rule_id}`];
    const tooltipText = `<strong>[${primaryDiag.rule_id}]</strong> ${primaryDiag.message}` +
      (rec && rec.title ? `<br><em style="color:#58a6ff;">💡 Fix: ${rec.title}</em>` : "");

    marker.addEventListener("mouseenter", (e) => {
      showTooltip(e, tooltipText);
    });
    marker.addEventListener("mouseleave", hideTooltip);
    marker.addEventListener("click", () => {
      jumpToLine(lineNum, primaryDiag.col || 1);
    });

    editor.setGutterMarker(lineNum - 1, "sca-gutter-markers", marker);
  }
}

export function jumpToLine(line, col = 1) {
  if (!editor) return;
  const lineIdx = Math.max(0, line - 1);
  const colIdx = Math.max(0, col - 1);

  editor.scrollIntoView({ line: lineIdx, ch: colIdx }, 100);
  editor.setCursor({ line: lineIdx, ch: colIdx });
  editor.focus();

  // Highlight flash effect
  const lineHandle = editor.addLineClass(lineIdx, "background", "sca-highlight-flash");
  setTimeout(() => {
    editor.removeLineClass(lineHandle, "background", "sca-highlight-flash");
  }, 900);
}

function showTooltip(event, htmlContent) {
  if (!tooltipEl) return;
  tooltipEl.innerHTML = htmlContent;
  const rect = event.target.getBoundingClientRect();
  tooltipEl.style.left = `${rect.right + 8}px`;
  tooltipEl.style.top = `${rect.top - 4}px`;
  tooltipEl.classList.add("visible");
}

function hideTooltip() {
  if (tooltipEl) {
    tooltipEl.classList.remove("visible");
  }
}
