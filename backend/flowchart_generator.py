import re
from typing import Dict, List


class FlowchartGenerator:
    def generate(self, code: str, language: str) -> Dict[str, object]:
        lines = [
            line.strip()
            for line in code.splitlines()
            if line.strip() and not line.strip().startswith(("#", "//", "--", "/*", "*"))
        ]
        limited_lines = lines[:12]

        nodes: List[Dict[str, str]] = [{"id": "START", "label": "Start", "shape": "terminal"}]
        for index, line in enumerate(limited_lines, start=1):
            nodes.append(
                {
                    "id": f"N{index}",
                    "label": self._step_label(line, language),
                    "shape": self._node_shape(line),
                }
            )
        nodes.append({"id": "END", "label": "End", "shape": "terminal"})

        mermaid_lines = ["flowchart TD"]
        for node in nodes:
            mermaid_lines.append(f"    {node['id']}{self._mermaid_node(node['shape'], node['label'])}")

        for index in range(len(nodes) - 1):
            mermaid_lines.append(f"    {nodes[index]['id']} --> {nodes[index + 1]['id']}")

        return {
            "mermaid": "\n".join(mermaid_lines),
            "steps": [node["label"] for node in nodes if node["id"] not in {"START", "END"}],
        }

    def _step_label(self, line: str, language: str) -> str:
        lower = line.lower()
        if line.startswith("for") or line.startswith("while"):
            return "Loop or repeated step"
        if lower.startswith("if") or lower.startswith("else if") or lower.startswith("elif"):
            return "Check condition"
        if lower.startswith("else"):
            return "Fallback branch"
        if lower.startswith("return"):
            return "Return result"
        if any(token in line for token in ["print(", "console.log", "System.out.println", "printf(", "cout <<"]):
            return "Display output"
        if language == "sql":
            if lower.startswith("select"):
                return "Fetch records"
            if lower.startswith("where"):
                return "Filter rows"
            if lower.startswith("order by"):
                return "Sort result"
        if re.search(r"^(def|function|class|public class)", line):
            return "Define reusable block"
        return "Process statement"

    def _node_shape(self, line: str) -> str:
        lower = line.lower()
        if line.startswith("for") or line.startswith("while") or lower.startswith("if") or lower.startswith("elif"):
            return "decision"
        if lower.startswith("return"):
            return "terminal"
        return "process"

    def _mermaid_node(self, shape: str, label: str) -> str:
        safe_label = label.replace('"', "'")
        if shape == "terminal":
            return f"([{safe_label}])"
        if shape == "decision":
            return f"{{{safe_label}}}"
        return f"[{safe_label}]"