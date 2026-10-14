# sca — Static Code Quality Analyzer for C

Two components:

1. **`cparse`** (C, Flex + Bison): lexes and parses a C subset and prints a JSON AST.
2. **`sca`** (Python): runs `cparse`, then performs semantic analysis, builds control-flow
   graphs, runs dataflow analyses and quality rules, and reports diagnostics.

## Features (target)
- AST checks: function length, nesting depth, parameter count, magic numbers, naming,
  unsafe library calls, assignment in condition, empty bodies
- Symbol-table checks: unused variables/parameters/functions, shadowing,
  constant array index out of bounds
- Flow checks (CFG + dataflow): unreachable code, missing return, uninitialized use,
  dead stores, cyclomatic complexity
- Text and JSON output, config file, inline suppression, CI-friendly exit codes

## Setup (Windows + WSL)
See `docs/BUILD_AND_RUN.md`. Short version, inside a WSL terminal:
```
sudo apt update && sudo apt install -y build-essential flex bison make python3 python3-venv python3-pip
bash scripts/check_env.sh
make build
make test
```

## Usage
```
sca analyze <file.c> [--rule ID ...] [--disable ID ...] [--fail-on error,warning]
sca ast <file.c>                   # dump the AST
sca tokens <file.c>                # dump tokens (from cparse --tokens)
sca parse <file.c>                 # Parse and print python AST
sca cfg <file.c> <func>            # dump a CFG (debugging)
sca liveness <file.c> <func>       # print liveness IN/OUT per block
```

## Exit codes
- 0: no findings at or above `--fail-on` severity
- 1: findings at or above `--fail-on` severity
- 2: usage error, unreadable file, or source failed to parse

## Docs
`docs/`: spec, C subset and grammar, JSON AST schema, architecture, build/run, rules,
testing, task plan.
