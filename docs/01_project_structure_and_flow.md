# Strwythura 프로젝트 구조 및 흐름도 분석

> **프로젝트명:** Strwythura (Entity-Resolved Knowledge Graph)
> **버전:** 2.0.3
> **라이선스:** MIT
> **작성자:** Paco Nathan (DerwenAI)
> **분석일:** 2026-02-27

---

## 1. 프로젝트 개요

Strwythura는 **구조화된 데이터와 비구조화된 데이터를 결합하여 Entity-Resolved Knowledge Graph를 구축**하는 Python 프레임워크입니다. "Context Engineering"을 통해 특정 도메인에 최적화된 AI 애플리케이션을 지원하며, GraphRAG(Graph-based Retrieval Augmented Generation) 파이프라인을 제공합니다.

### 핵심 기술 스택

| 분류 | 기술 |
|------|------|
| Entity Resolution | Senzing SDK (gRPC) |
| NLP/NER | spaCy, GLiNER, DSPy |
| Graph | NetworkX, RDFlib |
| Vector Store | LanceDB |
| Embeddings | Gensim Word2Vec, ArrowSpace |
| LLM | Ollama (Gemma3) |
| Visualization | PyVis, Streamlit |
| Observability | Opik, pyinstrument |

---

## 2. 디렉토리 및 파일 구조

```mermaid
graph TD
    ROOT["strwythura/ (root)"]

    ROOT --> CONFIG["설정 파일"]
    ROOT --> PIPELINE["파이프라인 스크립트"]
    ROOT --> PKG["strwythura/ (패키지)"]
    ROOT --> MISC["기타 파일"]

    CONFIG --> CT["config.toml"]
    CONFIG --> DJ["domain.json"]
    CONFIG --> PP["pyproject.toml"]

    PIPELINE --> P1["1_er.py<br/>Entity Resolution"]
    PIPELINE --> P2["2_sem.py<br/>Semantic Layer"]
    PIPELINE --> P3["3_parse.py<br/>Content Parsing"]
    PIPELINE --> P5["5_embed.py<br/>Embeddings"]
    PIPELINE --> P6["6_vis.py<br/>Visualization"]
    PIPELINE --> P7["7_errag.py<br/>GraphRAG"]
    PIPELINE --> PA["app.py<br/>Streamlit UI"]

    PKG --> INIT["__init__.py"]
    PKG --> CTX["ctx.py - DomainContext"]
    PKG --> ELEM["elem.py - Elements/Models"]
    PKG --> ENT["ent.py - EntityStore"]
    PKG --> ERKG["erkg.py - KnowledgeGraph"]
    PKG --> LEX["lex.py - LexicalGraph"]
    PKG --> NLP["nlp.py - Parser"]
    PKG --> OPT["opt.py - Optimization"]
    PKG --> PROF["prof.py - Profiler"]
    PKG --> RAG["rag.py - GraphRAG"]
    PKG --> SCRAPE["scrape.py - Scraper"]
    PKG --> VIS["vis.py - VisHTML"]
    PKG --> WORK["work.py - Workflow"]
    PKG --> RES["resources/ - Templates"]

    MISC --> LK["poetry.lock"]
    MISC --> LT["lint.sh"]
    MISC --> GI[".gitignore"]
    MISC --> RM["README.md"]

    style ROOT fill:#1a1a2e,stroke:#e94560,color:#fff
    style PKG fill:#16213e,stroke:#0f3460,color:#fff
    style PIPELINE fill:#0f3460,stroke:#533483,color:#fff
    style CONFIG fill:#533483,stroke:#e94560,color:#fff
```

---

## 3. 핵심 모듈 상세 구조

```mermaid
classDiagram
    class Workflow {
        +config: dict
        +thesaurus: Thesaurus
        +scraper: Scraper
        +dc: DomainContext
        +load_class() classmethod
        +load_parser()
        +populate_semantic_layer()
        +build_graph_backbone()
        +make_chunks()
        +crawl_chunk_parse()
        +distill_knowledge_graph()
        +load_assets()
    }

    class DomainContext {
        +entities: EntityStore
        +erkg: KnowledgeGraph
        +open_vector_tables()
        +add_chunk()
        +get_label_map()
        +promote_data_nodes()
        +promote_taxo_nodes()
        +promote_er_nodes()
        +promote_er_edges()
        +promote_ner_nodes()
        +link_entity_chunks()
        +co_occur_entities()
    }

    class Parser {
        +BASE_CONCEPT: str
        +STOP_WORDS: set
        +build_ner_pipe()
        +normalize_pos()
        +tokenize_lemma()
        +transform_sentence()
        +parse_para()
    }

    class EntityStore {
        +entities: OrderedDict
        +w2v_model: Word2Vec
        +encode_entity()
        +load_json() / save_json()
        +load_vec() / save_vec()
        +train_embeddings()
        +build_aspace()
    }

    class KnowledgeGraph {
        +graph: nx.MultiDiGraph
        +add_node()
        +add_edge()
        +get_node()
        +neighbors()
        +subgraph()
        +shortest_paths()
        +vis_nodes() / vis_edges()
    }

    class LexicalGraph {
        +graph: nx.MultiDiGraph
        +increment_edge()
        +add_sent()
        +run_textrank()
    }

    class GraphRAG {
        +dspy_rag: DSPy_RAG
        +question_answer()
        +run_errag()
        +find_rag_chunks()
        +find_nearby_entities()
        +augment_anchor_nodes()
        +perform_semantic_expansion()
        +extract_question_subgraph()
        +semantic_random_walk()
    }

    class Scraper {
        +get_cache()
        +scrub_text()
        +scrape_html()
    }

    class VisHTML {
        +gen_vis_html()
        +rebuild_html()
    }

    Workflow --> DomainContext : manages
    Workflow --> Parser : initializes
    Workflow --> Scraper : uses
    DomainContext --> EntityStore : contains
    DomainContext --> KnowledgeGraph : contains
    Parser --> DomainContext : references
    Parser --> LexicalGraph : builds
    GraphRAG --> Workflow : orchestrates
    GraphRAG --> DomainContext : queries
    VisHTML --> KnowledgeGraph : visualizes
```

---

## 4. 전체 파이프라인 흐름도

```mermaid
flowchart TB
    subgraph PHASE1["Phase 1: Entity Resolution"]
        ER_IN["구조화된 데이터<br/>(CSV, JSON)"]
        SZ["Senzing SDK<br/>(gRPC)"]
        ER_OUT["Entity Resolution<br/>결과 (JSONL)"]
        ER_IN --> SZ --> ER_OUT
    end

    subgraph PHASE2["Phase 2: Semantic Layer"]
        TAXO["도메인 Taxonomy<br/>(domain.json)"]
        RDF["RDF/SKOS<br/>시맨틱 그래프"]
        BACKBONE["Graph Backbone<br/>(NetworkX)"]
        ER_OUT --> RDF
        TAXO --> RDF
        RDF --> BACKBONE
    end

    subgraph PHASE3["Phase 3: Content Parsing"]
        DOCS["비구조화 문서<br/>(HTML, Text)"]
        SCRAPE["Web Scraper<br/>(BeautifulSoup)"]
        CHUNK["Text Chunking"]
        NER["NER 추출<br/>(spaCy + GLiNER)"]
        VECT["Vector Embedding<br/>(LanceDB)"]
        DOCS --> SCRAPE --> CHUNK
        CHUNK --> NER
        CHUNK --> VECT
    end

    subgraph PHASE4["Phase 4: Embeddings"]
        LEXG["Lexical Graph<br/>(TextRank)"]
        W2V["Word2Vec<br/>학습"]
        DISTILL["Knowledge Graph<br/>정제"]
        NER --> LEXG
        LEXG --> DISTILL
        LEXG --> W2V
    end

    subgraph PHASE5["Phase 5: Visualization"]
        PYVIS["PyVis HTML<br/>시각화"]
        STREAM["Streamlit<br/>대시보드"]
        DISTILL --> PYVIS
        DISTILL --> STREAM
    end

    subgraph PHASE6["Phase 6: GraphRAG Q&A"]
        QUERY["사용자 질의"]
        ERRAG["Enhanced GraphRAG<br/>(DSPy + Ollama)"]
        ANSWER["응답 생성"]
        QUERY --> ERRAG
        VECT --> ERRAG
        DISTILL --> ERRAG
        W2V --> ERRAG
        ERRAG --> ANSWER
    end

    PHASE1 --> PHASE2
    PHASE2 --> PHASE3
    PHASE3 --> PHASE4
    PHASE4 --> PHASE5
    PHASE4 --> PHASE6

    style PHASE1 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE2 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE3 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE4 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE5 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PHASE6 fill:#1b263b,stroke:#415a77,color:#e0e1dd
```

---

## 5. 파이프라인 스크립트별 실행 순서

| 단계 | 스크립트 | 역할 | 입력 | 출력 |
|------|----------|------|------|------|
| 1 | `1_er.py` | Entity Resolution | 구조화 데이터셋 | ER 결과 (JSONL) |
| 2 | `2_sem.py` | Semantic Layer 구축 | ER 결과 + Taxonomy | Thesaurus (TTL), ERKG, EntityStore |
| 3 | `3_parse.py` | 문서 파싱 & NER | 웹 문서/텍스트 | 벡터 임베딩, 엔티티, Lexical Graph |
| - | (4단계: Human-in-the-Loop) | 수동 큐레이션 | 추출된 엔티티 | 교정된 엔티티 |
| 5 | `5_embed.py` | 임베딩 학습 & KG 정제 | Lexical Graph + EntityStore | Word2Vec 모델, 정제된 ERKG |
| 6 | `6_vis.py` | 시각화 | ERKG | HTML 시각화 파일 |
| 7 | `7_errag.py` | GraphRAG Q&A | 모든 자산 | 대화형 Q&A |
| - | `app.py` | Streamlit 웹 UI | 모든 자산 | 웹 대시보드 |

---

## 6. 설정 파일 구조 (config.toml)

```mermaid
graph LR
    CONFIG["config.toml"]

    CONFIG --> SZ["[sz]<br/>Senzing gRPC<br/>서버 설정"]
    CONFIG --> ERKG_C["[erkg]<br/>Knowledge Graph<br/>파일 경로"]
    CONFIG --> CTX_C["[ctx]<br/>도메인 컨텍스트<br/>클래스 설정"]
    CONFIG --> NLP_C["[nlp]<br/>spaCy 모델<br/>GLiNER 설정"]
    CONFIG --> TR["[tr]<br/>TextRank<br/>파라미터"]
    CONFIG --> ENT_C["[ent]<br/>Entity 저장<br/>경로 설정"]
    CONFIG --> VECT_C["[vect]<br/>LanceDB<br/>벡터 설정"]
    CONFIG --> SCRAPER_C["[scraper]<br/>스크래퍼<br/>캐시 설정"]
    CONFIG --> VIS_C["[vis]<br/>시각화<br/>출력 설정"]
    CONFIG --> RAG_C["[rag]<br/>LLM/Ollama<br/>RAG 파라미터"]
    CONFIG --> OPIK_C["[opik]<br/>모니터링<br/>API 설정"]
    CONFIG --> PROF_C["[prof]<br/>프로파일링<br/>설정"]

    style CONFIG fill:#2d3436,stroke:#636e72,color:#dfe6e9
```

---

## 7. 모듈 의존성 맵

```mermaid
graph TD
    INIT["__init__.py<br/>(Public API)"]

    INIT --> CTX_M["ctx.py"]
    INIT --> ELEM_M["elem.py"]
    INIT --> ENT_M["ent.py"]
    INIT --> ERKG_M["erkg.py"]
    INIT --> LEX_M["lex.py"]
    INIT --> NLP_M["nlp.py"]
    INIT --> OPT_M["opt.py"]
    INIT --> PROF_M["prof.py"]
    INIT --> RAG_M["rag.py"]
    INIT --> SCRAPE_M["scrape.py"]
    INIT --> VIS_M["vis.py"]
    INIT --> WORK_M["work.py"]

    CTX_M --> ELEM_M
    CTX_M --> ENT_M
    CTX_M --> ERKG_M
    CTX_M --> LEX_M

    NLP_M --> CTX_M
    NLP_M --> ELEM_M

    RAG_M --> WORK_M
    RAG_M --> ENT_M

    WORK_M --> CTX_M
    WORK_M --> NLP_M
    WORK_M --> SCRAPE_M

    LEX_M --> ELEM_M
    ENT_M --> ELEM_M

    style INIT fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style WORK_M fill:#e17055,stroke:#fab1a0,color:#fff
    style RAG_M fill:#00b894,stroke:#55efc4,color:#fff
    style CTX_M fill:#0984e3,stroke:#74b9ff,color:#fff
```

---

## 8. 핵심 데이터 모델

```mermaid
erDiagram
    Entity {
        int uid PK
        string lemma_key
        string label
        string source
        float rank
        int count
    }

    TextChunk {
        int uid PK
        string url
        int sent_id
        string text
        vector embedding
    }

    KGNode {
        string iri PK
        string kind
        string label
        dict attributes
    }

    KGEdge {
        string src FK
        string dst FK
        float prob
        string rel_type
    }

    NounSpan {
        tuple loc
        string text
        string label
        string source
    }

    Entity ||--o{ NounSpan : "has spans"
    Entity ||--o{ TextChunk : "appears in"
    KGNode ||--o{ KGEdge : "connected by"
    TextChunk ||--o{ Entity : "contains"
```

이 문서는 Strwythura 프로젝트의 전체 구조, 모듈 구성, 파이프라인 흐름을 정리한 것입니다. 다음 문서에서는 블록 다이어그램과 시퀀스 다이어그램을 통해 세부 동작을 분석합니다.
