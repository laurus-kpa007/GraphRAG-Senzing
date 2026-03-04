# GraphRAG-Senzing 블록 다이어그램 및 시퀀스 다이어그램

> **프로젝트:** GraphRAG-Senzing (Agentic GraphRAG Pipeline)
> **최종 수정일:** 2026-03-04

---

## 1. 시스템 아키텍처 블록 다이어그램

```mermaid
block-beta
    columns 5

    block:INPUT:1
        columns 1
        A["워드 파일\n(.docx)"]
        B["텍스트 파일\n(.txt)"]
        C["마크다운 파일\n(.md)"]
    end

    block:PROCESSING:3
        columns 3
        D["DocumentLoader\n(python-docx/chardet)"]
        E["Text Chunking\n(1024자 단위)"]
        F["BGE-M3 Embedding\n(Ollama, 1024차원)"]
        G["spaCy NER\n(한국어/영어)"]
        H["Keyword Search\n(substring matching)"]
        I["Graph Search\n(entity co-occurrence)"]
        J["Vector Search\n(LanceDB ANN)"]
        K["Result Merge\n(UID 중복제거)"]
        L["LLM 응답 생성\n(Ollama /api/chat)"]
    end

    block:OUTPUT:1
        columns 1
        M["엔티티 저장소\n(JSONL)"]
        N["벡터 저장소\n(LanceDB)"]
        O["Q&A 응답"]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    E --> G
    F --> N
    G --> M
    J --> K
    H --> K
    I --> K
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
        CLI["CLI Runner\n(run_pipeline.py)"]
    end

    subgraph APPLICATION["애플리케이션 계층"]
        PIPELINE["AgenticPipeline\n(pipeline.py)"]
    end

    subgraph DOMAIN["도메인 계층"]
        LOADER["DocumentLoader\n(loaders.py)"]
        EMBEDDER["OllamaEmbedding\n(embeddings.py)"]
        LLM["OllamaLLM\n(embeddings.py)"]
    end

    subgraph INFRASTRUCTURE["인프라 계층"]
        LANCE["LanceDB\n(벡터 저장소)"]
        ENT_FILE["Entity Store\n(JSONL 파일)"]
        SPACY["spaCy\n(NER 엔진)"]
    end

    subgraph EXTERNAL["외부 서비스"]
        OLLAMA["Ollama Server\n(/api/embed, /api/chat)"]
    end

    subgraph OPTIONAL["선택적 (strwythura)"]
        STRW["strwythura.Workflow"]
    end

    APP --> PIPELINE
    CLI --> PIPELINE

    PIPELINE --> LOADER
    PIPELINE --> EMBEDDER
    PIPELINE --> LLM
    PIPELINE --> LANCE
    PIPELINE --> ENT_FILE
    PIPELINE --> SPACY
    PIPELINE -.-> STRW

    EMBEDDER --> OLLAMA
    LLM --> OLLAMA

    style PRESENTATION fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style APPLICATION fill:#0984e3,stroke:#74b9ff,color:#fff
    style DOMAIN fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style INFRASTRUCTURE fill:#00b894,stroke:#55efc4,color:#fff
    style EXTERNAL fill:#e17055,stroke:#fab1a0,color:#fff
    style OPTIONAL fill:#636e72,stroke:#b2bec3,color:#dfe6e9
```

### 2.2 데이터 저장소 블록 구조

```mermaid
graph LR
    subgraph PERSISTENCE["데이터 저장소"]
        direction TB
        subgraph FILES["파일 기반"]
            ENTJSON["Entity Store\n(data/output/ent.json, JSONL)"]
            GRAPHJSON["ERKG / Lex Graph\n(data/output/erkg.json, lex.json)"]
            CONFIG["설정 파일\n(config.toml, domain.json)"]
        end

        subgraph DB["데이터베이스"]
            LANCE["LanceDB\n(data/lancedb/, 벡터 임베딩)"]
        end

        subgraph MEMORY["인메모리"]
            CHUNKS["_chunks: list~dict~\n(uid, source, text, vector)"]
            ENTITIES["_entities: list~dict~\n(uid, text, label, count)"]
        end
    end

    style FILES fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style DB fill:#0984e3,stroke:#74b9ff,color:#fff
    style MEMORY fill:#6c5ce7,stroke:#a29bfe,color:#fff
```

---

## 3. 시퀀스 다이어그램

### 3.1 전체 파이프라인 실행 시퀀스 (run)

```mermaid
sequenceDiagram
    actor User as 사용자
    participant CLI as run_pipeline.py
    participant AP as AgenticPipeline
    participant DL as DocumentLoader
    participant OE as OllamaEmbedding
    participant LDB as LanceDB
    participant NLP as spaCy NLP

    Note over User,NLP: Phase 0 - 사전 확인
    User->>CLI: python run_pipeline.py data/documents/
    CLI->>AP: AgenticPipeline(config.toml)
    AP->>OE: is_available()
    OE->>OE: GET /api/tags (모델 확인)
    OE-->>AP: True/False

    Note over User,NLP: Phase 1 - 초기화
    AP->>AP: initialize()
    AP->>LDB: lancedb.connect("data/lancedb")
    LDB-->>AP: DB 연결

    Note over User,NLP: Phase 2 - 문서 로딩
    AP->>DL: load_documents(["data/documents/"])
    loop 각 파일
        DL->>DL: 포맷 감지 (.docx/.txt/.md)
        DL->>DL: 텍스트 추출 + 테이블 변환
        DL->>DL: _scrub() 정제 (NFC 정규화)
        DL-->>AP: paragraphs[]
    end

    Note over User,NLP: Phase 3 - 청킹 & 임베딩
    AP->>AP: make_chunks(paragraphs, max=1024)
    loop 각 배치 (8개씩)
        AP->>OE: embed_batch(texts)
        OE->>OE: POST /api/embed (BGE-M3)
        OE-->>AP: vectors[1024-dim]
        AP->>LDB: table.add(rows)
    end

    Note over User,NLP: Phase 4 - NLP 엔티티 추출
    alt strwythura 사용 가능
        AP->>AP: _run_strwythura_nlp()
    else standalone spaCy
        AP->>NLP: nlp(chunk_text)
        NLP-->>AP: doc.ents (NER)
        AP->>AP: 한국어 NOUN/PROPN 추가 추출
        AP->>AP: ent.json 저장 (JSONL)
    end

    AP-->>CLI: summary (문서 수, 청크 수)
    CLI-->>User: Pipeline Ready

    Note over User,NLP: Phase 5 - 대화형 Q&A
    AP->>AP: interactive()
    loop 사용자 질문
        User->>AP: question
        AP->>AP: query(question, conversation_history)
        AP-->>User: answer
    end
```

### 3.2 하이브리드 GraphRAG 질의응답 시퀀스 (query)

```mermaid
sequenceDiagram
    actor User as 사용자
    participant AP as AgenticPipeline
    participant OE as OllamaEmbedding
    participant LDB as LanceDB
    participant KW as _keyword_search
    participant GS as _graph_search
    participant EC as _get_entity_context
    participant LLM as OllamaLLM

    User->>AP: query("질문", conversation_history)

    Note over AP,LDB: Step 1 - 벡터 검색 (Semantic)
    AP->>OE: embed_text("질문")
    OE-->>AP: q_vec[1024]
    AP->>LDB: table.search(q_vec).limit(11)
    LDB-->>AP: vector_results[]

    Note over AP,KW: Step 2 - 키워드 검색 (Term Matching)
    AP->>KW: _keyword_search("질문", top_k=5)
    KW->>KW: 불용어 필터링 (한국어)
    KW->>KW: 전체 청크 순차 스캔
    KW->>KW: substring match + score
    KW-->>AP: keyword_results[]

    Note over AP,GS: Step 3 - 결과 병합 (UID 중복제거)
    AP->>AP: seen_uids로 중복제거
    AP->>AP: 벡터 우선 → 키워드 추가

    Note over AP,GS: Step 4 - 그래프 확장 (Entity Co-occurrence)
    AP->>GS: _graph_search("질문", initial_results[:5])
    GS->>GS: 초기 청크에서 엔티티 추출
    GS->>GS: 전체 청크에서 공유 엔티티 ≥ 2개인 청크 탐색
    GS-->>AP: graph_results[] (최대 5개)

    Note over AP,EC: Step 5 - 엔티티 컨텍스트 보강
    AP->>EC: _get_entity_context("질문", chunks)
    EC->>EC: ent.json 로드
    EC->>EC: 질문/청크 내 엔티티 매칭
    EC-->>AP: "[Related Entities]\n- 엔티티 [라벨] (mentions: N)"

    Note over AP,LLM: Step 6 - LLM 응답 생성
    AP->>AP: 언어 감지 (ko/en)
    AP->>AP: 시스템 프롬프트 구성 (날짜/시간 + 추론 규칙)
    AP->>AP: conversation_history 추가 (최근 N턴)
    AP->>LLM: chat(messages)
    LLM->>LLM: POST /api/chat (gemma3)
    LLM-->>AP: answer

    AP-->>User: {answer, sources, num_chunks, elapsed_sec}
```

### 3.3 문서 로딩 상세 시퀀스

```mermaid
sequenceDiagram
    participant AP as AgenticPipeline
    participant DL as DocumentLoader
    participant DOCX as DocxLoader
    participant TXT as TextLoader
    participant MD as MarkdownLoader

    AP->>DL: load(file_path)
    DL->>DL: suffix = path.suffix.lower()

    alt .docx 파일
        DL->>DOCX: _load_docx(path)
        DOCX->>DOCX: Document(path) (python-docx)
        loop 각 element in doc.element.body
            alt CT_P (단락)
                DOCX->>DOCX: para.text 추출
                DOCX->>DOCX: 이미지 설명 추출 (pic:cNvPr)
            else CT_Tbl (테이블)
                DOCX->>DOCX: _extract_table_text()
                DOCX->>DOCX: 헤더 감지 → [Row N] 형식 변환
            end
        end
        DOCX-->>DL: paragraphs[]

    else .txt 파일
        DL->>TXT: _load_text(path)
        TXT->>TXT: chardet.detect(raw) 인코딩 감지
        TXT->>TXT: KO_ENCODINGS 체인 시도
        TXT->>TXT: "\n\n" 기준 단락 분리
        TXT-->>DL: paragraphs[]

    else .md 파일
        DL->>MD: _load_markdown(path)
        MD->>MD: 코드블록 제거 (```...```)
        MD->>MD: 마크다운 문법 정제 (헤더, 링크, 볼드 등)
        MD->>MD: "\n\n" 기준 단락 분리
        MD-->>DL: paragraphs[]
    end

    DL->>DL: _scrub(p) for each paragraph
    Note over DL: NFC 정규화, 공백 정리,<br/>스마트 인용부호 변환
    DL-->>AP: cleaned paragraphs[]
```

### 3.4 Streamlit App 사용자 인터랙션 시퀀스

```mermaid
sequenceDiagram
    actor User as 사용자
    participant ST as Streamlit UI
    participant App as app.py
    participant AP as AgenticPipeline

    User->>ST: 앱 접속 (localhost:8501)
    ST->>App: 페이지 렌더링
    App->>App: config.toml 로드
    App-->>ST: 사이드바 (모델 정보, 상태)

    Note over User,AP: Tab 1 - 문서 업로드 & 파이프라인
    User->>ST: 파일 업로드 (.docx/.txt/.md)
    User->>ST: "파이프라인 실행" 클릭
    ST->>App: 업로드 파일 → data/uploads/ 저장

    App->>AP: AgenticPipeline()
    App->>AP: check_prerequisites()
    App->>AP: initialize()
    App->>AP: load_documents(paths)
    App->>AP: embed_and_store(documents)
    App->>AP: run_nlp_pipeline(documents)
    AP-->>App: pipeline ready
    App->>ST: session_state.pipeline = pipeline

    Note over User,AP: Tab 2 - Q&A 채팅
    User->>ST: 질문 입력
    ST->>App: question
    App->>AP: query(question, conversation_history=messages)
    AP-->>App: {answer, sources, num_chunks, elapsed_sec}
    App->>ST: 답변 표시 + 메타데이터
    App->>ST: session_state.messages 업데이트

    Note over User,AP: Tab 3 - 시스템 상태
    User->>ST: "상태 확인" 클릭
    ST->>AP: check_prerequisites()
    AP-->>ST: {ollama_server, llm_model, embed_model}
    ST->>ST: 엔티티/벡터 저장소 상태 표시
```

---

## 4. 하이브리드 검색 파이프라인 블록 다이어그램

```mermaid
graph TB
    QUESTION["사용자 질문"]

    subgraph RETRIEVAL["3단계 검색"]
        direction TB

        subgraph VEC_SEARCH["1. 벡터 검색 (Semantic)"]
            VS_Q["질문 임베딩\n(BGE-M3, 1024-dim)"]
            VS_S["LanceDB ANN 검색"]
            VS_R["관련 Chunks\n(top_k=11)"]
            VS_Q --> VS_S --> VS_R
        end

        subgraph KW_SEARCH["2. 키워드 검색 (Term Matching)"]
            KW_STOP["한국어 불용어 필터링"]
            KW_SCAN["전체 청크 순차 스캔\nsubstring match"]
            KW_RANK["점수 기반 정렬"]
            KW_STOP --> KW_SCAN --> KW_RANK
        end

        subgraph GRAPH_SEARCH["3. 그래프 검색 (Entity Co-occurrence)"]
            GS_ENT["초기 청크에서\n엔티티 추출"]
            GS_FIND["공유 엔티티 ≥ 2개인\n추가 청크 탐색"]
            GS_TOP["상위 5개 반환"]
            GS_ENT --> GS_FIND --> GS_TOP
        end
    end

    subgraph MERGE["결과 병합"]
        DEDUP["UID 중복 제거"]
        PRIORITY["우선순위: 벡터 > 키워드 > 그래프"]
        LIMIT["top_k 제한 (기본 11)"]
        DEDUP --> PRIORITY --> LIMIT
    end

    subgraph AUGMENT["컨텍스트 보강"]
        ENT_CTX["엔티티 컨텍스트\n(ent.json 매칭)"]
        TIME_CTX["현재 날짜/시간 주입"]
        REASON["추론 규칙 프롬프트"]
    end

    subgraph GENERATION["응답 생성"]
        LANG["언어 감지\n(한국어/영어)"]
        SYS_PROMPT["시스템 프롬프트 구성"]
        HISTORY["대화 이력 추가\n(최근 N턴)"]
        OLLAMA_CALL["Ollama /api/chat\n(gemma3)"]
        RESPONSE["최종 응답"]
        LANG --> SYS_PROMPT --> HISTORY --> OLLAMA_CALL --> RESPONSE
    end

    QUESTION --> VEC_SEARCH
    QUESTION --> KW_SEARCH

    VS_R --> MERGE
    KW_RANK --> MERGE
    MERGE --> GRAPH_SEARCH
    GS_TOP --> MERGE

    LIMIT --> AUGMENT
    AUGMENT --> GENERATION

    style RETRIEVAL fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style MERGE fill:#0984e3,stroke:#74b9ff,color:#fff
    style AUGMENT fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style GENERATION fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 5. NLP 엔티티 추출 흐름 (standalone spaCy)

```mermaid
flowchart TD
    INPUT["문서 청크 리스트"]

    subgraph SPACY_LOAD["spaCy 모델 로딩"]
        TRY1["설정된 모델 시도\n(ko_core_news_lg)"]
        TRY2["한국어 모델 fallback\n(ko_core_news_md/sm)"]
        TRY3["영어 모델 fallback\n(en_core_web_md/sm)"]
        TRY4["Blank 모델\n(xx + sentencizer)"]
        TRY1 -->|실패| TRY2 -->|실패| TRY3 -->|실패| TRY4
    end

    subgraph PER_CHUNK["청크별 처리"]
        NER_EXT["doc.ents 추출\n(Named Entity Recognition)"]
        LANG_DET["언어 감지\n_detect_language()"]
        KO_NOUN["한국어: NOUN/PROPN\n토큰 추가 추출"]
        NORM["정규화\n(한국어: 원문, 영어: lowercase)"]
    end

    subgraph OUTPUT["출력"]
        ENT_DICT["entities dict\n{text, label, count, lemma_key}"]
        ENT_FILE["data/output/ent.json\n(JSONL, ensure_ascii=False)"]
    end

    INPUT --> SPACY_LOAD --> PER_CHUNK
    NER_EXT --> NORM
    LANG_DET -->|ko| KO_NOUN --> NORM
    NORM --> ENT_DICT --> ENT_FILE

    style SPACY_LOAD fill:#e17055,stroke:#fab1a0,color:#fff
    style PER_CHUNK fill:#0984e3,stroke:#74b9ff,color:#fff
    style OUTPUT fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 6. LLM 프롬프트 구조

```mermaid
graph TD
    subgraph SYSTEM_PROMPT["시스템 프롬프트"]
        TIME["현재 날짜/시간\n2026-03-04 09:15:00 (Tuesday)"]
        ROLE["역할 정의\n지식이 풍부한 도우미"]
        RULES["중요 규칙 (6개)\n테이블 행 구분, 컨텍스트 기반"]
        REASONING["추론 규칙 (3개)\n단계별 계산, 논리적 추론, 직접 계산"]
    end

    subgraph USER_PROMPT["사용자 프롬프트"]
        CONTEXT["Context:\n검색된 청크 텍스트\n---\n[Related Entities]\n엔티티 목록"]
        QUESTION["Question: 사용자 질문"]
        ANSWER_TAG["Answer:"]
    end

    subgraph MESSAGES["Chat Messages 배열"]
        MSG_SYS["system: 시스템 프롬프트"]
        MSG_HIST["user/assistant: 대화 이력\n(최근 max_history_turns턴)"]
        MSG_USER["user: Context + Question"]
    end

    SYSTEM_PROMPT --> MSG_SYS
    USER_PROMPT --> MSG_USER
    MSG_SYS --> MESSAGES
    MSG_HIST --> MESSAGES
    MSG_USER --> MESSAGES

    style SYSTEM_PROMPT fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style USER_PROMPT fill:#0984e3,stroke:#74b9ff,color:#fff
    style MESSAGES fill:#00b894,stroke:#55efc4,color:#fff
```
