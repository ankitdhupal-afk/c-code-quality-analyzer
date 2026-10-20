/**
 * Main application coordinator for SCA Analyzer Web UI.
 */

import { initTheme } from "./theme.js";
import { initEditor, getCode, setCode, resetCode, setDiagnosticsMarkers, clearMarkers } from "./editor.js";
import { initPanels, renderResults, renderAst } from "./panels.js";
import { analyzeCode, fetchAst, fetchExamples, fetchExample } from "./api.js";

let isRunning = false;
let liveAnalysisTimer = null;

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Initialize Themes
  initTheme();

  // 2. Initialize Panels & Tabs with Fix Handlers
  initPanels(handleApplyFix, handleApplyAllSafe);

  // 3. Initialize CodeMirror Editor
  initEditor(handleRun, handleCodeChange);

  // 4. Initialize Split Pane Resizer
  initSplitPane();

  // 5. Initialize Top Bar Controls
  initTopBarControls();

  // 6. Populate Examples
  await loadExamplesDropdown();

  // 7. Initial Run
  handleRun();
});

export async function handleRun() {
  if (isRunning) return;
  const runBtn = document.getElementById("btn-run");
  const parserStatus = document.getElementById("parser-status");
  const timeElapsed = document.getElementById("time-elapsed");

  const code = getCode();
  if (!code.trim()) {
    clearMarkers();
    return;
  }

  isRunning = true;
  if (runBtn) {
    runBtn.classList.add("loading");
    runBtn.disabled = true;
  }
  if (parserStatus) parserStatus.textContent = "Analyzing...";

  try {
    const [result, astResult] = await Promise.all([
      analyzeCode(code),
      fetchAst(code).catch(() => null)
    ]);

    // Update status bar
    if (timeElapsed) timeElapsed.textContent = `${result.elapsed_ms || 0} ms`;
    if (parserStatus) {
      if (result.parse_errors && result.parse_errors.length > 0) {
        parserStatus.textContent = "Syntax Error";
        parserStatus.style.color = "var(--severity-error)";
      } else {
        parserStatus.textContent = "Ready";
        parserStatus.style.color = "var(--text-secondary)";
      }
    }

    // Set editor inline markers and gutter badges
    setDiagnosticsMarkers(result.diagnostics || [], result.recommendations || []);

    // Render results panels
    renderResults(result, code);

    // Render AST tree
    if (astResult && astResult.ok && astResult.ast) {
      renderAst(astResult.ast);
    }

  } catch (err) {
    if (parserStatus) {
      parserStatus.textContent = "Error";
      parserStatus.style.color = "var(--severity-error)";
    }
    showErrorBanner(err.message || "Failed to analyze code");
  } finally {
    isRunning = false;
    if (runBtn) {
      runBtn.classList.remove("loading");
      runBtn.disabled = false;
    }
  }
}

function handleCodeChange() {
  const liveToggle = document.getElementById("toggle-live-analysis");
  if (liveToggle && liveToggle.checked) {
    if (liveAnalysisTimer) clearTimeout(liveAnalysisTimer);
    liveAnalysisTimer = setTimeout(() => {
      handleRun();
    }, 800);
  }
}

function handleApplyFix(rec) {
  if (!rec.edits || rec.edits.length === 0) return;
  try {
    const currentCode = getCode();
    const newCode = applyClientEdits(currentCode, rec.edits);
    setCode(newCode);
    handleRun();
  } catch (err) {
    showErrorBanner(`Cannot apply fix: ${err.message}`);
  }
}

function handleApplyAllSafe(edits) {
  if (!edits || edits.length === 0) return;
  try {
    const currentCode = getCode();
    const newCode = applyClientEdits(currentCode, edits);
    setCode(newCode);
    handleRun();
  } catch (err) {
    showErrorBanner(`Cannot apply all safe fixes: ${err.message}`);
  }
}

function applyClientEdits(source, edits) {
  const lines = source.split("\n");
  const normEdits = [...edits].sort((a, b) => b.line_start - a.line_start);

  for (const edit of normEdits) {
    const lineStart = edit.line_start;
    const lineEnd = edit.line_end;
    const expectedOld = edit.expected_old || [];
    const newLines = edit.new || [];

    if (expectedOld.length > 0) {
      const actualOld = lines.slice(lineStart - 1, lineEnd);
      if (JSON.stringify(actualOld) !== JSON.stringify(expectedOld)) {
        throw new Error(`Lines ${lineStart}..${lineEnd} have changed since analysis.`);
      }
    }

    if (lineEnd === lineStart - 1) {
      lines.splice(lineStart - 1, 0, ...newLines);
    } else {
      lines.splice(lineStart - 1, lineEnd - lineStart + 1, ...newLines);
    }
  }

  return lines.join("\n");
}

function initSplitPane() {
  const resizer = document.getElementById("resizer");
  const paneLeft = document.getElementById("pane-editor");
  const paneRight = document.getElementById("pane-results");
  const workspace = document.querySelector(".workspace");

  if (!resizer || !paneLeft || !paneRight || !workspace) return;

  try {
    const savedFlex = localStorage.getItem("sca_split_ratio");
    if (savedFlex) {
      const [leftFlex, rightFlex] = savedFlex.split(":");
      paneLeft.style.flex = leftFlex;
      paneRight.style.flex = rightFlex;
    }
  } catch (e) {}

  let isDragging = false;

  resizer.addEventListener("mousedown", (e) => {
    isDragging = true;
    resizer.classList.add("dragging");
    document.body.style.cursor = "col-resize";
    e.preventDefault();
  });

  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const bounds = workspace.getBoundingClientRect();
    const offsetX = e.clientX - bounds.left;
    const totalWidth = bounds.width;

    if (offsetX > 200 && (totalWidth - offsetX) > 200) {
      const leftRatio = (offsetX / totalWidth).toFixed(4);
      const rightRatio = (1 - leftRatio).toFixed(4);
      paneLeft.style.flex = leftRatio;
      paneRight.style.flex = rightRatio;

      try {
        localStorage.setItem("sca_split_ratio", `${leftRatio}:${rightRatio}`);
      } catch (err) {}
    }
  });

  window.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      resizer.classList.remove("dragging");
      document.body.style.cursor = "";
    }
  });
}

function initTopBarControls() {
  const runBtn = document.getElementById("btn-run");
  if (runBtn) {
    runBtn.addEventListener("click", handleRun);
  }

  const uploadBtn = document.getElementById("btn-upload");
  const fileInput = document.getElementById("file-upload-input");
  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (event) => {
        setCode(event.target.result);
        handleRun();
      };
      reader.readAsText(file);
      fileInput.value = "";
    });
  }

  const downloadBtn = document.getElementById("btn-download");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const code = getCode();
      const blob = new Blob([code], { type: "text/x-csrc" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "main.c";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    });
  }

  const resetBtn = document.getElementById("btn-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      if (confirm("Reset editor to default template? Current edits will be lost.")) {
        resetCode();
        handleRun();
      }
    });
  }
}

async function loadExamplesDropdown() {
  const select = document.getElementById("select-examples");
  if (!select) return;

  try {
    const data = await fetchExamples();
    if (data.ok && data.examples) {
      select.innerHTML = `<option value="" disabled selected>Examples...</option>`;
      for (const ex of data.examples) {
        const opt = document.createElement("option");
        opt.value = ex.id;
        opt.textContent = `${ex.title} (${ex.id})`;
        select.appendChild(opt);
      }

      select.addEventListener("change", async () => {
        const selectedId = select.value;
        if (!selectedId) return;
        try {
          const detail = await fetchExample(selectedId);
          if (detail.ok && detail.code) {
            setCode(detail.code);
            handleRun();
          }
        } catch (e) {
          showErrorBanner(`Failed to load example '${selectedId}'`);
        }
      });
    }
  } catch (e) {}
}

function showErrorBanner(message) {
  let banner = document.getElementById("error-banner");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "error-banner";
    banner.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #cf222e;
      color: #fff;
      padding: 12px 18px;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      z-index: 9999;
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 12px;
    `;
    document.body.appendChild(banner);
  }
  banner.innerHTML = `<span>${message}</span> <button style="background:transparent; border:none; color:#fff; font-size:16px; cursor:pointer;" onclick="this.parentElement.remove()">&times;</button>`;
  setTimeout(() => {
    if (banner && banner.parentElement) banner.remove();
  }, 5000);
}
