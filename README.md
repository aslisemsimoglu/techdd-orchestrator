# TechDD Orchestrator
### AI-Powered Multi-Source Technical Due Diligence for M&A Decisions

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UiPath AgentHack 2026](https://img.shields.io/badge/UiPath-AgentHack%202026-red)](https://uipath-agenthack.devpost.com)
[![Track](https://img.shields.io/badge/Track-Maestro%20Case-blue)](https://uipath-agenthack.devpost.com)

---

## The Problem

Technical due diligence in M&A deals today takes **weeks of manual expert work**: lawyers and engineers sifting through hundreds of patents, academic papers, and technical reports to assess IP risk, technology maturity, and competitive landscape. This process is slow, expensive, inconsistent — and the most critical decisions in a deal depend on it.

## The Solution

TechDD Orchestrator is an agentic AI system that automates this entire pipeline. Given a target company or technology domain, the system:

1. **Autonomously ingests** patents (USPTO/EPO), academic publications (arXiv/Semantic Scholar), and technical reports from open data sources
2. **Cross-analyzes** documents using NLP and RAG pipelines to detect IP conflicts, technology overlaps, and factual inconsistencies across sources
3. **Generates a structured risk score** across dimensions: IP risk, technology maturity, competitive exposure, and consistency
4. **Escalates only critical findings** to human reviewers via UiPath Maestro Case — keeping humans in control where it matters

**Result: weeks of manual review compressed into hours, with full audit trail.**

---

## Architecture

```
User Input: Company / Technology Domain
                    ↓
        ┌─────────────────────────┐
        │     MAESTRO CASE        │
        │  Case opened, staged    │
        └─────────────────────────┘
                    ↓
    ┌───────────────────────────────────┐
    │          INTAKE AGENTS            │
    │  Patent Agent   → USPTO / EPO     │
    │  Literature Agent → arXiv / S2    │
    │  Report Agent   → Web / EDGAR     │
    └───────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────┐
    │         ANALYSIS AGENTS           │
    │  OCR Agent      → PDF extraction  │
    │  NLP Agent      → claim parsing   │
    │  RAG Agent      → cross-reference │
    │  Risk Agent     → scoring engine  │
    └───────────────────────────────────┘
                    ↓
    ┌───────────────────────────────────┐
    │       ORCHESTRATION LAYER         │
    │  Conflict detected?               │
    │  Risk score above threshold?      │
    │  Low confidence finding?          │
    └───────────────────────────────────┘
          ↙                    ↘
  Auto report             HUMAN REVIEW
  generated           (Maestro Human Task)
                    ↓
       Final Risk Report + Audit Trail
```

---

## UiPath Components Used

| Component | Role |
|---|---|
| **UiPath Maestro Case** | Orchestrates each DD request as a case with stages and handoffs |
| **Agent Builder** | Low-code intake and reporting agents |
| **Coded Agents (Python SDK)** | NLP, RAG, and risk scoring logic |
| **API Workflows** | Connects to USPTO, EPO, arXiv, Semantic Scholar, SEC EDGAR |
| **Document Understanding (IDP)** | OCR and structured extraction from PDF patents and papers |
| **Human Task** | Escalation of high-risk findings to human reviewers |

## Agent Type

This solution uses **both Coded Agents and Low-code Agents**:
- Coded Agents (Python SDK + LangChain) handle NLP, RAG, and risk scoring
- Low-code Agents (Agent Builder) handle intake orchestration and report generation
- UiPath Maestro Case coordinates the full pipeline end-to-end

**AI-Assisted Development:** This project is built using **Claude Code** (UiPath for Coding Agents), with prompt logs and session exports documented in `/docs/coding-agent-log/`.

---

## Data Sources

All open and free:

| Source | Data | API |
|---|---|---|
| USPTO Patent Full-Text | US Patents | patents.google.com / USPTO API |
| EPO Open Patent Services | European Patents | ops.epo.org |
| arXiv | Academic preprints | arxiv.org/help/api |
| Semantic Scholar | Academic papers + citations | api.semanticscholar.org |
| SEC EDGAR | Financial/technical filings | efts.sec.gov |
| OpenAlex | Open scholarly metadata | api.openalex.org |

---

## Project Structure

```
techdd-orchestrator/
├── agents/
│   ├── intake/
│   │   ├── patent_agent.py        # USPTO/EPO fetcher
│   │   ├── literature_agent.py    # arXiv/Semantic Scholar fetcher
│   │   └── report_agent.py        # SEC/web report fetcher
│   ├── analysis/
│   │   ├── ocr_agent.py           # PDF extraction pipeline
│   │   ├── nlp_agent.py           # Claim parsing and NER
│   │   ├── rag_agent.py           # Cross-source retrieval and comparison
│   │   └── risk_agent.py          # Risk scoring engine
│   └── orchestration/
│       └── coordinator.py         # LangChain multi-agent coordinator
├── uipath/
│   ├── maestro_case/              # Maestro Case flow exports
│   └── api_workflows/             # API Workflow configurations
├── docs/
│   ├── architecture.md
│   └── coding-agent-log/          # Claude Code session logs
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- UiPath Automation Cloud account (UiPath Labs access)
- API keys: OpenAI or Anthropic (for LLM), others are free/keyless

### Installation

```bash
git clone https://github.com/aslisemsimoglu/techdd-orchestrator.git
cd techdd-orchestrator
pip install -r requirements.txt
cp .env.example .env
# Fill in your API keys in .env (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
```

### Running the Agents (standalone test)

```bash
# Test patent fetcher
python agents/intake/patent_agent.py --query "transformer neural network" --limit 10

# Test literature fetcher
python agents/intake/literature_agent.py --query "large language models" --limit 10

# Run full analysis pipeline
python agents/orchestration/coordinator.py --target "example_company"
```

### UiPath Cloud Setup

1. Log in to UiPath Automation Cloud (UiPath Labs)
2. Import Maestro Case flow from `/uipath/maestro_case/`
3. Configure API Workflow connections in `/uipath/api_workflows/`
4. Deploy Coded Agents via UiPath Python SDK
5. Trigger a case from Orchestrator or via API

Full setup guide: [docs/architecture.md](docs/architecture.md)

---

## Hackathon

**UiPath AgentHack 2026** — Track 1: UiPath Maestro Case

Built with UiPath Automation Cloud · LangChain · Python · Claude Code

---

## License

MIT License — see [LICENSE](LICENSE) for details.
