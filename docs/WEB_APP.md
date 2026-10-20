# SCA Analyzer - Web Application Documentation

A modern, offline-capable, interactive web application for the **Static Code Quality Analyzer for C**. Inspired by clean, responsive developer IDEs like OneCompiler, this web interface provides instant semantic analysis, automated recommendations with before/after diff previews, circular code quality scoring, function-level metrics, and an interactive AST explorer.

---

## 1. Quickstart & How to Run

### 1.1 Requirements
- WSL (Ubuntu) or Linux environment.
- Python 3.10+ with `build-essential`, `flex`, `bison`, `make`.
- Compiled `cparse` binary (`build/cparse`).

### 1.2 Installation
From the project root inside your WSL shell:
```bash
# 1. Ensure C parser is built
make build

# 2. Install Python package with optional web extras (Flask)
pip install -e ".[web]"
```

### 1.3 Starting the Web Server
Launch the application using either the CLI subcommand or Python module:
```bash
# Using CLI entry point:
sca web --host 127.0.0.1 --port 8000

# Or via Python module directly:
python3 -m sca.web --host 127.0.0.1 --port 8000
```

Open your browser to:
👉 **`http://127.0.0.1:8000`**

---

## 2. Interface Layout & Features

The interface is structured as a dual-pane workspace with a draggable horizontal split divider:

### Top Navigation Bar
- **Logo & Title:** "SCA Analyzer" with a C99 language chip.
- **Examples Dropdown:** Instant pre-loaded C programs (`clean.c`, `smelly.c`, `security_bugs.c`, `flow_issues.c`, `complex_refactor.c`).
- **Upload (`.c`, `.h`):** Upload source files from local disk into the editor.
- **Download:** Save the current editor buffer to your machine as `main.c`.
- **Reset:** Revert code back to the default template.
- **Theme Toggle:** Switch between sleek dark mode (default) and crisp light mode (persisted in `localStorage`).
- **Run Button:** Prominent green button (`Ctrl+Enter` / `Cmd+Enter`) with active spinner while analyzing.

### Left Pane: Code Editor
- **Offline Vendored CodeMirror 5:** Full C syntax highlighting, bracket matching, and auto-indent. Zero runtime CDN dependencies.
- **Inline Gutter Markers:** Color-coded icons (`!`, `▲`, `i`) on affected lines.
- **Wavy Text Underlines:** Pinpoints exact error ranges directly in the code buffer.
- **Interactive Tooltips:** Hovering over gutter markers reveals the rule ID, message, and quick fix advice.
- **Status Bar:** Real-time line and column tracking (`Ln X, Col Y`), language tag, execution time in ms, and parser readiness.
- **Modified State Tracking:** Displays a subtle *"Results out of date"* badge when code is edited after a run.

### Right Pane: Analysis Results
1. **Output Tab (Default):**
   - Severity filter chips (**All**, **Errors**, **Warnings**, **Info**) with live issue counts.
   - Diagnostic cards detailing rule ID, location, message, and matching source line snippet.
   - Clicking any diagnostic immediately jumps and highlights that line in the editor.
   - Syntax error banner if the C parser encounters unrecoverable syntax errors.
2. **Recommendations Tab:**
   - Global banner showing score projection: *"Applying all safe fixes would raise your score from X to Y (+Z points)"*.
   - **Apply all safe fixes Button:** Applies all non-conflicting safe fixes in a single step and re-analyzes.
   - **Before/After Diff Preview:** Monospace visual diff displaying lines removed (`-`) and inserted (`+`).
   - **Apply fix Button:** Modifies the editor buffer and re-runs analysis. Reverts cleanly with `Ctrl+Z`.
   - **Stale Detection:** If code is changed in the editor, out-of-date fix buttons are automatically disabled with *"Stale (code changed)"*.
3. **Score Tab:**
   - **Animated Circular SVG Gauge:** Displays score (0–100) and letter grade with color transitions (A green, B blue, C amber, D orange, F red).
   - **Deductions Breakdown:** Horizontal progress bars displaying penalties deducted by each rule, sorted by impact.
4. **Metrics Tab:**
   - Per-function summary table: Function Name, Lines of Code (LOC), Parameter count, Max Nesting Depth, and Cyclomatic Complexity.
   - Highlighted warning pills when metrics exceed established thresholds (LOC > 50, Params > 5, Nesting > 4, Complexity > 10).
5. **AST Tab:**
   - Collapsible hierarchical tree view of the JSON AST.
   - "Expand All" and "Collapse All" controls.
   - Clickable line:col tags on nodes that navigate and highlight that construct in the code editor.
6. **CFG Tab:**
   - Control flow graph summary and CLI instructions (`sca cfg <file.c> <func>`).

---

## 3. Web API Reference

All JSON endpoints return responses following the standard schema:
- Success: `{"ok": true, ...}`
- Error: `{"ok": false, "error": {"code": "...", "message": "..."}}` with HTTP status 400, 404, 413, or 500.

### `GET /api/health`
Checks health status and verifies that the `cparse` binary exists and is executable.
- **Response (200):**
  ```json
  {
    "ok": true,
    "status": "healthy",
    "cparse": {
      "found": true,
      "path": "build/cparse"
    }
  }
  ```

### `GET /api/rules`
Lists all 18 registered analysis rules.
- **Response (200):**
  ```json
  {
    "ok": true,
    "rules": [
      {
        "id": "unused-variable",
        "name": "Unused Variable",
        "default_severity": "warning",
        "description": "Local variable declared but never read.",
        "tier": 2
      }
    ]
  }
  ```

### `GET /api/examples` & `GET /api/examples/<name>`
- `GET /api/examples`: Returns an array of example identifiers and descriptions.
- `GET /api/examples/<name>`: Returns the code for a specific example program. Path traversal (`..`) is strictly blocked (returns 400).

### `POST /api/analyze`
Analyzes C source code string and returns complete analysis results.
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "code": "int main() { int x; return 0; }",
    "disabled_rules": ["magic-number"]
  }
  ```
- **Response (200):**
  ```json
  {
    "ok": true,
    "parse_errors": [],
    "diagnostics": [
      {
        "file": "main.c",
        "line": 1,
        "col": 14,
        "end_line": 1,
        "end_col": 18,
        "message": "Local variable 'x' is declared but never read.",
        "rule_id": "unused-variable",
        "severity": "warning"
      }
    ],
    "summary": { "error": 0, "warning": 1, "info": 0 },
    "metrics": [
      { "function": "main", "loc": 1, "params": 0, "max_nesting": 0, "cyclomatic": 1 }
    ],
    "score": {
      "value": 98,
      "grade": "A (Excellent)",
      "total_issues": 1,
      "deductions": { "unused-variable": 2 }
    },
    "recommendations": [
      {
        "id": "rec-1",
        "rule_id": "unused-variable",
        "line": 1,
        "col": 14,
        "title": "Remove unused variable 'x'",
        "explanation": "Variable 'x' is declared but never read, so it adds clutter.",
        "priority": 2,
        "score_gain": 2,
        "safety": "safe",
        "edits": [
          { "line_start": 1, "line_end": 1, "expected_old": ["int main() { int x; return 0; }"], "new": [] }
        ]
      }
    ],
    "projected_score": 100,
    "elapsed_ms": 14.5
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Invalid JSON body or missing `code` string.
  - `413 Payload Too Large`: Code exceeds the 100 KB limit.

### `POST /api/ast`
Generates the JSON AST from `cparse` for the supplied C code.
- **Request Body:** `{"code": "..."}`
- **Response (200):** `{"ok": true, "ast": { "schema_version": 1, "unit": { ... } }}`

### `POST /api/cfg`
Returns basic blocks and directional edges for a given function.
- **Request Body:** `{"code": "...", "function": "main"}`
- **Response (200):** `{"ok": true, "function": "main", "blocks": [...], "edges": [...]}`

---

## 4. Security & Isolation Controls

1. **Static Analysis Only:** The server never compiles, links, or executes user code. Code is only parsed into an AST using `cparse`.
2. **Payload Size Enforcement:** Request bodies are strictly capped at 100 KB (`MAX_CONTENT_LENGTH = 100 * 1024`). Payloads exceeding this are rejected with HTTP 413.
3. **Isolated Temporary Files:** `cparse` invocations write to unique private directories created via `tempfile.mkdtemp()`. A `try...finally` block guarantees full directory cleanup after each request, even if errors occur.
4. **Execution Security:** Subprocesses are invoked with explicit argument lists (`no shell=True`) and enforced with a 10-second timeout.
5. **No Information Leaks:** Server errors (HTTP 500) return sanitized JSON error messages and never leak server directory paths, usernames, or stack traces.
6. **Local Binding:** The application binds to `127.0.0.1` by default without CORS or telemetry.

---

## 5. Manual QA Checklist

- [x] **Clean Example Analysis:** Load `clean.c` -> click Run -> Score is 100/100 (Grade A), 0 diagnostics, metrics table shows LOC 4, cyclomatic 1.
- [x] **Smelly Example Analysis:** Load `smelly.c` -> click Run -> Reports `unused-variable`, score 98/100, Projected Score 100/100.
- [x] **Apply Single Fix:** In Recommendations tab for `smelly.c`, click "Apply fix" -> `int x;` is removed from editor, analysis automatically re-runs, and score rises to 100/100.
- [x] **Undo Support:** Press `Ctrl+Z` / `Cmd+Z` in the editor -> code reverts to having `int x;`.
- [x] **Apply All Safe Fixes:** Load code with multiple safe issues -> click "Apply all safe fixes" -> all safe edits are applied and score updates.
- [x] **Stale Detection:** Manually edit a line with a pending recommendation -> the "Apply fix" button is disabled and indicates stale state.
- [x] **Theme Persistence:** Click theme toggle (☀️/🌙) -> background shifts cleanly between dark and light -> reload page -> theme remains preserved.
- [x] **Split Pane Resizing:** Drag the divider bar `#resizer` left and right -> reload page -> split ratio is preserved.
- [x] **AST Tree Exploration:** Switch to AST tab -> expand/collapse nodes -> click a line:col badge -> editor scrolls to and flashes that code construct.
- [x] **Responsive Layout:** Shrink viewport below 768px -> editor and results panes stack vertically; all buttons remain accessible.
- [x] **Keyboard Navigation:** Tab through all controls -> visible focus rings appear; `Ctrl+Enter` triggers analysis.
