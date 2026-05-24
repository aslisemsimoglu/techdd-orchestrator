# agents/analysis/nlp_agent.py

"""
NLP Agent - Extracts key entities, technology terms, and claims from documents
Runs fully locally using spaCy and regex — no API key required
"""

import re
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class NLPResult:
    doc_id: str
    title: str
    source: str
    key_terms: list[str]
    tech_entities: list[str]
    claims: list[str]
    summary_sentences: list[str]
    claim_count: int = 0


class NLPAgent:
    """
    Extracts structured information from patent and paper text.
    Uses regex + simple NLP — no external model needed for basic operation.
    """

    # Technology domain keywords to extract
    TECH_DOMAINS = [
        "machine learning", "deep learning", "neural network", "transformer",
        "large language model", "llm", "natural language processing", "nlp",
        "computer vision", "reinforcement learning", "generative ai",
        "diffusion model", "embedding", "fine-tuning", "rag",
        "retrieval augmented", "vector database", "knowledge graph",
        "robotics", "automation", "rpa", "api", "microservice",
        "blockchain", "cryptography", "cybersecurity", "cloud computing",
        "edge computing", "iot", "semiconductor", "quantum computing",
        "bioinformatics", "drug discovery", "genomics",
    ]

    # Patent claim starters
    CLAIM_PATTERNS = [
        r'[Cc]laim\s+\d+[:\.]?\s*(.+?)(?=\n|[Cc]laim\s+\d+|$)',
        r'(?:A\s+)?method\s+(?:for|of)\s+(.+?)(?=\.|$)',
        r'[Aa]\s+system\s+(?:for|of|that)\s+(.+?)(?=\.|$)',
        r'[Aa]\s+(?:computer-implemented\s+)?(?:apparatus|device)\s+(?:for|that)\s+(.+?)(?=\.|$)',
    ]

    def __init__(self):
        logger.info("NLPAgent initialized")

    def extract_key_terms(self, text: str) -> list[str]:
        """Extract technology domain terms from text"""
        if not text:
            return []
        text_lower = text.lower()
        found = []
        for term in self.TECH_DOMAINS:
            if term in text_lower:
                found.append(term)
        return list(set(found))

    def extract_tech_entities(self, text: str) -> list[str]:
        """Extract capitalized technical entities (product names, frameworks, etc.)"""
        if not text:
            return []

        # Match capitalized multi-word phrases (likely proper nouns / product names)
        pattern = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b'
        candidates = re.findall(pattern, text)

        # Filter: keep only meaningful ones (length > 3, not common words)
        stopwords = {
            "The", "This", "These", "That", "With", "From", "Into",
            "For", "And", "But", "Our", "We", "In", "Is", "Are",
            "Abstract", "Introduction", "Conclusion", "Figure", "Table"
        }
        entities = [c for c in candidates if c not in stopwords and len(c) > 3]

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                unique.append(e)

        return unique[:20]  # top 20

    def extract_claims(self, text: str) -> list[str]:
        """Extract patent claims or key assertions from text"""
        if not text:
            return []

        claims = []
        for pattern in self.CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                clean = match.strip().replace('\n', ' ')
                clean = re.sub(r'\s+', ' ', clean)
                if len(clean) > 20:
                    claims.append(clean[:300])

        return claims[:10]  # top 10 claims

    def extract_summary_sentences(self, text: str, n: int = 3) -> list[str]:
        """Extract most informative sentences (simple heuristic: longest sentences)"""
        if not text:
            return []

        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 50]

        # Score by length and keyword density
        def score(s):
            s_lower = s.lower()
            kw_hits = sum(1 for term in self.TECH_DOMAINS if term in s_lower)
            return len(s) + kw_hits * 20

        scored = sorted(sentences, key=score, reverse=True)
        return scored[:n]

    def process(self, document: dict) -> NLPResult:
        """Process a single document and return structured NLP result"""
        title = document.get("title", "")
        abstract = document.get("abstract", "")
        claims_text = document.get("claims", "")
        source = document.get("source", "unknown")
        doc_id = document.get("paper_id") or document.get("patent_id") or "unknown"

        full_text = f"{title} {abstract} {claims_text}"

        key_terms = self.extract_key_terms(full_text)
        tech_entities = self.extract_tech_entities(full_text)
        claims = self.extract_claims(claims_text or abstract)
        summary = self.extract_summary_sentences(abstract)

        result = NLPResult(
            doc_id=doc_id,
            title=title,
            source=source,
            key_terms=key_terms,
            tech_entities=tech_entities,
            claims=claims,
            summary_sentences=summary,
            claim_count=len(claims),
        )

        logger.debug(f"NLP processed: '{title[:50]}' → {len(key_terms)} terms, {len(claims)} claims")
        return result

    def process_batch(self, documents: list[dict]) -> list[NLPResult]:
        """Process multiple documents"""
        logger.info(f"NLP processing {len(documents)} documents")
        results = [self.process(doc) for doc in documents]
        logger.success(f"NLP complete: {len(results)} documents processed")
        return results

    def find_term_overlaps(self, results: list[NLPResult]) -> dict:
        """
        Find technology terms that appear across multiple documents.
        High overlap = potential IP conflict zone.
        """
        term_map: dict[str, list[str]] = {}

        for result in results:
            for term in result.key_terms:
                if term not in term_map:
                    term_map[term] = []
                term_map[term].append(f"{result.source}:{result.title[:40]}")

        # Keep only terms appearing in 2+ documents
        overlaps = {k: v for k, v in term_map.items() if len(v) >= 2}
        return overlaps


if __name__ == "__main__":
    mock_docs = [
        {
            "paper_id": "doc001",
            "title": "Deep Learning Patent for Neural Network Optimization",
            "abstract": "This patent presents a novel method for training neural networks using transformer architecture. The system leverages large language models for natural language processing tasks. A method for optimizing deep learning models using gradient descent.",
            "claims": "Claim 1: A method for training neural networks comprising gradient descent optimization. Claim 2: A system for natural language processing using transformer architecture.",
            "source": "USPTO",
        },
        {
            "paper_id": "doc002",
            "title": "Survey of Large Language Models for NLP Tasks",
            "abstract": "We present a comprehensive survey of large language models applied to natural language processing. Deep learning architectures including transformer models are evaluated. Our retrieval augmented generation system outperforms baselines.",
            "claims": "",
            "source": "arXiv",
        },
        {
            "paper_id": "doc003",
            "title": "Reinforcement Learning for Automation Systems",
            "abstract": "This paper explores reinforcement learning applied to robotic process automation. Neural network controllers are trained using machine learning techniques. Edge computing enables real-time inference.",
            "claims": "",
            "source": "arXiv",
        },
    ]

    agent = NLPAgent()
    results = agent.process_batch(mock_docs)

    print(f"\n{'='*60}")
    print("NLP EXTRACTION RESULTS")
    print(f"{'='*60}")

    for r in results:
        print(f"\n[{r.source}] {r.title[:60]}")
        print(f"  Key Terms     : {', '.join(r.key_terms)}")
        print(f"  Tech Entities : {', '.join(r.tech_entities[:5])}")
        print(f"  Claims ({r.claim_count}): {r.claims[0][:100] if r.claims else 'None'}...")
        print(f"  Summary       : {r.summary_sentences[0][:120] if r.summary_sentences else 'None'}...")

    print(f"\n{'='*60}")
    print("TERM OVERLAP ANALYSIS (potential IP conflict zones)")
    print(f"{'='*60}")
    overlaps = agent.find_term_overlaps(results)
    for term, sources in overlaps.items():
        print(f"  '{term}' appears in {len(sources)} documents:")
        for s in sources:
            print(f"    → {s}")