import os
import chromadb
from google import genai as google_genai
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import hashlib

load_dotenv()

_gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="./chroma_db")


from google.genai import types as google_types

def embed_texts(texts: list[str], batch_size: int = 90) -> list[list[float]]:
    """
    Embeds texts via Gemini, batched in groups of up to `batch_size` per
    API call (NOT one call per text). A single call costs 1 request against
    the RPM quota regardless of how many texts are inside `contents`, so a
    9-page PDF with ~80 chunks should cost ~1 request total, not ~80.
    `batch_size` is capped below Gemini's practical per-call limit as a
    safety margin for very large documents.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = _gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
            config=google_types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        all_embeddings.extend([e.values for e in result.embeddings])

    return all_embeddings


def embed_query(text: str) -> list[float]:
    """Same embedding space as embed_texts, single query string, tagged
    as a query rather than a document for slightly better retrieval matching."""
    result = _gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=[text],
        config=google_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return result.embeddings[0].values

# One-time migration: delete old 384-dim collection if it exists with wrong dims
try:
    existing = chroma_client.get_collection("learning_materials")
    sample = existing.get(limit=1, include=["embeddings"])
    if sample["embeddings"] and len(sample["embeddings"][0]) != 3072:
        chroma_client.delete_collection("learning_materials")
        print("Deleted stale collection with wrong embedding dimensions")
except Exception:
    pass  # Collection doesn't exist yet, that's fine

collection = chroma_client.get_or_create_collection(
    name="learning_materials",
    metadata={"hnsw:space": "cosine"}  # correct metadata key
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def process_and_store_pdf(pdf_path: str, subject_id: int, filename: str, document_id: int) -> dict:
    """
    Extract text from PDF, chunk it, embed, and store in ChromaDB,
    tagged with both subject_id (broad scope) and document_id (fine-grained,
    enables deleting just this document's chunks later without touching others).
    """
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        return {"status": "error", "message": "Could not extract text from PDF"}

    chunks = text_splitter.split_text(text)
    embeddings = embed_texts(chunks)

    ids, documents, metadatas, embeds = [], [], [], []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        chunk_id = hashlib.md5(f"{document_id}_{i}".encode()).hexdigest()
        ids.append(chunk_id)
        documents.append(chunk)
        metadatas.append({
            "subject_id": str(subject_id),
            "document_id": str(document_id),
            "source": filename,
            "chunk_index": i
        })
        embeds.append(embedding)

    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeds)

    return {
        "status": "success",
        "chunks_stored": len(chunks),
        "subject_id": subject_id,
        "document_id": document_id,
        "source": filename,
        "full_text": text
    }


def retrieve_context(query: str, subject_id: int, n_results: int = 3) -> str:
    """Retrieve relevant chunks for a query, hard-scoped to one subject_id."""
    query_embedding = [embed_query(query)]

    try:
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where={"subject_id": str(subject_id)}
        )
    except Exception:
        return ""

    if not results["documents"] or not results["documents"][0]:
        return ""

    parts = []
    for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
        parts.append(f"[Source: {metadata.get('source', 'unknown')}]\n{doc}")

    return "\n\n---\n\n".join(parts)


def get_subject_chunk_count(subject_id: int) -> int:
    """Count chunks stored for a given subject — used to show upload status."""
    try:
        results = collection.get(where={"subject_id": str(subject_id)})
        return len(results["ids"])
    except Exception:
        return 0


def delete_subject_material(subject_id: int):
    """Remove all chunks for a subject — used by the 'Replace material' flow."""
    try:
        collection.delete(where={"subject_id": str(subject_id)})
    except Exception:
        pass

def delete_document_material(document_id: int):
    """Remove only the chunks belonging to ONE document, leaving siblings intact."""
    try:
        collection.delete(where={"document_id": str(document_id)})
    except Exception:
        pass