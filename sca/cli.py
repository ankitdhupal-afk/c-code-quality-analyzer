import sys
import json
import argparse
from sca.frontend.runner import run_cparse
from sca.frontend.loader import load_ast

def main():
    parser = argparse.ArgumentParser(prog="sca", description="Static Code Quality Analyzer for C")
    subparsers = parser.add_subparsers(dest="command")

    parser_tokens = subparsers.add_parser("tokens", help="Dump tokens")
    parser_tokens.add_argument("file", help="Path to the C file")

    parser_parse = subparsers.add_parser("parse", help="Dump AST")
    parser_parse.add_argument("file", help="Path to the C file")

    parser_cfg = subparsers.add_parser("cfg", help="Dump CFG for a function")
    parser_cfg.add_argument("file", help="Path to the C file")
    parser_cfg.add_argument("func", help="Function name")

    parser_liveness = subparsers.add_parser("liveness", help="Dump Liveness IN/OUT sets for a function")
    parser_liveness.add_argument("file", help="Path to the C file")
    parser_liveness.add_argument("func", help="Function name")
    
    parser_score = subparsers.add_parser("score", help="Calculate a code quality score")
    parser_score.add_argument("file", help="Path to the C file")

    parser_analyze = subparsers.add_parser("analyze", help="Analyze code quality")
    parser_analyze.add_argument("file", help="Path to the C file")
    parser_analyze.add_argument("--rule", action="append", help="Only run these rules")
    parser_analyze.add_argument("--disable", action="append", help="Disable these rules")
    parser_analyze.add_argument("--fail-on", default="error,warning", help="Comma-separated severities to exit 1 on")

    args = parser.parse_args()

    if args.command == "tokens":
        data = run_cparse(args.file, tokens_only=True)
        print(json.dumps(data, indent=2))
        
    elif args.command == "parse":
        data = run_cparse(args.file)
        if "unit" not in data:
            print(json.dumps(data, indent=2))
            sys.exit(2)
        ast = load_ast(data)
        import pprint
        pprint.pprint(ast)

    elif args.command == "cfg":
        data = run_cparse(args.file)
        if "unit" not in data:
            sys.exit(2)
        ast = load_ast(data)
        from sca.analysis.cfg import build_cfg
        from sca.ast.nodes import FunctionDef
        found = False
        for item in ast.items:
            if isinstance(item, FunctionDef) and item.name == args.func:
                cfg = build_cfg(item)
                print(cfg.to_string())
                found = True
                break
        if not found:
            print(f"Function {args.func} not found.")

    elif args.command == "liveness":
        data = run_cparse(args.file)
        if "unit" not in data:
            sys.exit(2)
        ast = load_ast(data)
        from sca.analysis.cfg import build_cfg
        from sca.analysis.liveness import LivenessAnalysis
        from sca.ast.nodes import FunctionDef
        found = False
        for item in ast.items:
            if isinstance(item, FunctionDef) and item.name == args.func:
                cfg = build_cfg(item)
                analysis = LivenessAnalysis(cfg)
                analysis.run()
                for b in cfg.blocks:
                    print(f"Block {b.bid}:")
                    print(f"  IN:  {analysis.in_sets[b.bid]}")
                    print(f"  OUT: {analysis.out_sets[b.bid]}")
                found = True
                break
        if not found:
            print(f"Function {args.func} not found.")
            
    elif args.command == "score":
        data = run_cparse(args.file)
        if "unit" not in data:
            print("Failed to parse file.")
            sys.exit(2)
        ast = load_ast(data)
        
        from sca.rules.uninitialized import UninitializedVariableRule
        from sca.rules.unused import UnusedVariableRule, UnusedParameterRule
        from sca.rules.phase7 import UnusedFunctionRule, ShadowedVariableRule, ConstIndexOutOfBoundsRule
        from sca.rules.cfg_rules import UnreachableCodeRule, MissingReturnRule, HighComplexityRule
        from sca.rules.dataflow_rules import DeadStoreRule
        from sca.rules.ast_rules import FunctionTooLongRule, DeepNestingRule, TooManyParamsRule, MagicNumberRule, NamingConventionRule, UnsafeFunctionRule, AssignmentInConditionRule, EmptyBodyRule
        
        rules = [UninitializedVariableRule(), UnusedVariableRule(), UnusedParameterRule(), UnusedFunctionRule(), ShadowedVariableRule(), ConstIndexOutOfBoundsRule(), UnreachableCodeRule(), MissingReturnRule(), HighComplexityRule(), DeadStoreRule(), FunctionTooLongRule(), DeepNestingRule(), TooManyParamsRule(), MagicNumberRule(), NamingConventionRule(), UnsafeFunctionRule(), AssignmentInConditionRule(), EmptyBodyRule()]
        
        all_issues = []
        for r in rules:
            all_issues.extend(r.analyze(ast, args.file))
            
        weights = {
            "uninitialized": 10,
            "const-index-out-of-bounds": 10,
            "unsafe-function": 10,
            
            "dead-store": 5,
            "missing-return": 5,
            "unreachable-code": 5,
            "shadowed-variable": 5,
            "assignment-in-condition": 5,
            
            "unused-variable": 2,
            "unused-parameter": 2,
            "unused-function": 2,
            "magic-number": 2,
            "naming-convention": 1,
            "empty-body": 3,
            "high-complexity": 5,
            "function-too-long": 3,
            "deep-nesting": 4,
            "too-many-params": 3
        }
        
        total_penalty = 0
        deductions = {}
        for issue in all_issues:
            weight = weights.get(issue.rule_id, 2)
            total_penalty += weight
            deductions[issue.rule_id] = deductions.get(issue.rule_id, 0) + weight
            
        score = max(0, 100 - total_penalty)
        
        if score >= 90: grade = "A (Excellent)"
        elif score >= 80: grade = "B (Good)"
        elif score >= 70: grade = "C (Fair)"
        elif score >= 60: grade = "D (Poor)"
        else: grade = "F (Failing)"
        
        print("========================================")
        print(f"       Code Quality Score: {score}/100")
        print(f"       Grade: {grade}")
        print("========================================")
        print(f"Total Issues Found: {len(all_issues)}")
        print("")
        
        if deductions:
            print("Score Deductions by Rule:")
            for rule_id, penalty in sorted(deductions.items(), key=lambda x: x[1], reverse=True):
                print(f"  - {rule_id}: -{penalty} points")
        else:
            print("Perfect code! No deductions.")
            
        print("========================================")

    elif args.command == "analyze":
        data = run_cparse(args.file)
        if "unit" not in data:
            print(json.dumps(data, indent=2))
            sys.exit(2)
        ast = load_ast(data)
        
        from sca.rules.uninitialized import UninitializedVariableRule
        from sca.rules.unused import UnusedVariableRule, UnusedParameterRule
        from sca.rules.phase7 import UnusedFunctionRule, ShadowedVariableRule, ConstIndexOutOfBoundsRule
        from sca.rules.cfg_rules import UnreachableCodeRule, MissingReturnRule, HighComplexityRule
        from sca.rules.dataflow_rules import DeadStoreRule
        from sca.rules.ast_rules import FunctionTooLongRule, DeepNestingRule, TooManyParamsRule, MagicNumberRule, NamingConventionRule, UnsafeFunctionRule, AssignmentInConditionRule, EmptyBodyRule
        
        rules = [UninitializedVariableRule(), UnusedVariableRule(), UnusedParameterRule(), UnusedFunctionRule(), ShadowedVariableRule(), ConstIndexOutOfBoundsRule(), UnreachableCodeRule(), MissingReturnRule(), HighComplexityRule(), DeadStoreRule(), FunctionTooLongRule(), DeepNestingRule(), TooManyParamsRule(), MagicNumberRule(), NamingConventionRule(), UnsafeFunctionRule(), AssignmentInConditionRule(), EmptyBodyRule()]
        
        all_issues = []
        for r in rules:
            all_issues.extend(r.analyze(ast, args.file))

        # Parse inline suppressions from source code
        suppressions = {}
        try:
            with open(args.file, "r") as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    line_num = i + 1
                    import re
                    match1 = re.search(r'sca-disable-next-line[:\s]*([a-z0-9-]+)', line)
                    if match1:
                        rule_id = match1.group(1)
                        if (line_num + 1) not in suppressions:
                            suppressions[line_num + 1] = set()
                        suppressions[line_num + 1].add(rule_id)
                        
                    match2 = re.search(r'sca-disable[:\s]*([a-z0-9-]+)', line)
                    if match2 and not match1:
                        rule_id = match2.group(1)
                        if line_num not in suppressions:
                            suppressions[line_num] = set()
                        suppressions[line_num].add(rule_id)
        except Exception:
            pass
            
        filtered_issues = []
        for issue in all_issues:
            if issue.line in suppressions and issue.rule_id in suppressions[issue.line]:
                continue
            if getattr(args, 'rule', None) and issue.rule_id not in args.rule:
                continue
            if getattr(args, 'disable', None) and issue.rule_id in args.disable:
                continue
            filtered_issues.append(issue)
            
        all_issues = filtered_issues

        out = []
        for issue in all_issues:
            out.append({
                "file": issue.file,
                "line": issue.line,
                "col": issue.col,
                "message": issue.message,
                "rule_id": issue.rule_id
            })
            
        print(json.dumps(out, indent=2))
        
        if out:
            sys.exit(1)

    else:
        parser.print_help()
