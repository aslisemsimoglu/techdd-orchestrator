# TechDD Orchestrator

### UiPath Agentic Technical Due Diligence Platform for M&A Decisions

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![UiPath AgentHack 2026](https://img.shields.io/badge/UiPath-AgentHack%202026-red)](https://uipath-agenthack.devpost.com)
[![Track](https://img.shields.io/badge/Track-Maestro%20Case-blue)](https://uipath-agenthack.devpost.com)

---

## Overview

TechDD Orchestrator is an agentic technical due diligence prototype designed for M&A technology assessment.

The system collects patent and academic evidence, extracts technical signals, performs specialist technology due diligence analysis, computes risk scores, and decides whether a case can be auto-processed or escalated for human review.

The current implementation focuses on the Python coded-agent pipeline. The architecture is designed to evolve into a UiPath-native agentic automation solution using Maestro Case, Agent Builder, IXP, Human-in-the-Loop review, guardrails, evaluations, monitoring, and process operations.

---

## The Problem

Technical due diligence in M&A deals requires lawyers, engineers, and analysts to review patents, academic publications, technical reports, and product claims.

This process is often:

- Slow
- Expensive
- Inconsistent
- Difficult to audit
- Hard to scale across many target companies or technology domains

Critical deal decisions depend on whether the target technology is novel, mature, defensible, and free from major IP or technical conflict risks.

---

## The Solution

TechDD Orchestrator automates the first-pass technical due diligence workflow.

Given a company, technology, or domain query, the system:

1. Retrieves technical evidence from patents and academic literature.
2. Extracts key technical terms, claims, entities, summaries, and overlap zones.
3. Runs a specialist Technology Due Diligence Agent.
4. Computes a structured risk score.
5. Produces a final report with findings, evidence, risk scores, and escalation recommendation.

---

## Current Pipeline

```text
User Query
   ↓
Patent Agent
   ↓
Literature Agent
   ↓
NLP Agent
   ↓
Technology DD Agent
   ↓
Risk Agent
   ↓
Decision Logic
   ↓
Final Report
```

---

## Implemented Features

| Component | Status | Description |
|---|---:|---|
| Patent Agent | ✅ Implemented | Searches live patent sources and uses a demo-safe fallback when public APIs fail. |
| Literature Agent | ✅ Implemented | Retrieves academic papers from arXiv and Semantic Scholar-compatible sources. |
| NLP Agent | ✅ Implemented | Extracts technical terms, entities, claims, summaries, and overlap zones. |
| Technology DD Agent | ✅ Implemented | Produces novelty, overlap, maturity, evidence, and technical risk signals. |
| Risk Agent | ✅ Implemented | Combines rule-based risk signals with Technology DD outputs. |
| Coordinator | ✅ Implemented | Runs the end-to-end coded-agent pipeline and generates structured reports. |
| Demo-safe fallback | ✅ Implemented | Keeps the demo stable when public patent APIs are unavailable. |
| Structured report | ✅ Implemented | Prints document summary, Technology DD results, risk scores, flags, and recommendation. |

---

## UiPath-Oriented Target Architecture

The project is being evolved toward a UiPath-native agentic automation solution.

```text
UiPath Maestro Case
      ↓
Intake Agents
      ↓
IXP / Document Understanding
      ↓
Evidence + RAG Layer
      ↓
Specialist Technology DD Agent
      ↓
Risk Assessment Agent
      ↓
Decision Agent
      ├── Auto-close low-risk cases
      └── Escalate high-risk cases to Human Review
              ↓
        Maestro Human Task
              ↓
        Final DD Report + Audit Trail
```

---

## Planned UiPath Components

| UiPath Component | Planned Role |
|---|---|
| UiPath Maestro Case | Orchestrate each due diligence request as a case with stages, handoffs, and escalation points. |
| Agent Builder | Provide low-code intake, decision, and reporting agents. |
| Coded Agents | Host Python-based specialist DD, RAG, and risk agents. |
| IXP Generative Extraction | Extract structured data from complex PDFs, patents, technical reports, and diligence documents. |
| Validation Station | Enable human validation for uncertain or high-risk extracted evidence. |
| Human Task | Escalate high-risk or low-confidence cases to human reviewers. |
| Guardrails | Apply PII and prompt injection protection at tool level. |
| Evaluations | Validate faithfulness, trajectory, and report quality. |
| Process Monitoring | Track case status, escalation rates, duration, and risk distribution. |
| Process Operations | Inspect, retry, pause, resume, migrate, or troubleshoot process instances. |

---

## Technology Due Diligence Signals

The Technology DD Agent currently produces the following outputs:

| Signal | Meaning |
|---|---|
| `novelty_score` | Measures how differentiated or novel the collected evidence appears. |
| `overlap_score` | Measures technical similarity between patent and literature evidence. |
| `maturity_score` | Estimates whether the technology appears validated, benchmarked, or production-ready. |
| `evidence_score` | Measures source diversity and evidence sufficiency. |
| `overall_signal` | Produces the final technical DD interpretation. |
| `findings` | Lists human-readable technical findings. |
| `evidence_items` | Stores structured supporting evidence items. |

Example signal categories:

```text
MODERATE_TECHNICAL_RISK
HIGH_TECHNICAL_OVERLAP
LOW_MATURITY
INSUFFICIENT_EVIDENCE
PROMISING_DIFFERENTIATED_TECHNOLOGY
```

---

## Example Output

```text
TECHNOLOGY DUE DILIGENCE
Overall Signal   : MODERATE_TECHNICAL_RISK
Novelty Score    : 5.8/10
Overlap Score    : 3.16/10
Maturity Score   : 6.0/10
Evidence Score   : 5.4/10

TECH DD FINDINGS
• Evidence base includes 2 distinct source types.
• Novelty-related language was detected in the collected evidence.
• Moderate overlap detected between patent and literature evidence.

RISK SCORES
Overall Score      : 2.67/10
IP Risk            : 0.0/10
Competitive Exp.   : 0.42/10
Consistency Risk   : 9.67/10
```

---

## Data Sources

| Source | Data | Status |
|---|---|---|
| USPTO / patent-compatible sources | Patent metadata and claims | ✅ Implemented with fallback |
| arXiv | Academic preprints | ✅ Implemented |
| Semantic Scholar-compatible endpoint | Academic papers and metadata | ✅ Implemented / rate-limited |
| SEC EDGAR | Technical and financial filings | Planned |
| OpenAlex | Scholarly metadata | Planned |
| Uploaded technical reports | Internal DD documents | Planned through IXP / RAG |

---

## Project Structure

```text
techdd-orchestrator/
├── agents/
│   ├── intake/
│   │   ├── patent_agent.py        # Patent intake and demo-safe fallback
│   │   ├── literature_agent.py    # Academic literature intake
│   │   └── report_agent.py        # Planned external report intake
│   ├── extraction/
│   │   └── ixp_agent.py           # Planned IXP / document extraction layer
│   ├── analysis/
│   │   ├── nlp_agent.py           # Local technical term, claim, and overlap extraction
│   │   ├── ocr_agent.py           # Planned OCR / PDF extraction
│   │   ├── rag_agent.py           # Planned evidence retrieval and cross-source RAG
│   │   ├── tech_dd_agent.py       # Specialist Technology Due Diligence Agent
│   │   └── risk_agent.py          # Risk scoring and escalation logic
│   ├── decision/
│   │   └── decision_agent.py      # Planned explicit decision agent
│   ├── reporting/
│   │   └── report_agent.py        # Planned report generation agent
│   └── orchestration/
│       └── coordinator.py         # End-to-end coded-agent coordinator
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- Windows, macOS, or Linux
- Optional API keys for extended integrations
- UiPath Automation Cloud account for the planned Maestro and Agent Builder layers

### Installation

```bash
git clone https://github.com/aslisemsimoglu/techdd-orchestrator.git
cd techdd-orchestrator
pip install -r requirements.txt
```

---

## Running the Project

Run the full coded-agent pipeline:

```bash
python -m agents.orchestration.coordinator --query "transformer neural network patent" --max-papers 3 --max-patents 3
```

Run the patent intake agent:

```bash
python -m agents.intake.patent_agent --query "transformer neural network patent" --limit 3
```

Run the Technology DD agent test:

```bash
python -m agents.analysis.tech_dd_agent
```

---

## Current Limitations

This is an evolving hackathon prototype. The repository intentionally separates implemented features from planned UiPath-native capabilities.

Known limitations:

- `rag_agent.py` is reserved for the upcoming evidence retrieval and cross-source RAG layer.
- `ocr_agent.py` and `ixp_agent.py` are placeholders for document extraction integration.
- Live public APIs may fail due to network, DNS, or rate-limit issues; demo fallback is included for reliable demonstrations.
- Current NLP extraction uses lightweight local heuristics.
- UiPath Maestro Case artifacts are planned for the next orchestration phase.
- Human review, Validation Station, guardrails, evaluations, and process monitoring are planned extensions.

---

## Roadmap

### Phase 1 — Core Coded-Agent Pipeline

- Patent and literature intake
- NLP extraction
- Technology DD Agent
- Risk Agent V2
- Final structured report

### Phase 2 — Evidence and RAG Layer

- Semantic chunking
- Embedding-based retrieval
- Cross-source evidence matching
- RAG-supported citation layer
- Evidence confidence scoring

### Phase 3 — UiPath Agentic Automation Layer

- Maestro Case process
- Agent Builder components
- IXP Generative Extraction
- Human-in-the-loop review
- PII and prompt injection guardrails
- Evaluation sets and trace-based validation
- Process Monitoring and Process Operations

---

## Hackathon Context

Built for UiPath AgentHack 2026, Track 1: UiPath Maestro Case.

This project demonstrates how technical due diligence can evolve into a governed agentic workflow combining coded agents, evidence analysis, risk scoring, human review, and future UiPath orchestration.

---

## License

MIT License. See [LICENSE](LICENSE).
