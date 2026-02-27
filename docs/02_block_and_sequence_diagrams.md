# Strwythura 블록 다이어그램 및 시퀀스 다이어그램

> **분석 대상:** DerwenAI/strwythura v2.0.3
> **분석일:** 2026-02-27

---

## 1. 시스템 아키텍처 블록 다이어그램

```mermaid
block-beta
    columns 5

    block:INPUT:1
        columns 1
        A["구조화 데이터\n(CSV/JSON)"]
        B["비구조화 데이터\n(HTML/Text)"]
        C["도메인 Taxonomy\n(domain.json)"]
    end

    block:PROCESSING:3
        columns 3
        D["Entity Resolution\n(Senzing SDK)"]
        E["Semantic Layer\n(RDFlib/SKOS)"]
        F["NLP Pipeline\n(spaCy/GLiNER)"]
        G["Text Chunking\n& Vectorization"]
        H["Lexical Graph\n(TextRank)"]
        I["KG Construction\n(NetworkX)"]
        J["Word2Vec\n(Gensim)"]
        K["GraphRAG\n(DSPy)"]
        L["LLM Integration\n(Ollama)"]
    end

    block:OUTPUT:1
        columns 1
        M["Knowledge Graph"]
        N["Vector Store"]
        O["Q&A 응답"]
    end

    A --> D
    B --> F
    C --> E
    D --> E
    E --> I
    F --> G
    F --> H
    G --> N
    H --> I
    H --> J
    I --> M
    J --> K
    K --> L
    L --> O
```

---

## 2. 컴포넌트 블록 다이어그램

### 2.1 핵심 계층 구조

```mermaid
graph TB
    subgraph PRESENTATION["프레젠테이션 계층"]
        APP["Streamlit App\n(app.py)"]
        CLI["CLI Scripts\n(1~7_*.py)"]
        VISHTML["HTML Visualization\n(vis.py)"]
    end

    subgraph APPLICATION["애플리케이션 계층"]
        WF["Workflow\n워크플로우 관리"]
        GRAG["GraphRAG\nQ&A 엔진"]
        DSRAG["DSPy_RAG\nLLM 인터페이스"]
    end

    subgraph DOMAIN["도메인 계층"]
        DC["DomainContext\n도메인 컨텍스트"]
        PARSER["Parser\nNLP 파이프라인"]
        ES["EntityStore\n엔티티 저장소"]
    end

    subgraph INFRASTRUCTURE["인프라 계층"]
        KG["KnowledgeGraph\n(NetworkX)"]
        LG["LexicalGraph\n(TextRank)"]
        VS["VectorStore\n(LanceDB)"]
        SC["Scraper\n(BeautifulSoup)"]
    end

    subgraph EXTERNAL["외부 서비스"]
        SZ_EXT["Senzing gRPC\nServer"]
        OLLAMA["Ollama\nLLM Server"]
        OPIK_EXT["Opik\nObservability"]
    end

    APP --> WF
    APP --> GRAG
    CLI --> WF
    CLI --> GRAG

    WF --> DC
    WF --> PARSER
    WF --> SC
    GRAG --> DSRAG
    GRAG --> DC

    DC --> ES
    DC --> KG
    DC --> VS
    PARSER --> LG

    KG --> SZ_EXT
    DSRAG --> OLLAMA
    GRAG --> OPIK_EXT

    VISHTML --> KG

    style PRESENTATION fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style APPLICATION fill:#0984e3,stroke:#74b9ff,color:#fff
    style DOMAIN fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style INFRASTRUCTURE fill:#00b894,stroke:#55efc4,color:#fff
    style EXTERNAL fill:#e17055,stroke:#fab1a0,color:#fff
```

### 2.2 데이터 저장소 블록 구조

```mermaid
graph LR
    subgraph PERSISTENCE["데이터 저장소"]
        direction TB
        subgraph FILES["파일 기반"]
            TTL["Thesaurus\n(.ttl / Turtle RDF)"]
            JSONL["Entity Resolution\n(.jsonl)"]
            ENTJSON["Entity Store\n(.json)"]
            VECFILE["Entity Vectors\n(.txt)"]
            W2VFILE["Word2Vec Model\n(.w2v)"]
            GRAPHJSON["KG / Lexical Graph\n(.json)"]
        end

        subgraph DB["데이터베이스"]
            LANCE["LanceDB\n(벡터 임베딩)"]
            SQLITE["SQLite\n(스크래퍼 캐시)"]
        end

        subgraph MEMORY["인메모리"]
            NX["NetworkX\nMultiDiGraph"]
            ORDDICT["OrderedDict\n(엔티티)"]
            RDFG["RDFlib\nGraph"]
        end
    end

    style FILES fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style DB fill:#0984e3,stroke:#74b9ff,color:#fff
    style MEMORY fill:#6c5ce7,stroke:#a29bfe,color:#fff
```

---

## 3. 시퀀스 다이어그램

### 3.1 전체 파이프라인 실행 시퀀스

```mermaid
sequenceDiagram
    actor User as 사용자
    participant WF as Workflow
    participant SZ as Senzing SDK
    participant DC as DomainContext
    participant Parser as Parser
    participant Scraper as Scraper
    participant LG as LexicalGraph
    participant KG as KnowledgeGraph
    participant ES as EntityStore
    participant VS as VectorStore(LanceDB)

    Note over User,VS: Phase 1 - Entity Resolution
    User->>WF: 1_er.py 실행
    WF->>SZ: SzClient 초기화 (gRPC)
    SZ-->>WF: 연결 확인
    WF->>SZ: entity_resolution(datasets)
    SZ-->>WF: 해소된 엔티티 결과
    WF->>WF: JSONL 파일로 내보내기

    Note over User,VS: Phase 2 - Semantic Layer
    User->>WF: 2_sem.py 실행
    WF->>DC: open_vector_tables()
    WF->>WF: load_parser()
    WF->>DC: populate_semantic_layer()
    DC->>DC: RDF/SKOS 시맨틱 그래프 구축
    WF->>DC: build_graph_backbone()
    DC->>KG: promote_data_nodes()
    DC->>KG: promote_taxo_nodes()
    DC->>KG: promote_er_nodes()
    DC->>KG: promote_er_edges()
    WF->>WF: Thesaurus/EntityStore/ERKG 저장

    Note over User,VS: Phase 3 - Content Parsing
    User->>WF: 3_parse.py 실행
    WF->>WF: load_assets() (이전 결과 로드)
    WF->>WF: crawl_chunk_parse()
    loop 각 URL에 대해
        WF->>Scraper: scrape_html(url)
        Scraper-->>WF: paragraphs[]
        WF->>WF: make_chunks(paragraphs)
        loop 각 chunk에 대해
            WF->>DC: add_chunk(chunk)
            DC->>VS: 벡터 임베딩 저장
            WF->>Parser: parse_para(text)
            Parser->>Parser: transform_sentence()
            Parser->>DC: encode_entity()
            Parser->>LG: add_sent(entities)
        end
    end
    WF->>WF: EntityStore/Vectors/Graphs 저장

    Note over User,VS: Phase 5 - Embeddings & KG 정제
    User->>WF: 5_embed.py 실행
    WF->>WF: load_assets()
    WF->>WF: distill_knowledge_graph()
    WF->>LG: run_textrank()
    LG-->>WF: entity rankings
    WF->>DC: co_occur_entities()
    DC->>KG: 공출현 엣지 추가
    WF->>DC: promote_ner_nodes()
    DC->>KG: NER 노드 승격
    WF->>ES: train_embeddings()
    ES->>ES: Word2Vec 학습 (Skip-gram)
    WF->>WF: 모든 자산 저장
```

### 3.2 GraphRAG 질의응답 시퀀스

```mermaid
sequenceDiagram
    actor User as 사용자
    participant GRAG as GraphRAG
    participant DC as DomainContext
    participant VS as VectorStore
    participant KG as KnowledgeGraph
    participant ES as EntityStore
    participant W2V as Word2Vec
    participant NER as Parser(NER)
    participant LSH as MinHash/LSH
    participant DSPY as DSPy_RAG
    participant LLM as Ollama LLM

    User->>GRAG: question_answer(질문)
    GRAG->>GRAG: qa_signature(question)
    GRAG->>GRAG: run_errag(question)

    Note over GRAG,LLM: Step 1 - Vector 유사도 검색
    GRAG->>VS: find_rag_chunks(question)
    VS-->>GRAG: relevant_chunks[]

    Note over GRAG,LLM: Step 2 - NER 기반 엔티티 탐색
    GRAG->>NER: find_nearby_entities(question)
    NER->>NER: 질문에서 엔티티 추출
    NER->>LSH: MinHash 준비
    NER-->>GRAG: nearby_entities[], minhashes[]

    Note over GRAG,LLM: Step 3 - LSH 기반 앵커 노드 필터링
    GRAG->>LSH: augment_anchor_nodes()
    LSH->>KG: 엔티티 노드 매칭
    LSH-->>GRAG: anchor_nodes[]

    Note over GRAG,LLM: Step 4 - 시맨틱 확장
    GRAG->>W2V: perform_semantic_expansion()
    W2V->>W2V: 유사 임베딩 탐색
    W2V-->>GRAG: expanded_nodes[]

    Note over GRAG,LLM: Step 5 - 서브그래프 추출
    GRAG->>KG: extract_question_subgraph()
    KG->>KG: PageRank 기반 필터링
    KG-->>GRAG: subgraph

    Note over GRAG,LLM: Step 6 - 시맨틱 랜덤 워크
    GRAG->>KG: semantic_random_walk()
    KG->>KG: 최단 경로 생성
    KG-->>GRAG: paths[]

    Note over GRAG,LLM: Step 7 - 관련 Chunk 수집
    GRAG->>GRAG: find_chunk_neighbors()
    GRAG->>GRAG: get_chunks_text()
    GRAG-->>GRAG: context_text

    Note over GRAG,LLM: Step 8 - LLM 응답 생성
    GRAG->>DSPY: forward(context, question)
    DSPY->>LLM: Ollama API 호출
    LLM-->>DSPY: 생성된 응답
    DSPY-->>GRAG: response
    GRAG-->>User: 최종 답변 출력
```

### 3.3 Entity Resolution 상세 시퀀스

```mermaid
sequenceDiagram
    participant Script as 1_er.py
    participant WF as Workflow
    participant SZ as SzClient
    participant GRPC as Senzing gRPC

    Script->>WF: Workflow(config.toml)
    WF->>WF: 설정 로드

    Script->>SZ: SzClient(sz_config)
    SZ->>GRPC: gRPC 연결 (localhost:8261)
    GRPC-->>SZ: 연결 완료

    loop 각 데이터셋
        Script->>SZ: entity_resolution(dataset)
        SZ->>GRPC: addRecord()
        GRPC->>GRPC: 엔티티 매칭 & 병합
        GRPC-->>SZ: resolved entities
    end

    SZ-->>Script: 전체 ER 결과

    Script->>Script: JSON 결과 출력
    Script->>SZ: export_json_entity_report_iterator()
    SZ-->>Script: JSONL 스트림
    Script->>Script: JSONL 파일 저장
```

### 3.4 Content Parsing 상세 시퀀스

```mermaid
sequenceDiagram
    participant WF as Workflow
    participant SC as Scraper
    participant Cache as SQLite Cache
    participant Parser as Parser
    participant SpaCy as spaCy Pipeline
    participant GLiNER as GLiNER NER
    participant DC as DomainContext
    participant LG as LexicalGraph
    participant VS as LanceDB

    WF->>SC: scrape_html(url)
    SC->>Cache: 캐시 확인
    alt 캐시 히트
        Cache-->>SC: 캐시된 HTML
    else 캐시 미스
        SC->>SC: HTTP GET (SSL skip)
        SC->>Cache: 응답 저장
    end
    SC->>SC: BeautifulSoup 파싱
    SC->>SC: scrub_text() 정제
    SC-->>WF: paragraphs[]

    WF->>WF: make_chunks(paragraphs, max_size=1024)

    loop 각 chunk
        WF->>DC: add_chunk(chunk_text, url)
        DC->>VS: TextChunk 임베딩 저장

        WF->>Parser: parse_para(chunk_text)
        Parser->>SpaCy: nlp(text)
        SpaCy-->>Parser: Doc 객체

        loop 각 문장
            Parser->>Parser: transform_sentence(sent)
            Parser->>GLiNER: NER 추출
            GLiNER-->>Parser: named_entities[]
            Parser->>Parser: noun_chunks 추출
            Parser->>Parser: token 분석

            Note over Parser: 우선순위: NER > Noun Chunks > Tokens

            Parser->>Parser: tokenize_lemma()
            Parser->>DC: encode_entity(entity)
            Parser->>LG: add_sent(entity_sequence)
        end
    end
```

### 3.5 Streamlit App 사용자 인터랙션 시퀀스

```mermaid
sequenceDiagram
    actor User as 사용자
    participant ST as Streamlit UI
    participant App as app.py
    participant GRAG as GraphRAG
    participant LLM as Ollama LLM
    participant Opik as Opik Dashboard

    User->>ST: 앱 접속
    ST->>App: load_assets()
    App->>App: Workflow 초기화
    App->>GRAG: GraphRAG 인스턴스 생성
    App-->>ST: UI 렌더링

    User->>ST: 질문 입력
    ST->>App: handle_response(question)
    App->>GRAG: run_errag(question)

    GRAG->>GRAG: Vector 검색 + Entity 탐색
    GRAG->>GRAG: 서브그래프 추출
    GRAG->>LLM: DSPy forward()
    LLM-->>GRAG: 응답 텍스트

    GRAG->>Opik: 트레이스 기록
    GRAG-->>App: response + analytics

    App->>ST: 채팅 메시지 표시
    App->>ST: 분석 차트 표시
    ST-->>User: 응답 + 시각화

    User->>ST: 피드백 (별점)
    ST->>Opik: 피드백 기록
```

---

## 4. TextRank 알고리즘 블록 다이어그램

```mermaid
graph TB
    subgraph TEXTRANK["TextRank 알고리즘 흐름"]
        INPUT_SENT["입력 문장들"]
        TOKEN["토큰화 & 레마화"]
        COOCCUR["공출현 관계 추출<br/>(lookback=3)"]
        LEXGRAPH["Lexical Graph 구축<br/>(MultiDiGraph)"]
        EIGENVEC["고유벡터 중심성 계산<br/>(Personalized PageRank)"]
        QUANTILE["분위수 스트라이핑<br/>(정규화)"]
        RANKING["엔티티 랭킹 결과<br/>(DataFrame)"]

        INPUT_SENT --> TOKEN
        TOKEN --> COOCCUR
        COOCCUR --> LEXGRAPH
        LEXGRAPH --> EIGENVEC
        EIGENVEC --> QUANTILE
        QUANTILE --> RANKING
    end

    subgraph PARAMS["파라미터"]
        ALPHA["alpha = 0.85"]
        LOOKBACK["lookback = 3"]
        AMPLITUDE["amplitude = 4"]
    end

    ALPHA --> EIGENVEC
    LOOKBACK --> COOCCUR
    AMPLITUDE --> QUANTILE

    style TEXTRANK fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style PARAMS fill:#2d3436,stroke:#636e72,color:#dfe6e9
```

---

## 5. Enhanced GraphRAG 검색 파이프라인 블록 다이어그램

```mermaid
graph TB
    QUESTION["사용자 질문"]

    subgraph RETRIEVAL["다중 검색 전략"]
        direction TB

        subgraph VEC_SEARCH["벡터 유사도 검색"]
            VS_Q["질문 임베딩"]
            VS_S["LanceDB 검색"]
            VS_R["관련 Chunks"]
            VS_Q --> VS_S --> VS_R
        end

        subgraph ENTITY_SEARCH["엔티티 기반 검색"]
            NER_Q["질문 NER 추출"]
            MINHASH["MinHash 생성"]
            LSH_F["LSH 필터링"]
            ANCHOR["앵커 노드 선정"]
            NER_Q --> MINHASH --> LSH_F --> ANCHOR
        end

        subgraph SEMANTIC_EXP["시맨틱 확장"]
            W2V_Q["Word2Vec\n유사도 검색"]
            EXPAND["이웃 노드 확장"]
            W2V_Q --> EXPAND
        end
    end

    subgraph GRAPH_OPS["그래프 연산"]
        SUBGRAPH["서브그래프 추출\n(PageRank)"]
        RANDOM_WALK["시맨틱 랜덤 워크\n(최단 경로)"]
        CHUNK_NEIGHBOR["Chunk 이웃 탐색"]
        SUBGRAPH --> RANDOM_WALK --> CHUNK_NEIGHBOR
    end

    subgraph GENERATION["응답 생성"]
        CONTEXT["컨텍스트 조합"]
        DSPY_FWD["DSPy RAG\nSignature"]
        LLM_CALL["Ollama LLM\n호출"]
        RESPONSE["최종 응답"]
        CONTEXT --> DSPY_FWD --> LLM_CALL --> RESPONSE
    end

    QUESTION --> VEC_SEARCH
    QUESTION --> ENTITY_SEARCH
    QUESTION --> SEMANTIC_EXP

    VS_R --> GRAPH_OPS
    ANCHOR --> GRAPH_OPS
    EXPAND --> GRAPH_OPS

    CHUNK_NEIGHBOR --> GENERATION

    style RETRIEVAL fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style GRAPH_OPS fill:#0984e3,stroke:#74b9ff,color:#fff
    style GENERATION fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 6. 엔티티 처리 우선순위 블록 다이어그램

```mermaid
graph TD
    INPUT["입력 텍스트 (문장)"]

    subgraph PRIORITY["엔티티 추출 우선순위"]
        direction LR
        P1["1순위: NER 엔티티\n(GLiNER/spaCy NER)"]
        P2["2순위: Noun Chunks\n(spaCy 명사구)"]
        P3["3순위: Individual Tokens\n(개별 토큰)"]
        P1 --> P2 --> P3
    end

    subgraph OVERLAP["겹침 해소 규칙"]
        O1["within_loc():\n포함 관계 확인"]
        O2["overlaps_loc():\n겹침 관계 확인"]
        O3["높은 우선순위 유지\n낮은 우선순위 제거"]
    end

    subgraph OUTPUT_ENT["출력"]
        LEMMA["레마화된 키"]
        ENTITY_OBJ["Entity 객체 생성"]
        ENCODE["EntityStore 등록"]
    end

    INPUT --> PRIORITY
    PRIORITY --> OVERLAP
    OVERLAP --> OUTPUT_ENT

    style PRIORITY fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style OVERLAP fill:#e17055,stroke:#fab1a0,color:#fff
    style OUTPUT_ENT fill:#00b894,stroke:#55efc4,color:#fff
```

이 문서는 Strwythura의 주요 컴포넌트 간 상호작용과 데이터 흐름을 시퀀스/블록 다이어그램으로 상세히 분석한 자료입니다.
