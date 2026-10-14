import pytest
import os
import json
import subprocess

def test_rule_uninitialized(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { int x; int y = x + 1; return y; }")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path.parent.parent.parent) # point to project root
    
    # We will just run the CLI command `sca analyze test.c` directly
    # Wait, it's easier to run the python module directly.
    import sys
    from sca.frontend.runner import run_cparse
    from sca.frontend.loader import load_ast
    from sca.rules.uninitialized import UninitializedVariableRule
    
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = UninitializedVariableRule()
    issues = rule.analyze(ast, "test.c")
    
    assert len(issues) == 1
    assert issues[0].rule_id == "uninitialized"
    assert issues[0].line == 1
    assert issues[0].message == "Variable 'x' is used uninitialized."

def test_rule_uninitialized_branch(tmp_path):
    c_file = tmp_path / "test.c"
    # x is initialized in one branch, but not the other
    c_file.write_text("int main() { int x; if (1) { x = 2; } else { } return x; }")
    
    from sca.frontend.runner import run_cparse
    from sca.frontend.loader import load_ast
    from sca.rules.uninitialized import UninitializedVariableRule
    
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = UninitializedVariableRule()
    issues = rule.analyze(ast, "test.c")
    
    assert len(issues) == 1
    assert issues[0].rule_id == "uninitialized"
    assert issues[0].message == "Variable 'x' is used uninitialized."

def test_rule_uninitialized_safe(tmp_path):
    c_file = tmp_path / "test.c"
    # x is initialized in all branches
    c_file.write_text("int main() { int x; if (1) { x = 2; } else { x = 3; } return x; }")
    
    from sca.frontend.runner import run_cparse
    from sca.frontend.loader import load_ast
    from sca.rules.uninitialized import UninitializedVariableRule
    
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    
    rule = UninitializedVariableRule()
    issues = rule.analyze(ast, "test.c")
    
    assert len(issues) == 0
