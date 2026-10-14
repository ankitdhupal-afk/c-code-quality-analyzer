import pytest
import os
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast
from sca.analysis.cfg import build_cfg
from sca.analysis.liveness import LivenessAnalysis
from sca.ast import nodes

def test_liveness(tmp_path):
    c_file = tmp_path / "test.c"
    c_file.write_text("int main() { int x = 1; int y = x + 1; return y; }")
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    func = None
    for i in ast.items:
        if isinstance(i, nodes.FunctionDef) and i.name == "main":
            func = i
            break
            
    cfg = build_cfg(func)
    liveness = LivenessAnalysis(cfg)
    liveness.run()
    
    # Check that y is in GEN of the return block, x is in GEN of the y assignment, etc.
    # Since they are all in one block (Block 0 probably), check the whole block
    b0 = cfg.entry
    # Actually block 0 has the statements
    assert "x" in liveness.kill[b0.bid]
    assert "y" in liveness.kill[b0.bid]
    
    # Let's test a branch
    c_file.write_text("int main() { int x; if (1) { x = 2; } else { x = 3; } return x; }")
    data = run_cparse(str(c_file))
    ast = load_ast(data)
    for i in ast.items:
        if isinstance(i, nodes.FunctionDef) and i.name == "main":
            func = i
            break
    cfg = build_cfg(func)
    liveness = LivenessAnalysis(cfg)
    liveness.run()
    
    # the return block should have 'x' in its IN set
    # find the block with return statement
    ret_b = None
    for b in cfg.blocks:
        for stmt in b.statements:
            if isinstance(stmt, nodes.Return):
                ret_b = b
    assert "x" in liveness.in_sets[ret_b.bid]
