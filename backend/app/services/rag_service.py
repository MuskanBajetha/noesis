import os
import time
import hashlib
import chromadb
from google import genai as google_genai
from google.genai import types as google_types
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()

# --- DIAGNOSTIC LOG START ---
raw_key = os.getenv("GEMINI_API_KEY")
if raw_key:
    # Print the length and first 5 characters safely to logs (e.g. AIzaS)
    print(f"DEBUG_KEY_CHECK: Key found! Length: {len(raw_key)}, Starts with: {raw_key[:5]}")
else:
    print("DEBUG_KEY_CHECK: CRITICAL ERROR! GEMINI_API_KEY is completely empty or None inside Render.")
# --- DIAGNOSTIC LOG END ---

_gemini_client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Simple in-memory cache for query embeddings
_query_cache: dict[str, list[float]] = {}

try:
    existing = chroma_client.get_collection("learning_materials")
    sample = existing.get(limit=1, include=["embeddings"])
    if sample["embeddings"] and len(sample["embeddings"][0]) != 3072:
        chroma_client.delete_collection("learning_materials")
        print("Deleted stale collection with wrong embedding dimensions")
except Exception:
    pass

collection = chroma_client.get_or_create_collection(
    name="learning_materials",
    metadata={"hnsw:space": "cosine"}
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)


def _with_retry(fn, retries: int = 3, base_delay: float = 2.0):
    """Call fn with exponential backoff on failure."""
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(base_delay ** attempt)
            else:
                raise


def embed_texts(texts: list[str], batch_size: int = 90) -> list[list[float]]:
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        def _call():
            result = _gemini_client.models.embed_content(
                model="gemini-embedding-001",
                contents=batch,
                config=google_types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            return [e.values for e in result.embeddings]

        all_embeddings.extend(_with_retry(_call))

    return all_embeddings


def embed_query(text: str) -> list[float]:
    # Return cached embedding if we've seen this query before
    if text in _query_cache:
        return _query_cache[text]

    def _call():
        result = _gemini_client.models.embed_content(
            model="gemini-embedding-001",
            contents=[text],
            config=google_types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values

    embedding = _with_retry(_call)
    _query_cache[text] = embedding
    return embedding


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def process_and_store_pdf(pdf_path: str, subject_id: int, filename: str, document_id: int) -> dict:
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
    try:
        results = collection.get(where={"subject_id": str(subject_id)})
        return len(results["ids"])
    except Exception:
        return 0


def delete_subject_material(subject_id: int):
    try:
        collection.delete(where={"subject_id": str(subject_id)})
    except Exception:
        pass


def delete_document_material(document_id: int):
    try:
        collection.delete(where={"document_id": str(document_id)})
    except Exception:
        pass