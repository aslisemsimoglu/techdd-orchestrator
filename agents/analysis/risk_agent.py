# agents/analysis/risk_agent.py

"""
Risk Agent - Scores technical due diligence risk from patents and papers
Runs fully locally, no API key or network required
"""

from dataclasses import dataclass, field
from typing import Optional
from loguru import logger
import re


@dataclass
class RiskScore:
    overall: float          # 0.0 - 10.0
    ip_risk: float          # IP conflict / patent overlap risk
    tech_maturity: float    # How mature is the technology (higher = more mature = lower risk)
    competitive_exposure: float  # How crowded is the space
    consistency: float      # How consistent are findings across sources
    flags: list[str] = field(default_factory=list)   # Human-readable risk flags
    escalate: bool = False  # Should this be escalated to human reviewer


class RiskAgent:
    """
    Scores risk based on patent and literature findings.
    Pure logic, no external dependencies.
    """

    # Keywords that raise IP risk
    IP_RISK_KEYWORDS = [
        "infringement", "violation", "conflict", "dispute", "litigation",
        "injunction", "licensing", "royalty", "patent pending", "trade secret",
        "intellectual property", "claim overlap", "prior art"
    ]

    # Keywords suggesting immature / risky technology
    IMMATURITY_KEYWORDS = [
        "novel", "proposed", "preliminary", "experimental", "prototype",
        "proof of concept", "early stage", "under development", "future work",
        "limitation", "challenge", "open problem", "unsolved"
    ]

    # Keywords suggesting competitive crowding
    COMPETITION_KEYWORDS = [
        "competitive", "state of the art", "benchmark", "outperform",
        "comparison", "versus", "alternative", "competing", "rival"
    ]

    def __init__(self, escalation_threshold: float = 7.0):
        self.escalation_threshold = escalation_threshold
        logger.info(f"RiskAgent initialized (escalation threshold: {escalation_threshold})")

    def _keyword_score(self, text: str, keywords: list[str]) -> float:
        """Count keyword hits in text, return normalized score 0-10"""
        if not text:
            return 0.0
        text_lower = text.lower()
        hits = sum(1 for kw in keywords if kw in text_lower)
        return min(hits * 1.5, 10.0)

    def _assess_ip_risk(self, documents: list[dict]) -> tuple[float, list[str]]:
        """Assess IP conflict risk across all documents"""
        flags = []
        scores = []

        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('abstract', '')} {doc.get('claims', '')}"
            score = self._keyword_score(text, self.IP_RISK_KEYWORDS)
            scores.append(score)

            if score >= 3.0:
                flags.append(f"IP risk signal in: '{doc.get('title', 'Unknown')[:60]}...'")

        avg = sum(scores) / len(scores) if scores else 0.0

        # Extra flag if multiple documents signal IP risk
        if sum(1 for s in scores if s >= 3.0) >= 3:
            flags.append("CRITICAL: Multiple documents show IP conflict signals")
            avg = min(avg * 1.3, 10.0)

        return round(avg, 2), flags

    def _assess_tech_maturity(self, documents: list[dict]) -> tuple[float, list[str]]:
        """Assess technology maturity — lower score = less mature = higher risk"""
        flags = []
        scores = []

        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('abstract', '')}"
            immaturity = self._keyword_score(text, self.IMMATURITY_KEYWORDS)
            # Invert: high immaturity keywords = low maturity score
            maturity = max(0.0, 10.0 - immaturity)
            scores.append(maturity)

        avg = sum(scores) / len(scores) if scores else 5.0

        if avg < 4.0:
            flags.append("WARNING: Technology shows signs of low maturity")
        elif avg > 7.0:
            flags.append("INFO: Technology appears well-established")

        return round(avg, 2), flags

    def _assess_competitive_exposure(self, documents: list[dict]) -> tuple[float, list[str]]:
        """Assess how crowded/competitive the technology space is"""
        flags = []
        scores = []

        for doc in documents:
            text = f"{doc.get('title', '')} {doc.get('abstract', '')}"
            score = self._keyword_score(text, self.COMPETITION_KEYWORDS)
            scores.append(score)

        avg = sum(scores) / len(scores) if scores else 0.0

        # More documents = more crowded space
        doc_count_factor = min(len(documents) / 10, 1.0)
        avg = avg * (1 + doc_count_factor * 0.3)
        avg = min(avg, 10.0)

        if avg >= 5.0:
            flags.append(f"WARNING: High competitive activity detected ({len(documents)} sources)")

        return round(avg, 2), flags

    def _assess_consistency(self, documents: list[dict]) -> tuple[float, list[str]]:
        """
        Assess consistency across sources.
        Simple heuristic: check if patent claims contradict academic findings.
        """
        flags = []

        patents = [d for d in documents if d.get("source") in ("USPTO", "EPO")]
        papers = [d for d in documents if d.get("source") in ("arXiv", "SemanticScholar")]

        if not patents or not papers:
            return 5.0, ["INFO: Only one source type available, consistency check limited"]

        # Heuristic: extract key terms from patents vs papers
        patent_terms = set()
        for p in patents:
            words = re.findall(r'\b\w{6,}\b', p.get("abstract", "").lower())
            patent_terms.update(words[:50])

        paper_terms = set()
        for p in papers:
            words = re.findall(r'\b\w{6,}\b', p.get("abstract", "").lower())
            paper_terms.update(words[:50])

        if not patent_terms or not paper_terms:
            return 5.0, flags

        overlap = len(patent_terms & paper_terms)
        total = len(patent_terms | paper_terms)
        overlap_ratio = overlap / total if total > 0 else 0

        # High overlap = consistent sources = lower risk
        consistency_score = overlap_ratio * 10

        if consistency_score < 3.0:
            flags.append("WARNING: Low consistency between patent claims and academic literature")
        elif consistency_score > 7.0:
            flags.append("INFO: Patent claims and academic literature are well-aligned")

        return round(consistency_score, 2), flags

    def score(self, documents: list[dict]) -> RiskScore:
        """Main entry point — score a list of documents"""
        if not documents:
            logger.warning("No documents provided to RiskAgent")
            return RiskScore(
                overall=0.0, ip_risk=0.0, tech_maturity=5.0,
                competitive_exposure=0.0, consistency=5.0,
                flags=["WARNING: No documents provided"]
            )

        logger.info(f"Scoring risk for {len(documents)} documents")

        ip_risk, ip_flags = self._assess_ip_risk(documents)
        tech_maturity, maturity_flags = self._assess_tech_maturity(documents)
        competitive, comp_flags = self._assess_competitive_exposure(documents)
        consistency, cons_flags = self._assess_consistency(documents)

        # Overall risk: weighted average
        # IP risk weighted highest, maturity risk is inverse
        maturity_risk = 10.0 - tech_maturity
        overall = (
            ip_risk * 0.35 +
            maturity_risk * 0.25 +
            competitive * 0.20 +
            (10.0 - consistency) * 0.20
        )
        overall = round(min(overall, 10.0), 2)

        all_flags = ip_flags + maturity_flags + comp_flags + cons_flags
        escalate = overall >= self.escalation_threshold

        if escalate:
            all_flags.insert(0, f"🚨 ESCALATE TO HUMAN REVIEW — Overall risk: {overall}/10")

        result = RiskScore(
            overall=overall,
            ip_risk=ip_risk,
            tech_maturity=tech_maturity,
            competitive_exposure=competitive,
            consistency=consistency,
            flags=all_flags,
            escalate=escalate,
        )

        logger.info(f"Risk scoring complete — Overall: {overall}/10, Escalate: {escalate}")
        return result


if __name__ == "__main__":
    # Test with mock documents
    mock_docs = [
        {
            "title": "Deep Learning Patent for Neural Network Optimization",
            "abstract": "This patent claims a novel method for training neural networks. Prior art suggests significant overlap with existing techniques. Licensing required for commercial use.",
            "claims": "Claim 1: A method for optimizing neural networks using gradient descent with patent pending status.",
            "source": "USPTO",
        },
        {
            "title": "Survey of Large Language Models",
            "abstract": "We present a comprehensive survey of state of the art large language models. Comparison with competing approaches shows significant performance improvements. Early stage deployment challenges remain.",
            "source": "arXiv",
        },
        {
            "title": "Transformer Architecture: Limitations and Future Work",
            "abstract": "This paper explores the limitations of transformer architectures. Several open problems remain unsolved. Experimental results show promising but preliminary outcomes.",
            "source": "arXiv",
        },
    ]

    agent = RiskAgent(escalation_threshold=7.0)
    score = agent.score(mock_docs)

    print(f"\n{'='*60}")
    print(f"RISK ASSESSMENT REPORT")
    print(f"{'='*60}")
    print(f"Overall Risk Score : {score.overall}/10")
    print(f"IP Risk            : {score.ip_risk}/10")
    print(f"Tech Maturity      : {score.tech_maturity}/10 (higher = more mature)")
    print(f"Competitive Exp.   : {score.competitive_exposure}/10")
    print(f"Consistency        : {score.consistency}/10")
    print(f"Escalate to Human  : {'YES 🚨' if score.escalate else 'NO ✅'}")
    print(f"\nFlags:")
    for flag in score.flags:
        print(f"  • {flag}")