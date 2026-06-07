# agents/reporting/report_agent.py

"""
Report Agent - Generates structured technical due diligence reports.

This agent separates report generation from orchestration logic.
It is designed to map to the final reporting step in a UiPath Maestro Case flow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class ReportResult:
    report: dict
    executive_summary: str
    audit_trail: list[str] = field(default_factory=list)


class ReportAgent:
    """
    Builds a structured final report from:
    - case metadata
    - documents
    - NLP outputs
    - Technology DD results
    - Risk results
    - Decision results
    """

    def __init__(self):
        logger.info("ReportAgent initialized")

    def generate(
        self,
        case_id: str,
        query: str,
        status: str,
        documents: list[dict],
        term_overlaps: dict,
        tech_dd_result: dict,
        risk_score: dict,
        decision_result: dict,
    ) -> ReportResult:
        source_counts = self._source_breakdown(documents)
        top_overlaps = self._top_overlaps(term_overlaps)
        all_terms_count = self._count_unique_terms(term_overlaps)

        executive_summary = self._executive_summary(
            query=query,
            status=status,
            risk_score=risk_score,
            tech_dd_result=tech_dd_result,
            decision_result=decision_result,
            total_documents=len(documents),
        )

        report = {
            "case_id": case_id,
            "query": query,
            "generated_at": datetime.now().isoformat(),
            "status": status,
            "escalated": bool(decision_result.get("requires_human_review", False)),
            "executive_summary": executive_summary,
            "summary": {
                "total_documents": len(documents),
                "source_breakdown": source_counts,
                "total_key_terms": all_terms_count,
                "overlapping_terms": len(term_overlaps),
            },
            "technology_due_diligence": {
                "novelty_score": tech_dd_result.get("novelty_score"),
                "overlap_score": tech_dd_result.get("overlap_score"),
                "maturity_score": tech_dd_result.get("maturity_score"),
                "evidence_score": tech_dd_result.get("evidence_score"),
                "overall_signal": tech_dd_result.get("overall_signal"),
                "findings": tech_dd_result.get("findings", []),
                "evidence_items": tech_dd_result.get("evidence_items", []),
            },
            "risk_assessment": {
                "overall_score": risk_score.get("overall"),
                "ip_risk": risk_score.get("ip_risk"),
                "tech_maturity": risk_score.get("tech_maturity"),
                "competitive_exposure": risk_score.get("competitive_exposure"),
                "consistency": risk_score.get("consistency"),
                "flags": risk_score.get("flags", []),
            },
            "decision": {
                "decision": decision_result.get("decision"),
                "reason": decision_result.get("reason"),
                "requires_human_review": decision_result.get("requires_human_review"),
                "priority": decision_result.get("priority"),
                "routing_stage": decision_result.get("routing_stage"),
                "actions": decision_result.get("actions", []),
            },
            "top_overlap_terms": [
                {"term": term, "appears_in": len(sources), "sources": sources}
                for term, sources in top_overlaps
            ],
            "recommendation": self._recommendation(decision_result),
        }

        audit_trail = [
            "ReportAgent received completed case context.",
            f"Generated executive summary for query: {query}",
            f"Included {len(documents)} documents in the report.",
            f"Decision routed to: {decision_result.get('routing_stage')}",
        ]

        logger.info(f"Report generated for case {case_id}")
        return ReportResult(
            report=report,
            executive_summary=executive_summary,
            audit_trail=audit_trail,
        )

    @staticmethod
    def _source_breakdown(documents: list[dict]) -> dict:
        source_counts = {}
        for doc in documents:
            src = doc.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1
        return source_counts

    @staticmethod
    def _top_overlaps(term_overlaps: dict) -> list[tuple]:
        return sorted(
            term_overlaps.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        )[:5]

    @staticmethod
    def _count_unique_terms(term_overlaps: dict) -> int:
        return len(term_overlaps.keys())

    @staticmethod
    def _recommendation(decision_result: dict) -> str:
        decision = decision_result.get("decision")

        if decision == "REJECT":
            return "REJECT — Critical risk detected. Senior technical and legal review required."

        if decision == "HUMAN_REVIEW":
            return "ESCALATE TO HUMAN REVIEW — Material risk or uncertainty detected."

        if decision == "NEED_MORE_EVIDENCE":
            return "COLLECT MORE EVIDENCE — Current evidence is insufficient for reliable DD decision."

        if decision == "AUTO_APPROVE_WITH_AUDIT":
            return "APPROVED WITH AUDIT TRAIL — Risk is below threshold but findings should remain reviewable."

        return "APPROVED FOR AUTO-PROCESSING — Risk within acceptable threshold."

    @staticmethod
    def _executive_summary(
        query: str,
        status: str,
        risk_score: dict,
        tech_dd_result: dict,
        decision_result: dict,
        total_documents: int,
    ) -> str:
        overall = risk_score.get("overall")
        signal = tech_dd_result.get("overall_signal")
        decision = decision_result.get("decision")
        priority = decision_result.get("priority")

        return (
            f"TechDD Orchestrator analyzed '{query}' using {total_documents} technical evidence sources. "
            f"The Technology DD Agent produced signal '{signal}', and the Risk Agent assigned an overall "
            f"risk score of {overall}/10. The Decision Agent routed the case as '{decision}' "
            f"with priority '{priority}'. Current case status is '{status}'."
        )


if __name__ == "__main__":
    agent = ReportAgent()

    result = agent.generate(
        case_id="DD_DEMO_001",
        query="transformer neural network patent",
        status="CLOSED",
        documents=[
            {"source": "arXiv", "title": "Paper A"},
            {"source": "USPTO", "title": "Patent B"},
        ],
        term_overlaps={
            "neural network": ["arXiv:Paper A", "USPTO:Patent B"],
        },
        tech_dd_result={
            "novelty_score": 5.8,
            "overlap_score": 3.16,
            "maturity_score": 6.0,
            "evidence_score": 5.4,
            "overall_signal": "MODERATE_TECHNICAL_RISK",
            "findings": ["Moderate overlap detected."],
            "evidence_items": [],
        },
        risk_score={
            "overall": 2.67,
            "ip_risk": 0.0,
            "tech_maturity": 6.0,
            "competitive_exposure": 0.42,
            "consistency": 0.33,
            "flags": ["Low consistency between patent and literature."],
        },
        decision_result={
            "decision": "AUTO_APPROVE_WITH_AUDIT",
            "reason": "Moderate risk below threshold.",
            "requires_human_review": False,
            "priority": "LOW",
            "routing_stage": "AUTO_CLOSE_WITH_AUDIT",
            "actions": ["Generate structured DD report"],
        },
    )

    print(result.executive_summary)
    print(result.report)
