from dataclasses import dataclass
from typing import List
from sca.ast.nodes import TranslationUnit

@dataclass
class Issue:
    file: str
    line: int
    col: int
    message: str
    rule_id: str

class Rule:
    def analyze(self, ast: TranslationUnit, filename: str) -> List[Issue]:
        raise NotImplementedError
