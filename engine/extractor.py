import spacy
from pydantic import BaseModel
from spacy.language import Language
from spacy.pipeline import EntityRuler

from config import get_settings

SEED_SKILLS: list[str] = [
    "Python",
    "FastAPI",
    "SQL",
    "PostgreSQL",
    "Docker",
    "Kubernetes",
    "AWS",
    "GCP",
    "Azure",
    "React",
    "TypeScript",
    "JavaScript",
    "Node.js",
    "REST API",
    "GraphQL",
    "Machine Learning",
    "TensorFlow",
    "PyTorch",
    "pandas",
    "NumPy",
    "scikit-learn",
    "Git",
    "Linux",
    "Terraform",
    "Redis",
    "MongoDB",
    "Elasticsearch",
    "Spark",
    "Kafka",
    "Airflow",
    # Data Science / ML
    "XGBoost",
    "LightGBM",
    "Hugging Face",
    "transformers",
    "BERT",
    "LangChain",
    "Jupyter",
    "Matplotlib",
    "Seaborn",
    "SciPy",
    "MLflow",
    "DVC",
    "ONNX",
    # Cloud & Infrastructure
    "Lambda",
    "S3",
    "EC2",
    "RDS",
    "EKS",
    "CloudFormation",
    "Pulumi",
    "Ansible",
    "Helm",
    "Prometheus",
    "Grafana",
    "Datadog",
    # DevOps & CI/CD
    "GitHub Actions",
    "GitLab CI",
    "Jenkins",
    "CircleCI",
    "ArgoCD",
    "Nginx",
    "Vault",
    # Frontend
    "Vue.js",
    "Angular",
    "Next.js",
    "Tailwind CSS",
    "Webpack",
    "Vite",
    "Redux",
    "HTML",
    "CSS",
    # Backend
    "Django",
    "Flask",
    "Spring Boot",
    "Go",
    "Rust",
    "Java",
    "gRPC",
    "Ruby on Rails",
    # Databases
    "MySQL",
    "SQLite",
    "DynamoDB",
    "Cassandra",
    "Neo4j",
    "Snowflake",
    "BigQuery",
    "dbt",
    # Data Engineering
    "Databricks",
    "Hive",
    "Presto",
    "Celery",
    "Flink",
]

EDUCATION_KEYWORDS: list[str] = [
    "university",
    "college",
    "institute",
    "school",
    "bachelor",
    "master",
    "phd",
    "doctorate",
    "b.s.",
    "m.s.",
    "b.a.",
    "m.a.",
    "mba",
]

TITLE_KEYWORDS: list[str] = [
    "engineer",
    "developer",
    "architect",
    "analyst",
    "scientist",
    "manager",
    "lead",
    "director",
    "consultant",
    "specialist",
    "designer",
    "administrator",
    "devops",
    "sre",
    "mlops",
    "intern",
]

CERT_KEYWORDS: list[str] = [
    "certified",
    "certificate",
    "certification",
    "aws certified",
    "gcp professional",
    "azure certified",
    "ckad",
    "cka",
    "pmp",
    "comptia",
    "cissp",
    "ceh",
]


class ResumeEntities(BaseModel):
    skills: list[str]
    job_titles: list[str]
    companies: list[str]
    education: list[str]
    certifications: list[str]


class EntityExtractor:
    def __init__(self) -> None:
        settings = get_settings()
        self._nlp: Language = spacy.load(settings.SPACY_MODEL)
        self._add_skill_ruler()

    def _add_skill_ruler(self) -> None:
        ruler: EntityRuler = self._nlp.add_pipe(
            "entity_ruler", before="ner", config={"overwrite_ents": False}
        )
        patterns = [
            {"label": "SKILL", "pattern": skill} for skill in SEED_SKILLS
        ]
        patterns += [
            {"label": "SKILL", "pattern": skill.lower()} for skill in SEED_SKILLS
        ]
        ruler.add_patterns(patterns)

    def extract(self, text: str) -> ResumeEntities:
        if not text.strip():
            return ResumeEntities(
                skills=[],
                job_titles=[],
                companies=[],
                education=[],
                certifications=[],
            )

        doc = self._nlp(text)

        skills: list[str] = []
        companies: list[str] = []
        education: list[str] = []
        job_titles: list[str] = []
        certifications: list[str] = []

        for ent in doc.ents:
            if ent.label_ == "SKILL":
                skills.append(ent.text)
            elif ent.label_ == "ORG":
                lower = ent.text.lower()
                if any(kw in lower for kw in EDUCATION_KEYWORDS):
                    education.append(ent.text)
                else:
                    companies.append(ent.text)

        for token in doc:
            token_lower = token.text.lower()
            if any(kw in token_lower for kw in TITLE_KEYWORDS):
                span_start = max(0, token.i - 2)
                span_end = min(len(doc), token.i + 3)
                phrase = doc[span_start:span_end].text.strip()
                job_titles.append(phrase)

        lines = text.split("\n")
        for line in lines:
            line_lower = line.lower().strip()
            if any(kw in line_lower for kw in CERT_KEYWORDS):
                cleaned = line.strip()
                if cleaned:
                    certifications.append(cleaned)

        for seed in SEED_SKILLS:
            if seed.lower() in text.lower() and seed not in skills:
                skills.append(seed)

        return ResumeEntities(
            skills=_dedupe(skills),
            job_titles=_dedupe(job_titles),
            companies=_dedupe(companies),
            education=_dedupe(education),
            certifications=_dedupe(certifications),
        )


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        normalized = item.strip()
        key = normalized.lower()
        if key and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
