from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from backend.bug_detector import BugDetector
    from backend.complexity_analyzer import ComplexityAnalyzer
    from backend.explain_code import CodeExplanationEngine
    from backend.flowchart_generator import FlowchartGenerator
    from backend.optimization import OptimizationAdvisor
    from backend.translator import CodeTranslator
    from backend.voice_explainer import VoiceExplainer
except ImportError:
    from bug_detector import BugDetector
    from complexity_analyzer import ComplexityAnalyzer
    from explain_code import CodeExplanationEngine
    from flowchart_generator import FlowchartGenerator
    from optimization import OptimizationAdvisor
    from translator import CodeTranslator
    from voice_explainer import VoiceExplainer


class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1)
    language: Optional[str] = "python"
    target_language: Optional[str] = None


class TranslateRequest(BaseModel):
    code: str = Field(..., min_length=1)
    source_language: str = Field(..., min_length=1)
    target_language: str = Field(..., min_length=1)


class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    explainer = CodeExplanationEngine()
    app.state.explainer = explainer
    app.state.complexity = ComplexityAnalyzer()
    app.state.bug_detector = BugDetector()
    app.state.optimizer = OptimizationAdvisor()
    app.state.flowchart = FlowchartGenerator()
    app.state.translator = CodeTranslator(explainer)
    app.state.voice = VoiceExplainer()
    yield


app = FastAPI(
    title="AI Code Explanation Tool",
    description="Stateless multi-language code analysis with HuggingFace Transformers.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "AI Code Explanation Tool backend is running.",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model": app.state.explainer.get_model_info(),
    }


@app.post("/api/analyze")
def analyze_code(request: AnalyzeRequest):
    code = request.code.strip("\n")
    if not code.strip():
        raise HTTPException(status_code=400, detail="Code input cannot be empty.")

    language = request.language or app.state.explainer.detect_language(code)
    if language.lower() == "auto":
        language = app.state.explainer.detect_language(code)

    line_explanations = app.state.explainer.explain_code_lines(code, language)
    summary = app.state.explainer.summarize_code(code, language)
    complexity = app.state.complexity.analyze(code, language)
    bugs = app.state.bug_detector.detect(code, language)
    optimizations = app.state.optimizer.analyze(code, language, complexity)
    flowchart = app.state.flowchart.generate(code, language)

    translation = None
    if request.target_language:
        translation = app.state.translator.translate(code, language, request.target_language)

    return {
        "language": language,
        "summary": summary,
        "line_explanations": line_explanations,
        "complexity": complexity,
        "bugs": bugs,
        "optimizations": optimizations,
        "flowchart": flowchart,
        "translation": translation,
        "narration_text": app.state.explainer.compose_narration(summary, line_explanations),
        "model": app.state.explainer.get_model_info(),
    }


@app.post("/api/translate")
def translate_code(request: TranslateRequest):
    return app.state.translator.translate(
        request.code,
        request.source_language,
        request.target_language,
    )


@app.post("/api/voice")
def voice_explanation(request: VoiceRequest):
    try:
        return app.state.voice.synthesize(request.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)