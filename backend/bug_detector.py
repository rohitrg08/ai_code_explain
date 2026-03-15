import ast
import re
from typing import Dict, List


class BugDetector:
    def detect(self, code: str, language: str) -> List[Dict[str, object]]:
        issues: List[Dict[str, object]] = []
        issues.extend(self._check_brackets(code))

        normalized = (language or "").lower()
        if normalized == "python":
            issues.extend(self._check_python_issues(code))
        elif normalized in {"c", "c++", "java", "javascript"}:
            issues.extend(self._check_curly_language_issues(code, normalized))
        elif normalized == "sql":
            issues.extend(self._check_sql_issues(code))

        return sorted(issues, key=lambda item: (self._severity_rank(item["severity"]), item["line"]))

    def _check_brackets(self, code: str) -> List[Dict[str, object]]:
        pairs = {")": "(", "]": "[", "}": "{"}
        opening = set(pairs.values())
        stack: List[tuple[str, int]] = []
        issues: List[Dict[str, object]] = []

        line_number = 1
        for character in code:
            if character == "\n":
                line_number += 1
                continue
            if character in opening:
                stack.append((character, line_number))
            elif character in pairs:
                if not stack or stack[-1][0] != pairs[character]:
                    issues.append(
                        {
                            "line": line_number,
                            "severity": "error",
                            "message": f"Unmatched closing bracket `{character}` detected.",
                        }
                    )
                else:
                    stack.pop()

        for bracket, origin_line in stack:
            issues.append(
                {
                    "line": origin_line,
                    "severity": "error",
                    "message": f"Opening bracket `{bracket}` does not have a matching closing bracket.",
                }
            )
        return issues

    def _check_python_issues(self, code: str) -> List[Dict[str, object]]:
        issues: List[Dict[str, object]] = []

        try:
            ast.parse(code)
        except SyntaxError as exc:
            issues.append(
                {
                    "line": exc.lineno or 1,
                    "severity": "error",
                    "message": f"Python syntax error: {exc.msg}.",
                }
            )

        mutable_default_pattern = re.compile(r"def\s+\w+\(.*=\s*(\[\]|\{\}).*\):")
        for line_no, line in enumerate(code.splitlines(), start=1):
            if mutable_default_pattern.search(line):
                issues.append(
                    {
                        "line": line_no,
                        "severity": "warning",
                        "message": "Mutable default argument detected. Use `None` and create the object inside the function.",
                    }
                )
            if "== None" in line or "!= None" in line:
                issues.append(
                    {
                        "line": line_no,
                        "severity": "warning",
                        "message": "Prefer `is None` or `is not None` for identity comparison with None.",
                    }
                )
            if re.search(r"while\s+True\s*:", line) and "break" not in code:
                issues.append(
                    {
                        "line": line_no,
                        "severity": "warning",
                        "message": "Potential infinite loop: `while True` is present without an obvious `break` statement.",
                    }
                )
        return issues

    def _check_curly_language_issues(self, code: str, language: str) -> List[Dict[str, object]]:
        issues: List[Dict[str, object]] = []
        lines = code.splitlines()

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue

            if re.search(r"\bif\s*\([^)]*=[^=][^)]*\)", line):
                issues.append(
                    {
                        "line": line_no,
                        "severity": "warning",
                        "message": "Assignment inside an `if` condition may be a logical mistake.",
                    }
                )

            if language == "javascript" and "==" in line and "===" not in line:
                issues.append(
                    {
                        "line": line_no,
                        "severity": "warning",
                        "message": "Use strict equality (`===`) when possible to avoid type-coercion bugs.",
                    }
                )

            if language in {"c", "c++", "java"}:
                allowed_endings = (";", "{", "}", ":", ",")
                control_starts = ("if", "for", "while", "else", "switch", "case", "do", "@")
                if (
                    not line.endswith(allowed_endings)
                    and not line.startswith(control_starts)
                    and "(" not in line
                    and ")" not in line
                ):
                    issues.append(
                        {
                            "line": line_no,
                            "severity": "info",
                            "message": "This line may be missing a semicolon.",
                        }
                    )

        return issues

    def _check_sql_issues(self, code: str) -> List[Dict[str, object]]:
        issues: List[Dict[str, object]] = []
        lines = code.splitlines()
        full_sql = " ".join(line.strip() for line in lines).lower()

        if re.search(r"\bupdate\b", full_sql) and " where " not in full_sql:
            issues.append(
                {
                    "line": 1,
                    "severity": "warning",
                    "message": "UPDATE without WHERE can modify every row in the table.",
                }
            )
        if re.search(r"\bdelete\s+from\b", full_sql) and " where " not in full_sql:
            issues.append(
                {
                    "line": 1,
                    "severity": "warning",
                    "message": "DELETE without WHERE can remove every row in the table.",
                }
            )
        for line_no, line in enumerate(lines, start=1):
            if re.search(r"\bselect\s+\*", line, flags=re.IGNORECASE):
                issues.append(
                    {
                        "line": line_no,
                        "severity": "info",
                        "message": "Selecting all columns can be inefficient. Specify only the required columns when possible.",
                    }
                )
        return issues

    def _severity_rank(self, severity: str) -> int:
        order = {"error": 0, "warning": 1, "info": 2}
        return order.get(severity, 3)