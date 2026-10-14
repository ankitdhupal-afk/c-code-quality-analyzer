# Supported C subset

The analyzer targets a practical subset of C99. Anything outside it must give a syntax
error with line/column from `cparse`, never a crash.

## Preprocessing (no real preprocessor)
- The Flex lexer skips comments (`//`, `/* */`) while keeping line/column accurate.
- `#include ...` lines are recorded in `directives.includes` and otherwise ignored.
- `#define NAME <single literal>` (object-like) is recorded in `directives.defines`
  (so `magic-number` knows it is a named constant). Other `#...` lines (function-like macros,
  `#if`, `#ifdef`, etc.) are skipped; this is a known limitation.
- Python pre-declares common standard library functions (printf, scanf, malloc, calloc,
  realloc, free, strlen, strcpy, strncpy, strcmp, strcat, memcpy, memset, puts, gets, fgets,
  sprintf, snprintf, atoi, exit, abs) so calls to them are not "undeclared".

## Types
`void char short int long float double signed unsigned`, `const`, pointers (any depth),
arrays (constant or omitted size, multi-dimensional), `struct` definitions/variables with
`.` and `->`, and `typedef` of these.
Not supported: unions, enums (stretch), function pointers, bit-fields, variadic definitions,
`goto` and labels (lexed; parser reports "unsupported construct").

## Declarations
Global and local variables with optional initializers; multiple declarators per declaration
(`int a = 1, *b;`); array initializer lists `{1, 2, 3}`; function definitions and prototypes;
`static` and `extern` storage classes.

## Statements
Compound blocks, expression statements, empty statement, `if`/`else`, `while`, `do-while`,
`for` (declaration allowed in init), `switch` with `case`/`default`, `break`, `continue`,
`return`.
In the AST, `case X:` and `default:` are **marker statements** inside the switch body's
statement list (see AST_SCHEMA.md), which keeps fallthrough easy to model.

## Expressions (standard C precedence and associativity)
Primary: identifiers, integer/float/char/string literals, parentheses.
Postfix: call, index, `.`, `->`, `++`, `--`.
Unary: `+ - ! ~ * & ++ -- sizeof`, and casts `(type) expr`.
Binary: `* / %`, `+ -`, `<< >>`, `< > <= >=`, `== !=`, `&`, `^`, `|`, `&&`, `||`.
Ternary `?:`. Assignment `= += -= *= /= %= &= |= ^= <<= >>=`. Comma operator.

## Grammar (yacc-style sketch; the agent writes the full `parser.y`)
```
translation_unit : external_declaration | translation_unit external_declaration ;
external_declaration : function_definition | declaration ;
function_definition : decl_specifiers declarator compound_statement ;
declaration : decl_specifiers ';' | decl_specifiers init_declarator_list ';' ;
decl_specifiers : (storage_class | type_qualifier | type_specifier)+ ;
init_declarator_list : init_declarator | init_declarator_list ',' init_declarator ;
init_declarator : declarator | declarator '=' initializer ;
declarator : pointer direct_declarator | direct_declarator ;
direct_declarator : IDENT
                  | direct_declarator '[' constant_expr_opt ']'
                  | direct_declarator '(' param_list_opt ')' ;
statement : compound_statement | selection_statement | iteration_statement
          | jump_statement | expression_statement | declaration
          | CASE constant_expr ':' | DEFAULT ':' ;
selection_statement : IF '(' expr ')' statement %prec LOWER_THAN_ELSE
                    | IF '(' expr ')' statement ELSE statement
                    | SWITCH '(' expr ')' statement ;
```
Expressions: use the classic layered grammar OR a flat `expr : expr '+' expr ...` with
`%left/%right` precedence declarations. Either way, Bison must report zero conflicts.

## Typedef ambiguity (lexer hack)
When a `typedef` declaration is reduced, the parser records the declared name. The lexer
returns `TYPE_NAME` instead of `IDENT` for recorded names, so `T * x;` parses as a
declaration and `(T) y` as a cast.

## Syntax error recovery
Use Bison's `error` token in `statement`, `external_declaration` and `compound_statement`
to resynchronize at `;` or `}`. Collect each error as `{line, col, message}` (use
`%define parse.error verbose` and clean the message). Cap at 20 errors per file, then stop.
