# agents/analysis/tech_dd_agent.py

from dataclasses import dataclass, field
from loguru import logger
import re
from typing import Any


@dataclass
class TechnologyDDResult:
    novelty_score: float
    overlap_score: float
    maturity_score: float
    evidence_score: float
    overall_signal: str
    findings: list[str] = field(default_factory=list)
    evidence_items: list[dict] = field(default_factory=list)


class TechDDAgent:
    """
    Specialist Technical Due Diligence Agent.

    Purpose:
    - Reason over patents, papers, and extracted NLP results.
    - Produce evidence-based technical DD signals before final risk scoring.
    - Acts as the specialist coded agent layer in the UiPath agentic architecture.
    """

    MATURITY_SIGNALS = [
        "benchmark", "production", "deployment", "scalable", "evaluation",
        "experiment", "dataset", "real-world", "case study", "implementation",
        "performance", "validated", "commercial", "industrial"
    ]

    NOVELTY_SIGNALS = [
        "novel", "new", "proposed", "first", "original", "innovative",
        "previously", "prior art", "state of the art"
    ]

    OVERLAP_SIGNALS = [
        "similar", "overlap", "related", "same", "equivalent", "claim",
        "architecture", "method", "system", "framework", "model"
    ]

    def __init__(self):
        logger.info("TechDDAgent initialized")

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower()).strip()

    @staticmethod
    def _safe_text(doc: dict) -> str:
        return " ".join([
            str(doc.get("title", "")),
            str(doc.get("abstract", "")),
            str(doc.get("claims", "")),
        ])

    @staticmethod
    def _keyword_hits(text: str, keywords: list[str]) -> int:
        text = text.lower()
        return sum(1 for kw in keywords if kw in text)

    def _split_sources(self, documents: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
        patents = [d for d in documents if d.get("source") in ("USPTO", "EPO")]
        papers = [d for d in documents if d.get("source") in ("arXiv", "SemanticScholar")]
        reports = [d for d in documents if d.get("source") in ("SEC", "EDGAR", "Web", "Report")]
        return patents, papers, reports

    def _term_overlap_ratio(self, a: str, b: str) -> float:
        words_a = set(re.findall(r"\b[a-zA-Z]{5,}\b", self._normalize(a)))
        words_b = set(re.findall(r"\b[a-zA-Z]{5,}\b", self._normalize(b)))

        if not words_a or not words_b:
            return 0.0

        return len(words_a & words_b) / len(words_a | words_b)

    def analyze(
        self,
        documents: list[dict],
        nlp_results: list[dict] | None = None,
        rag_evidence: list[dict] | None = None,
    ) -> TechnologyDDResult:
        if not documents:
            return TechnologyDDResult(
                novelty_score=0.0,
                overlap_score=0.0,
                maturity_score=0.0,
                evidence_score=0.0,
                overall_signal="INSUFFICIENT_EVIDENCE",
                findings=["No documents were provided for technical due diligence."],
            )

        patents, papers, reports = self._split_sources(documents)
        findings = []
        evidence_items = []

        # Evidence score: source diversity + document count
        source_types = len(set(d.get("source", "unknown") for d in documents))
        evidence_score = min((len(documents) * 0.6) + (source_types * 1.5), 10.0)

        if len(patents) == 0:
            findings.append("No patent source was found; IP risk assessment is limited.")
        if len(papers) == 0:
            findings.append("No academic literature source was found; novelty assessment is limited.")
        if source_types >= 2:
            findings.append(f"Evidence base includes {source_types} distinct source types.")

        # Maturity score
        all_text = " ".join(self._safe_text(d) for d in documents)
        maturity_hits = self._keyword_hits(all_text, self.MATURITY_SIGNALS)
        maturity_score = min(3.0 + maturity_hits * 0.8 + len(documents) * 0.15, 10.0)

        if maturity_score >= 7:
            findings.append("Technology shows maturity signals such as evaluation, deployment, or benchmarking.")
        elif maturity_score <= 4:
            findings.append("Technology appears early-stage or weakly validated based on available evidence.")

        # Novelty score
        novelty_hits = self._keyword_hits(all_text, self.NOVELTY_SIGNALS)
        novelty_score = min(4.0 + novelty_hits * 0.9, 10.0)

        if novelty_hits > 0:
            findings.append("Novelty-related language was detected in the collected evidence.")

        # Overlap score: patent-paper similarity
        overlap_values = []
        for patent in patents:
            p_text = self._safe_text(patent)
            for paper in papers:
                paper_text = self._safe_text(paper)
                ratio = self._term_overlap_ratio(p_text, paper_text)
                if ratio > 0:
                    overlap_values.append(ratio)
                if ratio >= 0.12:
                    evidence_items.append({
                        "type": "patent_literature_overlap",
                        "patent_title": patent.get("title", "Unknown")[:120],
                        "paper_title": paper.get("title", "Unknown")[:120],
                        "overlap_ratio": round(ratio, 3),
                    })

        if overlap_values:
            overlap_score = min(max(overlap_values) * 40, 10.0)
        else:
            overlap_score = 0.0

        if overlap_score >= 6:
            findings.append("High overlap detected between patent and literature evidence.")
        elif overlap_score >= 3:
            findings.append("Moderate overlap detected between patent and literature evidence.")
        else:
            findings.append("No strong patent-literature overlap detected with the current heuristic evidence layer.")

        # Use future RAG evidence if present
        if rag_evidence:
            evidence_items.extend(rag_evidence)
            evidence_score = min(evidence_score + 1.0, 10.0)
            findings.append(f"RAG evidence layer contributed {len(rag_evidence)} additional evidence items.")

        # Overall signal
        if evidence_score < 3:
            overall_signal = "INSUFFICIENT_EVIDENCE"
        elif overlap_score >= 7:
            overall_signal = "HIGH_TECHNICAL_OVERLAP"
        elif maturity_score < 4:
            overall_signal = "LOW_MATURITY"
        elif novelty_score >= 7 and overlap_score < 4:
            overall_signal = "PROMISING_DIFFERENTIATED_TECHNOLOGY"
        else:
            overall_signal = "MODERATE_TECHNICAL_RISK"

        result = TechnologyDDResult(
            novelty_score=round(novelty_score, 2),
            overlap_score=round(overlap_score, 2),
            maturity_score=round(maturity_score, 2),
            evidence_score=round(evidence_score, 2),
            overall_signal=overall_signal,
            findings=findings,
            evidence_items=evidence_items[:10],
        )

        logger.info(f"Tech DD analysis complete: {overall_signal}")
        return result


if __name__ == "__main__":
    mock_docs = [
        {
            "title": "Transformer Neural Network Optimization Patent",
            "abstract": "A novel system and method for transformer architecture optimization in large language models.",
            "claims": "Claim 1: A method for optimizing transformer neural networks.",
            "source": "USPTO",
        },
        {
            "title": "Large Language Models and Transformer Optimization",
            "abstract": "This paper evaluates transformer architectures and benchmarking methods for large language model optimization.",
            "source": "arXiv",
        },
    ]

    agent = TechDDAgent()
    result = agent.analyze(mock_docs)
    print(result)