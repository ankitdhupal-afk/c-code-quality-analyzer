# Agent rules for this repository

(If your tool reads `GEMINI.md` instead, copy this file to `GEMINI.md`.)

## Mission
Build, from scratch, a CLI static code quality analyzer for C code with two parts:
- `cparse/`: Flex + Bison C front end that emits a JSON AST.
- `sca/`: Python analyzer that consumes that JSON.
`docs/TASKS.md` defines the order of work. There is no existing code.

## Environment
- Windows host with WSL (Ubuntu). Build, run and test ONLY inside WSL.
- The project lives on the Linux filesystem (e.g. `~/sca`), not under `/mnt/c`.
- Use LF line endings everywhere (`.gitattributes` enforces this).
- Run `bash scripts/check_env.sh` at the start of Phase 0 and report anything missing.
  If a tool is missing, tell me the exact `apt install` command; do not work around it.

## Hard constraints
- CLI only. No web server, UI, LSP or editor integration unless I explicitly ask later.
- C front end: `cparse` is written in C (C11) using **Flex** (`lexer.l`) and **Bison**
  (`parser.y`). No third-party C parsers (pycparser, libclang, tree-sitter, etc.).
- Analyzer: Python 3.10+, type hints everywhere, standard library only for the core;
  `pytest` allowed for tests.
- The ONLY interface between `cparse` and `sca` is the JSON AST defined in
  `docs/AST_SCHEMA.md`. Do not change the schema without asking; if a change is needed,
  propose it, update the schema doc, bump `schema_version`, and update both sides + tests.
- Support only the C subset in `docs/C_SUBSET.md`. Unsupported constructs must produce a
  clear syntax error with line/column, never a crash.
- Analysis is independent of presentation. Reporters only format `Diagnostic` objects;
  rules never print.
- Every AST node carries line, col, end_line, end_col (1-based; a tab counts as 1 column).

## cparse (C) rules
- Allocate AST nodes from a simple arena allocator; free the arena once at exit. Run the
  `make asan` target (AddressSanitizer + UBSan) in tests; no leaks or errors allowed.
- `cparse` must ALWAYS print valid JSON for readable input, even when there are syntax
  errors (they go in the `errors` array). It exits 0 in that case; exit 2 only for I/O or
  usage failures. It must never crash or hang on malformed input.
- `bison` must report **zero** conflicts. Resolve the dangling-else and operator precedence
  with `%left/%right/%nonassoc` declarations, not by accepting conflicts. If a conflict is
  unavoidable, use `%expect N` with a comment explaining each one.
- Use `%locations` and update `yylloc` in the lexer for every token.
- Escape JSON strings correctly (quotes, backslashes, control chars, UTF-8 passthrough).
- Typedef names use the "lexer hack" (parser records typedef names, lexer returns
  `TYPE_NAME` for them). Typedef shadowing by inner scopes is out of scope.

## sca (Python) rules
- Load and validate the JSON AST into Python dataclasses; fail clearly on schema mismatch.
- If `cparse` reports syntax errors for a file, report them as `parse-error` diagnostics and
  skip analysis of that file; continue with other files.
- One rule per file under `sca/rules/`, registered with the registry decorator.
- Diagnostics always carry rule id, severity, message, file, line, column.
- Deterministic output: sort diagnostics by (file, line, column, rule id).

## Working rules
- Work one phase of `docs/TASKS.md` at a time. Stop after each phase for review.
- Before each phase, state a short plan. After it, state what changed and test results.
- Every rule needs at least 2 positive and 2 negative golden tests before it is done.
- Never mark a task done if tests fail. Never delete or weaken a test to make it pass.
- Teaching project: keep code readable and comment the *why* of non-obvious parts
  (lexer states, grammar precedence decisions, scope handling, CFG construction,
  worklist solver, definite assignment, liveness).
- Do not add third-party dependencies without asking.
- Do not silently expand the C subset.

## Definition of done (per phase)
1. Code implemented. 2. Tests added and `make test` passing. 3. `sca rules` and docs updated
if rules changed. 4. Short summary written in the chat.
