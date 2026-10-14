import pytest
import os
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast
from sca.ast import nodes

def test_loader_simple(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { return 0; }")
    data = run_cparse(str(c_file))
    
    ast = load_ast(data)
    assert isinstance(ast, nodes.TranslationUnit)
    assert len(ast.items) == 1
    func = ast.items[0]
    assert isinstance(func, nodes.FunctionDef)
    assert func.name == "main"
    assert isinstance(func.return_type, nodes.BaseType)
    assert func.return_type.name == "int"
    assert len(func.params) == 0
    
    assert isinstance(func.body, nodes.Block)
    assert len(func.body.stmts) == 1
    ret = func.body.stmts[0]
    assert isinstance(ret, nodes.Return)
    assert isinstance(ret.value, nodes.IntLiteral)
    assert ret.value.text == "0"
