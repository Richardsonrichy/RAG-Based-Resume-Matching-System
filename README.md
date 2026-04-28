
#  RAG-Based Resume Matching System

##  Overview
This project implements a Retrieval-Augmented Generation (RAG) pipeline to match resumes with job descriptions using semantic search and keyword scoring.

##  Objectives
- Document chunking and embedding
- Vector database (ChromaDB)
- Semantic search
- Hybrid ranking (semantic + keyword)

##  Architecture
1. Load resumes (PDF/DOCX)
2. Chunk into sections (Summary, Skills, Experience, Education)
3. Generate embeddings (MiniLM)
4. Store in ChromaDB
5. Query embedding from job description
6. Retrieve top matches
7. Rank using hybrid scoring

##  Project Structure
RAG-Based-Profile-Matching/
├── data/resumes/
├── vector_db/
├── resume_rag.py
├── job_matcher.py
├── utils.py
├── generate_resumes.py
├── analysis.ipynb
├── requirements.txt
└── README.md

## Installation
pip install -r requirements.txt

## ▶ Run

# Step 1: 
python generate_resumes.py

# Step 2:
python resume_rag.py

# Step 3:
python job_matcher.py

##  Sample Output
{
  "job_description": "Python backend developer",
  "top_matches": [
    {
      "candidate_name": "John Doe",
      "resume_path": "data/resumes/resume.pdf",
      "match_score": 97,
      "matched_skills": ["python", "django", "api"],
      "relevant_excerpts": ["Developed REST APIs"],
      "reasoning": "Matched via EXPERIENCE section"
    }
  ],
  "latency_sec": 0.18
}

##  Notebook
analysis.ipynb contains:
- Pipeline steps
- Experiments
- Results
- Observations

##  Performance
- Latency: <1s
- DB: ChromaDB
- Model: MiniLM

##  Features
- Semantic search
- Hybrid scoring
- Metadata extraction
- Fast retrieval

##  Limitations
- Depends on resume quality
- Basic keyword extraction

## Future Work
- UI (Streamlit)
- Better NLP extraction
- Advanced embeddings

##  Conclusion
Production-ready RAG pipeline for resume-job matching using vector search and hybrid ranking.

