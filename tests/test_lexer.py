import os
from sca.frontend.runner import run_cparse_tokens, run_cparse

def test_lexer_tokens(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int x = 42; // comment\n/* block */ float y;")
    
    tokens = run_cparse_tokens(str(c_file))
    
    assert len(tokens) == 8
    assert tokens[0]["kind"] == "INT"
    assert tokens[1]["kind"] == "IDENT"
    assert tokens[1]["text"] == "x"
    assert tokens[2]["kind"] == "="
    assert tokens[3]["kind"] == "INT_LITERAL"
    assert tokens[3]["text"] == "42"
    assert tokens[4]["kind"] == ";"
    # comments are skipped
    assert tokens[5]["kind"] == "FLOAT"
    assert tokens[6]["kind"] == "IDENT"
    assert tokens[6]["text"] == "y"
    assert tokens[7]["kind"] == ";"

def test_lexer_directives(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("#include <stdio.h>\n#define MAX 100\nint main;")
    
    data = run_cparse(str(c_file))
    
    assert len(data["directives"]["includes"]) == 1
    assert data["directives"]["includes"][0]["text"] == "<stdio.h>"
    
    assert len(data["directives"]["defines"]) == 1
    assert data["directives"]["defines"][0]["name"] == "MAX"
    assert data["directives"]["defines"][0]["value"] == "100"

def test_lexer_errors(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("\"unterminated;")
    
    data = run_cparse(str(c_file))
    assert len(data["errors"]) == 1
    assert "unterminated string literal" in data["errors"][0]["message"]
