# Known Limitations

- **Language Subset**: `cparse` supports only a subset of standard C as defined in `C_SUBSET.md`. Advanced features like bitfields, `goto`, `union`, or complex struct manipulation might be unsupported.
- **Preprocessor**: The lexer natively captures `#include` and `#define` as directives but drops them from the execution flow. Thus, `#define` macros are completely bypassed; their actual usages are parsed as regular identifiers. 
- **Pointers & Aliasing**: The dataflow analysis (`dead-store` and `uninitialized-variable`) assumes variables are accessed directly. Inter-procedural analysis, pointer aliasing, or `&` address-taking impacts are largely ignored.
- **Inline Suppression**: Because the `cparse` lexer safely ignores comments, inline rule suppression relies on a lightweight Python regex parser that reads the original source text. It might be fooled by suppression patterns appearing within string literals.
- **Single File Analysis**: Cross-file dependency resolution is outside the scope of `sca`; each file is analyzed completely independently.
- **Type Information**: Type coercion rules, deep `sizeof` evaluation, and strict expression typing are minimally enforced.
