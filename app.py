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

# Import backend modules
from backend.document_processor import DocumentProcessor, DocumentProcessingError
from backend.chunker import DocumentChunker
from backend.embeddings import EmbeddingEngine
from backend.vector_store import VectorStore
from backend.retriever import KnowledgeRetriever
from backend.generator import ResponseGenerator

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
        "total_documents": len(vector_store.get_indexed_documents()),
        "total_chunks": vector_store.total_chunks,
        "embedding_model": embedding_engine.model_name,
        "embedding_dimension": vector_store.dimension,
        "generator_mode": generator.provider,
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
    Accepts user question, retrieves top-k relevant chunks,
    and generates a grounded answer with full source attribution.
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question") or data.get("query") or ""
    question = question.strip()

    if not question:
        return jsonify({"error": "Please enter a non-empty question."}), 400

    if vector_store.total_chunks == 0:
        return jsonify({
            "error": "The knowledge base is currently empty. Please upload at least one document first."
        }), 400

    print(f"\n[QUERY] Processing question: '{question}'")

    try:
        # Step 1: Semantic similarity search via retriever
        retrieval_data = retriever.retrieve(question)

        # Step 2: Grounded answer generation
        print("[GENERATION] Passing retrieved context to generator...")
        response = generator.generate_response(question, retrieval_data)

        # Enrich debug details for code walkthrough explainability mode
        debug_payload = {
            "query": question,
            "query_embedding_shape": retrieval_data["query_embedding_shape"],
            "top_similarity_score": retrieval_data["top_score"],
            "confidence": response.confidence,
            "generator_mode": response.debug_details.get("mode"),
            "retrieved_chunks_count": len(retrieval_data["all_retrieved"]),
            "selected_chunks_count": len(retrieval_data["relevant_results"]),
            "prompt_used": response.debug_details.get("prompt_used"),
            "all_retrieved_chunks": [r.to_dict() for r in retrieval_data["all_retrieved"]],
        }

        return jsonify({
            "answer": response.answer,
            "confidence": response.confidence,
            "sources": response.sources,
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
        return jsonify({
            "success": True,
            "message": "Knowledge base and vector index successfully cleared."
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
