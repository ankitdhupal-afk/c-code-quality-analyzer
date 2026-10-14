from sca.analysis.dataflow import DataflowAnalysis
from sca.analysis.cfg import CFG, BasicBlock
from sca.ast import nodes
from typing import Set

def extract_usage(node: nodes.Node):
    reads = set()
    writes = set()
    
    def visit(n: nodes.Node, is_lvalue: bool = False):
        if not n: return
        
        if isinstance(n, nodes.Identifier):
            if is_lvalue:
                writes.add(n.name)
            else:
                reads.add(n.name)
        elif isinstance(n, nodes.Assign):
            if n.op == '=':
                visit(n.value, False)
                visit(n.target, True)
            else:
                visit(n.value, False)
                visit(n.target, False)
                visit(n.target, True)
        elif isinstance(n, (nodes.Unary, nodes.Postfix)):
            if n.op in ('INC_OP', 'DEC_OP', '++', '--'):
                visit(n.operand, False)
                visit(n.operand, True)
            else:
                visit(n.operand, False)
        elif isinstance(n, nodes.VarDecl):
            if n.init:
                visit(n.init, False)
            if n.name:
                writes.add(n.name)
        else:
            if hasattr(n, '__dataclass_fields__'):
                for field in n.__dataclass_fields__:
                    val = getattr(n, field)
                    if isinstance(val, nodes.Node):
                        visit(val, False)
                    elif isinstance(val, list):
                        for item in val:
                            if isinstance(item, nodes.Node):
                                visit(item, False)
                                
    visit(node, False)
    return reads, writes

class LivenessAnalysis(DataflowAnalysis):
    def __init__(self, cfg: CFG):
        super().__init__(cfg, forward=False)
        self.gen: dict[int, Set[str]] = {}
        self.kill: dict[int, Set[str]] = {}
        
        for b in cfg.blocks:
            b_gen = set()
            b_kill = set()
            for stmt in b.statements:
                r, w = extract_usage(stmt)
                for var in r:
                    if var not in b_kill:
                        b_gen.add(var)
                for var in w:
                    b_kill.add(var)
            self.gen[b.bid] = b_gen
            self.kill[b.bid] = b_kill
            
    def transfer(self, block: BasicBlock, out_val: Set[str]) -> Set[str]:
        return self.gen[block.bid].union(out_val - self.kill[block.bid])
