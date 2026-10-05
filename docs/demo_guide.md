# Demo Guide
## AI-Based Knowledge Retrieval Platform — Milestone 4 Demo Walkthrough

**Purpose:** Step-by-step guide for demonstrating the platform to evaluators  
**Duration:** ~10–15 minutes for full demo

---

## Before the Demo — Startup Checklist

1. **Start the application:**
   ```powershell
   cd C:\path\to\knowledge-retrieval-platform
   venv\Scripts\Activate.ps1
   python app.py
   ```

2. **Open browser:** http://127.0.0.1:5000

3. **Verify the knowledge base is loaded.** Look for **"495 chunks"** (or similar) in the Knowledge Base counter.
   - If 0 chunks: Load the sample knowledge base (Step 1 below)

4. **Optional — Add Gemini API key** for real AI generation:
   - Open `.env`, add: `GEMINI_API_KEY=your_key_here`
   - Restart: `python app.py`

---

## Demo Script

### Step 1 — Load the Sample Knowledge Base

> "The system supports PDF, DOCX, TXT, and CSV document formats. Let me load the pre-built multi-domain knowledge base."

1. Click **"Sample Knowledge Bases"** → **"Load pre-built multi-domain test data"**
2. Or manually upload documents from `data/sample_docs/`:
   - `Artificial_Intelligence.docx`
   - `Operating_Systems.pdf`
   - `Cybersecurity_Basics.txt`
   - `students.csv`

**Point to show:** Each upload increments the chunk count. Explain that documents are parsed, chunked, embedded, and indexed in real-time.

**What to say:**
> "The system uses the `all-MiniLM-L6-v2` sentence transformer model to convert text into 384-dimensional vectors stored in a FAISS index. With 495 chunks loaded across 4 documents, queries are answered in milliseconds."

---

### Step 2 — Simple Factual Query (Operating Systems domain)

Type: **"What is virtual memory?"**

**What to show:**
- Answer appears with citation and confidence badge: "Type: Factual (90%) | Confidence: High"
- The answer correctly defines virtual memory with demand paging and page fault explanations
- Click **"📄 Sources (5) · Top match: 99% ▶"** to expand the sources panel
- Show that the top source is from `Operating_Systems.pdf — Page 4` with a 99% similarity score
- Click **"[+]"** on Agent Pipeline Trace to show the 3-stage execution: Query Understanding → Semantic Retrieval → Response Generation

**What to say:**
> "The Query Understanding Agent classified this as a factual query. The Retrieval Agent searched the FAISS index and found 5 relevant chunks. The top match scored 99% similarity. The Response Generation Agent synthesized the answer strictly from these chunks."

---

### Step 3 — Factual Query (AI domain)

Type: **"What is AI?"**

Then type: **"Types of AI?"**

**What to show:**
- "What is AI?" returns a clean definition
- "Types of AI?" returns a bulleted structured list (Narrow AI, General AI, Super AI)
- The two queries get different structured outputs despite retrieving similar chunks

**What to say:**
> "The system detects the query intent — 'types of' triggers a list-format synthesis. This is the intent-aware local synthesis engine that was improved in Milestone 4."

---

### Step 4 — Ambiguity Detection & Clarification (M2/M3 feature)

Type: **"networks"**

**What to show:**
- System displays: "Are you asking about Computer Networks (like LAN, WAN, protocols) or Neural Networks (used in Artificial Intelligence)?"
- Three clickable chips appear: "Computer Networks", "Neural Networks", "Network security"
- Click **"Computer Networks (LAN, WAN, protocols)"**
- Answer returns about computer networks
- Check pipeline trace: shows "Query Understanding → Clarification Generation" then after chip click "Query Resolution → Retrieval → Response"

**What to say:**
> "The Query Understanding Agent detected that 'networks' is a multi-meaning term. The Clarification Agent generated a targeted question with option chips. After the user selects an option, the Conversation Manager merges the original query with the clarification to retrieve the correct answer."

---

### Step 5 — Ambiguity Detection (another example)

Type: **"memory"**

**What to show:**
- Clarification: "Are you asking about Computer Memory (RAM/ROM), Memory Management in OS, or Memory in AI/ML?"
- Three options: "Computer Memory (RAM/ROM)", "OS Memory Management", "Memory in AI/ML"

---

### Step 6 — Conversation Memory (M3 feature)

Type: **"What is virtual memory?"**  
Then type: **"What are page faults?"**  
Then type: **"Explain this topic"**

**What to show:**
- After first question, the conversation memory stores "virtual memory" as the topic
- "Explain this topic" resolves to "Explain virtual memory" via conversation memory
- But "What are page faults?" is a self-contained query — it is NOT confused by prior context

**What to say:**
> "The Conversation Memory Agent stores the last 10 turns per conversation. Bare pronoun references like 'this topic' are resolved to the prior topic. But self-contained questions are never modified — the system correctly distinguishes genuine follow-ups from new questions."

---

### Step 7 — Cybersecurity Domain

Type: **"What is a phishing attack?"**

**What to show:**
- Answer retrieved from `Cybersecurity_Basics.txt`
- Source shows correct document and file type (TXT)

Type: **"Difference between symmetric and asymmetric encryption"**

**What to show:**
- Comparative query — system detects "difference between" pattern
- Answer structured for comparison

---

### Step 8 — CSV / Structured Data Query

Type: **"Show student records"**

**What to show:**
- Answer returns structured row data from `students.csv`
- Each row formatted as "Name: X | ID: Y | CGPA: Z"

**What to say:**
> "CSV files are processed row-by-row. Each row becomes an atomic chunk. The system can answer queries about student records, structured datasets, or any tabular data."

---

### Step 9 — Voice Interaction (M4 feature)

1. Click the **🎤 microphone button** (bottom of chat)
2. Speak: "What is machine learning?"
3. Show that the transcript appears in the input box and query is auto-submitted
4. On the answer, click **🔊 Listen**
5. The answer is read aloud

**What to say:**
> "The system uses the browser's built-in Web Speech API for both voice input and output — no external API is required. Users can ask questions by speaking and hear answers without looking at the screen."

---

### Step 10 — Analytics Dashboard (M4 feature)

1. Click **"Analytics & Gaps"** at the top of the page
2. Show:
   - **Total queries** processed
   - **Confidence breakdown** (High/Medium/Low/None)
   - **Query type breakdown** (factual/procedural/comparative/ambiguous)
   - **Recent query log** with status, similarity score, duration
   - **Knowledge Gaps** section — any topics the knowledge base doesn't cover

**What to say:**
> "The Analytics Engine records every query in SQLite — 18 fields per record including query type, confidence, similarity score, and response duration. The Knowledge Gap Detector clusters unanswered queries to show which topics need more documents."

3. Click **"Export CSV"** to download the analytics data

---

### Step 11 — "Not Found" Handling

Type: **"What is quantum computing?"** (not in the knowledge base)

**What to show:**
- Answer: "I couldn't find enough relevant information in the uploaded documents to answer this question."
- Confidence: None
- Sources: empty

**What to say:**
> "The system is strictly grounded — it never invents answers. When no relevant chunks are found above the similarity threshold, it honestly says it cannot answer from the available documents."

3. Go back to Analytics → Gaps — this query may appear as a gap.

---

### Step 12 — Run Tests (Optional, for evaluators)

Open a PowerShell terminal:

```powershell
venv\Scripts\Activate.ps1
python -m pytest tests/ -v --tb=short
```

**What to show:** 96 tests passing, 0 failures across 4 test suites.

---

## Feature Summary Checklist for Evaluators

| Feature | Where to Demo | Milestone |
|---------|--------------|-----------|
| PDF document upload + indexing | Upload panel → upload any PDF | M1 |
| DOCX parsing | Upload `Artificial_Intelligence.docx` | M1 |
| TXT parsing | Upload `Cybersecurity_Basics.txt` | M1 |
| CSV row-level retrieval | Upload `students.csv`, ask about students | M1 |
| Semantic similarity search | Any factual query | M1 |
| Grounded rejection (hallucination prevention) | Ask about quantum computing | M1 |
| Query type classification | Observe badge on each answer | M2 |
| Pipeline trace | Click [+] on any answer | M2 |
| Multi-agent orchestration | Pipeline trace shows 3 agents | M2 |
| Confidence scoring | High/Medium/Low badge on answers | M2 |
| Source citations | Click 📄 Sources | M2 |
| Ambiguity detection | Type "networks" or "memory" | M2/M3 |
| Clarification with option chips | Type ambiguous query, click chip | M3 |
| Multi-turn clarification | Complete a clarification flow | M3 |
| Follow-up resolution ("this topic") | Ask follow-up after a question | M3 |
| Conversation memory | Multiple questions in sequence | M3 |
| Analytics dashboard | Click "Analytics & Gaps" | M4 |
| Knowledge gap detection | Query something not in KB | M4 |
| CSV analytics export | Click "Export CSV" in analytics | M4 |
| Voice input (STT) | Click microphone, speak a query | M4 |
| Voice output (TTS) | Click "Listen" on an answer | M4 |
| Intent-aware structured answers | Ask "Why AI?" vs "What is AI?" | M4 |
| Auto-scroll to answer | Answer scrolls to top of view | M4 |
| Citation panel (collapsed) | Sources collapsed by default | M4 |

---

## GitHub Repository

```
https://github.com/geetha577/AI-Knowledge-Retrieval-Platform
```

**Clone command for evaluators:**
```bash
git clone https://github.com/geetha577/AI-Knowledge-Retrieval-Platform.git
cd AI-Knowledge-Retrieval-Platform
python -m venv venv
venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
python app.py
```

Then open: http://127.0.0.1:5000
