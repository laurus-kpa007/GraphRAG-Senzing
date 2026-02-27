# Strwythura 사용자 및 데이터 워크플로우 분석

> **분석 대상:** DerwenAI/strwythura v2.0.3
> **분석일:** 2026-02-27

---

## 1. 사용자 워크플로우 전체 흐름

```mermaid
journey
    title Strwythura 사용자 워크플로우
    section 환경 설정
      Python 환경 구축 (3.11~3.13): 3: 사용자
      Poetry 의존성 설치: 3: 사용자
      config.toml 설정: 4: 사용자
      domain.json 도메인 정의: 5: 사용자
      Senzing gRPC 서버 시작: 2: 사용자
      Ollama LLM 서버 시작: 3: 사용자
    section 파이프라인 실행
      1_er.py Entity Resolution: 4: 시스템
      2_sem.py Semantic Layer 구축: 4: 시스템
      3_parse.py 문서 크롤링 및 파싱: 5: 시스템
      수동 큐레이션 (Human-in-the-Loop): 3: 사용자
      5_embed.py 임베딩 학습: 4: 시스템
      6_vis.py 시각화 생성: 4: 시스템
    section 활용
      7_errag.py CLI Q&A: 5: 사용자
      app.py Streamlit 대시보드: 5: 사용자
      결과 분석 및 피드백: 4: 사용자
```

---

## 2. 사용자 역할별 워크플로우

```mermaid
graph TB
    subgraph ROLES["사용자 역할"]
        DE["데이터 엔지니어"]
        DS["데이터 사이언티스트"]
        DM["도메인 전문가"]
        EU["최종 사용자"]
    end

    subgraph DE_TASKS["데이터 엔지니어 작업"]
        DE1["데이터 소스 준비\n(CSV, JSON)"]
        DE2["config.toml 설정"]
        DE3["Senzing 서버 구성"]
        DE4["파이프라인 실행\n(1~5단계)"]
        DE5["인프라 모니터링"]
    end

    subgraph DS_TASKS["데이터 사이언티스트 작업"]
        DS1["domain.json\n도메인 정의"]
        DS2["Taxonomy 설계\n(SKOS/RDF)"]
        DS3["NER 라벨 매핑\n설정"]
        DS4["임베딩 모델 튜닝"]
        DS5["RAG 파라미터 최적화"]
    end

    subgraph DM_TASKS["도메인 전문가 작업"]
        DM1["추출된 엔티티\n검증"]
        DM2["관계 정확성\n확인"]
        DM3["KG 시각화\n검토"]
        DM4["Q&A 품질\n평가"]
    end

    subgraph EU_TASKS["최종 사용자 작업"]
        EU1["Streamlit UI로\n질문 입력"]
        EU2["응답 확인\n및 분석"]
        EU3["피드백 제공\n(별점)"]
    end

    DE --> DE_TASKS
    DS --> DS_TASKS
    DM --> DM_TASKS
    EU --> EU_TASKS

    DE_TASKS --> DS_TASKS
    DS_TASKS --> DM_TASKS
    DM_TASKS --> EU_TASKS

    style ROLES fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style DE_TASKS fill:#0984e3,stroke:#74b9ff,color:#fff
    style DS_TASKS fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style DM_TASKS fill:#e17055,stroke:#fab1a0,color:#fff
    style EU_TASKS fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 3. 데이터 워크플로우 상세 분석

### 3.1 전체 데이터 라이프사이클

```mermaid
flowchart TB
    subgraph INPUT_LAYER["데이터 입력 계층"]
        direction LR
        STRUCT["구조화 데이터\n(CSV/JSON)"]
        UNSTRUCT["비구조화 데이터\n(HTML/Text/Web)"]
        TAXONOMY["도메인 Taxonomy\n(TTL/SKOS)"]
    end

    subgraph INGEST["데이터 수집 계층"]
        direction LR
        SZ_ER["Senzing\nEntity Resolution"]
        SCRAPER["Web Scraper\n+ Cache (SQLite)"]
        TAXO_LOAD["Taxonomy Loader\n(RDFlib)"]
    end

    subgraph TRANSFORM["데이터 변환 계층"]
        direction TB

        subgraph SEM_TRANSFORM["시맨틱 변환"]
            RDF_BUILD["RDF 그래프 구축\n(SKOS Concepts)"]
            SPARQL["SPARQL 쿼리\n관계 추출"]
            PROMOTE["NetworkX 그래프\n승격(Promote)"]
        end

        subgraph TEXT_TRANSFORM["텍스트 변환"]
            CLEAN["텍스트 정제\n(Unicode NFKD)"]
            CHUNK_OP["청킹\n(max 1024 tokens)"]
            NLP_PROC["NLP 처리\n(spaCy + GLiNER)"]
        end

        subgraph ENTITY_TRANSFORM["엔티티 변환"]
            LEMMA["레마화\n(POS.lemma)"]
            DEDUP["중복 제거\n(우선순위 기반)"]
            IRI_GEN["IRI 생성\n(strw:lemma_*)"]
        end
    end

    subgraph STORE["데이터 저장 계층"]
        direction LR
        LANCE_STORE["LanceDB\n벡터 저장소"]
        NX_GRAPH["NetworkX\nKnowledge Graph"]
        ENT_STORE["EntityStore\n(JSONL)"]
        LEX_STORE["Lexical Graph\n(JSON)"]
        W2V_STORE["Word2Vec\n모델 파일"]
    end

    subgraph ANALYSIS["데이터 분석 계층"]
        direction LR
        TEXTRANK["TextRank\n(PageRank)"]
        COOCCUR["공출현\n확률 계산"]
        W2V_TRAIN["Word2Vec\n학습"]
        EMBED_SIM["임베딩\n유사도"]
    end

    subgraph OUTPUT_LAYER["데이터 출력 계층"]
        direction LR
        VIS_OUT["대화형 HTML\n시각화"]
        RAG_OUT["GraphRAG\nQ&A 응답"]
        ANALYTICS["성능 분석\n대시보드"]
    end

    INPUT_LAYER --> INGEST
    INGEST --> TRANSFORM
    TRANSFORM --> STORE
    STORE --> ANALYSIS
    ANALYSIS --> STORE
    STORE --> OUTPUT_LAYER

    SZ_ER --> RDF_BUILD
    SCRAPER --> CLEAN
    TAXO_LOAD --> RDF_BUILD

    CLEAN --> CHUNK_OP --> NLP_PROC
    NLP_PROC --> LEMMA --> DEDUP --> IRI_GEN

    RDF_BUILD --> SPARQL --> PROMOTE

    PROMOTE --> NX_GRAPH
    NLP_PROC --> LANCE_STORE
    IRI_GEN --> ENT_STORE
    NLP_PROC --> LEX_STORE

    TEXTRANK --> W2V_TRAIN --> W2V_STORE
    COOCCUR --> NX_GRAPH

    NX_GRAPH --> VIS_OUT
    NX_GRAPH --> RAG_OUT
    LANCE_STORE --> RAG_OUT
    W2V_STORE --> RAG_OUT

    style INPUT_LAYER fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style INGEST fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style TRANSFORM fill:#0984e3,stroke:#74b9ff,color:#fff
    style STORE fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style ANALYSIS fill:#e17055,stroke:#fab1a0,color:#fff
    style OUTPUT_LAYER fill:#00b894,stroke:#55efc4,color:#fff
```

### 3.2 데이터 포맷 변환 흐름

```mermaid
flowchart LR
    subgraph FORMATS["데이터 포맷 변환"]
        CSV_JSON["CSV/JSON\n(원본 데이터)"]
        JSONL["JSONL\n(ER 결과)"]
        TTL["Turtle (.ttl)\n(RDF/SKOS)"]
        RDFG["RDFlib Graph\n(인메모리)"]
        NXG["NetworkX\nMultiDiGraph"]
        JSON_ENT["JSONL\n(EntityStore)"]
        JSON_GRAPH["JSON\n(Graph Serialized)"]
        VEC_TXT["TXT\n(벡터 파일)"]
        W2V_BIN["W2V\n(모델 바이너리)"]
        LANCE_TBL["LanceDB Table\n(벡터 DB)"]
        HTML_OUT["HTML\n(시각화)"]
    end

    CSV_JSON -->|"Senzing SDK"| JSONL
    JSONL -->|"sz_semantics"| TTL
    TTL -->|"RDFlib parse"| RDFG
    RDFG -->|"SPARQL + Promote"| NXG
    NXG -->|"node_link_data"| JSON_GRAPH
    JSON_GRAPH -->|"node_link_graph"| NXG

    CSV_JSON -->|"NLP Parse"| JSON_ENT
    JSON_ENT -->|"load_json"| JSON_ENT
    JSON_ENT -->|"embed_sequence"| VEC_TXT
    VEC_TXT -->|"train_embeddings"| W2V_BIN

    CSV_JSON -->|"Embedding"| LANCE_TBL

    NXG -->|"PyVis"| HTML_OUT

    style FORMATS fill:#1b263b,stroke:#415a77,color:#e0e1dd
```

---

## 4. 핵심 데이터 처리 워크플로우

### 4.1 텍스트 청킹 워크플로우

```mermaid
flowchart TD
    URL["웹 URL 또는 문서"]
    FETCH["HTTP GET\n+ 캐시 확인"]
    HTML_PARSE["HTML 파싱\n(BeautifulSoup)"]
    EXTRACT_P["<p> 태그 추출"]
    SCRUB["텍스트 정제\nscrub_text()"]
    PARAS["paragraphs[] 리스트"]

    subgraph CHUNKING["청킹 프로세스 (make_chunks)"]
        CHECK_SIZE{"현재 버퍼 +\n새 단락 >\nmax_chunk?"}
        ADD_PARA["버퍼에 단락 추가"]
        FLUSH["현재 버퍼를\nchunk로 확정"]
        NEW_BUF["새 버퍼 시작"]
        FINAL["마지막 버퍼\nchunk로 확정"]
    end

    CHUNK_OUT["TextChunk 객체들"]

    subgraph PER_CHUNK["각 Chunk 처리"]
        ASSIGN_UID["UID 할당"]
        EMBED["벡터 임베딩\n(384차원)"]
        LANCE_ADD["LanceDB 저장"]
        KG_LINK["KG 노드 등록\n(NodeKind.Chunk)"]
    end

    URL --> FETCH --> HTML_PARSE --> EXTRACT_P --> SCRUB --> PARAS

    PARAS --> CHECK_SIZE
    CHECK_SIZE -->|No| ADD_PARA --> CHECK_SIZE
    CHECK_SIZE -->|Yes| FLUSH --> NEW_BUF --> CHECK_SIZE
    ADD_PARA -->|마지막| FINAL

    FLUSH --> CHUNK_OUT
    FINAL --> CHUNK_OUT

    CHUNK_OUT --> PER_CHUNK
    ASSIGN_UID --> EMBED --> LANCE_ADD
    LANCE_ADD --> KG_LINK

    style CHUNKING fill:#0984e3,stroke:#74b9ff,color:#fff
    style PER_CHUNK fill:#6c5ce7,stroke:#a29bfe,color:#fff
```

### 4.2 엔티티 추출 및 등록 워크플로우

```mermaid
flowchart TD
    TEXT["텍스트 Chunk"]
    SPACY["spaCy 파이프라인"]
    DOC["Doc 객체"]

    subgraph PER_SENT["문장별 처리"]
        SENT["문장 분리"]

        subgraph EXTRACTION["엔티티 추출 (transform_sentence)"]
            NER_EXT["NER 엔티티 추출\n(GLiNER/spaCy)"]
            NC_EXT["Noun Chunk 추출\n(spaCy)"]
            TOK_EXT["개별 토큰 추출\n(NOUN/PROPN)"]

            OVERLAP_CHECK["겹침 해소\n(우선순위 적용)"]
            NOUNSPAN["NounSpan[] 생성"]
        end

        subgraph REGISTRATION["엔티티 등록"]
            LEMMATIZE["레마화\ntokenize_lemma()"]
            LABEL_MAP["라벨 맵 조회\n(도메인 taxonomy)"]
            ENCODE["EntityStore 등록\nencode_entity()"]
            INSTANCE["EntityInstance\n생성"]
        end

        subgraph GRAPH_UPDATE["그래프 업데이트"]
            LEX_ADD["LexicalGraph.add_sent()\n공출현 관계 추가"]
            SEQ_EMBED["EntityStore.embed_sequence()\n벡터 시퀀스 기록"]
        end
    end

    TEXT --> SPACY --> DOC --> SENT

    SENT --> NER_EXT
    SENT --> NC_EXT
    SENT --> TOK_EXT

    NER_EXT --> OVERLAP_CHECK
    NC_EXT --> OVERLAP_CHECK
    TOK_EXT --> OVERLAP_CHECK

    OVERLAP_CHECK --> NOUNSPAN
    NOUNSPAN --> LEMMATIZE
    LEMMATIZE --> LABEL_MAP
    LABEL_MAP --> ENCODE
    ENCODE --> INSTANCE

    INSTANCE --> LEX_ADD
    INSTANCE --> SEQ_EMBED

    style EXTRACTION fill:#e17055,stroke:#fab1a0,color:#fff
    style REGISTRATION fill:#00b894,stroke:#55efc4,color:#fff
    style GRAPH_UPDATE fill:#0984e3,stroke:#74b9ff,color:#fff
```

### 4.3 Knowledge Graph 구축 워크플로우

```mermaid
flowchart TD
    subgraph BACKBONE["Backbone 구축 (Phase 2)"]
        ER_DATA["Entity Resolution\n결과 (JSONL)"]
        TAXO_DATA["Domain Taxonomy\n(TTL)"]

        SEM_LAYER["Semantic Layer\n(RDF/SKOS)"]

        PROMOTE_DATA["promote_data_nodes()\n데이터 레코드 노드"]
        PROMOTE_TAXO["promote_taxo_nodes()\n택소노미 노드/엣지"]
        PROMOTE_ER_N["promote_er_nodes()\nER 엔티티 노드"]
        PROMOTE_ER_E["promote_er_edges()\nER 관계 엣지"]

        KG_INIT["ERKG 초기 상태\n(Backbone)"]
    end

    subgraph ENRICHMENT["보강 (Phase 3 & 5)"]
        NER_NODES["promote_ner_nodes()\nNER 엔티티 승격"]
        CHUNK_LINKS["link_entity_chunks()\n엔티티-Chunk 연결"]
        COOCCUR_EDGES["co_occur_entities()\n공출현 엣지\n(조건부 확률)"]

        KG_ENRICHED["ERKG 보강 상태"]
    end

    subgraph DISTILL["정제 (Phase 5)"]
        TR_RANK["TextRank 실행\n(Personalized PageRank)"]
        RANK_ASSIGN["랭크 값 할당\n(정규화)"]
        FINAL_KG["최종 Knowledge Graph"]
    end

    ER_DATA --> SEM_LAYER
    TAXO_DATA --> SEM_LAYER

    SEM_LAYER --> PROMOTE_DATA
    SEM_LAYER --> PROMOTE_TAXO
    SEM_LAYER --> PROMOTE_ER_N
    SEM_LAYER --> PROMOTE_ER_E

    PROMOTE_DATA --> KG_INIT
    PROMOTE_TAXO --> KG_INIT
    PROMOTE_ER_N --> KG_INIT
    PROMOTE_ER_E --> KG_INIT

    KG_INIT --> NER_NODES
    KG_INIT --> CHUNK_LINKS
    NER_NODES --> KG_ENRICHED
    CHUNK_LINKS --> KG_ENRICHED
    KG_ENRICHED --> COOCCUR_EDGES

    COOCCUR_EDGES --> TR_RANK
    TR_RANK --> RANK_ASSIGN
    RANK_ASSIGN --> FINAL_KG

    style BACKBONE fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style ENRICHMENT fill:#0984e3,stroke:#74b9ff,color:#fff
    style DISTILL fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 5. GraphRAG 검색 워크플로우 상세

```mermaid
flowchart TD
    QUESTION["사용자 질문"]

    subgraph STAGE1["Stage 1: 벡터 검색"]
        Q_EMBED["질문 벡터화"]
        LANCE_SEARCH["LanceDB\n유사도 검색"]
        TOP_CHUNKS["상위 K개 Chunk\n(거리 < threshold)"]
        Q_EMBED --> LANCE_SEARCH --> TOP_CHUNKS
    end

    subgraph STAGE2["Stage 2: NER 기반 탐색"]
        Q_PARSE["질문 NER 추출\n(spaCy/GLiNER)"]
        Q_ENTITIES["질문 내 엔티티"]
        MINHASH_PREP["MinHash 생성\n(128 permutations)"]
        Q_PARSE --> Q_ENTITIES --> MINHASH_PREP
    end

    subgraph STAGE3["Stage 3: LSH 앵커 필터링"]
        LSH_INDEX["LSH 인덱스 구축"]
        KG_ENTITIES["KG 엔티티 노드\n매칭"]
        ANCHOR_SELECT["앵커 노드\n선정"]
        LSH_INDEX --> KG_ENTITIES --> ANCHOR_SELECT
    end

    subgraph STAGE4["Stage 4: 시맨틱 확장"]
        W2V_SIMILAR["Word2Vec\n유사 엔티티 검색"]
        EXPAND_NODES["확장된 노드 집합\n(상위 20개)"]
        W2V_SIMILAR --> EXPAND_NODES
    end

    subgraph STAGE5["Stage 5: 서브그래프 추출"]
        SHORTEST_PATH["앵커 노드 간\n최단 경로 계산"]
        PAGERANK_FILTER["PageRank 기반\n중요 노드 필터"]
        QUESTION_SUBGRAPH["질문 서브그래프"]
        SHORTEST_PATH --> PAGERANK_FILTER --> QUESTION_SUBGRAPH
    end

    subgraph STAGE6["Stage 6: 컨텍스트 조립"]
        CHUNK_NEIGHBORS["서브그래프 내\nChunk 이웃 탐색"]
        CONTEXT_TEXT["컨텍스트 텍스트\n조합"]
        CHUNK_NEIGHBORS --> CONTEXT_TEXT
    end

    subgraph STAGE7["Stage 7: LLM 응답"]
        DSPY_CALL["DSPy RAG\nSignature 호출"]
        OLLAMA_GEN["Ollama LLM\n응답 생성"]
        FINAL_ANS["최종 응답"]
        DSPY_CALL --> OLLAMA_GEN --> FINAL_ANS
    end

    QUESTION --> STAGE1
    QUESTION --> STAGE2

    TOP_CHUNKS --> STAGE3
    MINHASH_PREP --> STAGE3

    ANCHOR_SELECT --> STAGE4
    EXPAND_NODES --> STAGE5
    ANCHOR_SELECT --> STAGE5

    QUESTION_SUBGRAPH --> STAGE6
    TOP_CHUNKS --> STAGE6

    CONTEXT_TEXT --> STAGE7

    style STAGE1 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style STAGE2 fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style STAGE3 fill:#0984e3,stroke:#74b9ff,color:#fff
    style STAGE4 fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style STAGE5 fill:#e17055,stroke:#fab1a0,color:#fff
    style STAGE6 fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style STAGE7 fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 6. 임베딩 듀얼 전략 워크플로우

```mermaid
flowchart LR
    subgraph TEXT_EMBED["텍스트 임베딩 (384차원)"]
        TC["TextChunk"]
        SE["Sentence Embedding\n(LanceDB 모델)"]
        LANCE["LanceDB Table"]
        TC -->|"문장 단위"| SE -->|"저장"| LANCE
    end

    subgraph ENTITY_EMBED["엔티티 임베딩 (23차원)"]
        ES["Entity 시퀀스\n(UID 리스트)"]
        SG["Skip-gram\n(Word2Vec)"]
        W2V["Word2Vec Model"]
        ES -->|"학습"| SG -->|"저장"| W2V
    end

    subgraph USAGE["활용"]
        VS["벡터 유사도 검색\n(질문 → Chunk)"]
        SE_EXP["시맨틱 확장\n(엔티티 → 이웃 엔티티)"]
    end

    LANCE -->|"Stage 1"| VS
    W2V -->|"Stage 4"| SE_EXP

    style TEXT_EMBED fill:#0984e3,stroke:#74b9ff,color:#fff
    style ENTITY_EMBED fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style USAGE fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 7. 체크포인트 기반 파이프라인 워크플로우

```mermaid
stateDiagram-v2
    [*] --> Phase1_ER: 1_er.py 실행

    Phase1_ER: Phase 1 - Entity Resolution
    Phase1_ER --> Checkpoint1: 저장
    Checkpoint1: ER 결과 (JSONL)

    Checkpoint1 --> Phase2_Sem: 2_sem.py 실행
    Phase2_Sem: Phase 2 - Semantic Layer
    Phase2_Sem --> Checkpoint2: 저장
    Checkpoint2: Thesaurus (TTL)\nEntityStore (JSON)\nERKG (JSON)

    Checkpoint2 --> Phase3_Parse: 3_parse.py 실행
    Phase3_Parse: Phase 3 - Content Parsing
    Phase3_Parse --> Checkpoint3: 저장
    Checkpoint3: EntityStore (JSON)\nVectors (TXT)\nLexical Graph (JSON)\nERKG (JSON)\nLanceDB (벡터)

    Checkpoint3 --> Phase4_HITL: 수동 큐레이션
    Phase4_HITL: Phase 4 - Human-in-the-Loop
    Phase4_HITL --> Checkpoint3: 수정된 엔티티 저장

    Checkpoint3 --> Phase5_Embed: 5_embed.py 실행
    Phase5_Embed: Phase 5 - Embeddings
    Phase5_Embed --> Checkpoint5: 저장
    Checkpoint5: Word2Vec (W2V)\n정제된 ERKG (JSON)\n정제된 Lexical Graph (JSON)

    Checkpoint5 --> Phase6_Vis: 6_vis.py 실행
    Phase6_Vis: Phase 6 - Visualization
    Phase6_Vis --> OutputVis: HTML 시각화

    Checkpoint5 --> Phase7_RAG: 7_errag.py 실행
    Phase7_RAG: Phase 7 - GraphRAG
    Phase7_RAG --> OutputQA: Q&A 서비스

    Checkpoint5 --> Phase8_App: app.py 실행
    Phase8_App: Streamlit App
    Phase8_App --> OutputApp: 웹 대시보드

    note right of Checkpoint1: 재실행 시\n이 단계부터 시작 가능
    note right of Checkpoint2: 재실행 시\n이 단계부터 시작 가능
    note right of Checkpoint3: 재실행 시\n이 단계부터 시작 가능
    note right of Checkpoint5: 재실행 시\n이 단계부터 시작 가능
```

---

## 8. Observability 워크플로우

```mermaid
flowchart TD
    subgraph MONITORING["모니터링 계층"]
        direction TB

        subgraph PROFILING["성능 프로파일링"]
            PYINST["pyinstrument\nCall Stack 샘플링"]
            PSUTIL["psutil\n메모리 사용량"]
            PROF_REPORT["프로파일 리포트\n(콜 트리 + RSS)"]
            PYINST --> PROF_REPORT
            PSUTIL --> PROF_REPORT
        end

        subgraph LLM_OBS["LLM Observability"]
            OPIK_TRACE["Opik Tracing\n(TracedCallback)"]
            DSPY_LOG["DSPy 호출 로그"]
            TOKEN_COUNT["토큰 사용량\n추적"]
            RESPONSE_TIME["응답 시간\n측정"]

            OPIK_TRACE --> OPIK_DASH["Opik Dashboard\n(http://localhost:5173)"]
            DSPY_LOG --> OPIK_DASH
            TOKEN_COUNT --> OPIK_DASH
            RESPONSE_TIME --> OPIK_DASH
        end

        subgraph USER_FB["사용자 피드백"]
            STAR_RATING["별점 평가\n(1~5점)"]
            TRACE_LINK["트레이스 ID\n연결"]
            STAR_RATING --> OPIK_DASH
            TRACE_LINK --> OPIK_DASH
        end

        subgraph APP_ANALYTICS["앱 분석"]
            CHUNK_DIST["Chunk 거리\n분포 차트"]
            ANCHOR_VIS["앵커 노드\n그래프"]
            PERF_CHART["성능 추이\n차트"]
        end
    end

    style PROFILING fill:#e17055,stroke:#fab1a0,color:#fff
    style LLM_OBS fill:#0984e3,stroke:#74b9ff,color:#fff
    style USER_FB fill:#00b894,stroke:#55efc4,color:#fff
    style APP_ANALYTICS fill:#6c5ce7,stroke:#a29bfe,color:#fff
```

---

## 9. 에러 처리 및 복구 워크플로우

```mermaid
flowchart TD
    ERROR["에러 발생"]

    ERROR --> CHECK_TYPE{"에러 유형?"}

    CHECK_TYPE -->|"네트워크 에러\n(Senzing/Ollama)"| NET_ERR
    CHECK_TYPE -->|"파싱 에러\n(NLP)"| PARSE_ERR
    CHECK_TYPE -->|"그래프 에러\n(중복 노드)"| GRAPH_ERR
    CHECK_TYPE -->|"파일 I/O 에러"| IO_ERR

    subgraph NET_ERR["네트워크 에러 처리"]
        NET1["gRPC 연결 확인"]
        NET2["서버 상태 확인"]
        NET3["재연결 시도"]
    end

    subgraph PARSE_ERR["파싱 에러 처리"]
        PARSE1["scrub_text() 정제"]
        PARSE2["Unicode 정규화"]
        PARSE3["None 반환 (건너뛰기)"]
    end

    subgraph GRAPH_ERR["그래프 에러 처리"]
        GRAPH1["중복 노드 감지\n(icecream 경고)"]
        GRAPH2["update=True 시\n속성 병합"]
        GRAPH3["stop=True 시\n프로세스 중지"]
    end

    subgraph IO_ERR["파일 I/O 에러 처리"]
        IO1["체크포인트에서\n재시작"]
        IO2["이전 단계\n출력 확인"]
    end

    NET_ERR --> RETRY["체크포인트에서\n파이프라인 재시작"]
    PARSE_ERR --> CONTINUE["다음 항목 처리 계속"]
    GRAPH_ERR --> DECIDE{"중지/계속\n결정"}
    IO_ERR --> RETRY

    style NET_ERR fill:#e17055,stroke:#fab1a0,color:#fff
    style PARSE_ERR fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style GRAPH_ERR fill:#0984e3,stroke:#74b9ff,color:#fff
    style IO_ERR fill:#e17055,stroke:#fab1a0,color:#fff
```

이 문서는 Strwythura의 사용자 관점 및 데이터 관점에서의 워크플로우를 상세히 분석한 자료입니다.
