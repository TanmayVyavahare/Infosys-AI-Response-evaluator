# Aegis — AI Response Quality Evaluator

A production-grade system for evaluating AI-generated responses using Retrieval-Augmented Generation (RAG), semantic similarity, LLM-as-a-Judge, and intelligent local fallback algorithms.

## Architecture

```
User → Evaluation Form → FastAPI → Evaluation Coordinator
                                          │
                                   asyncio.gather()
                                   ┌──────┼──────┐
                                   │      │      │
                              Relevance  Accuracy  Groundedness
                              Agent      Agent     Agent
                                   │      │      │
                                   └──────┼──────┘
                                          │
                                    Verdict Engine → Dashboard
```

### Evaluation Agents

| Agent | Purpose | LLM Prompt | Fallback |
|-------|---------|------------|----------|
| **Relevance** | Does the response answer the question? | Answer relevancy | Cosine similarity + NER overlap + topic similarity |
| **Accuracy** | Are the facts correct? | Claim verification | Per-claim semantic similarity + NER + number matching |
| **Groundedness** | Are claims supported by evidence? | Faithfulness check | Per-claim context matching + NER cross-reference |
| **Completeness** | Are all requirements covered? | Coverage assessment | Requirement extraction + semantic presence checking |

### Key Design Decisions

- **Independent evaluators**: Each agent receives the same `EvaluationPackage` and operates in isolation
- **LLM + Fallback**: Every agent works without an LLM using sentence embeddings (all-MiniLM-L6-v2)
- **Concurrent execution**: All agents run via `asyncio.gather()` for parallel evaluation
- **Abstract LLM provider**: Supports OpenAI, Gemini, Ollama through one interface
- **FAISS caching**: Vector indices cached to disk with hash-based invalidation

## Quick Start

### Backend

```bash
cd aegis/backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure (optional — works without LLM in fallback mode)
copy .env.example .env
# Edit .env with your API key if you want LLM-based evaluation

# Run
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd aegis/frontend
npm install
npm run dev
```

Open http://localhost:5173

### Run Tests

```bash
cd aegis/backend
python -m pytest tests/test_evaluators.py -v
```

## API

### POST /api/evaluate

```json
{
  "question": "Who discovered gravity?",
  "ai_response": "Isaac Newton discovered gravity...",
  "reference_answer": "Sir Isaac Newton formulated...",
  "source_document": "Optional source text for RAG..."
}
```

**Response**: Metric scores, evidence, claims, verdict, processing time.

### GET /api/health

Returns system status and configuration.

## Project Structure

```
aegis/
├── backend/
│   ├── app/
│   │   ├── config/settings.py        # All thresholds and weights
│   │   ├── core/exceptions.py        # Custom exception hierarchy
│   │   ├── api/routes/               # FastAPI endpoints
│   │   ├── schemas/                   # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── llm_provider.py       # Abstract LLM (OpenAI/Gemini/Ollama)
│   │   │   └── evaluation_coordinator.py
│   │   ├── evaluation/
│   │   │   ├── base.py               # BaseEvaluator ABC
│   │   │   ├── relevance.py          # Relevance Agent
│   │   │   ├── accuracy.py           # Accuracy Agent
│   │   │   ├── groundedness.py       # Hallucination Agent
│   │   │   ├── completeness.py       # Completeness Agent
│   │   │   ├── prompts/              # LLM prompt templates
│   │   │   └── fallbacks/            # Local NLP utilities
│   │   ├── retrieval/
│   │   │   ├── document_loader.py    # PDF/TXT/DOCX
│   │   │   ├── chunker.py           # Recursive chunking
│   │   │   ├── embedder.py          # sentence-transformers
│   │   │   └── retriever.py         # FAISS search + caching
│   │   └── utils/
│   │       ├── json_validator.py     # LLM JSON parsing
│   │       └── text_processing.py    # Shared NLP
│   └── tests/
│       └── test_evaluators.py        # Agent validation
└── frontend/
    └── src/
        ├── components/               # ScoreGauge, ScoreCard, Form
        ├── hooks/useEvaluation.ts     # State management
        ├── services/api.ts            # API client
        └── types/evaluation.ts        # TypeScript types
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11+ |
| Frontend | React, TypeScript, Vite, TailwindCSS v4 |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Search | FAISS |
| LLM | OpenAI / Gemini / Ollama (abstract provider) |

## Configuration

All thresholds and weights are in `backend/app/config/settings.py`:

```python
weight_relevance = 0.25
weight_accuracy = 0.30
weight_groundedness = 0.25
weight_completeness = 0.20

similarity_threshold_high = 0.8
similarity_threshold_medium = 0.5
critical_hallucination_threshold = 0.3
```

Override any setting via environment variables or `.env` file.
