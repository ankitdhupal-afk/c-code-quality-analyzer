# Architecture

## Pipeline
```
 .c file
    |
    v
 cparse (C, Flex + Bison)           <- runs as a subprocess
   lexer.l -> tokens -> parser.y -> AST (arena) -> JSON on stdout
    |
    |  JSON AST (docs/AST_SCHEMA.md)
    v
 sca (Python)
   runner -> ast_loader -> semantic analysis (scopes, symbols)
                              |
                      CFG builder (per function, lazy)
                              |
                       analysis driver
              +---------------+---------------+
            Rule A          Rule B          Rule C
              +---------------+---------------+
          diagnostics (suppression filter, sorted)
                              |
                    reporter (text / json)
```

## Repository layout
```
Makefile                 build, test, asan, clean
pyproject.toml           Python package, `sca` entry point, pytest config
.gitignore  .gitattributes
scripts/check_env.sh     verifies gcc/flex/bison/make/python in WSL
cparse/
  lexer.l                Flex rules, yylloc tracking, directive capture, --tokens mode
  parser.y               Bison grammar (%locations, zero conflicts)
  ast.h  ast.c           node structs/constructors, arena allocator
  json.h json.c          AST -> JSON emitter, string escaping
  typedefs.h typedefs.c  typedef-name table for the lexer hack
  errors.h errors.c      syntax error collection (cap 20)
  main.c                 argument parsing, file reading, orchestration
build/                   generated: lexer.c, parser.c, parser.h, cparse, cparse-asan
sca/
  cli.py                 argparse, exit codes
  config.py              load/validate config, defaults, per-rule settings
  diagnostics.py         Diagnostic, Severity, sorting
  suppressions.py        analyzer:ignore parsing and filtering
  driver.py              file discovery, pipeline, rule failure isolation
  frontend/
    runner.py            locate/run cparse (subprocess, timeout), error mapping
    ast_nodes.py         dataclasses for every node kind + Visitor + children()
    ast_loader.py        JSON -> dataclasses, schema validation
    types.py             minimal C type model built from JSON types
    symbols.py           Scope, Symbol, SymbolTable
    semantic.py          scope building, identifier resolution, read/write tracking
  cfg/
    blocks.py            BasicBlock, CFG (entry, single exit, edges)
    builder.py           AST -> CFG
  dataflow/
    solver.py            generic worklist solver
    definite_assignment.py   forward, meet = intersection
    liveness.py              backward, meet = union
  rules/
    base.py              Rule base, registry, RuleContext
    <one file per rule>
  reporters/
    text.py  json_reporter.py
tests/
  parser/                *.c + *.expected.json golden files for cparse; fuzz test
  frontend/              ast_loader, semantic unit tests
  unit/                  cfg, solver, config, suppressions
  rules/<rule-id>/       positive_N.c, negative_N.c, positive_N.expected.json
  cli/                   end-to-end tests
examples/                clean.c, smelly.c, ...
```

## cparse design notes
- **Lexer (Flex)**: `%option noyywrap nounput noinput yylineno`. A `YY_USER_ACTION` macro
  updates `yylloc` (first/last line and column) for each token. Use start conditions for
  block comments, and for directive lines (`#include`, `#define`). Tabs count as 1 column.
  Identifiers return `TYPE_NAME` if the typedef table contains them, else `IDENT`.
- **Parser (Bison)**: `%locations`, `%define parse.error verbose`. Node constructors take a
  `YYLTYPE` span. Use precedence declarations for operators and the dangling else
  (`%nonassoc LOWER_THAN_ELSE` / `%nonassoc ELSE`). Mid-rule action registers a typedef name
  as soon as its declarator is parsed.
- **AST**: tagged structs (`kind` enum + union or per-kind structs). A single arena
  (`arena_alloc(size)`) backs all nodes and strings; `arena_free_all()` at exit.
- **JSON emitter**: recursive writer with correct escaping; stable key order as in the schema.
- **Errors**: the grammar's `error` productions call `report_error(loc, msg)`. After 20
  errors, stop parsing and emit the JSON anyway.

## sca design notes
- **runner.py**: resolve binary (`SCA_CPARSE` env var, else `build/cparse` relative to the
  repo root). Run with `subprocess.run([...], capture_output=True, timeout=10)`. Non-zero exit,
  invalid JSON, or crash (negative return code) raises a `FrontendError` that the driver turns
  into an exit-2 condition with a clear message.
- **ast_loader.py**: table-driven mapping from `kind` to dataclass; unknown kinds or missing
  required fields raise `SchemaError`.
- **semantic.py**: single pass creating nested `Scope`s (global, function, block, for-scope),
  declaring symbols, resolving every `Identifier` to a `Symbol`, and counting reads and writes
  (compound assignment and `++/--` count as read + write; `&x` counts as read + write
  conservatively; `*p = v` counts as a read of `p`).

## Core interfaces (Python)
```python
class Severity(Enum): ERROR; WARNING; INFO

@dataclass(frozen=True)
class Diagnostic:
    rule_id: str; severity: Severity; message: str
    file: str; line: int; col: int
    end_line: int | None = None; end_col: int | None = None

@dataclass
class RuleContext:
    file: str
    unit: TranslationUnit
    function: FunctionDef | None     # None for file-level rules
    symbols: SymbolTable
    source_lines: list[str]
    directives: Directives           # includes and #define constants
    config: RuleConfig
    def cfg(self) -> CFG: ...        # lazy, cached per function

class Rule:
    id: str
    default_severity: Severity
    description: str
    needs_cfg: bool = False
    def check(self, ctx: RuleContext) -> list[Diagnostic]: ...

@register_rule
class UnusedVariable(Rule): ...
```
Adding a rule = one new file with one decorated class; the registry auto-discovers modules in
`sca/rules/`.

## CFG
- `BasicBlock`: id, statements (AST refs), successors, predecessors.
- `CFG`: entry block, single synthetic exit block, all blocks.
- Handles: sequence, if/else, while, do-while, for (init/cond/step blocks), switch (using the
  flat `Case`/`Default` markers for fallthrough; `break` jumps to the end), break, continue,
  return.
- `return` edges go to exit. Statements after a terminator start a new block with no
  predecessors (this is how unreachable code is detected).
- `while (1)` and `for (;;)` have no exit edge from the condition.
- `&&`, `||`, `?:` are not split into blocks (simplification, documented). Cyclomatic
  complexity counts them as decision points by AST count.

## Dataflow framework
```python
def solve(cfg, direction, boundary, init, meet, transfer) -> tuple[IN, OUT]:
    # worklist algorithm to fixpoint, with iteration cap
```
- Definite assignment (forward, intersection) -> `uninitialized-variable`.
  Arrays and address-taken variables count as assigned (conservative).
- Live variables (backward, union) -> `dead-store`. Address-taken variables excluded.

## Error handling
- Syntax errors from cparse -> `parse-error` diagnostics; the file is skipped.
- Missing/crashing cparse -> exit 2 with message.
- Rule exceptions -> `internal-error` diagnostics.
