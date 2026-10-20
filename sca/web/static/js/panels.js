/**
 * Panels and Results View Module (Tabs, Output, Diagnostics, Filters).
 */

import { jumpToLine } from "./editor.js";

let currentDiagnostics = [];
let currentFilter = "all";
let currentSource = "";

export function initPanels() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetPanelId = tab.getAttribute("data-tab");
      switchTab(targetPanelId);
    });
  });

  // Filter chips on Output tab
  const filterChips = document.querySelectorAll(".chip-filter");
  filterChips.forEach(chip => {
    chip.addEventListener("click", () => {
      filterChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      currentFilter = chip.getAttribute("data-filter");
      renderDiagnosticsList();
    });
  });
}

export function switchTab(tabId) {
  // Update tab buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabId) {
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
    } else {
      btn.classList.remove("active");
      btn.setAttribute("aria-selected", "false");
    }
  });

  // Update panels
  document.querySelectorAll(".tab-panel").forEach(panel => {
    if (panel.id === `panel-${tabId}`) {
      panel.classList.add("active");
    } else {
      panel.classList.remove("active");
    }
  });
}

export function renderResults(result, sourceCode) {
  currentSource = sourceCode || "";
  const lines = currentSource.splitlines ? currentSource.splitlines() : currentSource.split("\n");

  // Check for syntax errors
  const container = document.getElementById("output-diagnostics-container");
  if (!container) return;

  if (result.parse_errors && result.parse_errors.length > 0) {
    currentDiagnostics = [];
    updateTabBadges(result);
    renderSyntaxErrors(result.parse_errors);
    return;
  }

  currentDiagnostics = result.diagnostics || [];
  updateTabBadges(result);
  renderDiagnosticsList();
}

function updateTabBadges(result) {
  const outputBadge = document.getElementById("badge-output");
  if (outputBadge) {
    const total = (result.parse_errors && result.parse_errors.length > 0)
      ? result.parse_errors.length
      : (result.diagnostics ? result.diagnostics.length : 0);
    outputBadge.textContent = total;
  }

  const recBadge = document.getElementById("badge-recommendations");
  if (recBadge) {
    const recCount = result.recommendations ? result.recommendations.length : 0;
    recBadge.textContent = recCount;
  }

  // Update filter chips counts
  const summary = result.summary || { error: 0, warning: 0, info: 0 };
  const totalDiags = (result.diagnostics || []).length;

  const countAll = document.getElementById("count-filter-all");
  const countErr = document.getElementById("count-filter-error");
  const countWarn = document.getElementById("count-filter-warning");
  const countInfo = document.getElementById("count-filter-info");

  if (countAll) countAll.textContent = totalDiags;
  if (countErr) countErr.textContent = summary.error || 0;
  if (countWarn) countWarn.textContent = summary.warning || 0;
  if (countInfo) countInfo.textContent = summary.info || 0;
}

function renderSyntaxErrors(errors) {
  const container = document.getElementById("output-diagnostics-container");
  let html = `<div class="syntax-error-banner">
    <div class="syntax-error-title">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      Syntax / Parser Error (${errors.length})
    </div>
    <p style="font-size: 13px; margin-bottom: 8px;">The C parser encountered errors and could not generate an AST:</p>`;

  for (const err of errors) {
    html += `<div style="font-family: var(--font-mono); font-size: 12px; margin-top: 4px; padding: 4px 8px; background: rgba(0,0,0,0.2); border-radius: 4px;">
      Line ${err.line}, Col ${err.col}: ${escapeHtml(err.message)}
    </div>`;
  }
  html += `</div>`;
  container.innerHTML = html;
}

function renderDiagnosticsList() {
  const container = document.getElementById("output-diagnostics-container");
  if (!container) return;

  const lines = currentSource.split("\n");

  const filtered = currentDiagnostics.filter(d => {
    if (currentFilter === "all") return true;
    return d.severity === currentFilter;
  });

  if (filtered.length === 0) {
    if (currentDiagnostics.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
          <h3 style="font-weight: 600;">No Issues Detected</h3>
          <p style="font-size: 13px;">Your C code passed all 18 quality checks with a perfect 100/100 score.</p>
        </div>`;
    } else {
      container.innerHTML = `
        <div class="empty-state">
          <p style="font-size: 13px;">No diagnostics matching the filter "${currentFilter}".</p>
        </div>`;
    }
    return;
  }

  let html = `<div class="diagnostics-list">`;
  for (const d of filtered) {
    const sev = d.severity || "warning";
    const lineNum = d.line;
    const colNum = d.col || 1;
    const lineSnippet = (lines[lineNum - 1] !== undefined) ? lines[lineNum - 1].trim() : "";

    html += `
      <div class="diag-card ${sev}" data-line="${lineNum}" data-col="${colNum}">
        <div class="diag-header">
          <span class="diag-rule">${escapeHtml(d.rule_id)}</span>
          <span class="diag-loc">Ln ${lineNum}, Col ${colNum}</span>
        </div>
        <div class="diag-msg">${escapeHtml(d.message)}</div>
        ${lineSnippet ? `<div class="diag-snippet">${escapeHtml(lineSnippet)}</div>` : ""}
      </div>
    `;
  }
  html += `</div>`;

  container.innerHTML = html;

  // Add click handlers to cards
  container.querySelectorAll(".diag-card").forEach(card => {
    card.addEventListener("click", () => {
      const line = parseInt(card.getAttribute("data-line"), 10);
      const col = parseInt(card.getAttribute("data-col"), 10);
      jumpToLine(line, col);
    });
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
