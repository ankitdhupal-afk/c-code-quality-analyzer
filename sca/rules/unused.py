from typing import List, Set
from sca.rules.base import Rule, Issue
from sca.ast import nodes
from sca.rules.uninitialized import extract_detailed_usage

class UnusedVariableRule(Rule):
    def analyze(self, ast: nodes.TranslationUnit, filename: str) -> List[Issue]:
        issues = []
        for item in ast.items:
            if isinstance(item, nodes.FunctionDef):
                issues.extend(self.analyze_func(item, filename))
        return issues
        
    def analyze_func(self, func: nodes.FunctionDef, filename: str) -> List[Issue]:
        issues = []
        
        # Collect all local variables
        local_vars = []
        
        def find_locals(n: nodes.Node):
            if not n: return
            if isinstance(n, nodes.VarDecl) and not getattr(n, 'is_global', False) and n.name:
                local_vars.append(n)
            
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
        
        # Collect all reads in the function
        reads = set()
        
        def collect_reads(n: nodes.Node):
            if not n: return
            
            # Use extract_detailed_usage for statement-level nodes if possible
            # Actually, extract_detailed_usage can handle any expression/statement!
            r, _ = extract_detailed_usage(n)
            for name, _ in r:
                reads.add(name)
                
            # We don't need to recursively call collect_reads because extract_detailed_usage already traverses the subtree!
        
        # Wait, if we just call extract_detailed_usage on the whole function body:
        r, _ = extract_detailed_usage(func.body)
        for name, _ in r:
            reads.add(name)
            
        for var in local_vars:
            if var.name not in reads:
                issues.append(Issue(
                    file=filename,
                    line=var.loc.line,
                    col=var.loc.col,
                    message=f"Local variable '{var.name}' is declared but never read.",
                    rule_id="unused-variable"
                ))
                
        return issues


class UnusedParameterRule(Rule):
    def analyze(self, ast: nodes.TranslationUnit, filename: str) -> List[Issue]:
        issues = []
        for item in ast.items:
            if isinstance(item, nodes.FunctionDef):
                issues.extend(self.analyze_func(item, filename))
        return issues
        
    def analyze_func(self, func: nodes.FunctionDef, filename: str) -> List[Issue]:
        issues = []
        
        # Skip function if it has no body (it's a prototype, though AST schema distinguishes Prototype)
        if not func.body:
            return issues
            
        reads = set()
        r, _ = extract_detailed_usage(func.body)
        for name, _ in r:
            reads.add(name)
            
        for param in func.params:
            if param.name and not param.name.startswith('_'):
                if param.name not in reads:
                    issues.append(Issue(
                        file=filename,
                        line=param.loc.line,
                        col=param.loc.col,
                        message=f"Parameter '{param.name}' is never referenced.",
                        rule_id="unused-parameter"
                    ))
                    
        return issues
