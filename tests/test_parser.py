import os
import json
import pytest
from sca.frontend.runner import run_cparse
import subprocess

def test_parser_golden(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { return 0; }")
    data = run_cparse(str(c_file))
    
    assert data["schema_version"] == 1
    assert data["errors"] == []
    assert data["unit"] is not None
    assert data["unit"]["kind"] == "TranslationUnit"
    items = data["unit"]["items"]
    assert len(items) == 1
    
    func = items[0]
    assert func["kind"] == "FunctionDef"
    assert func["name"] == "main"
    assert func["return_type"]["tk"] == "base"
    assert func["return_type"]["name"] == "int"
    assert len(func["params"]) == 0
    assert func["body"]["kind"] == "Block"
    assert func["body"]["stmts"][0]["kind"] == "Return"
    assert func["body"]["stmts"][0]["value"]["kind"] == "IntLiteral"
    assert func["body"]["stmts"][0]["value"]["text"] == "0"

def test_parser_truncation_fuzz(tmp_path):
    c_file = tmp_path / "test_fuzz.c"
    c_code = "int main(int argc, char **argv) { if (argc > 1) { return 1; } else { return 0; } }"
    
    # We truncate it one character at a time and ensure it doesn't crash (exit code != 139)
    # A crash due to ASAN will exit with a non-zero code but importantly not segfault or ASAN error code 1.
    # Actually ASAN exits with 1. We just run cparse as a subprocess and check there's no ASAN error string.
    cparse_bin = os.path.join(os.path.dirname(__file__), "..", "build", "cparse")
    
    for i in range(len(c_code), 0, -1):
        truncated = c_code[:i]
        c_file.write_text(truncated)
        result = subprocess.run([cparse_bin, str(c_file)], capture_output=True, text=True)
        # It may fail to parse, but it should not crash.
        assert "AddressSanitizer" not in result.stderr
        assert "Segmentation fault" not in result.stderr
        
        # Test tokens mode too
        result = subprocess.run([cparse_bin, "--tokens", str(c_file)], capture_output=True, text=True)
        assert "AddressSanitizer" not in result.stderr
        assert "Segmentation fault" not in result.stderr
