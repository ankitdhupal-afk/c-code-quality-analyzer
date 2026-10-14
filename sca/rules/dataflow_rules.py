from typing import List, Set
from sca.rules.base import Rule, Issue
from sca.ast import nodes
from sca.analysis.cfg import build_cfg
from sca.analysis.liveness import LivenessAnalysis
from sca.rules.uninitialized import extract_detailed_usage

class DeadStoreRule(Rule):
    def analyze(self, ast: nodes.TranslationUnit, filename: str) -> List[Issue]:
        issues = []
        for item in ast.items:
            if isinstance(item, nodes.FunctionDef):
                issues.extend(self.analyze_func(item, filename))
        return issues
        
    def analyze_func(self, func: nodes.FunctionDef, filename: str) -> List[Issue]:
        issues = []
        cfg = build_cfg(func)
        
        # Only check local variables
        local_vars = set()
        def find_locals(n: nodes.Node):
            if not n: return
            if isinstance(n, nodes.VarDecl) and not getattr(n, 'is_global', False) and n.name:
                local_vars.add(n.name)
            if hasattr(n, '__dataclass_fields__'):
                for field in n.__dataclass_fields__:
                    val = getattr(n, field)
                    if isinstance(val, nodes.Node):
                        find_locals(val)
                    elif isinstance(val, list):
                        for i in val:
                            if isinstance(i, nodes.Node):
                                find_locals(i)
        find_locals(func.body)
        
        liveness = LivenessAnalysis(cfg)
        liveness.run()
        
        for b in cfg.blocks:
            live = set(liveness.out_sets[b.bid])
            for stmt in reversed(b.statements):
                r, w = extract_detailed_usage(stmt)
                
                # Check dead stores
                for var in w:
                    if var in local_vars and var not in live:
                        # Dead store!
                        # Find the exact location of the write in this stmt
                        # extract_detailed_usage doesn't return write locations, so we just use stmt location
                        loc = stmt.loc
                        if loc:
                            issues.append(Issue(
                                file=filename,
                                line=loc.line,
                                col=loc.col,
                                message=f"Value assigned to '{var}' is never read (dead store).",
                                rule_id="dead-store"
                            ))
                            
                # Update live set: remove writes, add reads
                live -= w
                for name, _ in r:
                    live.add(name)
                    
        return issues
