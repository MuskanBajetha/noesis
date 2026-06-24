import os
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
import hashlib

load_dotenv()

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
    embeddings = embedding_model.encode(chunks).tolist()

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
    query_embedding = embedding_model.encode([query]).tolist()

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