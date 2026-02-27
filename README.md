# GraphRAG-Senzing

**Agentic GraphRAG Pipeline** - strwythura 기반 문서 분석 및 질의응답 시스템

## Overview

strwythura 프레임워크를 활용한 자율형(Agentic) GraphRAG 파이프라인입니다.
로컬 문서(.docx, .txt, .md)를 입력받아 Knowledge Graph를 구축하고,
Ollama 기반 LLM으로 GraphRAG Q&A를 제공합니다.

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

```bash
# Process specific files
python run_pipeline.py report.docx notes.txt spec.md

# Skip NLP (faster, vector-only RAG)
python run_pipeline.py --skip-nlp data/documents/

# Single query
python run_pipeline.py data/documents/ --query "What is GraphRAG?"

# Query existing data
python run_pipeline.py --query-only

# Check system status
python run_pipeline.py --check
```

## Project Structure

```
GraphRAG-Senzing/
├── src/
│   ├── __init__.py          # Package init
│   ├── loaders.py           # Document loaders (docx, txt, md)
│   ├── embeddings.py        # BGE-M3 + Ollama embedding client
│   └── pipeline.py          # Agentic pipeline orchestrator
├── data/
│   ├── documents/           # Input documents
│   ├── domain.ttl           # Domain taxonomy
│   ├── lancedb/             # Vector store (generated)
│   └── output/              # Pipeline outputs (generated)
├── docs/                    # Analysis documentation
├── app.py                   # Streamlit web UI
├── run_pipeline.py          # CLI runner
├── config.toml              # Configuration
├── domain.json              # Domain metadata
└── setup.sh                 # Environment setup
```

## Prerequisites

- Python 3.11+
- Ollama running locally (`http://localhost:11434`)
- `ollama pull bona/bge-m3:latest`
- `ollama pull gemma3:27b`
- GPU with 16GB+ VRAM recommended (for gemma3:27b Q4)
