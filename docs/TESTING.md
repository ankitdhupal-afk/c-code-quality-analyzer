# Testing strategy

Single entry point: `make test` (builds `cparse`, runs everything). `make asan` runs the
parser tests against the sanitizer build.

## Layers
1. **Lexer tests** (`cparse --tokens`): token kinds and positions, all literal forms,
   multi-char operators, comments (positions after comments stay correct), `#include` and
   `#define` capture, unterminated string/comment, bad characters.
2. **Parser golden tests** (`tests/parser/*.c` + `*.expected.json`): the exact JSON AST for
   each statement and expression form; precedence and associativity (`a - b - c`, `a = b = c`,
   `*p++`, casts vs parenthesized expressions, `a ? b : c ? d : e`); declarators
   (`int *a[10]`, `char **argv`); typedef disambiguation; dangling else (`if (a) if (b) x; else y;`
   binds to the inner `if`); switch/case markers.
3. **Parser robustness**:
   - Truncation fuzz: cut a valid file at every byte offset and run `cparse`; it must exit 0,
     print valid JSON, and never crash or time out.
   - Error recovery: a file with 3 separate syntax errors reports all 3; a file with >20 errors
     stops at 20.
   - `make asan`: no AddressSanitizer/UBSan findings on any parser test.
   - Bison reports zero conflicts (a test greps the build log).
4. **Schema tests**: every golden JSON validates against the loader; unknown `schema_version`
   and missing fields are rejected with clear messages.
5. **Semantic tests**: scoping, shadowing, redeclaration in the same scope, undeclared
   identifiers, read/write counting, array sizes, struct member resolution.
6. **CFG unit tests**: expected blocks/edges for each construct including switch fallthrough,
   nested loops with break/continue, `for(;;)`.
7. **Dataflow unit tests**: solver on small CFGs with hand-computed IN/OUT sets.
8. **Rule golden tests** (`tests/rules/<rule-id>/`): `positive_N.c` + `positive_N.expected.json`
   (rule fires exactly there) and `negative_N.c` (zero diagnostics for that rule).
9. **CLI end-to-end**: run on `examples/`; exit codes, JSON report validity, text output
   snippet and caret alignment, missing-`cparse` message.
10. **Regression**: every bug fix adds a test that failed first.

## Required C edge cases
- Empty file; only comments; function with empty body; `int main()` and `int main(void)`.
- `else if` chains: nesting depth must not grow per `else if`.
- Variable declared in one branch, used after the `if`.
- Shadowing across three levels, including `for (int i...)` scopes.
- `switch` with fallthrough, with and without `default`.
- Pointers: `*p = 1;`, `p[i] = 1`, `&x` passed to a function.
- String literals containing `//`, `/*`, escaped quotes.
- A directory with one broken file: others still analyzed.
- Suppression: same-line, previous-line, file-level, unknown rule id.
- Thresholds exactly at the limit (no report) and one over (report).
- Tabs in source (column accuracy; a tab is 1 column).
- Windows CRLF input files: positions and results must still be correct.

## Quality gates
- All tests pass before a phase is marked done.
- Each rule has >=2 positive and >=2 negative tests.
- False positives/negatives found go in `docs/KNOWN_LIMITATIONS.md`.
