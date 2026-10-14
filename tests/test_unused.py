import pytest
import os
import json
import subprocess
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast
from sca.rules.unused import UnusedVariableRule, UnusedParameterRule

def test_unused_variable(tmp_path):
    c_file = tmp_path / "test.c"
    # x is written but not read -> unused
    # y is read -> used
    # z is not read or written -> unused
    c_file.write_text("int main() { int x; int y = 1; int z; x = 2; return y; }")
    
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = UnusedVariableRule()
    issues = rule.analyze(ast, "test.c")
    
    assert len(issues) == 2
    names = [i.message for i in issues]
    assert any("Variable 'x'" in msg or "variable 'x'" in msg for msg in names)
    assert any("Variable 'z'" in msg or "variable 'z'" in msg for msg in names)
    
    # Check rule id
    assert issues[0].rule_id == "unused-variable"

def test_unused_parameter(tmp_path):
    c_file = tmp_path / "test.c"
    # a is used, b is unused, _c is unused but starts with _ (should be ignored)
    c_file.write_text("int func(int a, int b, int _c) { return a; }")
    
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = UnusedParameterRule()
    issues = rule.analyze(ast, "test.c")
    
    assert len(issues) == 1
    assert "Parameter 'b'" in issues[0].message
    assert issues[0].rule_id == "unused-parameter"
