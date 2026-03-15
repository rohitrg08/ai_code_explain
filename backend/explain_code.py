import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer


MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

LANGUAGE_LABELS = {
    "python": "Python",
    "c": "C",
    "c++": "C++",
    "java": "Java",
    "javascript": "JavaScript",
    "sql": "SQL",
}


@dataclass
class LoadedTaskModel:
    model_name: str
    tokenizer: Any = None
    model: Any = None
    available: bool = False
    load_error: str = ""


@dataclass
class LineExplanation:
    line_number: int
    code: str
    explanation: str


def normalize_language(language: str) -> str:
    raw = (language or "python").strip().lower()
    aliases = {
        "py": "python",
        "cpp": "c++",
        "cxx": "c++",
        "js": "javascript",
        "node": "javascript",
        "mysql": "sql",
        "postgres": "sql",
        "postgresql": "sql",
    }
    return aliases.get(raw, raw if raw in LANGUAGE_LABELS else "python")


class CodeExplanationEngine:
    def __init__(self, model_name: str | None = None, cache_dir: str | None = None) -> None:
        shared_default_model = model_name or os.getenv("CODE_MODEL_NAME", "Salesforce/codet5p-770m")
        self.cache_dir = cache_dir or str(MODELS_DIR)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.task_model_names = {
            "explanation": os.getenv("CODE_EXPLANATION_MODEL_NAME", shared_default_model),
            "summary": os.getenv("CODE_SUMMARY_MODEL_NAME", shared_default_model),
            "translation": os.getenv("CODE_TRANSLATION_MODEL_NAME", shared_default_model),
        }
        self.task_models: Dict[str, LoadedTaskModel] = {}
        self._shared_registry: Dict[str, LoadedTaskModel] = {}
        self._load_models()

    def _load_models(self) -> None:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        for task_name, model_name in self.task_model_names.items():
            if model_name in self._shared_registry:
                self.task_models[task_name] = self._shared_registry[model_name]
                continue

            bundle = LoadedTaskModel(model_name=model_name)
            try:
                bundle.tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    cache_dir=self.cache_dir,
                    use_fast=False,
                )
                bundle.model = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir=self.cache_dir,
                )
                bundle.model.to(self.device)
                bundle.model.eval()
                bundle.available = True
            except Exception as exc:
                bundle.available = False
                bundle.load_error = str(exc)

            self._shared_registry[model_name] = bundle
            self.task_models[task_name] = bundle

    def detect_language(self, code: str) -> str:
        text = code.strip()
        lower = text.lower()

        if any(token in text for token in ["#include", "cout <<", "std::", "using namespace std"]):
            return "c++"
        if "#include" in text or "printf(" in text or "scanf(" in text:
            return "c"
        if any(token in text for token in ["System.out.println", "public class", "public static void main"]):
            return "java"
        if any(token in text for token in ["console.log", "function ", "=>", "==="]):
            return "javascript"
        if any(token in lower for token in ["select ", "update ", "delete ", "insert into ", "from "]):
            return "sql"
        if re.search(r"^\s*def\s+\w+\(", text, flags=re.MULTILINE) or "print(" in text:
            return "python"
        return "python"

    def summarize_code(self, code: str, language: str) -> str:
        language = normalize_language(language)
        heuristic = self._heuristic_summary(code, language)
        prompt = (
            f"Summarize this {LANGUAGE_LABELS[language]} code in 2 concise sentences. "
            f"Focus on the program goal, main logic, and output.\n{code}\nSummary:"
        )
        ai_summary = self.generate_text(prompt, max_new_tokens=96, task="summary")
        return self._prefer_ai_text(ai_summary, heuristic)

    def explain_code_lines(self, code: str, language: str) -> List[Dict[str, str | int]]:
        language = normalize_language(language)
        lines = code.splitlines()
        non_empty_lines = [(index + 1, line) for index, line in enumerate(lines) if line.strip()]
        ai_explanations = {}

        if non_empty_lines:
            numbered_code = "\n".join(f"{line_no}: {text}" for line_no, text in non_empty_lines)
            token_budget = min(384, 24 * len(non_empty_lines) + 32)
            prompt = (
                f"Explain each numbered line of this {LANGUAGE_LABELS[language]} code. "
                f"Return one short explanation per line using the same numbers.\n"
                f"{numbered_code}\nExplanations:"
            )
            generated = self.generate_text(prompt, max_new_tokens=token_budget, task="explanation")
            ai_explanations = self._parse_numbered_explanations(generated)

        output: List[Dict[str, str | int]] = []
        for index, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped:
                explanation = "Blank line used to improve readability."
            else:
                heuristic = self._heuristic_line_explanation(raw_line, language)
                explanation = self._prefer_ai_text(ai_explanations.get(index, ""), heuristic)
            output.append(
                {
                    "line_number": index,
                    "code": raw_line,
                    "explanation": explanation,
                }
            )
        return output

    def compose_narration(self, summary: str, line_explanations: List[Dict[str, str | int]]) -> str:
        selected_lines = [
            f"Line {item['line_number']}: {item['explanation']}"
            for item in line_explanations
            if str(item["code"]).strip()
        ][:8]
        if not selected_lines:
            return summary
        return f"{summary}\n" + "\n".join(selected_lines)

    def get_model_info(self) -> Dict[str, object]:
        model_usage_count: Dict[str, int] = {}
        for model_name in self.task_model_names.values():
            model_usage_count[model_name] = model_usage_count.get(model_name, 0) + 1

        explanation_model = self.task_models.get("explanation")
        return {
            "model_name": explanation_model.model_name if explanation_model else "",
            "model_ready": any(bundle.available for bundle in self.task_models.values()),
            "device": str(self.device),
            "cache_dir": self.cache_dir,
            "tasks": {
                task_name: {
                    "model_name": bundle.model_name,
                    "model_ready": bundle.available,
                    "shared_instance": model_usage_count.get(bundle.model_name, 0) > 1,
                    "load_error": bundle.load_error,
                }
                for task_name, bundle in self.task_models.items()
            },
        }

    def generate_text(self, prompt: str, max_new_tokens: int = 96, task: str = "explanation") -> str:
        bundle = self.task_models.get(task) or self.task_models.get("explanation")
        if bundle is None or not bundle.available or bundle.tokenizer is None or bundle.model is None:
            return ""

        try:
            inputs = bundle.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512,
            )
            inputs = {key: value.to(self.device) for key, value in inputs.items()}

            with torch.no_grad():
                outputs = bundle.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    num_beams=4,
                    early_stopping=True,
                    temperature=0.2,
                )
            return self._clean_text(bundle.tokenizer.decode(outputs[0], skip_special_tokens=True))
        except Exception:
            return ""

    def _parse_numbered_explanations(self, generated_text: str) -> Dict[int, str]:
        explanations: Dict[int, str] = {}
        for raw_line in generated_text.splitlines():
            match = re.match(r"^\s*(\d+)\s*[:.\-]\s*(.+)$", raw_line.strip())
            if match:
                explanations[int(match.group(1))] = self._clean_text(match.group(2))
        return explanations

    def _prefer_ai_text(self, ai_text: str, fallback: str) -> str:
        cleaned = self._clean_text(ai_text)
        if self._looks_like_valid_ai_output(cleaned):
            return cleaned
        return fallback

    def _looks_like_valid_ai_output(self, text: str) -> bool:
        if not text or len(text.split()) < 3:
            return False
        blacklist = ["<pad>", "summarize", "translate", "explanations:"]
        return not any(token in text.lower() for token in blacklist)

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _heuristic_summary(self, code: str, language: str) -> str:
        lower = code.lower()
        loop_count = len(re.findall(r"\b(for|while)\b", lower))
        condition_count = len(re.findall(r"\b(if|else if|elif|case|when)\b", lower))
        function_count = len(re.findall(r"\b(def|function|public .*?\(|private .*?\(|int .*?\()", code))

        if language == "sql":
            if "select" in lower:
                return "This SQL query retrieves records from one or more tables, optionally filtering or sorting the result."
            if "update" in lower:
                return "This SQL statement updates rows in a table based on the provided condition."
            if "insert" in lower:
                return "This SQL statement inserts new rows into a table."
            if "delete" in lower:
                return "This SQL statement removes rows from a table."

        pieces = ["This code"]
        if function_count:
            pieces.append(f"defines {function_count} function or method blocks")
        if loop_count:
            pieces.append(f"uses {loop_count} loop construct(s)")
        if condition_count:
            pieces.append(f"contains {condition_count} conditional branch(es)")
        if any(token in code for token in ["print(", "console.log", "System.out.println", "printf(", "cout <<"]):
            pieces.append("produces output")
        if len(pieces) == 1:
            pieces.append("performs a sequence of operations")
        return ", ".join(pieces) + "."

    def _heuristic_line_explanation(self, line: str, language: str) -> str:
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped:
            return "Blank line used to improve readability."
        if stripped.startswith(("#", "//", "/*", "*", "--")):
            return "This is a comment that documents or explains the code."
        if re.match(r"^(from\s+\w+\s+import|import\s+\w+)", stripped):
            return "This line imports a module or dependency."
        if re.match(r"^def\s+(\w+)\(", stripped):
            name = re.findall(r"^def\s+(\w+)\(", stripped)[0]
            return f"This line defines the function `{name}`."
        if re.match(r"^(public|private|protected)?\s*(static\s+)?class\s+\w+", stripped):
            return "This line defines a class."
        if re.match(r"^class\s+\w+", stripped):
            return "This line defines a class."
        if re.match(r"^for\s+.+\s+in\s+range\((.+)\):", stripped):
            return "This line starts a loop that iterates through a numeric range."
        if re.match(r"^for\s+.+\s+in\s+.+:", stripped):
            return "This line starts a loop that iterates through a collection."
        if stripped.startswith("for "):
            return "This line starts a loop that repeats a block of code."
        if re.match(r"^for\s*\(", stripped):
            return "This line starts a loop with initialization, condition, and update expressions."
        if stripped.startswith("while "):
            return "This line starts a loop that continues while a condition remains true."
        if lower.startswith("if ") or lower.startswith("if("):
            return "This line checks a condition before executing the next block."
        if lower.startswith("elif ") or lower.startswith("else if"):
            return "This line defines an alternative condition to evaluate."
        if lower.startswith("else"):
            return "This line defines the fallback branch when earlier conditions are false."
        if stripped.startswith("return"):
            return "This line returns a value from the current function or method."
        if any(token in stripped for token in ["print(", "console.log", "System.out.println", "printf(", "cout <<"]):
            return "This line outputs a value or message."
        if language == "sql":
            if lower.startswith("select"):
                return "This line selects columns or expressions from a table."
            if lower.startswith("from"):
                return "This line specifies the source table for the query."
            if lower.startswith("where"):
                return "This line filters rows using a condition."
            if lower.startswith("group by"):
                return "This line groups rows for aggregation."
            if lower.startswith("order by"):
                return "This line sorts the query result."
            if lower.startswith("update"):
                return "This line updates rows in a table."
            if lower.startswith("delete"):
                return "This line deletes rows from a table."
            if lower.startswith("insert"):
                return "This line inserts new data into a table."

        typed_assignment = re.match(
            r"^(int|float|double|char|bool|boolean|long|short|String|var|auto)\s+(\w+)\s*=\s*(.+?);?$",
            stripped,
        )
        if typed_assignment:
            return f"This line creates the variable `{typed_assignment.group(2)}` and assigns it a value."

        python_assignment = re.match(r"^([A-Za-z_]\w*)\s*=\s*(.+)$", stripped)
        if python_assignment:
            return f"This line assigns a value to the variable `{python_assignment.group(1)}`."

        if re.match(r"^[A-Za-z_]\w*\(.*\);?$", stripped):
            return "This line calls a function or method."

        return "This line performs an operation as part of the program logic."