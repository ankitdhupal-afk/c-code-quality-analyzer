import pytest
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast
from sca.rules.cfg_rules import UnreachableCodeRule, MissingReturnRule, HighComplexityRule
from sca.rules.dataflow_rules import DeadStoreRule

def test_unreachable(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { return 0; int x = 1; }")
    data = run_cparse(str(c_file))
    rule = UnreachableCodeRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "unreachable-code"

def test_missing_return(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int foo() { int x = 1; } int main() { } void bar() { }")
    data = run_cparse(str(c_file))
    rule = MissingReturnRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert "foo" in issues[0].message
    assert issues[0].rule_id == "missing-return"

def test_high_complexity(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { if(1){} if(1){} if(1){} if(1){} if(1){} if(1){} if(1){} if(1){} if(1){} if(1){} }")
    data = run_cparse(str(c_file))
    rule = HighComplexityRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "high-complexity"

def test_dead_store(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { int x; x = 1; x = 2; return x; }")
    data = run_cparse(str(c_file))
    rule = DeadStoreRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "dead-store"
