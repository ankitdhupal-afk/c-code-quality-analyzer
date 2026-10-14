#!/usr/bin/env bash
# Verifies the toolchain needed to build and run sca inside WSL/Linux.
status=0
for tool in gcc flex bison make python3; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "ok       $tool: $("$tool" --version 2>&1 | head -n1)"
  else
    echo "MISSING  $tool"
    status=1
  fi
done

if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "ok       python >= 3.10"
  else
    echo "BAD      python is older than 3.10: $(python3 --version)"
    status=1
  fi
  python3 -c 'import venv' 2>/dev/null || { echo "MISSING  python3-venv"; status=1; }
fi

case "$PWD" in
  /mnt/*) echo "WARN     project is on the Windows filesystem ($PWD). Move it to ~/ for speed and LF line endings." ;;
esac

if [ "$status" -ne 0 ]; then
  echo
  echo "Fix with: sudo apt update && sudo apt install -y build-essential flex bison make python3 python3-venv python3-pip"
fi
exit "$status"
