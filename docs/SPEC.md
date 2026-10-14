# Specification

## 1. Purpose
Analyze C source files (subset in `docs/C_SUBSET.md`) and report code quality issues with
accurate locations and low false-positive rates. Two components: a Flex/Bison front end
(`cparse`) and a Python analyzer (`sca`) joined by the JSON AST in `docs/AST_SCHEMA.md`.

## 2. Inputs
- A `.c` file or a directory (searched recursively for `*.c`).
- Optional JSON config (see `sca.config.example.json`).

## 3. Components
1. **cparse lexer (Flex)**: tokens with line/column; comments; `#include`/`#define` capture;
   `--tokens` debug mode.
2. **cparse parser (Bison)**: LALR grammar for the subset, zero conflicts, typedef lexer hack,
   error recovery, AST built in an arena, JSON emitter.
3. **Python bridge**: runs `cparse` (subprocess, timeout), loads/validates JSON into AST
   dataclasses, provides `Visitor`/`children()`.
4. **Semantic analysis (Python)**: scope tree, symbol table (kind, type, declaration node, reads,
   writes), identifier resolution (`node.symbol`), array sizes, `undeclared-identifier`
   diagnostics. Retained for rules.
5. **CFG builder**: per function, basic blocks and edges.
6. **Dataflow framework**: generic worklist solver + analyses.
7. **Rules**: see `docs/RULES.md`.
8. **Driver, config, suppression, reporters, CLI.**

## 4. Functional requirements
FR1. Run all enabled rules over each function/file and collect diagnostics.
FR2. Diagnostic = {rule_id, severity, message, file, line, col, end_line?, end_col?}.
FR3. Severities: error, warning, info. Each rule has a default; config can override.
FR4. Rules can be enabled/disabled and thresholds changed via config or CLI flags.
FR5. Inline suppression comments (read by Python from the source text):
     `// analyzer:ignore <rule-id>[, <rule-id>]` on the same line or the line before;
     `// analyzer:ignore-file <rule-id>` in the first 10 lines suppresses file-wide.
FR6. Reporters: `text` (source snippet + caret) and `json` (schema below).
FR7. `sca metrics`: per-function LOC, params, max nesting, cyclomatic complexity.
FR8. Exit codes 0 / 1 / 2 as in README.
FR9. Directory analysis: a file with syntax errors yields `parse-error` diagnostics and is
     skipped; others continue; exit 2 at the end.
FR10. Debug commands: `sca ast`, `sca tokens`, `sca cfg`.
FR11. `docs/RULES.md` is the source of truth for rule behavior.

## 5. Non-functional requirements
- Deterministic, sorted output.
- A 1,000-line C file analyzes in under 1 second (parse + analysis).
- No network access, no global state.
- Rules are isolated: an exception inside a rule becomes an `internal-error` diagnostic.
- `cparse` never crashes or hangs on malformed input (truncation fuzz test, ASan clean).
- If `cparse` is missing or crashes, `sca` exits 2 with a clear message ("run `make build`").

## 6. JSON report schema (output of `sca analyze --format json`)
```json
{
  "version": "1",
  "files_analyzed": 3,
  "summary": {"error": 1, "warning": 4, "info": 2},
  "diagnostics": [
    {"rule_id": "unused-variable", "severity": "warning",
     "message": "Variable 'tmp' is declared but never used",
     "file": "examples/a.c", "line": 12, "col": 9, "end_line": 12, "end_col": 12}
  ],
  "metrics": [
    {"file": "examples/a.c", "function": "main", "loc": 24, "params": 0,
     "max_nesting": 3, "cyclomatic": 5}
  ]
}
```

## 7. Out of scope (for now)
Web UI, server, LSP, auto-fix, real preprocessing/macro expansion, inter-procedural analysis,
pointer/alias analysis, full C type checking.
