import os
import subprocess
import json

def get_cparse_bin() -> str:
    cparse_bin = os.environ.get("SCA_CPARSE", "build/cparse")
    if not os.path.exists(cparse_bin):
        raise RuntimeError(f"run `make build` to create {cparse_bin}")
    return cparse_bin

def run_cparse(filepath: str) -> dict:
    cparse_bin = get_cparse_bin()
    try:
        result = subprocess.run([cparse_bin, filepath], capture_output=True, text=True, timeout=10)
        if result.returncode not in (0, 1):
            raise RuntimeError(f"cparse failed with exit code {result.returncode}: {result.stderr}")
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("cparse timed out")
    except json.JSONDecodeError:
        raise RuntimeError("cparse output invalid JSON")

def run_cparse_tokens(filepath: str) -> list:
    cparse_bin = get_cparse_bin()
    try:
        result = subprocess.run([cparse_bin, "--tokens", filepath], capture_output=True, text=True, timeout=10)
        if result.returncode not in (0, 1):
            raise RuntimeError(f"cparse --tokens failed with exit code {result.returncode}: {result.stderr}")
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("cparse timed out")
    except json.JSONDecodeError:
        raise RuntimeError("cparse output invalid JSON")
