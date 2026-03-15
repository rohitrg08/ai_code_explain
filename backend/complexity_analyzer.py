import re
from typing import Dict, List


class ComplexityAnalyzer:
    def analyze(self, code: str, language: str) -> Dict[str, object]:
        cleaned_lines = [
            line.rstrip()
            for line in code.splitlines()
            if line.strip() and not line.strip().startswith(("#", "//", "--", "/*", "*"))
        ]

        loop_count = self._count_patterns(cleaned_lines, [r"\bfor\b", r"\bwhile\b"])
        max_loop_depth = self._estimate_loop_depth(cleaned_lines)
        recursion = self._detect_recursion(code)
        sort_usage = bool(re.search(r"\bsort\s*\(|\border\s+by\b", code, flags=re.IGNORECASE))
        collection_usage = bool(
            re.search(r"\b(list|dict|set|map|vector|array|deque|stack|queue)\b", code, flags=re.IGNORECASE)
        )

        time_complexity = "O(1)"
        time_reasoning: List[str] = ["No dominant loop or recursion pattern was detected."]

        if sort_usage:
            time_complexity = "O(n log n)"
            time_reasoning = ["Sorting or ordered retrieval usually dominates runtime with O(n log n) behavior."]
        elif max_loop_depth >= 3:
            time_complexity = "O(n^3)"
            time_reasoning = ["Three nested loop levels suggest cubic growth."]
        elif max_loop_depth == 2:
            time_complexity = "O(n^2)"
            time_reasoning = ["Two nested loop levels suggest quadratic growth."]
        elif loop_count >= 1:
            time_complexity = "O(n)"
            time_reasoning = ["A single main loop suggests linear growth with input size."]

        if recursion and time_complexity == "O(1)":
            time_complexity = "O(n)"
            time_reasoning = ["Recursive calls were detected, so runtime grows with recursion depth or input size."]
        if recursion and re.search(r"/\s*2|\bmid\b|\bleft\b|\bright\b|\blow\b|\bhigh\b", code):
            time_complexity = "O(log n)"
            time_reasoning = ["The recursive pattern looks like divide-and-conquer or binary splitting."]

        space_complexity = "O(1)"
        space_reasoning: List[str] = ["No large auxiliary data structure was clearly detected."]

        if recursion and time_complexity == "O(log n)":
            space_complexity = "O(log n)"
            space_reasoning = ["Recursive divide-and-conquer usually uses logarithmic call-stack space."]
        elif recursion:
            space_complexity = "O(n)"
            space_reasoning = ["Recursive execution can consume linear stack space in the worst case."]
        if collection_usage:
            space_complexity = "O(n)"
            space_reasoning = ["The code appears to use a collection whose size may scale with the input."]
        if re.search(r"\[\s*\[", code) or re.search(r"\bmatrix\b|\btable\b", code, flags=re.IGNORECASE):
            space_complexity = "O(n^2)"
            space_reasoning = ["A matrix-like structure suggests quadratic memory usage."]

        return {
            "time_complexity": time_complexity,
            "space_complexity": space_complexity,
            "time_reasoning": time_reasoning,
            "space_reasoning": space_reasoning,
            "signals": {
                "loop_count": loop_count,
                "max_loop_depth": max_loop_depth,
                "recursion_detected": recursion,
                "sort_usage": sort_usage,
            },
        }

    def _count_patterns(self, lines: List[str], patterns: List[str]) -> int:
        count = 0
        for line in lines:
            if any(re.search(pattern, line) for pattern in patterns):
                count += 1
        return count

    def _estimate_loop_depth(self, lines: List[str]) -> int:
        max_depth = 0
        indent_stack: List[int] = []
        brace_depth = 0

        for raw_line in lines:
            stripped = raw_line.strip()
            if re.search(r"\bfor\b|\bwhile\b", stripped):
                indent = len(raw_line) - len(raw_line.lstrip(" "))
                while indent_stack and indent <= indent_stack[-1]:
                    indent_stack.pop()
                indent_stack.append(indent)
                max_depth = max(max_depth, len(indent_stack))

            brace_depth += stripped.count("{")
            brace_depth -= stripped.count("}")
            if brace_depth > max_depth and re.search(r"\bfor\b|\bwhile\b", stripped):
                max_depth = brace_depth

        return max(max_depth, 0)

    def _detect_recursion(self, code: str) -> bool:
        function_names = re.findall(
            r"(?:def|function|int|float|double|char|bool|boolean|void|String)\s+([A-Za-z_]\w*)\s*\(",
            code,
        )
        for name in function_names:
            occurrences = len(re.findall(rf"\b{name}\s*\(", code))
            if occurrences > 1:
                return True
        return False