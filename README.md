# AI Code Explanation Tool for Multiple Programming Languages

This project is a stateless AIML major project that explains source code in real time using a pretrained HuggingFace Transformer model and a modular FastAPI backend. It supports Python, C, C++, Java, JavaScript, and SQL without using any database.

## System Architecture

### 1. Frontend Layer
- Built with HTML, CSS, and JavaScript
- Uses CodeMirror as the code editor
- Sends code snippets to the backend through REST APIs
- Displays explanation, complexity, bugs, optimization suggestions, translation, flowchart, and voice output

### 2. Backend Layer
- Built with FastAPI
- Exposes stateless APIs for code analysis and translation
- Orchestrates all processing modules in a single request pipeline

### 3. AI Layer
- Uses pretrained HuggingFace Transformers models
- Higher-capacity default model profile: `Salesforce/codet5p-770m`
- Supports separate checkpoints for explanation, summarization, and translation
- Runs inference with PyTorch and shares model weights when tasks use the same checkpoint

### 4. Processing Modules
- `explain_code.py`: HuggingFace model loader and explanation engine
- `complexity_analyzer.py`: time and space complexity estimation
- `bug_detector.py`: syntax and logical issue detection
- `optimization.py`: optimization suggestions
- `flowchart_generator.py`: Mermaid flowchart generation
- `translator.py`: multi-language code translation
- `voice_explainer.py`: text-to-speech synthesis

## Folder Structure

```text
AI-Code-Explainer/
|-- README.md
|-- requirements.txt
|-- frontend/
|   |-- index.html
|   |-- style.css
|   `-- script.js
|-- backend/
|   |-- __init__.py
|   |-- app.py
|   |-- explain_code.py
|   |-- complexity_analyzer.py
|   |-- bug_detector.py
|   |-- optimization.py
|   |-- flowchart_generator.py
|   |-- translator.py
|   `-- voice_explainer.py
`-- models/
```

## Features

- Multi-language code editor with syntax highlighting
- Line-by-line explanation
- High-level code summary
- Time complexity estimation
- Space complexity estimation
- Bug and warning detection
- Optimization suggestions
- Mermaid flowchart generation
- Cross-language translation
- Voice explanation with `pyttsx3` or `gTTS`

## Model Notes

- Default high-capacity checkpoint: `Salesforce/codet5p-770m`
- Cache directory: `AI-Code-Explainer/models/`
- You can set one shared checkpoint with `CODE_MODEL_NAME`
- You can also override each task independently:
  - `CODE_EXPLANATION_MODEL_NAME`
  - `CODE_SUMMARY_MODEL_NAME`
  - `CODE_TRANSLATION_MODEL_NAME`
- If two tasks use the same checkpoint, the backend reuses the same loaded model instance
- If a model is not downloaded yet or loading fails, the app still runs with heuristic fallbacks so the demo remains usable

## Installation Steps

### 1. Create a virtual environment

```powershell
cd AI-Code-Explainer
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

### 3. Optional: set stronger model checkpoints

```powershell
$env:CODE_MODEL_NAME="Salesforce/codet5p-770m"
$env:CODE_EXPLANATION_MODEL_NAME="Salesforce/codet5p-770m"
$env:CODE_SUMMARY_MODEL_NAME="Salesforce/codet5p-770m"
$env:CODE_TRANSLATION_MODEL_NAME="Salesforce/codet5p-770m"
```

You can replace one of these with `Salesforce/codet5-base-multi-sum` if you want a lighter summarization-focused setup.

### 4. Run the FastAPI backend

```powershell
uvicorn backend.app:app --reload
```

The backend starts at `http://127.0.0.1:8000`.

### 5. Open the frontend

Open `frontend/index.html` in a browser after the backend is running.

## API Endpoints

### `GET /api/health`
Returns backend status and model information.

### `POST /api/analyze`
Analyzes code and returns:
- detected language
- line-wise explanations
- summary
- complexity
- bug list
- optimization suggestions
- Mermaid flowchart
- optional translation

Example request:

```json
{
  "code": "for i in range(5):\n    print(i)",
  "language": "python",
  "target_language": "java"
}
```

### `POST /api/translate`
Translates code from one language to another.

### `POST /api/voice`
Converts explanation text into speech and returns base64 audio.

## Implementation Steps

1. Install dependencies from `requirements.txt`.
2. Load the pretrained CodeT5 model from HuggingFace inside `backend/explain_code.py`.
3. Start FastAPI and initialize the shared modules in `backend/app.py`.
4. Accept code input from the frontend and send it to `/api/analyze`.
5. Generate summary and line explanations with the model.
6. Estimate time and space complexity using pattern-based analysis.
7. Produce an approximate Mermaid flowchart from the code structure.
8. Convert summary text into speech with `pyttsx3` or `gTTS`.
9. Render results in the frontend, including flowchart and audio playback.

## Example Input and Output

### Input

```python
for i in range(5):
    print(i)
```

### Output

- Line 1: A loop iterates from 0 to 4.
- Line 2: The value of `i` is printed in each iteration.
- Summary: The program loops through five numbers and prints each one.
- Time Complexity: `O(n)`
- Space Complexity: `O(1)`

## Testing Instructions

1. Start the backend with `uvicorn backend.app:app --reload`.
2. Open `frontend/index.html`.
3. Paste sample code in Python, Java, C++, JavaScript, or SQL.
4. Click `Analyze Code`.
5. Verify that explanations, complexity, flowchart, and warnings appear.
6. Click `Translate` to convert code to another language.
7. Click `Generate Voice` to listen to the explanation.

## Suggested Viva Points

- Why CodeT5 is suitable for code understanding
- Why the architecture is stateless
- Difference between pretrained inference and model training
- Why heuristic analyzers are combined with the Transformer layer
- Real-time inference tradeoffs on CPU vs GPU

