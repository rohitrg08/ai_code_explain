import re
from typing import Dict, List


class OptimizationAdvisor:
    def analyze(self, code: str, language: str, complexity_report: Dict[str, object]) -> List[Dict[str, str]]:
        suggestions: List[Dict[str, str]] = []
        lower = code.lower()

        if complexity_report.get("signals", {}).get("max_loop_depth", 0) >= 2:
            suggestions.append(
                {
                    "title": "Reduce nested loops",
                    "detail": "Consider hash maps, sets, preprocessing, or indexing to avoid repeated full scans inside loops.",
                }
            )

        if language == "python" and re.search(r"for\s+\w+\s+in\s+.*:\s*$", code, flags=re.MULTILINE):
            if ".append(" in code:
                suggestions.append(
                    {
                        "title": "Use comprehensions where suitable",
                        "detail": "List, set, or dictionary comprehensions can make Python data transformations shorter and often faster.",
                    }
                )

        if re.search(r"(for|while).*(\n|\r\n).*([+]=|=.+\+)", code, flags=re.IGNORECASE):
            suggestions.append(
                {
                    "title": "Avoid repeated string concatenation in loops",
                    "detail": "Build a list of fragments and join them once, or use a language-specific builder type like `StringBuilder`.",
                }
            )

        if re.search(r"\bselect\s+\*", lower):
            suggestions.append(
                {
                    "title": "Select only required SQL columns",
                    "detail": "Fetching only necessary columns reduces I/O, memory usage, and network transfer time.",
                }
            )

        if re.search(r"\bin\b", code) and re.search(r"for\s+\w+\s+in", code):
            suggestions.append(
                {
                    "title": "Check membership with efficient containers",
                    "detail": "If repeated membership checks are used, a set or hash-based structure is usually faster than a list scan.",
                }
            )

        if complexity_report.get("signals", {}).get("recursion_detected"):
            suggestions.append(
                {
                    "title": "Review recursion depth",
                    "detail": "Memoization or an iterative approach can reduce repeated calls and lower stack usage in recursive solutions.",
                }
            )

        if any(token in code for token in ["print(", "console.log", "System.out.println", "printf("]) and len(code.splitlines()) > 20:
            suggestions.append(
                {
                    "title": "Limit debug output in production paths",
                    "detail": "Heavy console output can slow execution and make logs harder to read during large runs.",
                }
            )

        if not suggestions:
            suggestions.append(
                {
                    "title": "No major optimization issue detected",
                    "detail": "The current implementation looks reasonable for static analysis. Benchmark with real inputs if you need deeper optimization.",
                }
            )

        return suggestions