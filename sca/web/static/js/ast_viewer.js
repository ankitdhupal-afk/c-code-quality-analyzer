/**
 * Collapsible interactive JSON AST tree viewer with CodeMirror range highlighting.
 */

import { jumpToLine } from "./editor.js";

export function renderAstTree(container, astData) {
  if (!container) return;

  if (!astData || !astData.unit) {
    container.innerHTML = `
      <div class="empty-state">
        <p style="font-size: 13px;">No AST available. Ensure the C code has valid syntax and run analysis.</p>
      </div>`;
    return;
  }

  const rootUnit = astData.unit;

  container.innerHTML = `
    <div class="ast-toolbar">
      <div class="ast-toolbar-left">
        <button id="btn-ast-expand-all" class="btn-ast-tool">Expand All</button>
        <button id="btn-ast-collapse-all" class="btn-ast-tool">Collapse All</button>
      </div>
      <span class="ast-schema-label">Schema: C99 AST (v1)</span>
    </div>
    <div class="ast-tree-root" id="ast-tree-root"></div>
  `;

  const treeRoot = document.getElementById("ast-tree-root");
  treeRoot.appendChild(buildTreeNode(rootUnit, "root", true));

  // Expand / Collapse All handlers
  document.getElementById("btn-ast-expand-all").addEventListener("click", () => {
    treeRoot.querySelectorAll(".ast-children").forEach(el => el.style.display = "block");
    treeRoot.querySelectorAll(".ast-toggle").forEach(el => el.textContent = "▼");
  });

  document.getElementById("btn-ast-collapse-all").addEventListener("click", () => {
    treeRoot.querySelectorAll(".ast-children").forEach(el => el.style.display = "none");
    treeRoot.querySelectorAll(".ast-toggle").forEach(el => el.textContent = "▶");
  });
}

function buildTreeNode(node, propKey = "", isRoot = false) {
  const itemEl = document.createElement("div");
  itemEl.className = "ast-tree-item";

  if (node === null || node === undefined) {
    itemEl.innerHTML = `<span class="ast-key">${escapeHtml(propKey)}:</span> <span class="ast-null">null</span>`;
    return itemEl;
  }

  if (typeof node !== "object") {
    let valClass = "ast-primitive";
    if (typeof node === "string") valClass = "ast-string";
    else if (typeof node === "number") valClass = "ast-number";
    else if (typeof node === "boolean") valClass = "ast-bool";

    itemEl.innerHTML = `
      ${propKey ? `<span class="ast-key">${escapeHtml(propKey)}:</span> ` : ""}
      <span class="${valClass}">${escapeHtml(JSON.stringify(node))}</span>
    `;
    return itemEl;
  }

  if (Array.isArray(node)) {
    const header = document.createElement("div");
    header.className = "ast-node-header";

    const toggle = document.createElement("span");
    toggle.className = "ast-toggle";
    toggle.textContent = "▼";

    const label = document.createElement("span");
    label.className = "ast-array-label";
    label.innerHTML = `${propKey ? `<span class="ast-key">${escapeHtml(propKey)}</span>: ` : ""}Array[${node.length}]`;

    header.appendChild(toggle);
    header.appendChild(label);
    itemEl.appendChild(header);

    const childrenContainer = document.createElement("div");
    childrenContainer.className = "ast-children";

    node.forEach((child, idx) => {
      childrenContainer.appendChild(buildTreeNode(child, `[${idx}]`));
    });

    itemEl.appendChild(childrenContainer);

    header.addEventListener("click", (e) => {
      const isExpanded = childrenContainer.style.display !== "none";
      childrenContainer.style.display = isExpanded ? "none" : "block";
      toggle.textContent = isExpanded ? "▶" : "▼";
    });

    return itemEl;
  }

  // Object / AST Node
  const kind = node.kind || "Object";
  const line = node.line;
  const col = node.col || 1;

  const header = document.createElement("div");
  header.className = "ast-node-header";

  const toggle = document.createElement("span");
  toggle.className = "ast-toggle";
  toggle.textContent = "▼";

  const kindSpan = document.createElement("span");
  kindSpan.className = "ast-kind";
  kindSpan.textContent = kind;

  header.appendChild(toggle);
  if (propKey) {
    const keySpan = document.createElement("span");
    keySpan.className = "ast-key";
    keySpan.textContent = `${propKey}: `;
    header.appendChild(keySpan);
  }
  header.appendChild(kindSpan);

  // If node has identifying name or text property, display inline
  if (node.name) {
    const nameSpan = document.createElement("span");
    nameSpan.className = "ast-inline-name";
    nameSpan.textContent = `'${node.name}'`;
    header.appendChild(nameSpan);
  } else if (node.text) {
    const textSpan = document.createElement("span");
    textSpan.className = "ast-inline-text";
    textSpan.textContent = `"${node.text}"`;
    header.appendChild(textSpan);
  }

  // Location pill with jump-to-line action
  if (line !== undefined) {
    const locBadge = document.createElement("span");
    locBadge.className = "ast-loc-badge";
    locBadge.textContent = `${line}:${col}`;
    locBadge.title = `Jump to Line ${line}, Col ${col}`;
    locBadge.addEventListener("click", (e) => {
      e.stopPropagation();
      jumpToLine(line, col);
    });
    header.appendChild(locBadge);
  }

  itemEl.appendChild(header);

  const childrenContainer = document.createElement("div");
  childrenContainer.className = "ast-children";

  // Render object fields (skip metadata fields like schema_version, line, col, end_line, end_col in children)
  const ignoredKeys = new Set(["kind", "line", "col", "end_line", "end_col"]);
  for (const [k, v] of Object.entries(node)) {
    if (!ignoredKeys.has(k)) {
      childrenContainer.appendChild(buildTreeNode(v, k));
    }
  }

  itemEl.appendChild(childrenContainer);

  header.addEventListener("click", (e) => {
    // If locBadge was clicked, don't toggle
    if (e.target.classList.contains("ast-loc-badge")) return;
    const isExpanded = childrenContainer.style.display !== "none";
    childrenContainer.style.display = isExpanded ? "none" : "block";
    toggle.textContent = isExpanded ? "▶" : "▼";
  });

  return itemEl;
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
