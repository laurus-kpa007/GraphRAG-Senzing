# GraphRAG-Senzing 프로젝트 구조 및 흐름도

> **프로젝트명:** GraphRAG-Senzing (Agentic GraphRAG Pipeline)
> **기반 프레임워크:** strwythura v2.0.3 (DerwenAI) - 선택적 통합
> **최종 수정일:** 2026-03-04

---

## 1. 프로젝트 개요

GraphRAG-Senzing은 **로컬 문서(.docx, .txt, .md)를 대상으로 벡터 검색 + 키워드 검색 + 그래프 기반 검색을 결합한 하이브리드 GraphRAG Q&A 시스템**입니다.
strwythura 프레임워크를 선택적으로 활용하되, strwythura 없이도 독립적으로 동작하는 커스텀 파이프라인을 제공합니다.

### 핵심 기술 스택

| 분류 | 기술 | 비고 |
|------|------|------|
| LLM | Ollama (gemma3:4b/27b) | `/api/chat` 엔드포인트 사용 |
| Embeddings | BGE-M3 via Ollama | 1024차원, 다국어 지원 |
| Vector Store | LanceDB | 파일 기반, 서버 불필요 |
| 문서 로딩 | python-docx, chardet | .docx, .txt, .md 지원 |
| NLP/NER | spaCy (ko_core_news_lg) | 한국어 우선, 영어 fallback |
| Graph | NetworkX (인메모리) | strwythura 연동 시 ERKG 활용 |
| Web UI | Streamlit | 문서 업로드 + Q&A 채팅 |
| Profiling | pyinstrument | 선택적 성능 프로파일링 |
| HTTP Client | httpx | Ollama API 통신 |

---

## 2. 디렉토리 및 파일 구조

```mermaid
graph TD
    ROOT["GraphRAG-Senzing/ (root)"]

    ROOT --> SRC["src/ (핵심 소스)"]
    ROOT --> TESTS["tests/ (테스트)"]
    ROOT --> DATA["data/ (데이터)"]
    ROOT --> DOCS["docs/ (문서)"]
    ROOT --> TOOLS["tools/ (유틸리티)"]
    ROOT --> ENTRY["진입점 & 설정"]

    SRC --> S1["pipeline.py<br/>AgenticPipeline 오케스트레이터"]
    SRC --> S2["loaders.py<br/>DocumentLoader (docx/txt/md)"]
    SRC --> S3["embeddings.py<br/>OllamaEmbedding + OllamaLLM"]

    TESTS --> T1["test_integration.py<br/>통합 테스트 (25개)"]

    DATA --> D1["documents/<br/>입력 문서"]
    DATA --> D2["lancedb/<br/>벡터 저장소 (자동생성)"]
    DATA --> D3["output/<br/>엔티티/그래프 (자동생성)"]
    DATA --> D4["cache/<br/>스크래퍼 캐시"]
    DATA --> D5["uploads/<br/>Streamlit 업로드"]

    ENTRY --> E1["run_pipeline.py<br/>CLI 실행기"]
    ENTRY --> E2["app.py<br/>Streamlit Web UI"]
    ENTRY --> E3["config.toml<br/>전체 설정"]
    ENTRY --> E4["domain.json<br/>도메인 메타데이터"]
    ENTRY --> E5["setup.sh<br/>환경 설정 스크립트"]

    style ROOT fill:#1a1a2e,stroke:#e94560,color:#fff
    style SRC fill:#16213e,stroke:#0f3460,color:#fff
    style DATA fill:#0f3460,stroke:#533483,color:#fff
    style ENTRY fill:#533483,stroke:#e94560,color:#fff
```

### 실제 파일 트리

```
GraphRAG-Senzing/
├── src/
│   ├── __init__.py
│   ├── pipeline.py          ← AgenticPipeline (메인 오케스트레이터)
│   ├── loaders.py           ← DocumentLoader (docx/txt/md, 한글 인코딩)
│   └── embeddings.py        ← OllamaEmbedding + OllamaLLM 클라이언트
├── tests/
│   ├── __init__.py
│   └── test_integration.py  ← 통합 테스트 25개
├── tools/
│   ├── search_debug.py      ← 검색 디버깅 도구
│   └── visualize_graph.py   ← 그래프 시각화 도구
├── data/
│   ├── documents/           ← 입력 문서 (.docx, .txt, .md)
│   ├── lancedb/             ← LanceDB 벡터 저장소
│   ├── output/              ← ent.json, lex.json, erkg.json
│   ├── cache/               ← 스크래퍼 캐시
│   └── uploads/             ← Streamlit 파일 업로드
├── docs/                    ← 분석 문서
├── app.py                   ← Streamlit 웹 UI
├── run_pipeline.py          ← CLI 실행기
├── config.toml              ← 전체 설정 파일
├── domain.json              ← 도메인 메타데이터
├── pyproject.toml           ← 패키지 정의
├── requirements.txt         ← 의존성 목록
├── setup.sh                 ← 환경 설정 스크립트
└── README.md
```

---

## 3. 핵심 모듈 상세 구조

```mermaid
classDiagram
    class AgenticPipeline {
        +config: dict
        +domain: dict
        +loader: DocumentLoader
        +embedder: OllamaEmbedding
        +llm: OllamaLLM
        -_lance_db: lancedb.DBConnection
        -_lance_table: lancedb.Table
        -_chunks: list~dict~
        -_entities: list~dict~
        +check_prerequisites() dict
        +initialize()
        +load_documents(paths) dict
        +make_chunks(paragraphs) list
        +embed_and_store(documents) int
        +run_nlp_pipeline(documents)
        +query(question, conversation_history) dict
        +run(input_paths, skip_nlp) dict
        +interactive()
    }

    class DocumentLoader {
        +SUPPORTED_FORMATS: set
        +KO_ENCODINGS: list
        +load(file_path) list~str~
        +load_directory(dir_path) dict
        -_load_docx(path) list~str~
        -_load_text(path) list~str~
        -_load_markdown(path) list~str~
        -_extract_table_text(table) list~str~
        -_scrub(text) str
    }

    class OllamaEmbedding {
        +model: str
        +base_url: str
        +dim: int
        +embed_text(text) list~float~
        +embed_batch(texts) list
        +embed_numpy(text) ndarray
        +is_available() bool
    }

    class OllamaLLM {
        +model: str
        +base_url: str
        +temperature: float
        +max_tokens: int
        +generate(prompt, system) str
        +chat(messages) str
        +is_available() bool
    }

    AgenticPipeline --> DocumentLoader : uses
    AgenticPipeline --> OllamaEmbedding : uses
    AgenticPipeline --> OllamaLLM : uses
    AgenticPipeline --> LanceDB : stores vectors
    AgenticPipeline --> spaCy : NLP fallback

    style AgenticPipeline fill:#e17055,stroke:#fab1a0,color:#fff
    style DocumentLoader fill:#0984e3,stroke:#74b9ff,color:#fff
    style OllamaEmbedding fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style OllamaLLM fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 4. 전체 파이프라인 흐름도

```mermaid
flowchart TB
    subgraph PHASE1["Phase 1: 문서 로딩"]
        INPUT["로컬 문서<br/>(.docx, .txt, .md)"]
        LOADER["DocumentLoader<br/>(python-docx, chardet)"]
        PARAS["paragraphs[] 리스트"]
        INPUT --> LOADER --> PARAS
    end

    subgraph PHASE2["Phase 2: 청킹"]
        CHUNK["make_chunks()<br/>(max 1024자)"]
        PARAS --> CHUNK
    end

    subgraph PHASE3["Phase 3: 임베딩 & 벡터 저장"]
        BGE["BGE-M3 임베딩<br/>(1024차원, Ollama)"]
        LANCE["LanceDB 저장<br/>(data/lancedb/)"]
        CHUNK --> BGE --> LANCE
    end

    subgraph PHASE4["Phase 4: NLP 엔티티 추출"]
        STRW{"strwythura<br/>사용 가능?"}
        STRW_NLP["strwythura NLP<br/>(GLiNER + spaCy)"]
        SPACY_NLP["Standalone spaCy<br/>(ko_core_news_lg)"]
        ENT_STORE["엔티티 저장소<br/>(data/output/ent.json)"]
        CHUNK --> STRW
        STRW -->|Yes| STRW_NLP --> ENT_STORE
        STRW -->|No| SPACY_NLP --> ENT_STORE
    end

    subgraph PHASE5["Phase 5: 하이브리드 GraphRAG Q&A"]
        QUERY["사용자 질문"]
        VEC_SEARCH["벡터 검색<br/>(BGE-M3 → LanceDB)"]
        KW_SEARCH["키워드 검색<br/>(substring matching)"]
        GRAPH_SEARCH["그래프 검색<br/>(entity co-occurrence)"]
        MERGE["결과 병합<br/>(UID 중복제거)"]
        LLM["LLM 응답 생성<br/>(gemma3 via Ollama /api/chat)"]
        ANSWER["최종 답변"]

        QUERY --> VEC_SEARCH
        QUERY --> KW_SEARCH
        VEC_SEARCH --> MERGE
        KW_SEARCH --> MERGE
        MERGE --> GRAPH_SEARCH --> MERGE
        MERGE --> LLM --> ANSWER
    end

    PHASE1 --> PHASE2
    PHASE2 --> PHASE3
    PHASE2 --> PHASE4
    PHASE3 --> PHASE5
    PHASE4 --> PHASE5

    style PHASE1 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE2 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE3 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE4 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE5 fill:#1b263b,stroke:#415a77,color:#e0e1dd
```

---

## 5. 실행 방법 요약

| 방법 | 명령어 | 설명 |
|------|--------|------|
| CLI 기본 | `python run_pipeline.py data/documents/` | 문서 처리 → 대화형 Q&A |
| 특정 파일 | `python run_pipeline.py report.docx notes.txt` | 지정 파일만 처리 |
| NLP 건너뛰기 | `python run_pipeline.py --skip-nlp data/documents/` | 벡터 검색만 (빠른 모드) |
| 단일 질문 | `python run_pipeline.py data/documents/ --query "질문"` | 질문 후 종료 |
| Q&A만 | `python run_pipeline.py --query-only` | 기존 데이터로 Q&A |
| 상태 확인 | `python run_pipeline.py --check` | Ollama/모델 확인 |
| Streamlit | `streamlit run app.py` | 웹 UI 실행 |

---

## 6. 설정 파일 구조 (config.toml)

```mermaid
graph LR
    CONFIG["config.toml"]

    CONFIG --> SZ["[sz]<br/>Senzing gRPC<br/>(선택적)"]
    CONFIG --> ERKG_C["[erkg]<br/>Knowledge Graph<br/>파일 경로"]
    CONFIG --> NLP_C["[nlp]<br/>spaCy 모델<br/>GLiNER 설정"]
    CONFIG --> ENT_C["[ent]<br/>Entity 저장<br/>경로"]
    CONFIG --> VECT_C["[vect]<br/>LanceDB<br/>벡터 설정"]
    CONFIG --> RAG_C["[rag]<br/>LLM/Ollama<br/>RAG 파라미터"]
    CONFIG --> EMBED_C["[embed]<br/>BGE-M3 모델<br/>차원/URL"]
    CONFIG --> PROF_C["[prof]<br/>프로파일링<br/>설정"]

    style CONFIG fill:#2d3436,stroke:#636e72,color:#dfe6e9
```

### 현재 주요 설정값

| 섹션 | 키 | 값 | 설명 |
|------|-----|-----|------|
| `[rag]` | `lm_name` | `ollama_chat/gemma3:4b` | LLM 모델 |
| `[rag]` | `api_base` | `http://192.168.68.68:11434` | Ollama 서버 |
| `[rag]` | `temperature` | `0.0` | 결정적 응답 |
| `[rag]` | `max_tokens` | `3000` | 최대 응답 토큰 |
| `[rag]` | `max_chunks` | `11` | 검색 최대 청크 수 |
| `[embed]` | `model` | `bge-m3:latest` | 임베딩 모델 |
| `[embed]` | `dim` | `1024` | 임베딩 차원 |
| `[nlp]` | `spacy_model` | `ko_core_news_lg` | spaCy 모델 |
| `[vect]` | `chunk_size` | `1024` | 청크 최대 문자 수 |

---

## 7. 모듈 의존성 맵

```mermaid
graph TD
    CLI["run_pipeline.py<br/>(CLI 진입점)"]
    APP["app.py<br/>(Streamlit UI)"]

    CLI --> PIPELINE
    APP --> PIPELINE

    PIPELINE["pipeline.py<br/>AgenticPipeline"]
    PIPELINE --> LOADERS["loaders.py<br/>DocumentLoader"]
    PIPELINE --> EMBED["embeddings.py<br/>OllamaEmbedding"]
    PIPELINE --> LLM_MOD["embeddings.py<br/>OllamaLLM"]

    PIPELINE --> LANCE_EXT["LanceDB<br/>(벡터 저장소)"]
    PIPELINE --> SPACY_EXT["spaCy<br/>(NLP 엔티티 추출)"]
    PIPELINE -.-> STRW_EXT["strwythura<br/>(선택적 통합)"]

    EMBED --> OLLAMA["Ollama Server<br/>/api/embed"]
    LLM_MOD --> OLLAMA2["Ollama Server<br/>/api/chat"]

    LOADERS --> DOCX["python-docx"]
    LOADERS --> CHARDET["chardet"]

    style CLI fill:#e17055,stroke:#fab1a0,color:#fff
    style APP fill:#e17055,stroke:#fab1a0,color:#fff
    style PIPELINE fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style LOADERS fill:#0984e3,stroke:#74b9ff,color:#fff
    style EMBED fill:#00b894,stroke:#55efc4,color:#fff
    style LLM_MOD fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 8. 핵심 데이터 모델

```mermaid
erDiagram
    Chunk {
        int uid PK
        string source
        string text
        float_array vector "1024-dim float32"
    }

    Entity {
        int uid PK
        string text
        string label
        int count
        string lemma_key
    }

    LanceDBTable {
        string table_name "chunk"
        int dim "1024"
        string uri "data/lancedb"
    }

    EntityStore {
        string path "data/output/ent.json"
        string format "JSONL"
    }

    Chunk ||--o{ Entity : "contains"
    LanceDBTable ||--o{ Chunk : "stores"
    EntityStore ||--o{ Entity : "persists"
```

---

## 9. strwythura 통합 관계

현재 프로젝트는 strwythura를 **선택적 의존성**으로 취급합니다.

```mermaid
flowchart LR
    subgraph INDEPENDENT["독립 동작 (strwythura 없이)"]
        LOADER["DocumentLoader"]
        BGE["OllamaEmbedding<br/>(BGE-M3)"]
        LANCE["LanceDB"]
        SPACY["Standalone spaCy<br/>NER"]
        LLM["OllamaLLM<br/>(gemma3)"]
    end

    subgraph OPTIONAL["선택적 통합 (strwythura 있을 때)"]
        STRW_WORK["strwythura.Workflow"]
        STRW_PARSE["Parser (GLiNER + spaCy)"]
        STRW_LEX["LexicalGraph (TextRank)"]
        STRW_ERKG["KnowledgeGraph (ERKG)"]
        STRW_RAG["GraphRAG (DSPy)"]
    end

    INDEPENDENT -.->|"fallback"| OPTIONAL

    style INDEPENDENT fill:#00b894,stroke:#55efc4,color:#fff
    style OPTIONAL fill:#636e72,stroke:#b2bec3,color:#fff
```

| 기능 | strwythura 없을 때 | strwythura 있을 때 |
|------|-------------------|-------------------|
| NLP 엔티티 추출 | standalone spaCy NER | GLiNER + spaCy 통합 |
| 그래프 | entity co-occurrence 기반 | ERKG + LexicalGraph |
| LLM 호출 | Ollama /api/chat 직접 | DSPy RAG Signature |
| Q&A | 하이브리드 검색 (벡터+키워드+그래프) | Enhanced GraphRAG |
