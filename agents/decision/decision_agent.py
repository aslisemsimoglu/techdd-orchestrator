# agents/decision/decision_agent.py

"""
Decision Agent - Converts risk and technology due diligence signals into a case decision.

This agent represents the explicit decision layer of the TechDD pipeline.
It is designed to map naturally to UiPath Maestro Case routing:
- AUTO_APPROVE
- HUMAN_REVIEW
- NEED_MORE_EVIDENCE
- REJECT
"""

from dataclasses import dataclass, field
from loguru import logger


@dataclass
class DecisionResult:
    decision: str
    reason: str
    requires_human_review: bool
    priority: str
    routing_stage: str
    actions: list[str] = field(default_factory=list)


class DecisionAgent:
    """
    Makes the final routing decision based on:
    - overall risk score
    - Technology DD signal
    - evidence sufficiency
    - overlap level
    - escalation flag from RiskAgent
    """

    def __init__(
        self,
        human_review_threshold: float = 7.0,
        reject_threshold: float = 9.0,
        low_evidence_threshold: float = 3.5,
    ):
        self.human_review_threshold = human_review_threshold
        self.reject_threshold = reject_threshold
        self.low_evidence_threshold = low_evidence_threshold
        logger.info("DecisionAgent initialized")

    def decide(
        self,
        risk_score: dict,
        tech_dd_result: dict,
    ) -> DecisionResult:
        overall_risk = float(risk_score.get("overall", 0.0) or 0.0)
        escalated = bool(risk_score.get("escalate", False))

        signal = tech_dd_result.get("overall_signal", "UNKNOWN")
        evidence_score = float(tech_dd_result.get("evidence_score", 0.0) or 0.0)
        overlap_score = float(tech_dd_result.get("overlap_score", 0.0) or 0.0)

        # 1. Hard rejection / severe risk
        if overall_risk >= self.reject_threshold:
            return DecisionResult(
                decision="REJECT",
                reason=(
                    f"Overall risk is critically high ({overall_risk}/10). "
                    "The case should not be auto-processed."
                ),
                requires_human_review=True,
                priority="CRITICAL",
                routing_stage="EXECUTIVE_REVIEW",
                actions=[
                    "Block auto-approval",
                    "Escalate to senior technical reviewer",
                    "Request legal/IP review",
                ],
            )

        # 2. Insufficient evidence
        if signal == "INSUFFICIENT_EVIDENCE" or evidence_score < self.low_evidence_threshold:
            return DecisionResult(
                decision="NEED_MORE_EVIDENCE",
                reason=(
                    f"Evidence score is insufficient ({evidence_score}/10). "
                    "More sources are required before a reliable DD decision."
                ),
                requires_human_review=True,
                priority="MEDIUM",
                routing_stage="EVIDENCE_COLLECTION",
                actions=[
                    "Request additional patent documents",
                    "Request technical reports or product documentation",
                    "Re-run evidence retrieval after new documents are added",
                ],
            )

        # 3. Human review for high overlap or high risk
        if (
            escalated
            or overall_risk >= self.human_review_threshold
            or signal == "HIGH_TECHNICAL_OVERLAP"
            or overlap_score >= 7.0
        ):
            return DecisionResult(
                decision="HUMAN_REVIEW",
                reason=(
                    f"Case requires human review. Risk={overall_risk}/10, "
                    f"signal={signal}, overlap={overlap_score}/10."
                ),
                requires_human_review=True,
                priority="HIGH",
                routing_stage="MAESTRO_HUMAN_TASK",
                actions=[
                    "Create Maestro human review task",
                    "Attach Technology DD findings",
                    "Attach evidence items and risk flags",
                ],
            )

        # 4. Moderate risk: auto-close but keep audit trail
        if signal == "MODERATE_TECHNICAL_RISK" or overall_risk >= 4.0:
            return DecisionResult(
                decision="AUTO_APPROVE_WITH_AUDIT",
                reason=(
                    f"Moderate technical risk detected but below escalation threshold. "
                    f"Risk={overall_risk}/10, signal={signal}."
                ),
                requires_human_review=False,
                priority="LOW",
                routing_stage="AUTO_CLOSE_WITH_AUDIT",
                actions=[
                    "Generate structured DD report",
                    "Store risk score and Tech DD findings",
                    "Keep audit trail for reviewer access",
                ],
            )

        # 5. Low risk
        return DecisionResult(
            decision="AUTO_APPROVE",
            reason=(
                f"Risk is within acceptable range ({overall_risk}/10), "
                f"with signal={signal}."
            ),
            requires_human_review=False,
            priority="LOW",
            routing_stage="AUTO_CLOSE",
            actions=[
                "Generate final report",
                "Close case automatically",
                "Store decision metadata",
            ],
        )


if __name__ == "__main__":
    agent = DecisionAgent()

    mock_risk = {
        "overall": 2.67,
        "escalate": False,
    }

    mock_tech_dd = {
        "overall_signal": "MODERATE_TECHNICAL_RISK",
        "evidence_score": 5.4,
        "overlap_score": 3.16,
    }

    result = agent.decide(mock_risk, mock_tech_dd)
    print(result)
