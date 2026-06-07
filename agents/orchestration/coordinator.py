# agents/orchestration/coordinator.py

"""
TechDD Coordinator - Orchestrates all agents end-to-end.

Pipeline:
1. Intake: fetch patents and papers
2. NLP: extract terms, claims, entities, and overlaps
3. Technology DD: produce specialist due diligence signals
4. Risk: compute structured risk score
5. Human Review Evaluation: prepare human-review routing metadata
6. Decision: route case to auto-close or review
7. Report: generate final structured DD report
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

from agents.intake.literature_agent import LiteratureAgent, Paper
from agents.intake.patent_agent import PatentAgent, Patent
from agents.analysis.nlp_agent import NLPAgent, NLPResult
from agents.analysis.risk_agent import RiskAgent, RiskScore
from agents.analysis.tech_dd_agent import TechDDAgent, TechnologyDDResult
from agents.decision.decision_agent import DecisionAgent, DecisionResult
from agents.reporting.report_agent import ReportAgent, ReportResult

try:
    from agents.review.human_review_agent import HumanReviewAgent
except ModuleNotFoundError:
    HumanReviewAgent = None


load_dotenv()


@dataclass
class DDCase:
    """Represents a single technical due diligence case."""
    case_id: str
    query: str
    created_at: str
    status: str = "OPEN"
    documents: list[dict] = field(default_factory=list)
    nlp_results: list[dict] = field(default_factory=list)
    term_overlaps: dict = field(default_factory=dict)
    tech_dd_result: dict = field(default_factory=dict)
    risk_score: dict = field(default_factory=dict)
    review_result: dict = field(default_factory=dict)
    decision_result: dict = field(default_factory=dict)
    report_result: dict = field(default_factory=dict)
    final_report: dict = field(default_factory=dict)
    escalated: bool = False


class TechDDCoordinator:
    """
    Main orchestrator for the TechDD pipeline.

    This coordinator is intentionally coded-agent friendly and maps naturally
    to the planned UiPath Maestro Case flow.
    """

    def __init__(
        self,
        max_patents: int = 10,
        max_papers: int = 10,
        escalation_threshold: float = 7.0,
        arxiv_only: bool = True,
    ):
        self.literature_agent = LiteratureAgent(max_results=max_papers)
        self.patent_agent = PatentAgent(max_results=max_patents)
        self.nlp_agent = NLPAgent()
        self.tech_dd_agent = TechDDAgent()
        self.risk_agent = RiskAgent(escalation_threshold=escalation_threshold)
        self.decision_agent = DecisionAgent()
        self.report_agent = ReportAgent()

        self.review_agent = HumanReviewAgent() if HumanReviewAgent else None
        self.arxiv_only = arxiv_only

        logger.info("TechDDCoordinator initialized")

    def _generate_case_id(self, query: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = query[:20].replace(" ", "_").lower()
        return f"DD_{slug}_{timestamp}"

    @staticmethod
    def _papers_to_dicts(papers: list[Paper]) -> list[dict]:
        return [p.__dict__ for p in papers]

    @staticmethod
    def _patents_to_dicts(patents: list[Patent]) -> list[dict]:
        return [p.__dict__ for p in patents]

    def _evaluate_human_review(
        self,
        risk: RiskScore,
        tech_dd: TechnologyDDResult,
    ) -> dict:
        """
        Evaluate whether the case should be prepared for human review.

        If agents/review/human_review_agent.py exists, this uses it.
        If not, it falls back to deterministic routing logic.
        """

        if self.review_agent:
            try:
                review = self.review_agent.evaluate(
                    risk_score=risk.__dict__,
                    tech_dd_result=tech_dd.__dict__,
                )
                return review.__dict__ if hasattr(review, "__dict__") else dict(review)
            except TypeError:
                review = self.review_agent.evaluate(risk.overall, tech_dd)
                return review.__dict__ if hasattr(review, "__dict__") else dict(review)
            except Exception as exc:
                logger.warning(f"HumanReviewAgent failed, using fallback logic: {exc}")

        review_required = (
            risk.overall >= 7.0
            or tech_dd.overlap_score >= 7.0
            or tech_dd.overall_signal in {"HIGH_TECHNICAL_OVERLAP", "INSUFFICIENT_EVIDENCE"}
            or (tech_dd.novelty_score >= 8.0 and tech_dd.evidence_score <= 4.0)
        )

        if review_required:
            return {
                "review_required": True,
                "review_type": "TECHNICAL_DD_REVIEW",
                "reason": (
                    f"Human review recommended. Risk={risk.overall}/10, "
                    f"signal={tech_dd.overall_signal}, overlap={tech_dd.overlap_score}/10, "
                    f"evidence={tech_dd.evidence_score}/10."
                ),
                "priority": "HIGH" if risk.overall >= 7.0 or tech_dd.overlap_score >= 7.0 else "MEDIUM",
                "routing_stage": "MAESTRO_HUMAN_TASK",
            }

        return {
            "review_required": False,
            "review_type": "NONE",
            "reason": "No human review required based on current risk and evidence signals.",
            "priority": "LOW",
            "routing_stage": "AUTO_ROUTE",
        }

    def run(self, query: str) -> DDCase:
        """
        Run the full due diligence pipeline for a given query.
        Returns a completed DDCase.
        """

        case_id = self._generate_case_id(query)
        case = DDCase(
            case_id=case_id,
            query=query,
            created_at=datetime.now().isoformat(),
            status="OPEN",
        )

        logger.info("=" * 60)
        logger.info(f"NEW DD CASE: {case_id}")
        logger.info(f"Query: {query}")
        logger.info("=" * 60)

        # ── STAGE 1: INTAKE ─────────────────────────────────────
        case.status = "PROCESSING"
        logger.info("STAGE 1: Document Intake")

        papers = self.literature_agent.search(query, arxiv_only=self.arxiv_only)
        paper_dicts = self._papers_to_dicts(papers)

        patents = self.patent_agent.search(query)
        patent_dicts = self._patents_to_dicts(patents)

        case.documents = paper_dicts + patent_dicts

        logger.success(
            f"Intake complete: {len(paper_dicts)} papers + "
            f"{len(patent_dicts)} patents = {len(case.documents)} total documents"
        )

        if not case.documents:
            logger.warning("No documents found, closing case")
            case.status = "CLOSED"
            case.final_report = {"error": "No documents found for query"}
            return case

        # ── STAGE 2: NLP ANALYSIS ───────────────────────────────
        logger.info("STAGE 2: NLP Analysis")

        nlp_results: list[NLPResult] = self.nlp_agent.process_batch(case.documents)
        case.nlp_results = [r.__dict__ for r in nlp_results]
        case.term_overlaps = self.nlp_agent.find_term_overlaps(nlp_results)

        logger.success(f"NLP complete: {len(case.term_overlaps)} overlapping terms found")

        # ── STAGE 3: TECHNOLOGY DUE DILIGENCE ───────────────────
        logger.info("STAGE 3: Technology Due Diligence Analysis")

        tech_dd: TechnologyDDResult = self.tech_dd_agent.analyze(
            documents=case.documents,
            nlp_results=case.nlp_results,
        )
        case.tech_dd_result = tech_dd.__dict__

        logger.success(
            f"Tech DD complete: signal={tech_dd.overall_signal}, "
            f"overlap={tech_dd.overlap_score}/10, "
            f"maturity={tech_dd.maturity_score}/10"
        )

        # ── STAGE 4: RISK SCORING ───────────────────────────────
        logger.info("STAGE 4: Risk Scoring")

        risk: RiskScore = self.risk_agent.score(
            documents=case.documents,
            tech_dd_result=case.tech_dd_result,
        )
        case.risk_score = risk.__dict__
        case.escalated = risk.escalate

        logger.success(f"Risk scoring complete: {risk.overall}/10")

        # ── STAGE 5: HUMAN REVIEW EVALUATION ────────────────────
        logger.info("STAGE 5: Human Review Evaluation")

        case.review_result = self._evaluate_human_review(
            risk=risk,
            tech_dd=tech_dd,
        )

        logger.info(
            f"Human review evaluation complete: "
            f"required={case.review_result.get('review_required')}, "
            f"type={case.review_result.get('review_type')}, "
            f"priority={case.review_result.get('priority')}"
        )

        # ── STAGE 6: DECISION AGENT ─────────────────────────────
        logger.info("STAGE 6: Decision Agent")

        decision: DecisionResult = self.decision_agent.decide(
            risk_score=case.risk_score,
            tech_dd_result=case.tech_dd_result,
        )

        if case.review_result.get("review_required"):
            decision.decision = "HUMAN_REVIEW"
            decision.requires_human_review = True
            decision.priority = case.review_result.get("priority", decision.priority)
            decision.routing_stage = "MAESTRO_HUMAN_TASK"
            decision.reason = case.review_result.get("reason", decision.reason)
            decision.actions = [
                "Create Maestro human review task",
                "Attach Technology DD findings",
                "Attach risk flags and evidence summary",
                "Pause automatic closure until reviewer decision",
            ]

        case.decision_result = decision.__dict__
        case.escalated = decision.requires_human_review

        if decision.requires_human_review:
            case.status = "REVIEW"
            logger.warning(
                f"Decision Agent routed case to human review: "
                f"{decision.decision} | Priority={decision.priority}"
            )
        else:
            case.status = "CLOSED"
            logger.success(
                f"Decision Agent auto-routed case: "
                f"{decision.decision} | Stage={decision.routing_stage}"
            )

        # ── STAGE 7: REPORT ─────────────────────────────────────
        logger.info("STAGE 7: Generating Report")

        report_result: ReportResult = self.report_agent.generate(
            case_id=case.case_id,
            query=case.query,
            status=case.status,
            documents=case.documents,
            term_overlaps=case.term_overlaps,
            tech_dd_result=case.tech_dd_result,
            risk_score=case.risk_score,
            decision_result=case.decision_result,
        )

        case.report_result = report_result.__dict__
        case.final_report = report_result.report

        logger.info("=" * 60)
        logger.info(f"CASE COMPLETE: {case.case_id} → Status: {case.status}")
        logger.info("=" * 60)

        return case

    def print_report(self, case: DDCase):
        """Pretty print the final report."""

        r = case.final_report

        if not r:
            print("No report generated.")
            return

        print(f"\n{'=' * 65}")
        print("  TECHDD ORCHESTRATOR — FINAL REPORT")
        print(f"{'=' * 65}")
        print(f"  Case ID  : {r['case_id']}")
        print(f"  Query    : {r['query']}")
        print(f"  Status   : {r['status']}")
        print(f"  Escalated: {'YES 🚨' if r['escalated'] else 'NO ✅'}")
        print(f"{'=' * 65}")

        summary = r["summary"]
        print("\n  DOCUMENTS")
        print(f"  Total    : {summary['total_documents']}")

        for src, count in summary["source_breakdown"].items():
            print(f"  {src:<20}: {count}")

        tdd = r.get("technology_due_diligence", {})
        if tdd:
            print("\n  TECHNOLOGY DUE DILIGENCE")
            print(f"  Overall Signal   : {tdd.get('overall_signal')}")
            print(f"  Novelty Score    : {tdd.get('novelty_score')}/10")
            print(f"  Overlap Score    : {tdd.get('overlap_score')}/10")
            print(f"  Maturity Score   : {tdd.get('maturity_score')}/10")
            print(f"  Evidence Score   : {tdd.get('evidence_score')}/10")

            findings = tdd.get("findings", [])
            if findings:
                print("\n  TECH DD FINDINGS")
                for finding in findings:
                    print(f"  • {finding}")

            evidence_items = tdd.get("evidence_items", [])
            if evidence_items:
                print("\n  TECH DD EVIDENCE ITEMS")
                for item in evidence_items[:5]:
                    print(f"  • {item}")

        risk_assessment = r["risk_assessment"]
        print("\n  RISK SCORES (0-10, higher = more risk)")
        print(f"  Overall Score      : {risk_assessment['overall_score']}/10")
        print(f"  IP Risk            : {risk_assessment['ip_risk']}/10")
        print(f"  Tech Maturity Risk : {10 - risk_assessment['tech_maturity']:.2f}/10")
        print(f"  Competitive Exp.   : {risk_assessment['competitive_exposure']}/10")
        print(f"  Consistency Risk   : {10 - risk_assessment['consistency']:.2f}/10")

        print("\n  FLAGS")
        flags = risk_assessment.get("flags", [])
        if flags:
            for flag in flags:
                print(f"  • {flag}")
        else:
            print("  • No risk flags generated.")

        review = case.review_result
        if review:
            print("\n  HUMAN REVIEW EVALUATION")
            print(f"  Required      : {review.get('review_required')}")
            print(f"  Review Type   : {review.get('review_type')}")
            print(f"  Priority      : {review.get('priority')}")
            print(f"  Routing Stage : {review.get('routing_stage')}")
            print(f"  Reason        : {review.get('reason')}")

        decision = r.get("decision", {})
        if decision:
            print("\n  DECISION AGENT")
            print(f"  Decision      : {decision.get('decision')}")
            print(f"  Priority      : {decision.get('priority')}")
            print(f"  Routing Stage : {decision.get('routing_stage')}")
            print(f"  Human Review  : {decision.get('requires_human_review')}")
            print(f"  Reason        : {decision.get('reason')}")

            actions = decision.get("actions", [])
            if actions:
                print("\n  DECISION ACTIONS")
                for action in actions:
                    print(f"  • {action}")

        print("\n  TOP IP CONFLICT ZONES")
        overlap_terms = r.get("top_overlap_terms", [])

        if overlap_terms:
            for item in overlap_terms:
                print(f"  '{item['term']}' — appears in {item['appears_in']} sources")
        else:
            print("  No overlapping terms detected.")

        print("\n  RECOMMENDATION")
        print(f"  {r['recommendation']}")
        print(f"{'=' * 65}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--query", type=str, default="transformer neural network patent")
    parser.add_argument("--max-papers", type=int, default=8)
    parser.add_argument("--max-patents", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=7.0)
    parser.add_argument("--save", type=str, default=None, help="Save report to JSON file")

    args = parser.parse_args()

    coordinator = TechDDCoordinator(
        max_patents=args.max_patents,
        max_papers=args.max_papers,
        escalation_threshold=args.threshold,
        arxiv_only=True,
    )

    completed_case = coordinator.run(args.query)
    coordinator.print_report(completed_case)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(completed_case.final_report, f, indent=2, ensure_ascii=False)

        print(f"Report saved to {args.save}")
