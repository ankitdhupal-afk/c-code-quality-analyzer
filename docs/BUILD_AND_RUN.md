# Build and run (Windows + WSL)

## 0. Use WSL, with the project on the Linux filesystem
```
# in a WSL (Ubuntu) terminal
mkdir -p ~/sca && cd ~/sca        # put the project here, NOT under /mnt/c/...
```
Why: builds are much faster, and Windows line endings (CRLF) can break Flex/Bison and shell
scripts. `.gitattributes` forces LF.

Opening the folder in Antigravity: use its option to open a folder inside WSL
(a "WSL"/remote connection, if available in your version) so its terminal runs in WSL.
If that is not available, keep the project in WSL, let the agent edit files, and run
`make build` / `make test` yourself in a WSL terminal and paste any errors back.

## 1. Install the toolchain (once)
```
sudo apt update
sudo apt install -y build-essential flex bison make python3 python3-venv python3-pip
bash scripts/check_env.sh
```
Python must be 3.10 or newer (Ubuntu 22.04 ships 3.10, Ubuntu 24.04 ships 3.12).

## 2. Python environment
```
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"      # installs the `sca` command and pytest
```

## 3. Make targets (the agent creates the Makefile in Phase 0)
```
make build     # flex + bison + gcc -> build/cparse
make test      # builds, runs C-side golden tests and all pytest tests
make asan      # builds build/cparse-asan with -fsanitize=address,undefined and runs parser tests
make clean
```

## 4. Run
```
# parser only (JSON AST to stdout)
build/cparse examples/clean.c
build/cparse --tokens examples/clean.c

# full analyzer
sca analyze examples/smelly.c
sca analyze examples/ --format json --fail-on warning
python -m sca analyze examples/smelly.c      # works without installing
```
`sca` finds the parser at `build/cparse`; override with the `SCA_CPARSE` environment
variable. It runs `cparse` as a subprocess with a timeout (default 10 s).

## 5. Troubleshooting
- `flex: command not found` / `bison: command not found`: re-run the apt install above.
- `conflicts: N shift/reduce`: not allowed; see AGENTS.md (fix with precedence declarations).
- `\r` or `$'\r': command not found` errors: files have CRLF endings; run
  `sed -i 's/\r$//' <file>` or re-checkout with `.gitattributes` in place.
- Very slow builds: the project is under `/mnt/c`; move it into `~/`.
