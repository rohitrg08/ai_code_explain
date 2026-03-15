const FALLBACK_API_BASE = "https://ai-code-explain.onrender.com";

const inferredOrigin =
  window.location.origin && window.location.origin.startsWith("http")
    ? window.location.origin
    : FALLBACK_API_BASE;

const API_BASE = inferredOrigin.includes(":8000")
  ? inferredOrigin
  : FALLBACK_API_BASE;
  
const languageModeMap = {
    python: "python",
    c: "text/x-csrc",
    "c++": "text/x-c++src",
    java: "text/x-java",
    javascript: "javascript",
    sql: "text/x-sql",
    auto: "python",
};

let editor;
let lastAnalysis = null;

mermaid.initialize({ startOnLoad: false, theme: "neutral" });

function initializeEditor() {
    editor = CodeMirror.fromTextArea(document.getElementById("codeInput"), {
        lineNumbers: true,
        mode: languageModeMap.python,
        theme: "default",
        indentUnit: 4,
        tabSize: 4,
        lineWrapping: true,
    });
}

function setStatus(message, kind = "info") {
    const pill = document.getElementById("statusPill");
    pill.textContent = message;
    pill.style.background = kind === "error"
        ? "rgba(209, 67, 67, 0.15)"
        : "rgba(13, 148, 136, 0.12)";
    pill.style.color = kind === "error" ? "#a92d2d" : "#0b6e66";
}

function getSelectedLanguage() {
    return document.getElementById("languageSelect").value;
}

function getTargetLanguage() {
    return document.getElementById("targetLanguageSelect").value;
}

function switchEditorMode() {
    const language = getSelectedLanguage();
    editor.setOption("mode", languageModeMap[language] || "python");
}

async function fetchHealth() {
    try {
        const response = await fetch(`${API_BASE}/api/health`);
        const data = await response.json();
        document.getElementById("modelOutput").textContent = JSON.stringify(data.model, null, 2);
        setStatus(data.model.model_ready ? "Backend connected and model ready" : "Backend connected with heuristic fallback");
    } catch (error) {
        setStatus("Backend connection failed", "error");
        document.getElementById("modelOutput").textContent = String(error);
    }
}

function renderComplexity(complexity) {
    const container = document.getElementById("complexityOutput");
    container.innerHTML = `
        <p><strong>Time Complexity:</strong> ${complexity.time_complexity}</p>
        <p><strong>Space Complexity:</strong> ${complexity.space_complexity}</p>
        <p class="meta-line">${complexity.time_reasoning.join(" ")}</p>
        <p class="meta-line">${complexity.space_reasoning.join(" ")}</p>
    `;
}

function renderLineExplanations(lines) {
    const container = document.getElementById("lineExplanationOutput");
    if (!lines.length) {
        container.innerHTML = "<p>No line explanations available.</p>";
        return;
    }

    container.innerHTML = lines.map((item) => `
        <div class="line-item">
            <div class="meta-line">Line ${item.line_number}</div>
            <div class="line-code">${escapeHtml(item.code || " ")}</div>
            <div>${escapeHtml(item.explanation)}</div>
        </div>
    `).join("");
}

function renderIssues(targetId, items, emptyMessage, includeSeverity = false) {
    const container = document.getElementById(targetId);
    if (!items || !items.length) {
        container.innerHTML = `<p>${emptyMessage}</p>`;
        return;
    }

    container.innerHTML = items.map((item) => {
        const severityClass = includeSeverity ? `severity-${item.severity}` : "";
        const title = item.title || `${item.severity?.toUpperCase() || "INFO"} - Line ${item.line || "-"}`;
        const detail = item.detail || item.message;
        return `
            <div class="list-item ${severityClass}">
                <strong>${escapeHtml(title)}</strong>
                <div>${escapeHtml(detail)}</div>
            </div>
        `;
    }).join("");
}

async function renderFlowchart(flowchart) {
    const container = document.getElementById("flowchartOutput");
    container.innerHTML = `<div class="mermaid">${flowchart.mermaid}</div>`;
    try {
        await mermaid.run({ querySelector: ".mermaid" });
    } catch (error) {
        container.textContent = flowchart.mermaid;
    }
}

function renderTranslation(translation) {
    const container = document.getElementById("translationOutput");
    if (!translation) {
        container.textContent = "Run Analyze + Translate to see converted code.";
        return;
    }

    container.textContent = `${translation.translated_code}\n\nMethod: ${translation.method}\nNote: ${translation.note}`;
}

function renderAnalysis(data) {
    lastAnalysis = data;
    document.getElementById("summaryOutput").textContent = data.summary;
    document.getElementById("modelOutput").textContent = JSON.stringify(data.model, null, 2);
    renderComplexity(data.complexity);
    renderLineExplanations(data.line_explanations);
    renderIssues("bugOutput", data.bugs, "No obvious bugs or warnings detected.", true);
    renderIssues("optimizationOutput", data.optimizations, "No optimization suggestions generated.");
    renderTranslation(data.translation);
    renderFlowchart(data.flowchart);
    setStatus(`Analysis completed for ${data.language}`);
}

async function analyzeCode(includeTranslation = false) {
    const code = editor.getValue();
    if (!code.trim()) {
        setStatus("Please enter code before analysis", "error");
        return;
    }

    setStatus("Analyzing code...");
    try {
        const response = await fetch(`${API_BASE}/api/analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code,
                language: getSelectedLanguage(),
                target_language: includeTranslation ? getTargetLanguage() : null,
            }),
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        const data = await response.json();
        renderAnalysis(data);
    } catch (error) {
        setStatus("Analysis failed", "error");
        document.getElementById("summaryOutput").textContent = String(error);
    }
}

async function generateVoice() {
    if (!lastAnalysis) {
        await analyzeCode(false);
        if (!lastAnalysis) {
            return;
        }
    }

    setStatus("Generating voice narration...");
    try {
        const response = await fetch(`${API_BASE}/api/voice`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: lastAnalysis.narration_text }),
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        const data = await response.json();
        const audioPlayer = document.getElementById("audioPlayer");
        audioPlayer.src = `data:${data.mime_type};base64,${data.audio_base64}`;
        document.getElementById("voiceMeta").textContent = `Voice generated using ${data.engine}.`;
        setStatus("Voice narration ready");
    } catch (error) {
        setStatus("Voice generation failed", "error");
        document.getElementById("voiceMeta").textContent = String(error);
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

document.addEventListener("DOMContentLoaded", () => {
    initializeEditor();
    fetchHealth();
    document.getElementById("languageSelect").addEventListener("change", switchEditorMode);
    document.getElementById("analyzeBtn").addEventListener("click", () => analyzeCode(false));
    document.getElementById("translateBtn").addEventListener("click", () => analyzeCode(true));
    document.getElementById("voiceBtn").addEventListener("click", generateVoice);
});