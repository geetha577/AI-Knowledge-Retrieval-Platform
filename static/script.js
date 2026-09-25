/**
 * script.js
 * AI-Based Knowledge Retrieval Platform — Milestone 3
 * Conversational Multi-Agent Query Resolution, Ambiguity Clarification & Ingestion UI
 */

"use strict";

// ============================================================
// DOM Element References
// ============================================================

// Sidebar: Upload & Knowledge Base
const dropZone          = document.getElementById("drop-zone");
const fileInput         = document.getElementById("file-input");
const uploadError       = document.getElementById("upload-error");
const uploadProgressArea= document.getElementById("upload-progress-area");
const uploadStatusLabel = document.getElementById("upload-status-label");
const uploadProgressBar = document.getElementById("upload-progress-bar");
const documentsList     = document.getElementById("documents-list");
const chunkCountBadge   = document.getElementById("chunk-count-badge");
const refreshDocsBtn    = document.getElementById("refresh-docs-btn");
const sampleDocsList    = document.getElementById("sample-docs-list");
const resetBtn          = document.getElementById("reset-btn");
const healthBadge       = document.getElementById("health-badge");

// Chat & Query Stream
const chatStream        = document.getElementById("chat-stream");
const emptyChatState    = document.getElementById("empty-chat-state");
const clearChatBtn      = document.getElementById("clear-chat-btn");
const liveProgressArea  = document.getElementById("live-progress-area");
const progressStepsTrail= document.getElementById("progress-steps-trail");

// Input Area
const queryInput        = document.getElementById("query-input");
const askBtn            = document.getElementById("ask-btn");
const queryError        = document.getElementById("query-error");
const activeSessionInd  = document.getElementById("active-session-indicator");
const sessionText       = document.getElementById("session-text");
const cancelSessionBtn  = document.getElementById("cancel-session-btn");
const voiceInputBtn     = document.getElementById("voice-input-btn");
const voiceStatusBar    = document.getElementById("voice-status-bar");
const voiceStatusText   = document.getElementById("voice-status-text");
const stopVoiceBtn      = document.getElementById("stop-voice-btn");

// Application State
let currentConvId = null;
let currentSessionId = null;
let currentOriginalQuery = null;
let isProcessing = false;
let speechRecognizer = null;
let isRecording = false;


// ============================================================
// Initialization
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
    loadDocuments();
    loadSampleDocs();
    setupEventListeners();
    setupAutoResizeTextarea();
    setupVoiceInput();
});


function setupEventListeners() {
    // File upload
    if (fileInput) fileInput.addEventListener("change", handleFileSelect);
    if (dropZone) {
        dropZone.addEventListener("dragover", handleDragOver);
        dropZone.addEventListener("dragleave", handleDragLeave);
        dropZone.addEventListener("drop", handleDrop);
    }

    // Refresh & Reset
    if (refreshDocsBtn) refreshDocsBtn.addEventListener("click", loadDocuments);
    if (resetBtn) resetBtn.addEventListener("click", handleResetKnowledgeBase);

    // Query Actions
    if (askBtn) askBtn.addEventListener("click", () => submitQuery());
    if (clearChatBtn) clearChatBtn.addEventListener("click", handleClearChat);
    if (cancelSessionBtn) cancelSessionBtn.addEventListener("click", handleCancelSession);

    // Enter to send, Shift+Enter for newline
    if (queryInput) {
        queryInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submitQuery();
            }
        });
    }

    // Suggested prompt cards in empty state
    document.querySelectorAll(".prompt-card").forEach(card => {
        card.addEventListener("click", () => {
            const query = card.getAttribute("data-query");
            if (query) {
                queryInput.value = query;
                submitQuery(query);
            }
        });
    });
}


function setupAutoResizeTextarea() {
    if (!queryInput) return;
    queryInput.addEventListener("input", () => {
        queryInput.style.height = "auto";
        queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + "px";
    });
}


// ============================================================
// Section: System Health & Knowledge Base Management
// ============================================================

async function checkHealth() {
    try {
        const res = await fetch("/health");
        if (res.ok) {
            const data = await res.json();
            updateChunkBadge(data.total_chunks || 0);
        }
    } catch (err) {
        console.warn("Health check failed:", err);
    }
}

async function loadDocuments() {
    try {
        const res = await fetch("/documents");
        if (!res.ok) throw new Error("Failed to fetch documents.");
        const data = await res.json();
        const docs = data.documents || [];
        const totalChunks = data.total_chunks || 0;

        renderDocumentsList(docs);
        updateChunkBadge(totalChunks);
    } catch (err) {
        if (documentsList) {
            documentsList.innerHTML = `<p class="empty-state">Could not load documents list.</p>`;
        }
    }
}


function renderDocumentsList(docs) {
    if (!documentsList) return;
    if (!docs || docs.length === 0) {
        documentsList.innerHTML = `<p class="empty-state">No documents indexed yet.</p>`;
        return;
    }

    documentsList.innerHTML = docs.map(doc => `
        <div class="doc-item">
            <div class="doc-item-name" title="${escapeHtml(doc.document_name)}">
                ${escapeHtml(doc.document_name)}
            </div>
            <div class="doc-item-meta">
                ${doc.total_chunks} chunk${doc.total_chunks === 1 ? "" : "s"}
            </div>
        </div>
    `).join("");
}

function updateChunkBadge(count) {
    if (!chunkCountBadge) return;
    if (count > 0) {
        chunkCountBadge.textContent = `${count} chunks`;
        showElement(chunkCountBadge);
    } else {
        hideElement(chunkCountBadge);
    }
}

async function loadSampleDocs() {
    if (!sampleDocsList) return;
    try {
        const res = await fetch("/sample_docs");
        if (!res.ok) return;
        const data = await res.json();
        const samples = data.samples || [];

        if (samples.length === 0) {
            sampleDocsList.innerHTML = `<p class="hint-text">No sample documents found.</p>`;
            return;
        }

        sampleDocsList.innerHTML = samples.map(doc => `
            <button class="sample-doc-btn" onclick="loadSampleFile('${escapeHtml(doc.filename)}')">
                <span>${escapeHtml(doc.filename)}</span>
                <span class="format-badge">${(doc.type || doc.format || "DOC").toUpperCase()}</span>
            </button>
        `).join("");
    } catch (err) {
        console.warn("Error loading sample docs:", err);
    }
}

async function loadSampleFile(filename) {
    hideElement(uploadError);
    showUploadProgress("Indexing sample document...");

    try {
        // Bug Fix: use POST /load_sample with JSON body, not URL param
        const res = await fetch("/load_sample", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename }),
        });
        const data = await res.json();
        hideUploadProgress();

        if (!res.ok || data.error) {
            showError(uploadError, data.error || "Failed to index sample.");
        } else {
            showUploadSuccess(`✅ "${data.document_name}" loaded — ${data.chunks_created} chunks indexed.`);
            await loadDocuments();
        }
    } catch (err) {
        hideUploadProgress();
        showError(uploadError, "Network error loading sample document.");
    }
}



async function handleResetKnowledgeBase() {
    if (!confirm("Are you sure you want to clear the knowledge base and all active clarification sessions?")) {
        return;
    }

    try {
        const res = await fetch("/reset", { method: "POST" });
        if (res.ok) {
            handleCancelSession();
            handleClearChat();
            await loadDocuments();
            alert("Knowledge base and clarification sessions successfully cleared.");
        }
    } catch (err) {
        alert("Failed to reset knowledge base. Please try again.");
    }
}


// ============================================================
// Section: Document Upload Handlers
// ============================================================

function handleDragOver(e) {
    e.preventDefault();
    if (dropZone) dropZone.classList.add("dragover");
}

function handleDragLeave() {
    if (dropZone) dropZone.classList.remove("dragover");
}

function handleDrop(e) {
    e.preventDefault();
    if (dropZone) dropZone.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFile(files[0]);
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) uploadFile(files[0]);
}

async function uploadFile(file) {
    hideElement(uploadError);
    hideElement(uploadSuccessMsg());
    const allowed = ["pdf", "docx", "txt", "csv"];
    const ext = file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showError(uploadError, `Unsupported format '.${ext}'. Please upload PDF, DOCX, TXT, or CSV.`);
        return;
    }

    showUploadProgress(`Uploading & indexing ${file.name}...`);

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/upload", { method: "POST", body: formData });
        const data = await res.json();
        hideUploadProgress();

        if (!res.ok || data.error) {
            showError(uploadError, data.error || "Upload failed.");
        } else {
            if (fileInput) fileInput.value = "";
            showUploadSuccess(`✅ "${data.document_name}" indexed — ${data.chunks_created} chunks created.`);
            await loadDocuments();
        }
    } catch (err) {
        hideUploadProgress();
        showError(uploadError, "Network error during upload.");
    }
}

function uploadSuccessMsg() {
    let el = document.getElementById("upload-success-msg");
    if (!el) {
        el = document.createElement("div");
        el.id = "upload-success-msg";
        el.className = "alert alert-success";
        el.style.cssText = "display:none; margin-top:0.5rem; font-size:0.82rem;";
        const errorEl = document.getElementById("upload-error");
        if (errorEl && errorEl.parentNode) {
            errorEl.parentNode.insertBefore(el, errorEl.nextSibling);
        }
    }
    return el;
}

function showUploadSuccess(message) {
    const el = uploadSuccessMsg();
    el.textContent = message;
    showElement(el);
    setTimeout(() => hideElement(el), 5000);
}



function showUploadProgress(label) {
    if (!uploadProgressArea) return;
    if (uploadStatusLabel) uploadStatusLabel.textContent = label;
    if (uploadProgressBar) uploadProgressBar.style.width = "75%";
    showElement(uploadProgressArea);
}

function hideUploadProgress() {
    if (!uploadProgressArea) return;
    if (uploadProgressBar) uploadProgressBar.style.width = "100%";
    setTimeout(() => {
        hideElement(uploadProgressArea);
        if (uploadProgressBar) uploadProgressBar.style.width = "0%";
    }, 400);
}


// ============================================================
// Section: Conversational Query & Multi-Turn Clarification
// ============================================================

async function submitQuery(overrideText = null) {
    if (isProcessing) return;

    const text = (overrideText !== null ? overrideText : (queryInput ? queryInput.value : "")).trim();
    if (!text) {
        showError(queryError, "Please type a question or clarification.");
        return;
    }

    hideElement(queryError);
    if (queryInput) {
        queryInput.value = "";
        queryInput.style.height = "auto";
    }

    // Hide empty state on first message
    if (emptyChatState) hideElement(emptyChatState);

    // Append user message to chat stream
    appendUserMessage(text);

    // Set UI loading state
    isProcessing = true;
    if (askBtn) {
        askBtn.disabled = true;
        askBtn.querySelector(".btn-text").textContent = "Resolving...";
    }

    // Show live progress indicator
    showLiveProgress(currentSessionId ? "Resolving clarification..." : "Understanding query...");

    try {
        // Animate initial agent progress
        await sleep(200);
        updateProgressTrail([
            { label: "Understanding Query", state: "active" },
            { label: currentSessionId ? "Merging Context" : "Analyzing Intent", state: "pending" },
            { label: "Retrieval", state: "pending" },
            { label: "Response", state: "pending" },
        ]);

        const payload = {
            question: text,
            session_id: currentSessionId,
            is_clarification: Boolean(currentSessionId),
            conv_id: currentConvId,
        };

        const res = await fetch("/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        hideLiveProgress();

        if (data.conv_id) {
            currentConvId = data.conv_id;
        }

        if (!res.ok || data.error) {
            appendErrorMessage(data.error || "Could not process request. Please try again.");
            resetButtonState();
            return;
        }

        // Branch 1: Ambiguity detected -> Clarification Required
        if (data.status === "clarification_required") {
            currentSessionId = data.session_id;
            currentOriginalQuery = data.original_query || text;

            showActiveSessionBanner(currentOriginalQuery);
            appendClarificationMessage(data);

            if (queryInput) {
                queryInput.placeholder = "Type your clarification or choose a suggestion above...";
                queryInput.focus();
            }
        }
        // Branch 2: Resolved or normal grounded answer
        else {
            currentSessionId = null;
            currentOriginalQuery = null;
            hideActiveSessionBanner();

            appendAssistantAnswer(data);

            if (queryInput) {
                queryInput.placeholder = "Ask a question about your knowledge base... (Press Enter to send)";
            }
        }

    } catch (err) {
        hideLiveProgress();
        appendErrorMessage("Network error: Could not reach the server.");
    } finally {
        resetButtonState();
        scrollToBottom();
    }
}

function resetButtonState() {
    isProcessing = false;
    if (askBtn) {
        askBtn.disabled = false;
        askBtn.querySelector(".btn-text").textContent = "Ask";
    }
}


// ============================================================
// Section: Chat Message Rendering
// ============================================================

function appendUserMessage(text) {
    if (!chatStream) return;
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    const msgEl = document.createElement("div");
    msgEl.className = "msg-user";
    msgEl.innerHTML = `
        <div class="msg-user-bubble">${escapeHtml(text)}</div>
        <div class="msg-timestamp">${timeStr}</div>
    `;
    chatStream.appendChild(msgEl);
    scrollToBottom();
}

function appendClarificationMessage(data) {
    if (!chatStream) return;
    const qText = data.clarification_question || "Could you please provide more details to clarify your request?";
    const reason = data.debug_details?.reason || "";
    const suggestions = data.suggested_options || [];

    const msgEl = document.createElement("div");
    msgEl.className = "msg-assistant";

    let chipsHtml = "";
    if (suggestions.length > 0) {
        chipsHtml = `
            <div class="suggestion-chips-container">
                ${suggestions.map(opt => `
                    <button class="suggestion-chip" onclick="handleSuggestionClick('${escapeHtml(opt)}')">
                        ${escapeHtml(opt)}
                    </button>
                `).join("")}
            </div>
        `;
    }

    msgEl.innerHTML = `
        <div class="msg-clarification-card">
            <div class="clarification-callout-header">
                <span class="clarification-callout-tag">Clarification Needed</span>
                <span class="clarification-banner-title">Before I answer, I need a little more information</span>
            </div>
            <div class="clarification-question-text">${escapeHtml(qText)}</div>
            ${reason ? `<div class="clarification-reason-hint">${escapeHtml(reason)}</div>` : ""}
            ${chipsHtml}
        </div>
    `;

    chatStream.appendChild(msgEl);
    scrollToBottom();
}

function handleSuggestionClick(optionText) {
    if (isProcessing) return;
    if (queryInput) {
        queryInput.value = optionText;
    }
    submitQuery(optionText);
}

function appendAssistantAnswer(data) {
    if (!chatStream) return;

    const msgEl = document.createElement("div");
    msgEl.className = "msg-assistant";

    const qType = (data.query_type || "factual").toLowerCase();
    let qBadgeClass = "badge-factual";
    if (qType === "procedural") qBadgeClass = "badge-procedural";
    else if (qType === "comparative") qBadgeClass = "badge-comparative";
    else if (qType === "ambiguous") qBadgeClass = "badge-ambiguous";

    const conf = data.confidence || "None";
    let confClass = "badge-none";
    if (conf.toLowerCase() === "high") confClass = "badge-high";
    else if (conf.toLowerCase() === "medium") confClass = "badge-medium";
    else if (conf.toLowerCase() === "low") confClass = "badge-low";

    const confPercent = data.classification_confidence ? ` (${Math.round(data.classification_confidence * 100)}%)` : "";

    // Resolved query notice if applicable
    let resolvedHtml = "";
    if (data.resolved_query) {
        resolvedHtml = `
            <div class="msg-resolved-notice">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span><strong>Context Resolved:</strong> ${escapeHtml(data.resolved_query)}</span>
            </div>
        `;
    }

    // Milestone 3.4 — Response Transparency Panel
    const sources = data.sources || [];
    const sourceCardId = `transparency-${Date.now()}`;
    let transparencyHtml = "";

    if (sources.length > 0) {
        const topScore = Math.max(...sources.map(s => s.similarity_score || 0));
        const topScorePct = Math.round(topScore * 100);

        transparencyHtml = `
            <div class="transparency-panel">
                <button type="button" class="transparency-toggle-btn" onclick="toggleSources('${sourceCardId}')">
                    <div class="transparency-toggle-left">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                            <polyline points="10 9 9 9 8 9"/>
                        </svg>
                        <span>Evidence &amp; Transparency Panel</span>
                        <span class="transparency-badge">${sources.length} chunk${sources.length === 1 ? "" : "s"}</span>
                    </div>
                    <span id="icon-${sourceCardId}">▼</span>
                </button>
                <div class="transparency-content" id="${sourceCardId}">
                    <div class="transparency-summary-bar">
                        <span><strong>Retrieved Evidence:</strong> ${sources.length} chunk${sources.length === 1 ? "" : "s"} from vector index</span>
                        <span><strong>Top Relevance:</strong> ${topScorePct}%</span>
                    </div>
                    ${sources.map((src, idx) => {
                        const score = src.similarity_score !== undefined ? Math.round(src.similarity_score * 100) : 0;
                        const pageText = src.page_number ? `Page ${src.page_number}` : (src.row_number ? `Row ${src.row_number}` : "Main section");
                        let fillClass = "score-fill-low";
                        if (score >= 70) fillClass = "score-fill-high";
                        else if (score >= 40) fillClass = "score-fill-medium";

                        const citationRef = src.citation_ref || `[Citation #${idx + 1}]`;
                        const snippet = src.full_text || src.text_snippet || src.content || "Snippet unavailable.";

                        return `
                            <div class="chunk-evidence-card">
                                <div class="chunk-evidence-header">
                                    <span class="chunk-citation-badge">${escapeHtml(citationRef)}</span>
                                    <span class="chunk-doc-info">${escapeHtml(src.document_name || "Document")} &middot; ${pageText}</span>
                                    <div class="chunk-score-area">
                                        <div class="score-progress-bar" title="Similarity match: ${score}%">
                                            <div class="score-progress-fill ${fillClass}" style="width: ${Math.min(score, 100)}%;"></div>
                                        </div>
                                        <span class="chunk-score-label">${score}%</span>
                                    </div>
                                </div>
                                <div class="chunk-text-evidence">${escapeHtml(snippet)}</div>
                            </div>
                        `;
                    }).join("")}
                </div>
            </div>
        `;
    } else if (conf.toLowerCase() === "none" || conf.toLowerCase() === "low") {
        transparencyHtml = `
            <div class="transparency-panel">
                <div style="padding: 0.75rem 1.15rem;">
                    <div class="low-confidence-box">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;">
                            <circle cx="12" cy="12" r="10"/>
                            <line x1="12" y1="8" x2="12" y2="12"/>
                            <line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                        <div>
                            <strong>Evidence Transparency Note:</strong> No indexed document chunks met the minimum similarity threshold (0.25). A grounded rejection was generated to prevent hallucination.
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // Pipeline telemetry trace
    const traceId = `trace-${Date.now()}`;
    const stages = data.pipeline_stages || [];
    let traceHtml = "";
    if (stages.length > 0) {
        const traceFormatted = JSON.stringify(stages, null, 2);
        traceHtml = `
            <div class="pipeline-trace-box">
                <button class="trace-toggle-btn" onclick="toggleTrace('${traceId}')">
                    <span>Agent Pipeline Trace (${stages.length} stages)</span>
                    <span id="icon-${traceId}">+</span>
                </button>
                <div class="trace-details" id="${traceId}" style="display:none;">${escapeHtml(traceFormatted)}</div>
            </div>
        `;
    }

    msgEl.innerHTML = `
        <div class="msg-assistant-card">
            <div class="msg-assistant-header">
                <div class="assistant-badges">
                    <span class="badge ${qBadgeClass}">Type: ${capitalize(qType)}${confPercent}</span>
                    <span class="badge ${confClass}">Confidence: ${conf}</span>
                </div>
                <!-- Milestone 3.3 Text-to-Speech (TTS) Control -->
                <div class="tts-controls-group">
                    <button type="button" class="btn-tts" onclick="handleTTS(this)" title="Read answer aloud via Web Speech API">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
                        </svg>
                        <span class="tts-label">Listen</span>
                    </button>
                </div>
            </div>
            ${resolvedHtml}
            <div class="msg-answer-body">
                ${escapeHtml(data.answer || "No response generated.")}
            </div>
            ${transparencyHtml}
            ${traceHtml}
        </div>
    `;

    chatStream.appendChild(msgEl);
    scrollToBottom();
}

function appendErrorMessage(errorText) {
    if (!chatStream) return;
    const msgEl = document.createElement("div");
    msgEl.className = "msg-assistant";
    msgEl.innerHTML = `
        <div class="alert alert-error" style="max-width: 90%;">
            <strong>Error:</strong> ${escapeHtml(errorText)}
        </div>
    `;
    chatStream.appendChild(msgEl);
    scrollToBottom();
}

function toggleSources(id) {
    const el = document.getElementById(id);
    const icon = document.getElementById(`icon-${id}`);
    if (!el) return;
    if (el.style.display === "none") {
        el.style.display = "flex";
        if (icon) icon.textContent = "▲";
    } else {
        el.style.display = "none";
        if (icon) icon.textContent = "▼";
    }
}

function toggleTrace(id) {
    const el = document.getElementById(id);
    const icon = document.getElementById(`icon-${id}`);
    if (!el) return;
    if (el.style.display === "none") {
        el.style.display = "block";
        if (icon) icon.textContent = "-";
    } else {
        el.style.display = "none";
        if (icon) icon.textContent = "+";
    }
}


// ============================================================
// Section: Clarification Session Controls
// ============================================================

function showActiveSessionBanner(originalQuery) {
    if (!activeSessionInd || !sessionText) return;
    sessionText.textContent = `Clarifying: "${originalQuery.length > 40 ? originalQuery.slice(0, 40) + '...' : originalQuery}"`;
    showElement(activeSessionInd);
}

function hideActiveSessionBanner() {
    if (activeSessionInd) hideElement(activeSessionInd);
}

function handleCancelSession() {
    currentSessionId = null;
    currentOriginalQuery = null;
    hideActiveSessionBanner();
    if (queryInput) {
        queryInput.placeholder = "Ask a question about your knowledge base... (Press Enter to send)";
    }
}

function handleClearChat() {
    if (chatStream) {
        chatStream.innerHTML = "";
        if (emptyChatState) {
            chatStream.appendChild(emptyChatState);
            showElement(emptyChatState);
        }
    }
    handleCancelSession();
    currentConvId = null;
    if (window.speechSynthesis) window.speechSynthesis.cancel();
}


// ============================================================
// Section: Live Progress Indicator
// ============================================================

function showLiveProgress(initialStep) {
    if (!liveProgressArea || !progressStepsTrail) return;
    progressStepsTrail.innerHTML = `<span class="trail-step active">${escapeHtml(initialStep)}</span>`;
    showElement(liveProgressArea);
}

function updateProgressTrail(steps) {
    if (!progressStepsTrail) return;
    progressStepsTrail.innerHTML = steps.map((s, idx) => `
        ${idx > 0 ? '<span class="trail-arrow">&rarr;</span>' : ''}
        <span class="trail-step ${s.state}">${escapeHtml(s.label)}</span>
    `).join("");
}

function hideLiveProgress() {
    if (liveProgressArea) hideElement(liveProgressArea);
}


// ============================================================
// Section: Utility Functions
// ============================================================

function scrollToBottom() {
    if (!chatStream) return;
    chatStream.scrollTop = chatStream.scrollHeight;
}

function capitalize(s) {
    if (!s) return "";
    return s.charAt(0).toUpperCase() + s.slice(1);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

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


// ============================================================
// Section: Milestone 3.3 — Voice Input & Text-to-Speech (TTS)
// ============================================================

function setupVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        if (voiceInputBtn) {
            voiceInputBtn.title = "Speech Recognition is not supported in this browser (Use Chrome or Edge).";
            voiceInputBtn.style.opacity = "0.5";
        }
        return;
    }

    try {
        speechRecognizer = new SpeechRecognition();
        speechRecognizer.continuous = false;
        speechRecognizer.interimResults = true;
        speechRecognizer.lang = "en-US";

        speechRecognizer.onstart = () => {
            isRecording = true;
            if (voiceInputBtn) voiceInputBtn.classList.add("recording");
            if (voiceStatusBar) {
                if (voiceStatusText) voiceStatusText.textContent = "Listening... Speak your query clearly.";
                showElement(voiceStatusBar);
            }
        };

        speechRecognizer.onresult = (event) => {
            let transcript = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            if (queryInput) {
                queryInput.value = transcript;
                queryInput.style.height = "auto";
                queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + "px";
            }
        };

        speechRecognizer.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            stopVoiceInput();
            if (event.error === "not-allowed") {
                showError(queryError, "Microphone permission denied. Please allow microphone access in your browser settings.");
            } else if (event.error !== "no-speech") {
                showError(queryError, `Voice recognition notice: ${event.error}`);
            }
        };

        speechRecognizer.onend = () => {
            stopVoiceInput();
        };

        if (voiceInputBtn) {
            voiceInputBtn.addEventListener("click", () => {
                if (isRecording) {
                    stopVoiceInput();
                } else {
                    startVoiceInput();
                }
            });
        }

        if (stopVoiceBtn) {
            stopVoiceBtn.addEventListener("click", stopVoiceInput);
        }
    } catch (e) {
        console.warn("Could not initialize SpeechRecognition:", e);
    }
}

function startVoiceInput() {
    if (!speechRecognizer) {
        alert("Web Speech API is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
        return;
    }
    hideElement(queryError);
    try {
        speechRecognizer.start();
    } catch (err) {
        console.warn("Speech recognition already active or error:", err);
    }
}

function stopVoiceInput() {
    isRecording = false;
    if (voiceInputBtn) voiceInputBtn.classList.remove("recording");
    if (voiceStatusBar) hideElement(voiceStatusBar);
    if (speechRecognizer) {
        try { speechRecognizer.stop(); } catch (e) {}
    }
}

function handleTTS(btn) {
    if (!window.speechSynthesis) {
        alert("Text-to-Speech (Web Speech API) is not supported in this browser.");
        return;
    }

    // If currently speaking, stop
    if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        document.querySelectorAll(".btn-tts").forEach(b => {
            b.classList.remove("speaking");
            const lbl = b.querySelector(".tts-label");
            if (lbl) lbl.textContent = "Listen";
        });
        return;
    }

    // Locate response text in parent card
    const card = btn.closest(".msg-assistant-card");
    if (!card) return;
    const body = card.querySelector(".msg-answer-body");
    if (!body) return;
    const textToSpeak = body.textContent.trim();
    if (!textToSpeak) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.lang = "en-US";

    btn.classList.add("speaking");
    const lbl = btn.querySelector(".tts-label");
    if (lbl) lbl.textContent = "Stop";

    utterance.onend = () => {
        btn.classList.remove("speaking");
        if (lbl) lbl.textContent = "Listen";
    };

    utterance.onerror = () => {
        btn.classList.remove("speaking");
        if (lbl) lbl.textContent = "Listen";
    };

    window.speechSynthesis.speak(utterance);
}

