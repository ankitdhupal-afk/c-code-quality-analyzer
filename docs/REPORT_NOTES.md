# Project Report Notes

## 1. Lexer (Flex)
The lexer handles tokens seamlessly, supporting distinct C primitives (identifiers, numeric forms, keywords, string literals).
- **Line & Column Tracking**: Done dynamically via a custom `yylloc` tracking macro over `yytext`, accurately tagging token boundaries.
- **Directives**: Lexer traps lines starting with `#` in an exclusive state to safely scrape `includes` and `defines` before dropping them out of the standard token stream.

## 2. Grammar & Parser (Bison)
- **Conflicts & Precedence**: Resolved the classic "dangling-else" ambiguity by setting explicit precedence declarations (`%nonassoc LOWER_THAN_ELSE` vs `%nonassoc ELSE`).
- **AST Generation**: Used a custom Arena allocator in C to quickly allocate node structures (`ast.c`), avoiding massive `malloc/free` overhead. JSON emission traverses this Arena recursively.

## 3. Data Flow & CFG Construction
- **Object-Oriented CFG**: The Python CFG component (`CFGBuilder`) models basic blocks as lists of executable statements mapping accurately back to Python Dataclass AST equivalents.
- **Jumps**: Supported advanced jump architectures like `break` and `continue` by hooking a stack structure directly onto the traversal loop (`while/do-while/for`) allowing blocks to bridge dynamically.
- **Worklist Solver**: Built a powerful, flexible worklist solver (`DataflowAnalysis`) supporting both **Forward propagation** (Uninitialized variables) and **Backward propagation** (Liveness analysis). 

## 4. Quality Rules Engine
- **AST Rules**: Direct mapping traversal, tracking properties like line lengths, block scopes (Nesting Depth), limits (Parameters), and naming conventions (RegEx).
- **CFG Rules**: Utilizes the CFG edge network to detect Unreachable Code paths and Missing Returns.
- **Dataflow Rules**: Leverages liveness algorithms natively to accurately flag unused variables and Dead Stores without false positives around branched logical usage.
- **Inline Suppression**: We decoupled inline `// sca-disable` scanning into an independent Python pre-pass regex parser, since Bison AST explicitly filters out comments to maintain purity.
