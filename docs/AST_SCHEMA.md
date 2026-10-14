# JSON AST schema (version 1)

This is the only contract between `cparse` (C) and `sca` (Python). Both sides must be
tested against it. `cparse file.c` writes one JSON document to stdout.

## Top level
```json
{
  "schema_version": 1,
  "file": "examples/a.c",
  "errors": [ {"line": 3, "col": 7, "message": "syntax error, unexpected ';'"} ],
  "directives": {
    "includes": [ {"text": "<stdio.h>", "line": 1, "col": 1} ],
    "defines":  [ {"name": "MAX", "value": "100", "line": 2, "col": 1} ]
  },
  "unit": { "kind": "TranslationUnit", "items": [ ... ] }
}
```
- `unit` may be `null` if the file could not be parsed at all; otherwise it holds the
  (possibly partial) tree. `sca` skips analysis when `errors` is non-empty.
- Strings are JSON-escaped; numbers in the source are kept as text (`text`/`value`) so no
  precision is lost.

## Common node fields
Every node object has: `"kind"` (string), `"line"`, `"col"`, `"end_line"`, `"end_col"`
(integers, 1-based, end is the position just after the last character).
Absent children are `null`; lists are `[]` when empty.

## Types (objects with `"tk"`, no position)
| tk | fields |
|---|---|
| `base` | `name` (e.g. `"unsigned int"`, `"char"`, `"void"`), `const` (bool) |
| `pointer` | `to` (Type), `const` (bool) |
| `array` | `of` (Type), `size` (Expr or null) |
| `struct` | `name` (string or null), `fields` (list of VarDecl, or null if only referenced) |
| `typedef` | `name` |
| `function` | `returns` (Type), `params` (list of Param) |

## Top-level items and declarations
| kind | fields |
|---|---|
| `FunctionDef` | `name`, `return_type` (Type), `params` ([Param]), `storage` (`"static"`/`"extern"`/null), `body` (Block) |
| `Prototype` | `name`, `return_type`, `params`, `storage` |
| `VarDecl` | `name`, `type` (Type), `storage` (`"static"`/`"extern"`/null), `init` (Expr, InitList or null), `is_global` (bool) |
| `TypedefDecl` | `name`, `type` |
| `StructDef` | `name`, `fields` ([VarDecl]) (standalone `struct S {...};`) |
| `Param` | `name` (string or null), `type` |

A declaration with several declarators (`int a, *b;`) becomes several `VarDecl` nodes.
At file scope they are separate entries in `items`; inside functions they are wrapped in
`DeclStmt`.

## Statements
| kind | fields |
|---|---|
| `Block` | `stmts` |
| `DeclStmt` | `decls` ([VarDecl / TypedefDecl / StructDef]) |
| `ExprStmt` | `expr` |
| `EmptyStmt` | |
| `If` | `cond`, `then`, `else` (or null) |
| `While` | `cond`, `body` |
| `DoWhile` | `body`, `cond` |
| `For` | `init` (DeclStmt, ExprStmt or null), `cond` (Expr or null), `step` (Expr or null), `body` |
| `Switch` | `expr`, `body` (Block) |
| `Case` | `value` (Expr): marker statement inside a switch body's `stmts`; it has no body |
| `Default` | marker statement, as above |
| `Break`, `Continue` | |
| `Return` | `value` (Expr or null) |

## Expressions
| kind | fields |
|---|---|
| `Identifier` | `name` |
| `IntLiteral` | `text` (e.g. `"0x1F"`, `"10UL"`) |
| `FloatLiteral` | `text` |
| `CharLiteral` | `text` (raw, with quotes) |
| `StringLiteral` | `text` (raw, with quotes and escapes) |
| `Unary` | `op` (`+ - ! ~ * & ++ --`), `operand`: prefix operators |
| `Postfix` | `op` (`++` or `--`), `operand` |
| `Binary` | `op` (including `,`), `left`, `right` |
| `Assign` | `op` (`=`, `+=`, ...), `target`, `value` |
| `Ternary` | `cond`, `then`, `else` |
| `Call` | `callee` (Expr), `args` |
| `Index` | `base`, `index` |
| `Member` | `base`, `name`, `arrow` (bool) |
| `Cast` | `type`, `operand` |
| `Sizeof` | `operand` (Expr or null), `type` (Type or null): exactly one is set |
| `InitList` | `items` (Exprs or nested InitLists) |

## Compatibility
- Adding a new optional field is allowed without a version bump.
- Renaming/removing fields or changing meaning requires bumping `schema_version` and
  updating `cparse`, `sca/frontend/ast_loader.py`, and all golden tests together.
- `sca` must reject an unknown `schema_version` with a clear message.
