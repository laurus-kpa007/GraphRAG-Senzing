# GraphRAG-Senzing

**Agentic GraphRAG Pipeline** - Multi-Agent RAG with Planning, Reflection & Validation

## Overview

2025/2026 최신 연구를 기반으로 한 **Agentic GraphRAG** 파이프라인입니다.

### 🤖 Agentic RAG Features

**Multi-Agent Workflow** (LangGraph-style):
- **Planning Agent**: Query decomposition & strategy selection
- **Grader Agent**: Document relevance assessment (CRAG pattern)
- **Reasoning Agent**: Multi-hop reasoning with interleaved retrieval
- **Validation Agent**: Fact-checking & consistency verification (Self-RAG)
- **Reflection Agent**: Retry on validation failure (up to 3 attempts)

**Key Capabilities**:
- 🧠 **Complex Reasoning**: Multi-hop question answering with reasoning chains
- ✅ **Self-Validation**: Automatic fact-checking against source documents
- 🔄 **Self-Reflection**: Query rephrasing & strategy adjustment on failure
- 📊 **Audit Trail**: Full execution history with citations & confidence scores
- 🎯 **Hybrid Search**: Vector (BGE-M3) + Keyword + Graph expansion

### 📚 Research Foundation

Based on 2025/2026 state-of-the-art research:
- **Corrective RAG (CRAG)**: Document grading & web fallback
- **Self-RAG**: Reflection & validation during generation
- **Interleaved R&R**: Multi-hop reasoning with iterative retrieval
- **LangGraph Patterns**: State machine orchestration

See [docs/agentic_graphrag_design.md](docs/agentic_graphrag_design.md) for detailed architecture.

## Stack

| Component | Technology |
|-----------|-----------|
| **LLM** | Ollama `gemma3:27b` |
| **Embeddings** | Ollama `bona/bge-m3:latest` (1024-dim) |
| **Vector Store** | LanceDB |
| **NLP** | spaCy + GLiNER |
| **KG Framework** | strwythura (NetworkX, RDFlib) |
| **UI** | Streamlit |

## Quick Start

```bash
# 1. Setup
bash setup.sh

# 2. Place documents
cp your_docs/*.docx data/documents/
cp your_docs/*.txt data/documents/
cp your_docs/*.md data/documents/

# 3. Run pipeline + interactive Q&A
python run_pipeline.py data/documents/

# 4. Or use Streamlit UI
streamlit run app.py
```

## CLI Usage

### Standard Mode (Hybrid Search)
```bash
# Process documents + interactive Q&A
python run_pipeline.py data/documents/

# Single query
python run_pipeline.py data/documents/ --query "재택근무 승인자는?"

# Query existing data
python run_pipeline.py --query-only
```

### 🤖 Agentic Mode (Multi-Agent RAG)
```bash
# Test agentic vs standard comparison
python test_agentic.py

# Interactive agentic session
python test_agentic.py interactive

# Or use pipeline directly
python -c "from src.pipeline import AgenticPipeline; p = AgenticPipeline(); p.initialize(); p.load_chunks_from_lancedb(); p.load_entities(); p.interactive(agentic=True)"
```

### Example: Agentic Mode Output
```
Q: 누나 결혼하면 경조금은 얼마인가요?

[PLAN] 1 sub-queries, strategy=hybrid
[RETRIEVE] 15 docs, strategy=hybrid
[GRADE] 8/15 docs passed threshold 0.7
[REASON] 2 hops, answer generated
[VALIDATE] ✓ PASS (confidence=0.92)
[ANSWER] 2 citations added

A: 형제자매(누나)가 결혼하면 경조금은 50만원입니다.
   Validation: ✓ (confidence: 0.92)
   Reasoning: 2 steps
   Citations: 2
   Retries: 0
   Retrieved: 15 docs, Relevant: 8 docs
```

### Other Commands
```bash
# Check system status
python run_pipeline.py --check

# Skip NLP (faster, vector-only)
python run_pipeline.py --skip-nlp data/documents/

# Graph visualization
python tools/visualize_graph.py --graph erkg

# Search debugging
python tools/search_debug.py "백신휴가"
```

## Project Structure

```
GraphRAG-Senzing/
├── src/
│   ├── agentic/             # 🤖 Agentic RAG agents
│   │   ├── __init__.py
│   │   ├── state.py         # State machine definitions
│   │   ├── base_agent.py    # Base agent class
│   │   ├── agents.py        # Planning, Grader, Reasoning, Validation, Reflection
│   │   └── orchestrator.py  # Multi-agent orchestrator
│   ├── __init__.py
│   ├── loaders.py           # Document loaders (docx, txt, md)
│   ├── embeddings.py        # BGE-M3 + Ollama LLM client
│   └── pipeline.py          # Pipeline orchestrator (standard + agentic)
├── tools/
│   ├── visualize_graph.py   # Graph visualization
│   ├── search_debug.py      # Search debugging
│   └── README.md
├── data/
│   ├── documents/           # Input documents
│   ├── domain.ttl           # Domain taxonomy
│   ├── lancedb/             # Vector store (generated)
│   └── output/              # Pipeline outputs (generated)
├── docs/
│   └── agentic_graphrag_design.md  # Architecture documentation
├── app.py                   # Streamlit web UI
├── run_pipeline.py          # CLI runner
├── test_agentic.py          # Agentic mode testing
├── config.toml              # Configuration
├── requirements.txt         # Python dependencies
└── domain.json              # Domain metadata
```

## Prerequisites

- Python 3.11+
- Ollama running locally (`http://localhost:11434`)
- `ollama pull bona/bge-m3:latest`
- `ollama pull gemma3:27b`
- GPU with 16GB+ VRAM recommended (for gemma3:27b Q4)
