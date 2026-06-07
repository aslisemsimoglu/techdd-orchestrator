from dataclasses import dataclass
from loguru import logger


@dataclass
class HumanReviewResult:
    review_required: bool
    review_type: str
    reason: str
    priority: str


class HumanReviewAgent:

    def __init__(self):
        logger.info("HumanReviewAgent initialized")

    def evaluate(self, risk_score, tech_dd_result):

        if risk_score >= 7:
            return HumanReviewResult(
                True,
                "IP_SPECIALIST",
                f"High overall risk score ({risk_score}/10)",
                "HIGH"
            )

        if (
            tech_dd_result.novelty_score >= 8
            and tech_dd_result.evidence_score <= 4
        ):
            return HumanReviewResult(
                True,
                "TECHNICAL_EXPERT",
                "High novelty claim with weak evidence",
                "HIGH"
            )

        if tech_dd_result.maturity_score <= 3:
            return HumanReviewResult(
                True,
                "DOMAIN_REVIEWER",
                "Technology maturity too low",
                "MEDIUM"
            )

        return HumanReviewResult(
            False,
            "NONE",
            "No human review required",
            "LOW"
        )