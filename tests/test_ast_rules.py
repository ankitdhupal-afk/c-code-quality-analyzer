import pytest
import os
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast
from sca.rules.ast_rules import *

def test_deep_nesting(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { if(1) { if(1) { if(1) { if(1) { if(1) {} } } } } }")
    data = run_cparse(str(c_file))
    rule = DeepNestingRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "deep-nesting"

def test_too_many_params(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("void f(int a, int b, int c, int d, int e, int f) {}")
    data = run_cparse(str(c_file))
    rule = TooManyParamsRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "too-many-params"

def test_magic_number(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { int x = 42; const int y = 42; int z[42]; switch(x){ case 42: break; } return 0; }")
    data = run_cparse(str(c_file))
    rule = MagicNumberRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert "42" in issues[0].message
    assert issues[0].rule_id == "magic-number"

def test_unsafe_function(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { char buf[10]; gets(buf); scanf(\"%s\", buf); scanf(\"%10s\", buf); }")
    data = run_cparse(str(c_file))
    rule = UnsafeFunctionRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 2
    assert issues[0].rule_id == "unsafe-function"
    assert "gets" in issues[0].message
    assert "scanf" in issues[1].message

def test_assignment_in_condition(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { int x; if (x = 5) { } }")
    data = run_cparse(str(c_file))
    rule = AssignmentInConditionRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "assignment-in-condition"

def test_empty_body(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { if (1); }")
    data = run_cparse(str(c_file))
    rule = EmptyBodyRule()
    issues = rule.analyze(load_ast(data), "test.c")
    assert len(issues) == 1
    assert issues[0].rule_id == "empty-body"
