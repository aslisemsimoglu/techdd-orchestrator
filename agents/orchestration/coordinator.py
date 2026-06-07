# agents/orchestration/coordinator.py

"""
TechDD Coordinator - Orchestrates all agents end-to-end
This is the main pipeline that connects intake → NLP → risk scoring
"""

import json
import time
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

load_dotenv()


@dataclass
class DDCase:
    """Represents a single Due Diligence case"""
    case_id: str
    query: str
    created_at: str
    status: str = "OPEN"  # OPEN → PROCESSING → REVIEW → CLOSED
    documents: list[dict] = field(default_factory=list)
    nlp_results: list[dict] = field(default_factory=list)
    term_overlaps: dict = field(default_factory=dict)
    tech_dd_result: dict = field(default_factory=dict)
    risk_score: dict = field(default_factory=dict)
    escalated: bool = False
    decision_result: dict = field(default_factory=dict)
    final_report: dict = field(default_factory=dict)
    report_result: dict = field(default_factory=dict)


class TechDDCoordinator:
    """
    Main orchestrator — runs the full TechDD pipeline:
    1. Intake: fetch patents + papers
    2. NLP: extract terms, claims, entities
    3. Risk: score IP risk, maturity, consistency
    4. Decision: escalate or auto-close
    5. Report: generate final output
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
        self.arxiv_only = arxiv_only
        self.report_agent = ReportAgent()
        logger.info("TechDDCoordinator initialized")

    def _generate_case_id(self, query: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = query[:20].replace(" ", "_").lower()
        return f"DD_{slug}_{timestamp}"

    def _papers_to_dicts(self, papers: list[Paper]) -> list[dict]:
        return [p.__dict__ for p in papers]

    def _patents_to_dicts(self, patents: list[Patent]) -> list[dict]:
        return [p.__dict__ for p in patents]

    def run(self, query: str) -> DDCase:
        """
        Run the full due diligence pipeline for a given query.
        Returns a completed DDCase with risk assessment and report.
        """
        case_id = self._generate_case_id(query)
        case = DDCase(
            case_id=case_id,
            query=query,
            created_at=datetime.now().isoformat(),
            status="OPEN",
        )

        logger.info(f"{'='*60}")
        logger.info(f"NEW DD CASE: {case_id}")
        logger.info(f"Query: {query}")
        logger.info(f"{'='*60}")

        # ── STAGE 1: INTAKE ──────────────────────────────────────
        case.status = "PROCESSING"
        logger.info("STAGE 1: Document Intake")

        papers = self.literature_agent.search(query, arxiv_only=self.arxiv_only)
        paper_dicts = self._papers_to_dicts(papers)

        patents = self.patent_agent.search(query)
        patent_dicts = self._patents_to_dicts(patents)

        case.documents = paper_dicts + patent_dicts
        logger.success(f"Intake complete: {len(paper_dicts)} papers + {len(patent_dicts)} patents = {len(case.documents)} total documents")

        if not case.documents:
            logger.warning("No documents found, closing case")
            case.status = "CLOSED"
            case.final_report = {"error": "No documents found for query"}
            return case

        # ── STAGE 2: NLP ANALYSIS ────────────────────────────────
        logger.info("STAGE 2: NLP Analysis")
        nlp_results: list[NLPResult] = self.nlp_agent.process_batch(case.documents)
        case.nlp_results = [r.__dict__ for r in nlp_results]
        case.term_overlaps = self.nlp_agent.find_term_overlaps(nlp_results)

        logger.success(f"NLP complete: {len(case.term_overlaps)} overlapping terms found")

        # ── STAGE 3: TECHNOLOGY DUE DILIGENCE ANALYSIS ─────────────────────
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

        # ── STAGE 4: RISK SCORING ────────────────────────────────
        logger.info("STAGE 4: Risk Scoring")
        risk: RiskScore = self.risk_agent.score(
            documents=case.documents,
            tech_dd_result=case.tech_dd_result,
        )
        case.risk_score = risk.__dict__
        case.escalated = risk.escalate

        logger.success(f"Risk scoring complete: {risk.overall}/10")

        # ── STAGE 5: DECISION AGENT ─────────────────────────────
        logger.info("STAGE 5: Decision Agent")
        decision: DecisionResult = self.decision_agent.decide(
            risk_score=case.risk_score,
            tech_dd_result=case.tech_dd_result,
        )
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

        # ── STAGE 6: REPORT ──────────────────────────────────────
        logger.info("STAGE 6: Generating Report")
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
        report = report_result.report
        case.final_report = report

        logger.info(f"{'='*60}")
        logger.info(f"CASE COMPLETE: {case_id} → Status: {case.status}")
        logger.info(f"{'='*60}")

        return case

    def _generate_report(
        self,
        case: DDCase,
        risk: RiskScore,
        nlp_results: list[NLPResult],
    ) -> dict:
        """Generate structured final report"""

        # Top overlapping terms (potential IP conflict zones)
        top_overlaps = sorted(
            case.term_overlaps.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:5]

        # Collect all unique key terms
        all_terms = set()
        for r in nlp_results:
            all_terms.update(r.key_terms)

        # Source breakdown
        source_counts = {}
        for doc in case.documents:
            src = doc.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        report = {
            "case_id": case.case_id,
            "query": case.query,
            "generated_at": datetime.now().isoformat(),
            "status": case.status,
            "escalated": case.escalated,
            "summary": {
                "total_documents": len(case.documents),
                "source_breakdown": source_counts,
                "total_key_terms": len(all_terms),
                "overlapping_terms": len(case.term_overlaps),
            },
            "technology_due_diligence": {
                "novelty_score": case.tech_dd_result.get("novelty_score"),
                "overlap_score": case.tech_dd_result.get("overlap_score"),
                "maturity_score": case.tech_dd_result.get("maturity_score"),
                "evidence_score": case.tech_dd_result.get("evidence_score"),
                "overall_signal": case.tech_dd_result.get("overall_signal"),
                "findings": case.tech_dd_result.get("findings", []),
                "evidence_items": case.tech_dd_result.get("evidence_items", []),
            },
            "risk_assessment": {
                "overall_score": risk.overall,
                "ip_risk": risk.ip_risk,
                "tech_maturity": risk.tech_maturity,
                "competitive_exposure": risk.competitive_exposure,
                "consistency": risk.consistency,
                "flags": risk.flags,
            },
            "top_overlap_terms": [
                {"term": term, "appears_in": len(sources), "sources": sources}
                for term, sources in top_overlaps
            ],
            "recommendation": (
                "ESCALATE TO HUMAN REVIEW — Critical risk factors detected."
                if case.escalated
                else "APPROVED FOR AUTO-PROCESSING — Risk within acceptable threshold."
            ),
            "decision": {
                "decision": case.decision_result.get("decision"),
                "reason": case.decision_result.get("reason"),
                "requires_human_review": case.decision_result.get("requires_human_review"),
                "priority": case.decision_result.get("priority"),
                "routing_stage": case.decision_result.get("routing_stage"),
                "actions": case.decision_result.get("actions", []),
            },
        }

        return report

    def print_report(self, case: DDCase):
        """Pretty print the final report"""
        r = case.final_report
        if not r:
            print("No report generated.")
            return

        print(f"\n{'='*65}")
        print(f"  TECHDD ORCHESTRATOR — FINAL REPORT")
        print(f"{'='*65}")
        print(f"  Case ID  : {r['case_id']}")
        print(f"  Query    : {r['query']}")
        print(f"  Status   : {r['status']}")
        print(f"  Escalated: {'YES 🚨' if r['escalated'] else 'NO ✅'}")
        print(f"{'='*65}")

        s = r["summary"]
        print(f"\n  DOCUMENTS")
        print(f"  Total    : {s['total_documents']}")
        for src, count in s["source_breakdown"].items():
            print(f"  {src:<20}: {count}")

        tdd = r.get("technology_due_diligence", {})
        if tdd:
            print(f"\n  TECHNOLOGY DUE DILIGENCE")
            print(f"  Overall Signal   : {tdd.get('overall_signal')}")
            print(f"  Novelty Score    : {tdd.get('novelty_score')}/10")
            print(f"  Overlap Score    : {tdd.get('overlap_score')}/10")
            print(f"  Maturity Score   : {tdd.get('maturity_score')}/10")
            print(f"  Evidence Score   : {tdd.get('evidence_score')}/10")

            findings = tdd.get("findings", [])
            if findings:
                print(f"\n  TECH DD FINDINGS")
                for finding in findings:
                    print(f"  • {finding}")

            evidence_items = tdd.get("evidence_items", [])
            if evidence_items:
                print(f"\n  TECH DD EVIDENCE ITEMS")
                for item in evidence_items[:5]:
                    print(f"  • {item}")

        ra = r["risk_assessment"]
        print(f"\n  RISK SCORES (0-10, higher = more risk)")
        print(f"  Overall Score      : {ra['overall_score']}/10")
        print(f"  IP Risk            : {ra['ip_risk']}/10")
        print(f"  Tech Maturity Risk : {10 - ra['tech_maturity']:.2f}/10")
        print(f"  Competitive Exp.   : {ra['competitive_exposure']}/10")
        print(f"  Consistency Risk   : {10 - ra['consistency']:.2f}/10")

        print(f"\n  FLAGS")
        for flag in ra["flags"]:
            print(f"  • {flag}")

        decision = r.get("decision", {})
        if decision:
            print(f"\n  DECISION AGENT")
            print(f"  Decision      : {decision.get('decision')}")
            print(f"  Priority      : {decision.get('priority')}")
            print(f"  Routing Stage : {decision.get('routing_stage')}")
            print(f"  Human Review  : {decision.get('requires_human_review')}")
            print(f"  Reason        : {decision.get('reason')}")

            actions = decision.get("actions", [])
            if actions:
                print(f"\n  DECISION ACTIONS")
                for action in actions:
                    print(f"  • {action}")

        print(f"\n  TOP IP CONFLICT ZONES")
        for item in r["top_overlap_terms"]:
            print(f"  '{item['term']}' — appears in {item['appears_in']} sources")

        print(f"\n  RECOMMENDATION")
        print(f"  {r['recommendation']}")
        print(f"{'='*65}\n")


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

    case = coordinator.run(args.query)
    coordinator.print_report(case)

    if args.save:
        with open(args.save, "w") as f:
            json.dump(case.final_report, f, indent=2)
        print(f"Report saved to {args.save}")