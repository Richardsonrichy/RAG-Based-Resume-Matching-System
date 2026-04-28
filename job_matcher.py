import chromadb
import json
import time
from utils import embed_text, extract_skills, keyword_score, check_must_have

# ─── Connect to same persistent DB ────────────────────────────────────────────
DB_PATH = "vector_db"
COLLECTION_NAME = "resumes"

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


def search(query, top_k=10):
    """
    Embed the query and retrieve top_k similar chunks from ChromaDB.
    Returns raw results including distances.
    """
    emb = embed_text(query)

    # Clamp top_k to available documents
    available = collection.count()
    if available == 0:
        print("❌ No resumes indexed. Run resume_rag.py first.")
        return None

    k = min(top_k, available)

    results = collection.query(
        query_embeddings=[emb.tolist()],
        n_results=k,
        include=["documents", "metadatas", "distances", "embeddings"]
    )

    if not results["documents"] or not results["documents"][0]:
        return None

    return results


def cosine_distance_to_score(distance):
    """
    ChromaDB cosine distance: 0 = identical, 2 = opposite.
    Convert to 0-100 score where 100 = perfect match.
    """
    # distance range [0, 2] → similarity [0, 1] → score [0, 100]
    similarity = 1 - (distance / 2)
    return round(max(0, min(100, similarity * 100)))


def aggregate_by_candidate(results, query):
    """
    ChromaDB returns one row per CHUNK. Multiple chunks belong to the same resume.
    This aggregates chunks by filename, keeping the best-scoring chunk per file.
    """
    candidates = {}   # key: file name

    distances = results.get("distances", [[]])[0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
        file_name = meta["file"]
        semantic_score = cosine_distance_to_score(dist)
        kw_bonus = keyword_score(doc, query)
        total_score = min(100, semantic_score + kw_bonus)

        if file_name not in candidates:
            candidates[file_name] = {
                "meta": meta,
                "best_score": total_score,
                "best_doc": doc,
                "best_section": meta.get("section", "UNKNOWN"),
                "all_docs": [doc],
                "semantic_score": semantic_score,
            }
        else:
            # Keep track of all chunks; update best if this one scores higher
            candidates[file_name]["all_docs"].append(doc)
            if total_score > candidates[file_name]["best_score"]:
                candidates[file_name]["best_score"] = total_score
                candidates[file_name]["best_doc"] = doc
                candidates[file_name]["best_section"] = meta.get("section", "UNKNOWN")
                candidates[file_name]["semantic_score"] = semantic_score

    return candidates


def build_output(candidates, query):
    """Build sorted, formatted match results."""
    matches = []

    for file_name, data in candidates.items():
        meta = data["meta"]
        must_pass = check_must_have(query, meta)
        penalty = 0 if must_pass else 15
        final_score = max(0, data["best_score"] - penalty)

        # Matched skills: union across all chunks for this candidate
        all_text = "\n".join(data["all_docs"])
        matched = extract_skills(all_text)

        # Build reasoning string
        reasons = [f"Best match via {data['best_section']} section"]
        if not must_pass:
            reasons.append("missing required experience years (-15 pts)")

        matches.append({
            "candidate_name": meta.get("name", file_name),
            "resume_path": f"data/resumes/{file_name}",
            "match_score": final_score,
            "semantic_score": data["semantic_score"],
            "matched_skills": matched,
            "relevant_excerpts": [data["best_doc"][:200]],
            "reasoning": " | ".join(reasons),
            "education": meta.get("education", "Unknown"),
            "experience_years": meta.get("experience_years", 0),
        })

    # Sort by final score descending
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches


def match_job(job_description, top_k=10):
    """Main matching function. Returns structured JSON-ready output."""
    start = time.time()

    results = search(job_description, top_k=top_k)
    if not results:
        return {
            "job_description": job_description,
            "top_matches": [],
            "error": "No results found. Index resumes first.",
            "latency_sec": 0
        }

    candidates = aggregate_by_candidate(results, job_description)
    top_matches = build_output(candidates, job_description)

    end = time.time()

    return {
        "job_description": job_description,
        "top_matches": top_matches,
        "total_candidates_found": len(top_matches),
        "latency_sec": round(end - start, 3)
    }


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  RAG Job Matcher")
    print("=" * 55)
    print("\n🔍 Enter Job Description (press Enter twice when done):\n")

    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    jd = " ".join(lines)

    if not jd.strip():
        print("❌ No job description entered.")
        exit(1)

    print("\n⏳ Matching...\n")
    result = match_job(jd)

    print("🎯 MATCH RESULTS:\n")
    print(json.dumps(result, indent=2))