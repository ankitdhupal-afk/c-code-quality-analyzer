import os
from sca.frontend.runner import run_cparse

def test_runner_empty_file(tmp_path):
    empty_file = tmp_path / "empty.c"
    empty_file.write_text("")
    
    data = run_cparse(str(empty_file))
    
    assert data["schema_version"] == 1
    assert data["errors"] == []
    assert data["directives"]["includes"] == []
    assert data["directives"]["defines"] == []
    assert data["unit"] is None
