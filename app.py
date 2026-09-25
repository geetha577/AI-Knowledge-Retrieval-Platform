"""
app.py
Flask Application & API Routes for AI-Based Knowledge Retrieval Platform.
Coordinates document ingestion, chunking, embedding generation, FAISS indexing,
semantic retrieval, and grounded response generation.
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize core paths
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"
SAMPLE_DOCS_DIR = BASE_DIR / "data" / "sample_docs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)

from backend.document_processor import DocumentProcessor, DocumentProcessingError
from backend.chunker import DocumentChunker
from backend.embeddings import EmbeddingEngine
from backend.vector_store import VectorStore
from backend.retriever import KnowledgeRetriever
from backend.generator import ResponseGenerator
from backend.query_understanding_agent import QueryUnderstandingAgent
from backend.retrieval_agent import RetrievalAgent
from backend.response_generation_agent import ResponseGenerationAgent
from backend.clarification_agent import ClarificationAgent
from backend.conversation_manager import ConversationManager
from backend.orchestrator import MultiAgentOrchestrator

# Create Flask application
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB upload limit

# Global RAG pipeline components
doc_processor = DocumentProcessor(upload_dir=str(UPLOAD_DIR))
chunker = DocumentChunker(
    chunk_size=int(os.getenv("CHUNK_SIZE", "500")),
    chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
)
embedding_engine = EmbeddingEngine(
    model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
)
vector_store = VectorStore(
    persist_dir=str(VECTOR_STORE_DIR),
    dimension=embedding_engine.dimension,
)
retriever = KnowledgeRetriever(
    vector_store=vector_store,
    embedding_engine=embedding_engine,
    top_k=int(os.getenv("TOP_K", "5")),
    similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", "0.25")),
)
generator = ResponseGenerator()

# Milestone 2 & 3 Multi-Agent Architecture
query_understanding_agent = QueryUnderstandingAgent()
retrieval_agent = RetrievalAgent(retriever=retriever)
response_generation_agent = ResponseGenerationAgent(generator=generator)
clarification_agent = ClarificationAgent()
conversation_manager = ConversationManager()
orchestrator = MultiAgentOrchestrator(
    query_understanding_agent=query_understanding_agent,
    retrieval_agent=retrieval_agent,
    response_generation_agent=response_generation_agent,
    clarification_agent=clarification_agent,
    conversation_manager=conversation_manager,
)


# ----------------------------------------------------------------------
# Page Routes
# ----------------------------------------------------------------------

@app.route("/")
def index():
    """Serves the main Knowledge Retrieval Platform dashboard."""
    return render_template("index.html")


# ----------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health_check():
    """System health check and vector database status."""
    return jsonify({
        "status": "healthy",
        "milestone": "Milestone 2 / Milestone 3 - Multi-Agent Architecture, Memory, Voice & Transparency",
        "total_documents": len(vector_store.get_indexed_documents()),
        "total_chunks": vector_store.total_chunks,
        "embedding_model": embedding_engine.model_name,
        "embedding_dimension": vector_store.dimension,
        "generator_mode": generator.provider,
        "agents": [
            "QueryUnderstandingAgent",
            "ClarificationAgent",
            "ConversationMemoryAgent",
            "RetrievalAgent",
            "ResponseGenerationAgent",
            "MultiAgentOrchestrator",
        ],
    })


@app.route("/documents", methods=["GET"])
def list_documents():
    """Returns the list of currently indexed knowledge base documents."""
    docs = vector_store.get_indexed_documents()
    return jsonify({
        "documents": docs,
        "total_documents": len(docs),
        "total_chunks": vector_store.total_chunks,
    })


@app.route("/upload", methods=["POST"])
def upload_document():
    """
    Handles file upload, text extraction, semantic chunking,
    embedding generation, and FAISS indexing.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded in request."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "No file selected."}), 400

    filename = uploaded_file.filename
    print(f"\n[UPLOAD] Received file: {filename}")

    try:
        # Step 1 & 2: Validate and save file safely
        saved_path = doc_processor.save_file(uploaded_file)
        print(f"[UPLOAD] Saved safely to: {saved_path}")

        # Step 3 & 4: Extract and clean text
        print(f"[UPLOAD] Extracting text from {saved_path.suffix.upper()}...")
        segments = doc_processor.extract(saved_path)
        print(f"[UPLOAD] Extracted {len(segments)} segment(s).")

        # Step 5: Chunk document
        chunks = chunker.chunk_document(filename, segments)
        print(f"[CHUNKING] Created {len(chunks)} chunks with attribution metadata.")

        if not chunks:
            return jsonify({"error": "No text content could be derived from this document."}), 400

        # Step 6: Generate dense vector embeddings
        chunk_texts = [c.text for c in chunks]
        print(f"[EMBEDDING] Generating embeddings for {len(chunks)} chunks...")
        embeddings = embedding_engine.generate_embeddings(chunk_texts)
        print(f"[EMBEDDING] Embeddings generated with shape: {embeddings.shape}")

        # Step 7: Store in FAISS vector store and persist
        print(f"[INDEX] Adding {len(chunks)} vectors to FAISS index...")
        vector_store.add_documents(chunks, embeddings)

        pages = sorted(list(set(c.page_number for c in chunks if c.page_number is not None)))

        return jsonify({
            "success": True,
            "message": f"Successfully indexed '{filename}'.",
            "document_name": filename,
            "document_type": Path(filename).suffix.lstrip(".").upper(),
            "chunks_created": len(chunks),
            "pages_indexed": pages if pages else None,
            "total_chunks_in_store": vector_store.total_chunks,
            "total_documents": len(vector_store.get_indexed_documents()),
        }), 200

    except DocumentProcessingError as e:
        print(f"[UPLOAD ERROR] {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[UPLOAD UNEXPECTED ERROR] {str(e)}")
        return jsonify({"error": f"Failed to process document: {str(e)}"}), 500


@app.route("/query", methods=["POST"])
def query_knowledge_base():
    """
    Accepts user question or clarification response, passes through Multi-Agent Orchestrator:
    Query Understanding Agent -> (Clarification Agent if ambiguous) -> Retrieval Agent -> Response Generation Agent,
    and returns answer, confidence, sources, query_type, session_id, and pipeline stages.
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question") or data.get("query") or data.get("clarification") or ""
    question = question.strip()
    session_id = data.get("session_id")
    conv_id = data.get("conv_id")
    is_clarification = data.get("is_clarification", False) or bool(session_id and data.get("clarification"))

    if not question:
        return jsonify({"error": "Please enter a non-empty question or clarification."}), 400

    if vector_store.total_chunks == 0:
        return jsonify({
            "error": "The knowledge base is currently empty. Please upload at least one document first."
        }), 400

    # Ensure conv_id exists
    if not conv_id:
        conv_id = conversation_manager.get_or_create_memory().conv_id

    print(f"\n[QUERY] Processing query via Multi-Agent Orchestrator: '{question}' (Session: {session_id}, Conv: {conv_id})")

    try:
        # Step 1: Execute multi-agent orchestration pipeline
        indexed_docs = vector_store.get_indexed_documents()
        result = orchestrator.process_query(
            query=question,
            session_id=session_id,
            is_clarification=is_clarification,
            available_docs=indexed_docs,
            conv_id=conv_id,
        )

        # Step 2: Format explainability details for UI
        debug_payload = result.get("debug_details", {})
        gen_debug = debug_payload.get("generation_debug", {})

        # Extract candidates for explainability panel
        retrieved_results = debug_payload.get("retrieved_results", [])
        all_chunks = []
        for r in retrieved_results:
            all_chunks.append({
                "chunk_id": r.get("chunk_id", ""),
                "document_name": r.get("document", ""),
                "text": r.get("content", ""),
                "similarity_score": r.get("score", 0.0),
                "relevance": r.get("relevance", "Medium"),
            })

        effective_query = result.get("query", question)
        debug_payload.update({
            "query": effective_query,
            "original_query": result.get("original_query", question),
            "resolved_query": result.get("resolved_query"),
            "query_type": result.get("query_type"),
            "classification_confidence": result.get("classification_confidence"),
            "route": result.get("route"),
            "confidence": result.get("confidence"),
            "generator_mode": gen_debug.get("mode") or generator.provider,
            "top_similarity_score": debug_payload.get("top_similarity_score", 0.0),
            "retrieved_chunks_count": len(retrieved_results),
            "selected_chunks_count": len(result.get("sources", [])),
            "all_retrieved_chunks": all_chunks,
            "query_embedding_shape": [1, embedding_engine.dimension],
            "prompt_used": gen_debug.get("prompt_used"),
            "pipeline_stages": result.get("pipeline_stages", []),
            "session_id": result.get("session_id"),
        })

        return jsonify({
            "status": result.get("status", "answered"),
            "query": effective_query,
            "original_query": result.get("original_query", question),
            "resolved_query": result.get("resolved_query"),
            "answer": result["answer"],
            "clarification_question": result.get("clarification_question"),
            "suggested_options": result.get("suggested_options", []),
            "session_id": result.get("session_id"),
            "conv_id": result.get("conv_id", conv_id),
            "confidence": result["confidence"],
            "sources": result["sources"],
            "query_type": result["query_type"],
            "classification_confidence": result["classification_confidence"],
            "route": result["route"],
            "pipeline_stages": result["pipeline_stages"],
            "debug_details": debug_payload,
        }), 200

    except Exception as e:
        import traceback
        print(f"[QUERY ERROR] {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Error executing query: {str(e)}"}), 500



@app.route("/sample_docs", methods=["GET"])
def list_sample_docs():
    """Lists pre-built sample documents available for instant demonstration."""
    samples = []
    if SAMPLE_DOCS_DIR.exists():
        for f in SAMPLE_DOCS_DIR.glob("*"):
            if f.is_file() and f.suffix.lower() in [".pdf", ".docx", ".txt", ".csv"]:
                samples.append({
                    "filename": f.name,
                    "type": f.suffix.lstrip(".").upper(),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                })
    return jsonify({"samples": samples})


@app.route("/load_sample", methods=["POST"])
def load_sample_doc():
    """Ingests a pre-built sample document into the knowledge base."""
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename specified."}), 400

    sample_path = SAMPLE_DOCS_DIR / filename
    if not sample_path.exists():
        return jsonify({"error": f"Sample file '{filename}' not found."}), 404

    try:
        segments = doc_processor.extract(sample_path)
        chunks = chunker.chunk_document(filename, segments)
        chunk_texts = [c.text for c in chunks]
        embeddings = embedding_engine.generate_embeddings(chunk_texts)
        vector_store.add_documents(chunks, embeddings)

        pages = sorted(list(set(c.page_number for c in chunks if c.page_number is not None)))

        return jsonify({
            "success": True,
            "message": f"Successfully loaded sample document '{filename}'.",
            "document_name": filename,
            "chunks_created": len(chunks),
            "pages_indexed": pages if pages else None,
            "total_chunks_in_store": vector_store.total_chunks,
            "total_documents": len(vector_store.get_indexed_documents()),
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load sample: {str(e)}"}), 500


@app.route("/reset", methods=["POST"])
def reset_knowledge_base():
    """Utility endpoint to clear the vector index and start fresh."""
    try:
        vector_store.clear()
        conversation_manager.clear_all()
        return jsonify({
            "success": True,
            "message": "Knowledge base, vector index, and active clarification sessions successfully cleared."
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ----------------------------------------------------------------------
# Application Entry Point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() == "true"
    print(f"\n=======================================================")
    print(f" AI-Based Knowledge Retrieval Platform (RAG System)")
    print(f" Server starting on http://127.0.0.1:{port}")
    print(f" Indexed Documents: {len(vector_store.get_indexed_documents())}")
    print(f" Total Chunks:      {vector_store.total_chunks}")
    print(f" Embedding Model:   {embedding_engine.model_name}")
    print(f" Generator Mode:    {generator.provider}")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
