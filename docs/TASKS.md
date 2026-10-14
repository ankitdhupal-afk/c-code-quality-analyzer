# Task plan

Work phase by phase. Stop after each phase for review. There is no existing code.
All commands run inside WSL.

## Phase 0: Environment and scaffolding
- [ ] Run `bash scripts/check_env.sh`; report missing tools with exact apt commands
- [ ] `Makefile` (build, test, asan, clean), `pyproject.toml` (package `sca`, `sca` entry point,
      pytest config, `dev` extra), `build/` ignored by git
- [ ] Minimal `cparse` (Flex + Bison + C) that parses an empty file and prints valid JSON with
      `schema_version`, `file`, empty `errors`, `directives`, empty `unit`
- [ ] Python: `sca/frontend/runner.py` runs `cparse`; `python -m sca --help` works
- [ ] `examples/clean.c` and `examples/smelly.c` (smelly triggers many planned rules)
**Done when:** `make test` passes with one end-to-end test (Python runs cparse on an empty file).

## Phase 1: Lexer (Flex)
- [ ] `lexer.l`: keywords, identifiers, int/hex/octal/float/char/string literals, all operators,
      comments, `#include`/`#define` capture, line/column tracking via `yylloc`
- [ ] `cparse --tokens file.c` prints tokens as JSON; `sca tokens` wraps it
- [ ] Lexer errors (unterminated string/comment, bad char) reported in `errors`
- [ ] Lexer tests
**Done when:** every example lexes with correct positions for every token, including after comments.

## Phase 2: Grammar, AST and JSON (Bison)
- [ ] `ast.h/c` with arena allocator and constructors; `json.c` emitter per AST_SCHEMA.md
- [ ] `parser.y`: declarations/declarators, statements, expressions, switch markers, structs,
      typedef lexer hack, `%locations`
- [ ] Zero Bison conflicts (precedence declarations); document each precedence decision in comments
- [ ] Error recovery with `error` productions, 20-error cap, valid JSON always printed
- [ ] Golden JSON tests, truncation fuzz test, `make asan` clean
**Done when:** all golden tests pass, fuzz test never crashes, ASan clean, zero conflicts.

## Phase 3: Python bridge and AST model
- [ ] `ast_nodes.py` dataclasses + `Visitor` + `children()`
- [ ] `ast_loader.py` with schema validation (`SchemaError`)
- [ ] Runner error handling (missing binary, crash, timeout, invalid JSON)
- [ ] `sca ast <file.c>` pretty-prints the tree
**Done when:** every golden JSON loads; loader rejects bad schema versions/fields with clear errors.

## Phase 4: Semantic analysis
- [ ] Scope tree, symbols, identifier resolution, read/write tracking
- [ ] Pre-declared stdlib functions; `#define` constants as symbols
- [ ] Type model; array sizes from constant expressions
- [ ] `undeclared-identifier` and redeclaration diagnostics
- [ ] Semantic tests
**Done when:** every identifier in the examples resolves; read/write counts are correct in tests.

## Phase 5: Analysis infrastructure and first rules
- [ ] Rule base, registry auto-discovery, `RuleContext`
- [ ] Driver (file discovery, pipeline, failure isolation, parse-error handling)
- [ ] Config loader/validation; text and JSON reporters; `analyze` and `rules` commands; exit codes
- [ ] Rules: `function-too-long`, `deep-nesting`, `too-many-params`
**Done when:** `sca analyze examples/` works end to end with golden tests for these rules.

## Phase 6: Remaining AST rules and suppression
- [ ] `magic-number`, `naming-convention`, `unsafe-function`, `assignment-in-condition`, `empty-body`
- [ ] Inline suppression; `--rule`, `--disable`, `--fail-on`
**Done when:** suppression and threshold tests pass.

## Phase 7: Symbol-table rules
- [ ] `unused-variable`, `unused-parameter`, `unused-function`, `shadowed-variable`,
      `const-index-out-of-bounds`
**Done when:** scope/shadowing edge cases in TESTING.md pass.

## Phase 8: CFG
- [ ] BasicBlock/CFG and builder for all control flow in the subset
- [ ] `sca cfg` debug command (text and Graphviz DOT)
- [ ] Rules: `unreachable-code`, `missing-return`, `high-complexity`; `sca metrics`
**Done when:** CFG unit tests cover every construct; complexity matches hand-computed values.

## Phase 9: Dataflow
- [ ] Generic worklist solver with iteration cap
- [ ] Definite assignment -> `uninitialized-variable`
- [ ] Liveness -> `dead-store`
- [ ] Solver unit tests with hand-computed sets
**Done when:** loops, branches, and switch give correct results, no known false positives in `examples/`.

## Phase 10: Polish and documentation
- [ ] `docs/KNOWN_LIMITATIONS.md`
- [ ] README usage verified against real CLI output
- [ ] `docs/REPORT_NOTES.md` for the project report: lexer (regexes, start conditions), grammar
      and how conflicts were eliminated (dangling else, precedence), typedef lexer hack, error
      recovery, JSON contract, scopes, CFG, worklist solver, definite assignment, liveness
- [ ] Optional: CI workflow running `make test`
**Done when:** fresh clone in WSL -> setup -> `make test` -> CLI works from README alone.

## Deferred (do not start)
Web interface, LSP/editor integration, auto-fix, stretch rules (ask first).
