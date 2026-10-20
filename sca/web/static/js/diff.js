/**
 * Lightweight diff preview renderer for recommendation edits.
 */

export function renderDiffPreview(edits) {
  if (!edits || edits.length === 0) return "";

  let html = `<div class="diff-preview">`;

  for (const edit of edits) {
    const oldLines = edit.expected_old || [];
    const newLines = edit.new || [];

    if (oldLines.length > 0) {
      for (const line of oldLines) {
        html += `<div class="diff-line diff-del"><span class="diff-marker">-</span><span class="diff-text">${escapeHtml(line)}</span></div>`;
      }
    } else {
      html += `<div class="diff-line diff-info"><span class="diff-marker">#</span><span class="diff-text">Insert at line ${edit.line_start}:</span></div>`;
    }

    for (const line of newLines) {
      html += `<div class="diff-line diff-add"><span class="diff-marker">+</span><span class="diff-text">${escapeHtml(line)}</span></div>`;
    }
  }

  html += `</div>`;
  return html;
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
