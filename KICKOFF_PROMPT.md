# Kickoff prompt (paste this into Antigravity's agent panel)

You are building, from scratch, a CLI static code quality analyzer for C source code.

Architecture (two parts, two languages):
- `cparse/`: a C program built with **Flex and Bison** that parses a C subset and prints a
  JSON AST to stdout (the contract is `docs/AST_SCHEMA.md`).
- `sca/`: a **Python** package that runs `cparse`, loads the JSON AST, then does semantic
  analysis, CFG construction, dataflow analysis, rules, reporting and the CLI.

Environment: Windows with WSL (Ubuntu). All building and running happens inside WSL.

1. Read `AGENTS.md`, then everything in `docs/` in this order: SPEC.md, C_SUBSET.md,
   AST_SCHEMA.md, ARCHITECTURE.md, BUILD_AND_RUN.md, RULES.md, TESTING.md, TASKS.md.
2. There is NO existing code. Start with Phase 0 of `docs/TASKS.md`, beginning with
   `bash scripts/check_env.sh` to verify gcc, flex, bison, make and python3 exist in WSL.
3. Before writing code, post a short plan for Phase 0 and Phase 1 and wait for my approval.
4. Work one phase at a time. At the end of each phase: run `make test`, summarize what
   changed, and stop for review.

Scope: CLI only. Do NOT build any web UI, server, or editor integration.
Do NOT use third-party C parsers (pycparser, libclang, tree-sitter). The parser must be
Flex + Bison, written by hand.
