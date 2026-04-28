import os
import chromadb
from pypdf import PdfReader
import docx
from utils import chunk_resume, embed_text, extract_metadata

# ─── Persistent ChromaDB client ───────────────────────────────────────────────
DB_PATH = "vector_db"
COLLECTION_NAME = "resumes"
RESUME_FOLDER = "data/resumes"


def load_pdf(path):
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages.append(extracted)
    return "\n".join(pages)


def load_docx(path):
    doc = docx.Document(path)
    return "\n".join([p.text for p in doc.paragraphs])


def load_resumes(folder):
    """Load all PDF and DOCX resumes from a folder."""
    data = []
    if not os.path.exists(folder):
        print(f"❌ Folder not found: {folder}")
        return data

    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        try:
            if file.endswith(".pdf"):
                text = load_pdf(path)
            elif file.endswith(".docx"):
                text = load_docx(path)
            else:
                continue

            if not text.strip():
                print(f"⚠️  Empty text extracted from: {file}")
                continue

            data.append({"file": file, "text": text})
            print(f"✅ Loaded: {file}")
        except Exception as e:
            print(f"❌ Failed to load {file}: {e}")

    return data


def index_resumes(resumes, collection):
    """Chunk, embed, and store all resumes in ChromaDB."""
    total_chunks = 0

    for r in resumes:
        chunks = chunk_resume(r["text"])
        metadata = extract_metadata(r["text"])

        if not chunks:
            print(f"⚠️  No chunks extracted from: {r['file']}")
            continue

        for i, chunk in enumerate(chunks):
            if not chunk["content"].strip():
                continue

            try:
                emb = embed_text(chunk["content"])

                # ✅ All metadata values must be str/int/float — no lists/None
                chunk_meta = {
                    "section": chunk["section"],
                    "file": r["file"],
                    "name": str(metadata.get("name", "Unknown")),
                    "skills": str(metadata.get("skills", "")),
                    "experience_years": int(metadata.get("experience_years", 0)),
                    "education": str(metadata.get("education", "Unknown")),
                }

                doc_id = f"{r['file'].replace(' ', '_')}_{i}"

                collection.add(
                    documents=[chunk["content"]],
                    embeddings=[emb.tolist()],
                    metadatas=[chunk_meta],
                    ids=[doc_id]
                )
                total_chunks += 1

            except Exception as e:
                print(f"❌ Error indexing chunk {i} of {r['file']}: {e}")

        print(f"   → Indexed {len(chunks)} chunks for: {r['file']} | Name: {metadata['name']}")

    return total_chunks


if __name__ == "__main__":
    print("=" * 55)
    print("  RAG Resume Indexer")
    print("=" * 55)

    # Load resumes
    resumes = load_resumes(RESUME_FOLDER)
    print(f"\n📄 Loaded {len(resumes)} resume(s)\n")

    if not resumes:
        print("No resumes found. Add PDF/DOCX files to data/resumes/")
        exit(1)

    # Setup ChromaDB — wipe old collection and recreate
    client = chromadb.PersistentClient(path=DB_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print("🗑️  Cleared old collection\n")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}   # ✅ use cosine similarity
    )

    # Index
    total = index_resumes(resumes, collection)

    print(f"\n✅ Indexing complete — {total} total chunks stored to '{DB_PATH}/'")
    print(f"   Collection size: {collection.count()} entries")