/**
 * script.js
 * Frontend controller for the AI-Based Knowledge Retrieval Platform.
 * Handles document upload, query execution, and dynamic UI rendering.
 */

// ============================================================
// DOM Element References
// ============================================================

const fileInput        = document.getElementById("file-input");
const dropZone         = document.getElementById("drop-zone");
const documentsList    = document.getElementById("documents-list");
const chunkCountBadge  = document.getElementById("chunk-count-badge");
const uploadError      = document.getElementById("upload-error");
const uploadProgressArea = document.getElementById("upload-progress-area");
const uploadStatusLabel  = document.getElementById("upload-status-label");
const uploadProgressBar  = document.getElementById("upload-progress-bar");

const queryInput       = document.getElementById("query-input");
const askBtn           = document.getElementById("ask-btn");
const micBtn           = document.getElementById("mic-btn");
const micIcon          = document.getElementById("mic-icon");
const micLabel         = document.getElementById("mic-label");
const speakBtn         = document.getElementById("speak-btn");
const queryError       = document.getElementById("query-error");
const queryStatusArea  = document.getElementById("query-status-area");
const pipelineSteps    = document.getElementById("pipeline-steps");


const answerArea       = document.getElementById("answer-area");
const answerText       = document.getElementById("answer-text");
const confidenceBadge  = document.getElementById("confidence-badge");

const sourcesArea      = document.getElementById("sources-area");
const sourcesList      = document.getElementById("sources-list");

const debugArea        = document.getElementById("debug-area");
const debugToggleBtn   = document.getElementById("debug-toggle-btn");
const debugContent     = document.getElementById("debug-content");
const debugToggleIcon  = document.getElementById("debug-toggle-icon");

const refreshDocsBtn   = document.getElementById("refresh-docs-btn");
const resetBtn         = document.getElementById("reset-btn");
const sampleDocsList   = document.getElementById("sample-docs-list");


// ============================================================
// Initialization
// ============================================================

window.addEventListener("DOMContentLoaded", () => {
    loadDocuments();
    loadSampleDocs();
    setupDropZone();
});


// ============================================================
// Section: Document Upload
// ============================================================

/** Set up drag-and-drop event handlers on the drop zone element. */
function setupDropZone() {
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.classList.add("drag-over");
    });
    dropZone.addEventListener("dragleave", () => {
        dropZone.classList.remove("drag-over");
    });
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file) handleFileUpload(file);
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files[0]) handleFileUpload(fileInput.files[0]);
    });
}

/** Uploads a file to the Flask /upload endpoint and updates the UI. */
async function handleFileUpload(file) {
    // Clear previous errors
    hideElement(uploadError);
    showUploadProgress("Uploading file...", 15);

    const formData = new FormData();
    formData.append("file", file);

    try {
        showUploadProgress("Extracting text content...", 35);

        const response = await fetch("/upload", {
            method: "POST",
            body: formData,
        });
        const data = await response.json();

        if (!response.ok || data.error) {
            showError(uploadError, data.error || "Upload failed. Please try again.");
            hideUploadProgress();
            return;
        }

        showUploadProgress("Generating embeddings...", 65);
        await sleep(300); // Brief visual pause for UX

        showUploadProgress("Writing to vector index...", 85);
        await sleep(300);

        showUploadProgress("Indexed successfully!", 100);
        await sleep(700);
        hideUploadProgress();

        // Refresh the document list
        loadDocuments();

        // Reset file input so the same file can be re-uploaded if needed
        fileInput.value = "";

    } catch (err) {
        showError(uploadError, "Network error: Could not reach the server.");
        hideUploadProgress();
    }
}

/** Shows upload progress bar and label. */
function showUploadProgress(label, percent) {
    showElement(uploadProgressArea);
    uploadStatusLabel.textContent = label;
    uploadProgressBar.style.width = percent + "%";
}

/** Hides the upload progress bar. */
function hideUploadProgress() {
    setTimeout(() => {
        hideElement(uploadProgressArea);
        uploadProgressBar.style.width = "0%";
    }, 400);
}


// ============================================================
// Section: Document List
// ============================================================

/** Fetches indexed document metadata from /documents and renders the list. */
async function loadDocuments() {
    try {
        const response = await fetch("/documents");
        const data = await response.json();
        renderDocumentsList(data.documents || []);

        if (data.total_chunks > 0) {
            chunkCountBadge.textContent = `${data.total_chunks} chunks indexed`;
            showElement(chunkCountBadge);
        } else {
            hideElement(chunkCountBadge);
        }
    } catch (err) {
        documentsList.innerHTML = `<p class="empty-state">Could not load document list.</p>`;
    }
}

/** Renders the list of indexed documents. */
function renderDocumentsList(docs) {
    if (docs.length === 0) {
        documentsList.innerHTML = `<p class="empty-state">No documents indexed yet.</p>`;
        return;
    }
    documentsList.innerHTML = docs.map(doc => {
        const ext = doc.document_type ? doc.document_type.toLowerCase() : "other";
        const iconClass = `doc-icon-${ext}`;
        const meta = doc.pages && doc.pages.length > 0
            ? `${doc.chunk_count} chunks — Pages: ${doc.pages.join(", ")}`
            : `${doc.chunk_count} chunks`;
        return `
            <div class="doc-item">
                <div class="doc-item-icon ${iconClass}">${doc.document_type || "?"}</div>
                <div class="doc-item-info">
                    <div class="doc-item-name" title="${escapeHtml(doc.document_name)}">${escapeHtml(doc.document_name)}</div>
                    <div class="doc-item-meta">${meta}</div>
                </div>
            </div>
        `;
    }).join("");
}

refreshDocsBtn.addEventListener("click", () => loadDocuments());


// ============================================================
// Section: Sample Documents
// ============================================================

/** Loads sample document list from /sample_docs. */
async function loadSampleDocs() {
    try {
        const response = await fetch("/sample_docs");
        const data = await response.json();
        renderSampleDocs(data.samples || []);
    } catch (err) {
        sampleDocsList.innerHTML = `<p class="hint-text">Could not load sample documents.</p>`;
    }
}

/** Renders sample document items with "Load" buttons. */
function renderSampleDocs(samples) {
    if (samples.length === 0) {
        sampleDocsList.innerHTML = `<p class="hint-text">No sample documents found.</p>`;
        return;
    }
    sampleDocsList.innerHTML = samples.map(s => `
        <div class="sample-doc-item">
            <span class="sample-doc-name">${escapeHtml(s.filename)}</span>
            <span class="sample-doc-size">${s.size_kb} KB</span>
            <button class="btn btn-outline btn-sm" onclick="loadSampleDocument('${escapeHtml(s.filename)}', this)">Load</button>
        </div>
    `).join("");
}

/** Loads a specific sample document via /load_sample endpoint. */
async function loadSampleDocument(filename, btn) {
    btn.disabled = true;
    btn.textContent = "Loading...";
    hideElement(uploadError);

    try {
        const response = await fetch("/load_sample", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename }),
        });
        const data = await response.json();

        if (!response.ok || data.error) {
            showError(uploadError, data.error || "Failed to load sample.");
            btn.disabled = false;
            btn.textContent = "Load";
            return;
        }

        btn.textContent = "Loaded";
        btn.style.color = "var(--color-success)";
        btn.style.borderColor = "var(--color-success)";
        loadDocuments();

    } catch (err) {
        showError(uploadError, "Network error loading sample.");
        btn.disabled = false;
        btn.textContent = "Load";
    }
}


// ============================================================
// Section: Query Execution
// ============================================================

askBtn.addEventListener("click", runQuery);

queryInput.addEventListener("keydown", (e) => {
    // Allow Ctrl+Enter or Shift+Enter to submit
    if (e.key === "Enter" && (e.ctrlKey || e.shiftKey)) {
        e.preventDefault();
        runQuery();
    }
});

/** Submits the user's question to /query and renders results. */
async function runQuery() {
    const question = queryInput.value.trim();

    hideElement(queryError);
    hideElement(answerArea);
    hideElement(sourcesArea);
    hideElement(debugArea);

    if (!question) {
        showError(queryError, "Please enter a question before submitting.");
        return;
    }

    askBtn.disabled = true;
    askBtn.textContent = "Searching...";

    // Show pipeline steps
    showElement(queryStatusArea);
    renderPipelineSteps([
        { id: "step-query",     label: "Received Query",          state: "done" },
        { id: "step-embed",     label: "Generating Embedding",    state: "active" },
        { id: "step-search",    label: "Semantic Search",         state: "pending" },
        { id: "step-filter",    label: "Relevance Filtering",     state: "pending" },
        { id: "step-generate",  label: "Generating Answer",       state: "pending" },
    ]);

    try {
        // Animate pipeline steps sequentially
        await sleep(400);
        updateStep("step-embed", "done");
        updateStep("step-search", "active");

        const response = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });
        const data = await response.json();

        updateStep("step-search", "done");
        updateStep("step-filter", "active");
        await sleep(300);
        updateStep("step-filter", "done");
        updateStep("step-generate", "active");
        await sleep(300);

        if (!response.ok || data.error) {
            showError(queryError, data.error || "Query failed. Please try again.");
            updateStep("step-generate", "error");
            askBtn.disabled = false;
            askBtn.textContent = "Ask Question";
            return;
        }

        updateStep("step-generate", "done");

        // Render answer, sources, and debug panel
        renderAnswer(data);
        renderSources(data.sources || []);
        renderDebugPanel(data.debug_details || {}, question, data.answer);

    } catch (err) {
        showError(queryError, "Network error: Could not reach the server.");
        clearPipelineSteps();
    }

    askBtn.disabled = false;
    askBtn.textContent = "Ask Question";
}

/** Renders pipeline status step indicators. */
function renderPipelineSteps(steps) {
    pipelineSteps.innerHTML = steps.map((step, idx) => `
        ${idx > 0 ? '<span class="step-connector">&#8594;</span>' : ""}
        <span class="pipeline-step ${step.state === "active" ? "active" : step.state === "done" ? "done" : ""}"
              id="${step.id}">
            ${step.label}
        </span>
    `).join("");
}

function updateStep(id, state) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = `pipeline-step ${state}`;
}

function clearPipelineSteps() {
    hideElement(queryStatusArea);
}


// ============================================================
// Section: Answer Rendering
// ============================================================

/** Renders the generated answer and confidence badge. */
function renderAnswer(data) {
    const confidence = data.confidence || "None";
    const badgeClass = confidenceBadgeClass(confidence);

    confidenceBadge.className = `badge ${badgeClass}`;
    confidenceBadge.textContent = `Confidence: ${confidence}`;

    answerText.textContent = data.answer || "No answer returned.";
    showElement(answerArea);
}

function confidenceBadgeClass(confidence) {
    switch (confidence.toLowerCase()) {
        case "high":   return "badge-high";
        case "medium": return "badge-medium";
        case "low":    return "badge-low";
        default:       return "badge-none";
    }
}


// ============================================================
// Section: Sources Rendering
// ============================================================

/** Renders the retrieved source cards with expandable chunk text. */
function renderSources(sources) {
    if (!sources || sources.length === 0) {
        hideElement(sourcesArea);
        return;
    }

    const scoreClass = (rel) => {
        switch ((rel || "").toLowerCase()) {
            case "high":   return "badge-high";
            case "medium": return "badge-medium";
            case "low":    return "badge-low";
            default:       return "badge-none";
        }
    };

    sourcesList.innerHTML = sources.map((src, idx) => {
        const pageMeta = src.page_number
            ? `Page ${src.page_number}`
            : src.row_number
            ? `Row ${src.row_number}`
            : "Full document";

        const scorePercent = Math.round((src.similarity_score || 0) * 100);

        return `
            <div class="source-card">
                <div class="source-card-header" onclick="toggleSource(${idx})">
                    <div class="source-info">
                        <div class="source-title">${idx + 1}. ${escapeHtml(src.document_name)}</div>
                        <div class="source-meta">${pageMeta} &mdash; Similarity: ${scorePercent}%</div>
                    </div>
                    <span class="badge source-score-badge ${scoreClass(src.relevance)}">${escapeHtml(src.relevance || "N/A")}</span>
                    <span class="expand-icon" id="expand-icon-${idx}">+</span>
                </div>
                <div class="source-card-body" id="source-body-${idx}">
                    <p class="hint-text" style="margin-bottom:0.5rem;">Retrieved chunk text:</p>
                    <div class="source-chunk-text">${escapeHtml(src.full_text || src.text_snippet || "")}</div>
                </div>
            </div>
        `;
    }).join("");

    showElement(sourcesArea);
}

/** Toggles the expand/collapse state of a source chunk card. */
function toggleSource(idx) {
    const body = document.getElementById(`source-body-${idx}`);
    const icon = document.getElementById(`expand-icon-${idx}`);
    if (!body || !icon) return;

    const isOpen = body.classList.toggle("open");
    icon.textContent = isOpen ? "−" : "+";
    icon.classList.toggle("open", isOpen);
}


// ============================================================
// Section: Retrieval Details (Explainability Mode)
// ============================================================

debugToggleBtn.addEventListener("click", () => {
    const isOpen = debugContent.style.display !== "none";
    debugContent.style.display = isOpen ? "none" : "block";
    debugToggleIcon.textContent = isOpen ? "+" : "−";
});

/** Populates the explainability panel with RAG pipeline step data. */
function renderDebugPanel(debug, question, answer) {
    showElement(debugArea);

    // Ensure it starts collapsed
    debugContent.style.display = "none";
    debugToggleIcon.textContent = "+";

    // Step 1: Query
    setDebugValue("dbg-query", question);

    // Step 2: Embedding Shape
    const shape = debug.query_embedding_shape || [];
    setDebugValue("dbg-embedding", `Vector shape: [${shape.join(", ")}] (normalized float32)`);

    // Step 3: All retrieved chunks
    const allChunks = debug.all_retrieved_chunks || [];
    if (allChunks.length > 0) {
        const chunksText = allChunks.map((c, i) =>
            `[${i+1}] Score: ${(c.similarity_score || 0).toFixed(4)} | ${c.document_name} | ${c.text ? c.text.slice(0, 80) + "..." : "N/A"}`
        ).join("\n");
        setDebugValue("dbg-all-chunks", chunksText);
    } else {
        setDebugValue("dbg-all-chunks", "No chunks retrieved (empty knowledge base or FAISS index issue).");
    }

    // Step 4: Scores
    const scores = allChunks.map((c, i) =>
        `[${i+1}] ${(c.similarity_score || 0).toFixed(4)} — ${c.relevance || "N/A"}`
    ).join("\n");
    setDebugValue("dbg-scores", scores || "No scores available.");

    // Step 5: Selected context (only those that passed threshold)
    const selectedCount = debug.selected_chunks_count || 0;
    const totalCount    = debug.retrieved_chunks_count || 0;
    setDebugValue("dbg-selected", `${selectedCount} of ${totalCount} chunks passed the similarity threshold and were used as context.`);

    // Step 6: Generator mode
    setDebugValue("dbg-generator", debug.generator_mode || "Unknown");

    // Step 7: Final answer
    setDebugValue("dbg-final-answer", answer || "No answer generated.");
}

function setDebugValue(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}


// ============================================================
// Section: Reset Knowledge Base
// ============================================================

resetBtn.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to clear the entire knowledge base? This cannot be undone.")) return;

    try {
        const response = await fetch("/reset", { method: "POST" });
        const data = await response.json();
        if (data.success) {
            loadDocuments();
            hideElement(answerArea);
            hideElement(sourcesArea);
            hideElement(debugArea);
            hideElement(queryStatusArea);
        }
    } catch (err) {
        alert("Could not reset the knowledge base. Please try again.");
    }
});

// ============================================================
// Section: Web Speech API Integration (STT & TTS)
// ============================================================


let recognition = null;
let isRecording = false;

// Check Web Speech API SpeechRecognition availability
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
        isRecording = true;
        micBtn.classList.add("mic-recording");
        micIcon.textContent = "⏹️";
        micLabel.textContent = "Listening...";
        hideElement(queryError);
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        queryInput.value = transcript;
        micLabel.textContent = "Voice Input";
        micIcon.textContent = "🎤";
        micBtn.classList.remove("mic-recording");
        isRecording = false;
        // Automatically trigger query if recognized clearly
        if (transcript.trim().length > 3) {
            runQuery();
        }
    };


    recognition.onerror = (event) => {
        console.warn("Speech recognition error:", event.error);
        micBtn.classList.remove("mic-recording");
        micIcon.textContent = "🎤";
        micLabel.textContent = "Voice Input";
        isRecording = false;
        if (event.error !== "no-speech") {
            showError(queryError, `Speech recognition error: ${event.error}`);
        }
    };

    recognition.onend = () => {
        micBtn.classList.remove("mic-recording");
        micIcon.textContent = "🎤";
        micLabel.textContent = "Voice Input";
        isRecording = false;
    };
}

if (micBtn) {
    micBtn.addEventListener("click", () => {
        if (!recognition) {
            alert("Web Speech API is not supported in this browser. Please use Chrome, Edge, or Safari.");
            return;
        }

        if (isRecording) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch (err) {
                console.warn("Recognition already started or error:", err);
            }
        }
    });
}

// Web Speech API Text-to-Speech (speechSynthesis)
if (speakBtn) {
    speakBtn.addEventListener("click", () => {
        if (!("speechSynthesis" in window)) {
            alert("Text-to-Speech is not supported in your browser.");
            return;
        }

        if (window.speechSynthesis.speaking) {
            window.speechSynthesis.cancel();
            speakBtn.textContent = "🔊 Read Aloud";
            return;
        }

        const textToRead = answerText.textContent.trim();
        if (!textToRead) return;

        const utterance = new SpeechSynthesisUtterance(textToRead);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        utterance.lang = "en-US";

        utterance.onstart = () => {
            speakBtn.textContent = "⏹️ Stop";
        };

        utterance.onend = () => {
            speakBtn.textContent = "🔊 Read Aloud";
        };

        utterance.onerror = () => {
            speakBtn.textContent = "🔊 Read Aloud";
        };

        window.speechSynthesis.speak(utterance);
    });
}



// ============================================================
// Utility Functions
// ============================================================

/** Pause execution for a given number of milliseconds. */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/** Escapes HTML special characters to prevent XSS. */
function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function showElement(el) { if (el) el.style.display = ""; }
function hideElement(el) { if (el) el.style.display = "none"; }

function showError(el, message) {
    if (!el) return;
    el.textContent = message;
    showElement(el);
}
