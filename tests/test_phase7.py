import pytest
import os
import json
import subprocess
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast
from sca.rules.phase7 import UnusedFunctionRule, ShadowedVariableRule, ConstIndexOutOfBoundsRule

def test_unused_function(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("static int foo() { return 0; } int main() { return 0; }")
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = UnusedFunctionRule()
    issues = rule.analyze(ast, "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "unused-function"
    assert "foo" in issues[0].message

def test_shadowed_variable(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int x; int main(int x) { { int x; } return x; }")
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = ShadowedVariableRule()
    issues = rule.analyze(ast, "test.c")
    assert len(issues) == 2
    assert issues[0].rule_id == "shadowed-variable"
    assert issues[1].rule_id == "shadowed-variable"

def test_const_index(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { int arr[5]; arr[5] = 1; arr[-1] = 2; arr[0] = 3; }")
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = ConstIndexOutOfBoundsRule()
    issues = rule.analyze(ast, "test.c")
    assert len(issues) == 2
    assert "index 5" in issues[0].message
    assert "index -1" in issues[1].message
    assert issues[0].rule_id == "const-index-out-of-bounds"
