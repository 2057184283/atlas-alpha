# Atlas Alpha 🎯

> **Atlas does not answer questions. It discovers problems.**

An autonomous financial research system that continuously monitors market anomalies — price/fundamental divergences, flow regime shifts, and thesis conflicts — and initiates structured investigations before humans ask the first question.

This is not a chatbot. This is an anomaly detection and investigation engine for equity research.

---

## What Makes Atlas Different

| Traditional Financial AI | Atlas |
|---|---|
| "Analyze this stock for me" | "I found CATL has a -4.8% divergence vs sector. Here are 5 hypotheses." |
| LLM does everything | **LLM reasons; Python calculates; rules detect** |
| Black-box confidence | **Thesis tree with auditable evidence** |
| No time discipline | **Strict Point-in-Time isolation** |
| Single-turn Q&A | **Multi-step autonomous investigation** |

---

## 30-Second Demo

```bash
# 1. Clone
git clone https://github.com/yourname/atlas-alpha.git
cd atlas-alpha

# 2. Install dependencies
pip install -e .

# 3. Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# 4. Run the demo (uses real market data + simulated anomaly)
python demo.py
```

You will see:
1. **Divergence Engine** detects a statistical anomaly (Z-score based, zero LLM)
2. **Investigation Agent** generates 5 competing hypotheses
3. **Reviewer Agent** attacks the conclusions
4. **Thesis Engine** maps the impact to existing investment assumptions
5. **Human approval gate** pauses before modifying formal thesis

---

## Architecture

Atlas is deliberately **not** "frontend + agent + database". It is 6 layers:

```
┌─────────────────────────────────────────┐
│  Atlas Web (WIP)                        │
│  Radar | Investigation | Thesis | AgentOps│
├─────────────────────────────────────────┤
│  Agent Orchestration                    │
│  Orchestrator → Investigator → Reviewer │
├─────────────────────────────────────────┤
│  Intelligence Engines (Deterministic)   │
│  Market State | Divergence | Participant│
│  Thesis | Scenario | Portfolio          │
├─────────────────────────────────────────┤
│  Skill Library                          │
│  Technical | Flow | Event | Valuation   │
├─────────────────────────────────────────┤
│  Tool Layer (MCP-Ready)                 │
│  Market Data | Financial DB | Search    │
├─────────────────────────────────────────┤
│  Data Layer                             │
│  Price | Fundamentals | News | Flow     │
└─────────────────────────────────────────┘
```

**Key design principle: LLM does not do math.**

MACD, Z-scores, volatility, correlation, DCF — all computed by deterministic Python. LLM is responsible for: understanding context, proposing explanations, organizing evidence, and judging what deserves deeper investigation.

---

## Core Engines

### 1. Divergence Engine (`atlas/engines/divergence.py`)
Detects 6 types of market anomalies using **statistical models only**, no LLM hallucination:

- Stock vs Sector divergence
- Stock vs Market divergence
- Price vs Earnings expectation
- Price vs Fundamental news
- Price vs Flow behavior
- Current vs Historical regime

Each signal carries `severity`, `z_score`, and raw `metrics` — fully auditable.

### 2. Thesis Engine (`atlas/engines/thesis.py`)
Every stock is not a report. It is a **monitored hypothesis tree**.

```
宁德时代
├── H1: 欧洲销量保持两位数增长 (Confidence: 78)
├── H2: 海外毛利率保持 >20% (Confidence: 81)
├── H3: 储能成为第二增长曲线 (Confidence: 72)
└── H4: 市占率保持稳定 (Confidence: 84)
```

Each node has: supporting evidence, contradicting evidence, key variables, overturn conditions. The Agent knows exactly which judgment today's news should impact.

### 3. Participant Engine (Planned)
Infers flow regime from order-book features:
```json
{
  "allocation_flow": 0.46,
  "momentum_flow": 0.18,
  "event_driven": 0.17,
  "retail_sentiment": 0.11,
  "passive_flow": 0.08
}
```

### 4. Investigation Agent (`atlas/agents/investigator.py`)
Receives a divergence signal, proposes 5 competing hypotheses, and maps evidence to each. Uses structured output (JSON mode) for reliability.

### 5. Reviewer Agent (`atlas/agents/reviewer.py`)
Deliberately attacks the investigation report. Checks for:
- Numerical errors
- Evidence conflicts
- Temporal leakage (using future data)
- Confirmation bias

### 6. Orchestrator (`atlas/agents/orchestrator.py`)
Decides whether an anomaly deserves investigation, plans steps, and routes to human approval when thesis confidence changes.

---

## Point-in-Time Discipline

Every piece of evidence carries 4 timestamps:

```json
{
  "source": "Company Announcement",
  "published_at": "2025-01-15T09:00:00Z",
  "available_at": "2025-01-15T09:30:00Z",
  "retrieved_at": "2025-01-15T10:00:00Z",
  "content_hash": "sha256:..."
}
```

Backtesting strictly enforces: `evidence.available_at <= simulation_date`. This prevents the most common failure mode in financial AI: accidentally training on future information.

---

## Human-in-the-Loop

Two gates require human approval:

1. **Modifying formal earnings assumptions** (e.g., 2027E Europe growth 15% → 8%)
2. **Changing Investment Thesis** (e.g., "Bullish" → "Neutral")

AI proposes. Human decides. This is B-grade product logic, not toy logic.

---

## Project Status

- [x] Divergence Engine (6 anomaly types, statistical)
- [x] Thesis Tree with confidence tracking
- [x] Investigation Agent (5-hypothesis generation)
- [x] Reviewer Agent (adversarial validation)
- [x] Point-in-Time evidence layer
- [x] Sample data + demo script
- [ ] Web UI (Market Radar + Investigation Board)
- [ ] Live market data (MCP protocol)
- [ ] Portfolio Engine (Thesis Exposure analysis)
- [ ] Scenario Lab (sensitivity modeling)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Engines | Python, pandas, numpy, scipy |
| Agents | OpenAI API (JSON mode, structured output) |
| Models | Pydantic (strict schema validation) |
| Data | yfinance (demo), MCP-ready architecture |
| Tests | pytest |

**Intentionally lightweight.** No Kafka, no Spark, no microservices. A research demo should be clone-and-run in 60 seconds.

---

## File Structure

```
atlas-alpha/
├── README.md
├── pyproject.toml
├── demo.py                    # One-command demo
├── atlas/
│   ├── __init__.py
│   ├── models.py              # All Pydantic schemas
│   ├── engines/
│   │   ├── divergence.py      # Statistical anomaly detection
│   │   └── thesis.py          # Hypothesis tree management
│   ├── agents/
│   │   ├── orchestrator.py    # Task routing
│   │   ├── investigator.py    # Hypothesis generation
│   │   └── reviewer.py        # Adversarial review
│   └── tools/
│       ├── market_data.py     # Data fetching
│       └── evidence_store.py  # PIT evidence storage
├── tests/
│   ├── test_divergence.py
│   ├── test_thesis.py
│   └── test_pit.py            # Point-in-time discipline
├── data/
│   └── thesis_catl.json       # Sample thesis tree
└── notebooks/
    └── 01_divergence_demo.ipynb
```

---

## License

MIT

---

> **Atlas V1 Core Thesis:** The system does not replace the researcher. It continuously observes the relationship between fundamentals, expectations, prices, and flows — actively discovers where things start to go wrong, autonomously generates research questions, validates explanations, and propagates changes to investment views and portfolio risk.
