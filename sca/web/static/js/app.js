/**
 * Main application coordinator for SCA Analyzer Web UI.
 */

import { initTheme } from "./theme.js";
import { initEditor, getCode, setCode, resetCode, setDiagnosticsMarkers, clearMarkers } from "./editor.js";
import { initPanels, renderResults } from "./panels.js";
import { analyzeCode, fetchExamples, fetchExample } from "./api.js";

let isRunning = false;
let liveAnalysisTimer = null;

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Initialize Themes
  initTheme();

  // 2. Initialize Panels & Tabs
  initPanels();

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

async function handleRun() {
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
    const result = await analyzeCode(code);

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

function initSplitPane() {
  const resizer = document.getElementById("resizer");
  const paneLeft = document.getElementById("pane-editor");
  const paneRight = document.getElementById("pane-results");
  const workspace = document.querySelector(".workspace");

  if (!resizer || !paneLeft || !paneRight || !workspace) return;

  // Restore saved split position
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
  // Run Button
  const runBtn = document.getElementById("btn-run");
  if (runBtn) {
    runBtn.addEventListener("click", handleRun);
  }

  // Upload Button
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

  // Download Button
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

  // Reset Button
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
  } catch (e) {
    // If examples fail to fetch, silent fallback
  }
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
