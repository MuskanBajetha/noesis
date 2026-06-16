import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import hashlib

load_dotenv()

# ── Init embedding model & ChromaDB ─────────────────────

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="./chroma_db")

collection = chroma_client.get_or_create_collection(
    name="learning_materials",
    metadata={"heuristic": "cosine"}
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)

# ── PDF Processing ───────────────────────────────────────

def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def process_and_store_pdf(pdf_path: str, topic: str) -> dict:
    """Extract text from PDF, chunk it, embed and store in ChromaDB."""
    print(f"Processing PDF: {pdf_path} for topic: {topic}")

    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        return {"status": "error", "message": "Could not extract text from PDF"}

    chunks = text_splitter.split_text(text)
    print(f"Created {len(chunks)} chunks")

    embeddings = embedding_model.encode(chunks).tolist()

    ids = []
    documents = []
    metadatas = []
    embeds = []

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = hashlib.md5(f"{pdf_path}_{i}".encode()).hexdigest()
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({"topic": topic, "source": os.path.basename(pdf_path), "chunk_index": i})
        embeds.append(embedding)

    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeds
    )

    return {
        "status": "success",
        "chunks_stored": len(chunks),
        "topic": topic,
        "source": os.path.basename(pdf_path)
    }


def retrieve_context(query: str, topic: str = None, n_results: int = 3) -> str:
    """Retrieve relevant chunks from ChromaDB for a given query."""
    query_embedding = embedding_model.encode([query]).tolist()

    where_filter = {"topic": topic} if topic else None

    try:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_filter if where_filter else None
        )
    except Exception:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )

    if not results["documents"] or not results["documents"][0]:
        return ""

    context_parts = []
    for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
        source = metadata.get("source", "unknown")
        context_parts.append(f"[Source: {source}]\n{doc}")

    return "\n\n---\n\n".join(context_parts)


def get_collection_stats() -> dict:
    """Get stats about stored documents."""
    count = collection.count()
    return {"total_chunks": count}