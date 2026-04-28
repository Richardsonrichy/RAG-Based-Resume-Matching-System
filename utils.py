import re
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

# ─── Expanded skill list ───────────────────────────────────────────────────────
SKILLS_LIST = [
    # Languages
    "python", "java", "javascript", "typescript", "golang", "scala", "ruby",
    "c++", "c#", "rust", "kotlin", "swift", "r", "matlab", "bash", "shell",
    # Web / API
    "django", "flask", "fastapi", "spring boot", "node.js", "express",
    "rest", "graphql", "grpc", "api", "microservices", "soap",
    # Data / ML / AI
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "spark", "hadoop", "kafka", "airflow", "mlops", "llm", "rag",
    # Databases
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "cassandra", "sqlite", "oracle", "dynamodb", "cosmos db",
    # Query / Analytics
    "kusto", "kql", "azure data explorer", "bigquery", "snowflake",
    "redshift", "hive", "presto", "databricks",
    # Cloud
    "azure", "aws", "gcp", "google cloud", "ec2", "s3", "lambda",
    "azure functions", "cloud run", "app service",
    # DevOps / Infra
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "git",
    "github actions", "ci/cd", "helm", "prometheus", "grafana",
    "datadog", "elk stack", "linux", "devops",
    # Frontend
    "react", "angular", "vue", "html", "css",
]


def clean_text(text):
    text = re.sub(r"-{2,}", "", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def embed_text(text):
    return model.encode(text)


def chunk_resume(text):
    """
    Split resume text into section-based chunks.
    Handles common section headers case-insensitively.
    """
    section_keywords = [
        "professional summary", "summary", "objective",
        "skills", "technical skills", "core competencies",
        "experience", "work experience", "employment history",
        "education", "academic background",
        "projects", "certifications", "achievements", "awards"
    ]

    chunks = []
    current_section = "OTHER"
    current_text = ""

    for line in text.split("\n"):
        stripped = line.strip()
        normalized = stripped.lower()

        matched_section = None
        for kw in section_keywords:
            if normalized == kw or normalized.startswith(kw + " "):
                matched_section = kw.upper()
                break

        if matched_section:
            if current_text.strip():
                chunks.append({
                    "section": current_section,
                    "content": clean_text(current_text)
                })
            current_section = matched_section
            current_text = ""
        else:
            current_text += line + "\n"

    # flush last section
    if current_text.strip():
        chunks.append({
            "section": current_section,
            "content": clean_text(current_text)
        })

    return chunks


def extract_skills(text):
    """Return list of matched skills from text."""
    text_lower = text.lower()
    matched = []
    for skill in SKILLS_LIST:
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
            matched.append(skill)
    return list(set(matched))


def extract_metadata(text):
    """
    Extract name, skills, experience years, education from raw resume text.
    Returns ChromaDB-safe types (str, int, float only — no lists).
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    name = lines[0] if lines else "Unknown"

    # Remove markdown/hyperlink artifacts like [B.Tech](http://B.Tech)
    clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)

    skills = extract_skills(clean)

    # Experience: grab first number followed by "year"
    exp_match = re.search(r'(\d+)\+?\s*years?', clean.lower())
    experience = int(exp_match.group(1)) if exp_match else 0

    # Education
    education = "Unknown"
    clean_lower = clean.lower()
    if "phd" in clean_lower or "ph.d" in clean_lower:
        education = "PhD"
    elif "m.tech" in clean_lower or "mtech" in clean_lower or "m tech" in clean_lower:
        education = "M.Tech"
    elif "m.sc" in clean_lower or "msc" in clean_lower or "master" in clean_lower:
        education = "Masters"
    elif "b.tech" in clean_lower or "btech" in clean_lower or "b tech" in clean_lower:
        education = "B.Tech"
    elif "b.e" in clean_lower or "bachelor" in clean_lower:
        education = "Bachelors"

    return {
        "name": name,
        # ✅ ChromaDB needs string — NOT a list
        "skills": ", ".join(skills) if skills else "",
        "experience_years": experience,
        "education": education
    }


def keyword_score(text, query):
    """
    Bonus score: count how many meaningful query words appear in text.
    Skips stop words.
    """
    stop_words = {"for", "with", "and", "the", "a", "an", "of", "in",
                  "to", "is", "we", "are", "looking", "required", "must"}
    query_words = [w for w in query.lower().split() if w not in stop_words]
    text_lower = text.lower()
    return sum(2 for w in query_words if re.search(r'\b' + re.escape(w) + r'\b', text_lower))


def check_must_have(query, metadata):
    """
    Returns False if candidate clearly doesn't meet hard requirements in JD.
    Checks: years of experience.
    """
    query_lower = query.lower()

    # Look for "X+ years" or "X years" pattern in JD
    exp_match = re.search(r'(\d+)\+?\s*years?', query_lower)
    if exp_match:
        required_exp = int(exp_match.group(1))
        candidate_exp = metadata.get("experience_years", 0)
        if isinstance(candidate_exp, (int, float)) and candidate_exp < required_exp:
            return False

    return True