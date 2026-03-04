# GraphRAG-Senzing 사용자 및 데이터 워크플로우

> **프로젝트:** GraphRAG-Senzing (Agentic GraphRAG Pipeline)
> **최종 수정일:** 2026-03-04

---

## 1. 사용자 워크플로우 전체 흐름

```mermaid
journey
    title GraphRAG-Senzing 사용자 워크플로우
    section 환경 설정
      Ollama 설치 및 서버 시작: 3: 사용자
      BGE-M3 임베딩 모델 다운로드: 3: 사용자
      gemma3 LLM 모델 다운로드: 3: 사용자
      pip install 의존성 설치: 3: 사용자
      spaCy 모델 다운로드: 2: 사용자
    section 문서 준비
      문서를 data/documents/에 복사: 4: 사용자
      config.toml 설정 확인: 4: 사용자
    section 파이프라인 실행
      run_pipeline.py 실행: 5: 시스템
      문서 로딩 + 청킹: 5: 시스템
      BGE-M3 임베딩 + LanceDB 저장: 4: 시스템
      NLP 엔티티 추출 (spaCy): 4: 시스템
    section 활용
      CLI 대화형 Q&A: 5: 사용자
      Streamlit 웹 UI Q&A: 5: 사용자
```

---

## 2. 사용자 역할별 워크플로우

```mermaid
graph TB
    subgraph ROLES["사용자 역할"]
        ADMIN["관리자/개발자"]
        EU["최종 사용자"]
    end

    subgraph ADMIN_TASKS["관리자 작업"]
        A1["Ollama 서버 설정\n(IP, 포트, 모델)"]
        A2["config.toml 설정\n(LLM, 임베딩, 청크 크기)"]
        A3["문서 데이터 관리\n(data/documents/)"]
        A4["파이프라인 실행\n(run_pipeline.py)"]
        A5["시스템 모니터링\n(프로파일링, 로그)"]
    end

    subgraph EU_TASKS["최종 사용자 작업"]
        E1["Streamlit UI 접속\n(localhost:8501)"]
        E2["문서 업로드\n(.docx, .txt, .md)"]
        E3["파이프라인 실행\n(버튼 클릭)"]
        E4["Q&A 채팅\n(한국어/영어)"]
        E5["시스템 상태 확인"]
    end

    ADMIN --> ADMIN_TASKS
    EU --> EU_TASKS

    ADMIN_TASKS --> EU_TASKS

    style ROLES fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style ADMIN_TASKS fill:#0984e3,stroke:#74b9ff,color:#fff
    style EU_TASKS fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 3. 데이터 워크플로우 상세

### 3.1 전체 데이터 라이프사이클

```mermaid
flowchart TB
    subgraph INPUT_LAYER["데이터 입력 계층"]
        direction LR
        DOCX["워드 파일\n(.docx)"]
        TXT["텍스트 파일\n(.txt)"]
        MD["마크다운 파일\n(.md)"]
    end

    subgraph INGEST["데이터 수집 계층"]
        direction LR
        DOCX_LOAD["DocxLoader\n(python-docx)"]
        TXT_LOAD["TextLoader\n(chardet 인코딩 감지)"]
        MD_LOAD["MarkdownLoader\n(문법 제거)"]
    end

    subgraph TRANSFORM["데이터 변환 계층"]
        direction TB

        subgraph TEXT_TRANSFORM["텍스트 변환"]
            SCRUB["텍스트 정제\n(NFC 정규화, 공백 정리)"]
            CHUNK_OP["청킹\n(max 1024 chars)"]
        end

        subgraph EMBED_TRANSFORM["임베딩 변환"]
            BGE["BGE-M3 임베딩\n(Ollama /api/embed)"]
            VEC["1024차원 벡터 생성"]
        end

        subgraph NLP_TRANSFORM["NLP 변환"]
            SPACY_NER["spaCy NER\n(개체명 인식)"]
            KO_NOUN["한국어 명사 추출\n(NOUN/PROPN)"]
            LANG_DET["언어 감지\n(한국어/영어)"]
        end
    end

    subgraph STORE["데이터 저장 계층"]
        direction LR
        LANCE_STORE["LanceDB\n(data/lancedb/)"]
        ENT_STORE["Entity Store\n(data/output/ent.json)"]
        CHUNKS_MEM["인메모리 청크 리스트\n(_chunks[])"]
    end

    subgraph QUERY["데이터 검색 계층"]
        direction LR
        VEC_SEARCH["벡터 검색\n(ANN)"]
        KW_SEARCH["키워드 검색\n(substring match)"]
        GRAPH_SEARCH["그래프 검색\n(entity co-occurrence)"]
    end

    subgraph OUTPUT_LAYER["데이터 출력 계층"]
        direction LR
        ANSWER["Q&A 응답\n(gemma3 LLM)"]
        METADATA["메타데이터\n(sources, elapsed, chunks)"]
    end

    INPUT_LAYER --> INGEST
    INGEST --> TRANSFORM
    TRANSFORM --> STORE
    STORE --> QUERY
    QUERY --> OUTPUT_LAYER

    DOCX --> DOCX_LOAD
    TXT --> TXT_LOAD
    MD --> MD_LOAD

    DOCX_LOAD --> SCRUB
    TXT_LOAD --> SCRUB
    MD_LOAD --> SCRUB

    SCRUB --> CHUNK_OP
    CHUNK_OP --> BGE --> VEC --> LANCE_STORE
    CHUNK_OP --> SPACY_NER --> ENT_STORE
    CHUNK_OP --> CHUNKS_MEM
    LANG_DET --> KO_NOUN --> ENT_STORE

    LANCE_STORE --> VEC_SEARCH
    CHUNKS_MEM --> KW_SEARCH
    ENT_STORE --> GRAPH_SEARCH

    VEC_SEARCH --> ANSWER
    KW_SEARCH --> ANSWER
    GRAPH_SEARCH --> ANSWER

    style INPUT_LAYER fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style INGEST fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style TRANSFORM fill:#0984e3,stroke:#74b9ff,color:#fff
    style STORE fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style QUERY fill:#e17055,stroke:#fab1a0,color:#fff
    style OUTPUT_LAYER fill:#00b894,stroke:#55efc4,color:#fff
```

### 3.2 데이터 포맷 변환 흐름

```mermaid
flowchart LR
    subgraph FORMATS["데이터 포맷 변환"]
        DOCX_IN[".docx\n(python-docx)"]
        TXT_IN[".txt\n(chardet)"]
        MD_IN[".md\n(regex)"]
        PARA["paragraphs[]\n(Python list)"]
        CHUNKS["chunks[]\n(max 1024자)"]
        VECTORS["vectors[]\n(1024-dim float32)"]
        LANCE_TBL["LanceDB Table\n(uid, source, text, vector)"]
        ENT_JSONL["ent.json\n(JSONL, UTF-8)"]
        ANSWER_OUT["JSON Response\n{answer, sources, chunks}"]
    end

    DOCX_IN -->|"Paragraph + Table 추출"| PARA
    TXT_IN -->|"\\n\\n 기준 분리"| PARA
    MD_IN -->|"문법 제거 + 분리"| PARA
    PARA -->|"make_chunks()"| CHUNKS
    CHUNKS -->|"BGE-M3 embed"| VECTORS
    VECTORS -->|"table.add()"| LANCE_TBL
    CHUNKS -->|"spaCy NER"| ENT_JSONL
    LANCE_TBL -->|"table.search()"| ANSWER_OUT
    ENT_JSONL -->|"entity context"| ANSWER_OUT

    style FORMATS fill:#1b263b,stroke:#415a77,color:#e0e1dd
```

---

## 4. 핵심 데이터 처리 워크플로우

### 4.1 텍스트 청킹 워크플로우

```mermaid
flowchart TD
    FILE["입력 파일\n(.docx / .txt / .md)"]
    LOAD["DocumentLoader.load()"]
    PARAS["paragraphs[] 리스트"]

    subgraph CHUNKING["청킹 프로세스 (make_chunks)"]
        CHECK_SIZE{"현재 버퍼 +\n새 단락 >\n1024자?"}
        ADD_PARA["버퍼에 단락 추가"]
        FLUSH["현재 버퍼를\nchunk로 확정"]
        NEW_BUF["새 버퍼 시작"]
        FINAL["마지막 버퍼\nchunk로 확정"]
    end

    CHUNK_OUT["chunks[] 리스트"]

    subgraph PER_CHUNK["각 Chunk 처리"]
        ASSIGN_UID["UID 할당 (순차)"]
        EMBED["BGE-M3 임베딩\n(1024차원, Ollama)"]
        LANCE_ADD["LanceDB table.add()"]
        MEM_ADD["_chunks[] 리스트에 추가"]
    end

    FILE --> LOAD --> PARAS

    PARAS --> CHECK_SIZE
    CHECK_SIZE -->|No| ADD_PARA --> CHECK_SIZE
    CHECK_SIZE -->|Yes| FLUSH --> NEW_BUF --> CHECK_SIZE
    ADD_PARA -->|마지막| FINAL

    FLUSH --> CHUNK_OUT
    FINAL --> CHUNK_OUT

    CHUNK_OUT --> PER_CHUNK
    ASSIGN_UID --> EMBED --> LANCE_ADD
    LANCE_ADD --> MEM_ADD

    style CHUNKING fill:#0984e3,stroke:#74b9ff,color:#fff
    style PER_CHUNK fill:#6c5ce7,stroke:#a29bfe,color:#fff
```

### 4.2 워드 파일 테이블 처리 워크플로우

```mermaid
flowchart TD
    TABLE["워드 문서 테이블\n(CT_Tbl)"]

    subgraph DETECT["헤더 감지"]
        CHECK{"첫 행 셀이\n모두 짧고 비어있지 않은가?"}
        HAS_HEADER["헤더 있음"]
        NO_HEADER["헤더 없음"]
    end

    subgraph WITH_HEADER["헤더가 있는 경우"]
        INTRO["[Table: N rows with columns: 컬럼1, 컬럼2, ...]"]
        ROW_FORMAT["[Row 1] 컬럼1: 값1 | 컬럼2: 값2 | ..."]
        BLANK["빈 줄 (행 구분)"]
    end

    subgraph NO_HEADER_FMT["헤더가 없는 경우"]
        PLAIN_INTRO["[Table: N rows]"]
        PLAIN_ROW["Row 1: 셀1 | 셀2 | ..."]
    end

    TABLE --> DETECT
    CHECK -->|Yes| HAS_HEADER --> WITH_HEADER
    CHECK -->|No| NO_HEADER --> NO_HEADER_FMT

    style DETECT fill:#e17055,stroke:#fab1a0,color:#fff
    style WITH_HEADER fill:#00b894,stroke:#55efc4,color:#fff
    style NO_HEADER_FMT fill:#0984e3,stroke:#74b9ff,color:#fff
```

### 4.3 엔티티 추출 워크플로우 (standalone spaCy)

```mermaid
flowchart TD
    CHUNKS["문서 청크 리스트"]
    SPACY_LOAD["spaCy 모델 로딩\n(ko_core_news_lg 우선)"]

    subgraph PER_CHUNK["청크별 처리"]
        DOC_PARSE["nlp(chunk_text)\nDoc 객체 생성"]

        subgraph NER["NER 엔티티 추출"]
            ENT_LOOP["doc.ents 순회"]
            ENT_FILTER["길이 > 1 필터"]
            ENT_NORM["정규화\n(한국어: 원문, 영어: lowercase)"]
            ENT_COUNT["count += 1\n(빈도 카운트)"]
        end

        subgraph KO_EXTRA["한국어 추가 추출"]
            LANG_CHECK{"_detect_language()\n한국어 비율 > 30%?"}
            TOKEN_LOOP["NOUN/PROPN 토큰 순회"]
            TOKEN_ADD["엔티티 사전에 추가"]
        end
    end

    subgraph SAVE["저장"]
        ENT_DICT["entities dict\n{uid, text, label, count, lemma_key}"]
        JSONL["data/output/ent.json\n(JSONL, ensure_ascii=False)"]
        MEM["_entities[] 리스트"]
    end

    CHUNKS --> SPACY_LOAD --> PER_CHUNK
    DOC_PARSE --> NER
    DOC_PARSE --> KO_EXTRA
    ENT_LOOP --> ENT_FILTER --> ENT_NORM --> ENT_COUNT
    LANG_CHECK -->|ko| TOKEN_LOOP --> TOKEN_ADD
    NER --> ENT_DICT
    KO_EXTRA --> ENT_DICT
    ENT_DICT --> JSONL
    ENT_DICT --> MEM

    style PER_CHUNK fill:#0984e3,stroke:#74b9ff,color:#fff
    style NER fill:#e17055,stroke:#fab1a0,color:#fff
    style KO_EXTRA fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style SAVE fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 5. GraphRAG 검색 워크플로우 상세

```mermaid
flowchart TD
    QUESTION["사용자 질문"]

    subgraph STAGE1["Stage 1: 벡터 검색"]
        Q_EMBED["질문 벡터화\n(BGE-M3, 1024-dim)"]
        LANCE_SEARCH["LanceDB ANN 검색\ntable.search(q_vec).limit(k)"]
        VEC_RESULTS["vector_results[]\n(거리 순 정렬)"]
        Q_EMBED --> LANCE_SEARCH --> VEC_RESULTS
    end

    subgraph STAGE2["Stage 2: 키워드 검색"]
        STOPWORD["한국어 불용어 필터링\n(은/는/이/가/을/를...)"]
        SPLIT["질문 split + 길이 > 1 필터"]
        SCAN["전체 _chunks[] 순차 스캔\nsubstring match"]
        KW_SCORE["score = 매칭 term 수"]
        KW_RESULTS["keyword_results[]\n(score 순 정렬)"]
        STOPWORD --> SPLIT --> SCAN --> KW_SCORE --> KW_RESULTS
    end

    subgraph STAGE3["Stage 3: 결과 병합"]
        MERGE_VEC["벡터 결과 추가\n(우선)"]
        MERGE_KW["키워드 결과 추가\n(UID 중복 제외)"]
        SEEN["seen_uids set"]
        MERGE_VEC --> SEEN
        MERGE_KW --> SEEN
    end

    subgraph STAGE4["Stage 4: 그래프 확장"]
        EXTRACT_ENT["초기 청크 상위 5개에서\n엔티티 추출"]
        FIND_COOCCUR["전체 청크에서\n공유 엔티티 ≥ 2개 탐색"]
        GRAPH_RESULTS["graph_results[]\n(overlap score 순, 최대 5개)"]
        EXTRACT_ENT --> FIND_COOCCUR --> GRAPH_RESULTS
    end

    subgraph STAGE5["Stage 5: 컨텍스트 조립"]
        JOIN_TEXT["청크 텍스트 결합\n(\\n\\n---\\n\\n 구분)"]
        ENT_CONTEXT["엔티티 컨텍스트 추가\n[Related Entities]"]
        FINAL_CTX["최종 컨텍스트"]
        JOIN_TEXT --> ENT_CONTEXT --> FINAL_CTX
    end

    subgraph STAGE6["Stage 6: LLM 응답"]
        LANG_DET["언어 감지 (ko/en)"]
        SYS_PROMPT["시스템 프롬프트 구성\n(날짜 + 규칙 + 추론)"]
        CONV_HIST["대화 이력 추가\n(최근 max_history_turns턴)"]
        CHAT_API["Ollama /api/chat\n(gemma3)"]
        FINAL_ANS["최종 응답\n{answer, sources, elapsed}"]
        LANG_DET --> SYS_PROMPT --> CONV_HIST --> CHAT_API --> FINAL_ANS
    end

    QUESTION --> STAGE1
    QUESTION --> STAGE2

    VEC_RESULTS --> STAGE3
    KW_RESULTS --> STAGE3

    SEEN --> STAGE4
    GRAPH_RESULTS --> SEEN

    SEEN --> STAGE5
    FINAL_CTX --> STAGE6

    style STAGE1 fill:#1b263b,stroke:#415a77,color:#e0e1dd
    style STAGE2 fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style STAGE3 fill:#0984e3,stroke:#74b9ff,color:#fff
    style STAGE4 fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style STAGE5 fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style STAGE6 fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 6. 대화 메모리 워크플로우

```mermaid
flowchart TD
    subgraph CONV_MEMORY["대화 메모리 관리"]
        Q1["Q1: 사용자 질문"]
        A1["A1: 시스템 응답"]
        Q2["Q2: 후속 질문"]
        A2["A2: 후속 응답 (이전 맥락 참조)"]

        HISTORY["conversation_history[]\n(role: user/assistant)"]
        TRIM["최근 max_history_turns턴만 유지\n(기본 5턴 = 10개 메시지)"]
        INJECT["messages[] 배열에 주입\n(system → history → user)"]

        Q1 --> HISTORY
        A1 --> HISTORY
        Q2 --> HISTORY
        A2 --> HISTORY
        HISTORY --> TRIM --> INJECT
    end

    subgraph COMMANDS["특수 명령"]
        CLEAR["'clear' → history 초기화"]
        QUIT["'quit' → 세션 종료"]
    end

    style CONV_MEMORY fill:#0984e3,stroke:#74b9ff,color:#fff
    style COMMANDS fill:#e17055,stroke:#fab1a0,color:#fff
```

---

## 7. 에러 처리 및 복구 워크플로우

```mermaid
flowchart TD
    ERROR["에러 발생"]

    ERROR --> CHECK_TYPE{"에러 유형?"}

    CHECK_TYPE -->|"Ollama 연결 실패\n(httpx.ConnectError)"| OLLAMA_ERR
    CHECK_TYPE -->|"모델 미설치\n(is_available=False)"| MODEL_ERR
    CHECK_TYPE -->|"문서 로딩 실패\n(FileNotFoundError)"| FILE_ERR
    CHECK_TYPE -->|"임베딩 실패\n(Empty vector)"| EMBED_ERR
    CHECK_TYPE -->|"spaCy 모델 없음\n(OSError)"| SPACY_ERR
    CHECK_TYPE -->|"LanceDB 스키마 불일치"| LANCE_ERR

    subgraph OLLAMA_ERR["Ollama 에러"]
        O1["ollama serve 실행 확인"]
        O2["api_base URL 확인\n(config.toml)"]
    end

    subgraph MODEL_ERR["모델 에러"]
        M1["ollama pull 모델명"]
        M2["ollama list로 확인"]
    end

    subgraph FILE_ERR["파일 에러"]
        F1["파일 경로 확인"]
        F2["인코딩 자동 감지\n(chardet + KO_ENCODINGS)"]
    end

    subgraph EMBED_ERR["임베딩 에러"]
        E1["[0.0] * dim 으로 fallback"]
        E2["로그 경고 출력"]
    end

    subgraph SPACY_ERR["spaCy 에러"]
        S1["한국어/영어 모델 순차 시도"]
        S2["blank('xx') + sentencizer fallback"]
        S3["--skip-nlp 옵션으로 건너뛰기"]
    end

    subgraph LANCE_ERR["LanceDB 에러"]
        L1["rm -rf data/lancedb/"]
        L2["파이프라인 재실행"]
    end

    style OLLAMA_ERR fill:#e17055,stroke:#fab1a0,color:#fff
    style MODEL_ERR fill:#e17055,stroke:#fab1a0,color:#fff
    style FILE_ERR fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style EMBED_ERR fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style SPACY_ERR fill:#0984e3,stroke:#74b9ff,color:#fff
    style LANCE_ERR fill:#e17055,stroke:#fab1a0,color:#fff
```

---

## 8. 프로파일링 워크플로우

```mermaid
flowchart TD
    subgraph PROFILING["성능 프로파일링 (선택적)"]
        CONFIG_CHECK{"config.toml\n[prof] use_pyinst = true?"}
        IMPORT_CHECK{"pyinstrument\n설치 여부?"}

        START["Profiler().start()\n파이프라인 시작 시"]
        RUN["파이프라인 전체 실행\n(load → embed → NLP)"]
        STOP["Profiler().stop()\n파이프라인 완료 시"]

        HTML_REPORT["data/output/profile_report.html\n(Call Stack 시각화)"]
        TEXT_LOG["로그 출력\n(Unicode Call Tree)"]
    end

    CONFIG_CHECK -->|Yes| IMPORT_CHECK
    CONFIG_CHECK -->|No| SKIP["프로파일링 건너뛰기"]
    IMPORT_CHECK -->|Yes| START --> RUN --> STOP
    IMPORT_CHECK -->|No| WARN["경고: pip install pyinstrument"]
    STOP --> HTML_REPORT
    STOP --> TEXT_LOG

    style PROFILING fill:#6c5ce7,stroke:#a29bfe,color:#fff
```
