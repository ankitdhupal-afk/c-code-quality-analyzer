import pytest
from sca.service import analyze_source, analyze_file
from sca.recommendations import build_recommendations, apply_edits, Edit, Recommendation

def test_apply_edits_deletion():
    source = "line 1\nline 2\nline 3\n"
    edits = [Edit(line_start=2, line_end=2, expected_old=["line 2"], new=[])]
    out = apply_edits(source, edits)
    assert out == "line 1\nline 3\n"

def test_apply_edits_replacement():
    source = "int x = 5;\n"
    edits = [Edit(line_start=1, line_end=1, expected_old=["int x = 5;"], new=["int x = 10;"])]
    out = apply_edits(source, edits)
    assert out == "int x = 10;\n"

def test_apply_edits_insertion():
    source = "int main() {\n}\n"
    edits = [Edit(line_start=2, line_end=1, expected_old=[], new=["    return 0;"])]
    out = apply_edits(source, edits)
    assert out == "int main() {\n    return 0;\n}\n"

def test_apply_edits_stale_conflict():
    source = "int x = 5;\n"
    edits = [Edit(line_start=1, line_end=1, expected_old=["int y = 0;"], new=["int x = 10;"])]
    with pytest.raises(ValueError, match="Edit conflict"):
        apply_edits(source, edits)

def test_rec_unused_variable():
    code = "int main() {\n    int unused_var;\n    return 0;\n}"
    res = analyze_source(code)
    assert len(res.recommendations) >= 1
    rec = next(r for r in res.recommendations if r["rule_id"] == "unused-variable")
    assert rec["safety"] == "safe"
    assert rec["score_gain"] == 2
    assert len(rec["edits"]) == 1
    assert "unused_var" in rec["title"]

def test_rec_empty_body():
    code = "int main() {\n    if (1);\n    return 0;\n}"
    res = analyze_source(code)
    rec = next(r for r in res.recommendations if r["rule_id"] == "empty-body")
    assert rec["safety"] == "review"
    assert len(rec["edits"]) == 1

def test_rec_assignment_in_condition():
    code = "int main() {\n    int x = 0;\n    if (x = 5)\n        return 1;\n    return 0;\n}"
    res = analyze_source(code)
    rec = next(r for r in res.recommendations if r["rule_id"] == "assignment-in-condition")
    assert rec["safety"] == "review"
    assert len(rec["edits"]) == 1
    assert "==" in rec["edits"][0]["new"][0]

def test_rec_missing_return():
    code = "int foo(int x) {\n    if (x > 0)\n        return 1;\n}"
    res = analyze_source(code)
    rec = next(r for r in res.recommendations if r["rule_id"] == "missing-return")
    assert rec["safety"] == "review"
    assert len(rec["edits"]) == 1
    assert "return 0;" in rec["edits"][0]["new"][0]

def test_rec_uninitialized():
    code = "int main() {\n    int uninit_var;\n    return uninit_var;\n}"
    res = analyze_source(code)
    rec = next(r for r in res.recommendations if r["rule_id"] in ("uninitialized", "uninitialized-variable"))
    assert rec["safety"] == "review"
    assert len(rec["edits"]) == 1
    assert "= 0;" in rec["edits"][0]["new"][0]

def test_rec_unused_parameter():
    code = "int foo(int unused_p) {\n    return 0;\n}"
    res = analyze_source(code)
    rec = next(r for r in res.recommendations if r["rule_id"] == "unused-parameter")
    assert rec["safety"] == "review"
    assert len(rec["edits"]) == 1
    assert "_unused_p" in rec["edits"][0]["new"][0]

def test_rec_manual_rules():
    # Test that structural and stylistic rules give clear manual guidance
    code = """int main() {
    int arr[2];
    arr[5] = 1;
    return 42;
}
"""
    res = analyze_source(code)
    rules_found = {r["rule_id"] for r in res.recommendations}
    assert "const-index-out-of-bounds" in rules_found
    assert "magic-number" in rules_found

    for r in res.recommendations:
        if r["rule_id"] in ("const-index-out-of-bounds", "magic-number"):
            assert r["safety"] == "manual"
            assert len(r["edits"]) == 0
            assert len(r["explanation"]) > 0

def test_projected_score_smelly():
    res = analyze_file("examples/smelly.c")
    assert res.score.value == 98
    assert res.projected_score == 100

# =======================================================================
# MANDATORY PROPERTY TEST
# =======================================================================
@pytest.mark.parametrize("source_snippet, expected_rule", [
    ("int main() {\n    int x;\n    return 0;\n}", "unused-variable"),
    ("int main() {\n    if (1);\n    return 0;\n}", "empty-body"),
    ("int main() {\n    int x = 0;\n    if (x = 5)\n        return 1;\n    return 0;\n}", "assignment-in-condition"),
    ("int foo(int x) {\n    if (x > 0)\n        return 1;\n}", "missing-return"),
    ("int main() {\n    int x;\n    return x;\n}", "uninitialized"),
    ("int main() {\n    return 0;\n    int x = 5;\n}", "unreachable-code"),
    ("int foo(int p) {\n    return 0;\n}", "unused-parameter"),
    ("int main() {\n    char buf[10];\n    gets(buf);\n    return 0;\n}", "unsafe-function"),
])
def test_property_recommendation_fixes(source_snippet, expected_rule):
    """
    Property test (required):
    For every recommendation with safety 'safe' or 'review' and non-empty edits,
    applying the edits to the source and re-running analysis must:
      (a) still parse without syntax errors, and
      (b) no longer contain that specific diagnostic.
    """
    initial_analysis = analyze_source(source_snippet)
    recs = initial_analysis.recommendations

    matching_recs = [r for r in recs if r["rule_id"] == expected_rule]
    assert len(matching_recs) >= 1, f"Expected rule {expected_rule} was not triggered."

    for rec in matching_recs:
        if rec["safety"] in ("safe", "review") and rec["edits"]:
            # Apply edits
            fixed_source = apply_edits(source_snippet, rec["edits"])

            # Re-analyze
            new_analysis = analyze_source(fixed_source)

            # (a) No syntax/parse errors
            assert new_analysis.parse_errors == [], (
                f"Applying edits for {expected_rule} caused syntax error:\n"
                f"{new_analysis.parse_errors}\nModified code:\n{fixed_source}"
            )

            # (b) Diagnostic is eliminated
            new_diags = [d["rule_id"] for d in new_analysis.diagnostics]
            assert expected_rule not in new_diags, (
                f"Rule {expected_rule} was not cleared after applying fix.\n"
                f"Remaining diags: {new_diags}\nModified code:\n{fixed_source}"
            )
