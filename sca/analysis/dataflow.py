from typing import Set, Dict, List, Any
from sca.analysis.cfg import CFG, BasicBlock

class DataflowAnalysis:
    def __init__(self, cfg: CFG, forward: bool = True):
        self.cfg = cfg
        self.forward = forward
        self.in_sets: Dict[int, Set[Any]] = {b.bid: set() for b in cfg.blocks}
        self.out_sets: Dict[int, Set[Any]] = {b.bid: set() for b in cfg.blocks}
        
    def meet(self, block: BasicBlock) -> Set[Any]:
        res = set()
        if self.forward:
            preds = block.preds
            if preds:
                for p in preds:
                    res.update(self.out_sets[p.bid])
        else:
            succs = block.succs
            if succs:
                for s in succs:
                    res.update(self.in_sets[s.bid])
        return res
        
    def transfer(self, block: BasicBlock, in_val: Set[Any]) -> Set[Any]:
        raise NotImplementedError
        
    def run(self):
        worklist = list(self.cfg.blocks)
        
        while worklist:
            b = worklist.pop(0)
            meet_val = self.meet(b)
            
            if self.forward:
                self.in_sets[b.bid] = meet_val
                new_out = self.transfer(b, meet_val)
                if new_out != self.out_sets[b.bid]:
                    self.out_sets[b.bid] = new_out
                    for s in b.succs:
                        if s not in worklist:
                            worklist.append(s)
            else:
                self.out_sets[b.bid] = meet_val
                new_in = self.transfer(b, meet_val)
                if new_in != self.in_sets[b.bid]:
                    self.in_sets[b.bid] = new_in
                    for p in b.preds:
                        if p not in worklist:
                            worklist.append(p)
