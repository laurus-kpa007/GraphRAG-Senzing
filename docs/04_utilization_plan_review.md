# Strwythura 활용 계획 검토

> **분석 대상:** DerwenAI/strwythura v2.0.3
> **분석일:** 2026-02-27
> **활용 환경:**
> - **입력 소스:** 워드 파일(.docx), 텍스트 파일(.txt), 마크다운 파일(.md)
> - **LLM:** Ollama gemma3:27b
> - **임베딩 모델:** bona/bge-m3:latest

---

## 1. 활용 계획 개요

### 1.1 목표 아키텍처

```mermaid
graph TB
    subgraph INPUT_CUSTOM["커스텀 입력 소스"]
        DOCX["워드 파일\n(.docx)"]
        TXT["텍스트 파일\n(.txt)"]
        MD["마크다운 파일\n(.md)"]
    end

    subgraph PROCESSING["처리 파이프라인"]
        LOADER["문서 로더\n(커스텀)"]
        PIPELINE["Strwythura\n파이프라인"]
    end

    subgraph MODELS["모델 스택"]
        LLM["Ollama\ngemma3:27b"]
        EMBED["bona/bge-m3:latest\n(임베딩)"]
    end

    subgraph OUTPUT_CUSTOM["출력"]
        KG["Knowledge Graph"]
        QA["GraphRAG Q&A"]
        VIS_O["대화형 시각화"]
    end

    INPUT_CUSTOM --> LOADER --> PIPELINE
    MODELS --> PIPELINE
    PIPELINE --> OUTPUT_CUSTOM

    style INPUT_CUSTOM fill:#e17055,stroke:#fab1a0,color:#fff
    style PROCESSING fill:#0984e3,stroke:#74b9ff,color:#fff
    style MODELS fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style OUTPUT_CUSTOM fill:#00b894,stroke:#55efc4,color:#fff
```

### 1.2 원본 vs 커스텀 구성 비교

| 항목 | 원본 (Strwythura 기본) | 커스텀 (활용 계획) | 변경 필요 여부 |
|------|----------------------|-------------------|--------------|
| **입력 소스** | HTML 웹페이지 (URL) | .docx, .txt, .md 파일 | **변경 필요** |
| **LLM** | Ollama gemma3:12b | Ollama gemma3:27b | 설정 변경 |
| **임베딩 모델** | LanceDB 내장 모델 (384차원) | bona/bge-m3:latest (1024차원) | **변경 필요** |
| **NLP 파이프라인** | spaCy en_core_web_md | spaCy (언어에 따라 변경) | 검토 필요 |
| **Entity Resolution** | Senzing SDK (gRPC) | 선택적 사용 | 검토 필요 |
| **벡터 저장소** | LanceDB | LanceDB (유지) | 차원 조정 |
| **시각화** | PyVis + Streamlit | PyVis + Streamlit (유지) | - |

---

## 2. 입력 소스 변환 전략

### 2.1 문서 로더 아키텍처

```mermaid
flowchart TD
    subgraph FILE_INPUT["파일 입력"]
        DOCX_FILE["워드 파일\n(.docx)"]
        TXT_FILE["텍스트 파일\n(.txt)"]
        MD_FILE["마크다운 파일\n(.md)"]
    end

    subgraph LOADERS["문서 로더 (신규 개발 필요)"]
        DOCX_LOADER["DocxLoader\n(python-docx)"]
        TXT_LOADER["TextLoader\n(built-in)"]
        MD_LOADER["MarkdownLoader\n(markdown-it-py)"]
    end

    subgraph UNIFIED["통합 인터페이스"]
        PARA_LIST["paragraphs[]\n(문단 리스트)"]
        META["메타데이터\n(파일명, 경로, 제목)"]
    end

    subgraph EXISTING["기존 파이프라인 (변경 불필요)"]
        MAKE_CHUNKS["make_chunks()\n텍스트 청킹"]
        ADD_CHUNK["add_chunk()\n벡터 저장"]
        PARSE_PARA["parse_para()\nNLP 파싱"]
    end

    DOCX_FILE --> DOCX_LOADER
    TXT_FILE --> TXT_LOADER
    MD_FILE --> MD_LOADER

    DOCX_LOADER --> PARA_LIST
    TXT_LOADER --> PARA_LIST
    MD_LOADER --> PARA_LIST

    DOCX_LOADER --> META
    TXT_LOADER --> META
    MD_LOADER --> META

    PARA_LIST --> MAKE_CHUNKS
    MAKE_CHUNKS --> ADD_CHUNK
    MAKE_CHUNKS --> PARSE_PARA

    style LOADERS fill:#e17055,stroke:#fab1a0,color:#fff
    style UNIFIED fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style EXISTING fill:#00b894,stroke:#55efc4,color:#fff
```

### 2.2 각 포맷별 로더 구현 검토

#### 워드 파일 (.docx)

| 항목 | 내용 |
|------|------|
| **라이브러리** | `python-docx` |
| **추출 대상** | 단락(paragraph), 표(table), 헤더(header), 목록(list) |
| **난이도** | 중간 |
| **주의사항** | 이미지/차트는 별도 처리 필요, 스타일 정보 활용 가능 |

```python
# 예시 구현 코드 (DocxLoader)
from docx import Document

class DocxLoader:
    def load(self, file_path: str) -> list[str]:
        doc = Document(file_path)
        paragraphs = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        # 표 데이터도 텍스트로 변환
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(
                    cell.text.strip() for cell in row.cells
                )
                if row_text.strip("| "):
                    paragraphs.append(row_text)
        return paragraphs
```

#### 텍스트 파일 (.txt)

| 항목 | 내용 |
|------|------|
| **라이브러리** | Python 내장 |
| **추출 대상** | 줄 단위 또는 빈 줄 기준 단락 분리 |
| **난이도** | 낮음 |
| **주의사항** | 인코딩 감지 필요 (UTF-8, EUC-KR 등) |

```python
# 예시 구현 코드 (TextLoader)
import chardet

class TextLoader:
    def load(self, file_path: str) -> list[str]:
        with open(file_path, "rb") as f:
            raw = f.read()
            encoding = chardet.detect(raw)["encoding"] or "utf-8"

        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        # 빈 줄 기준으로 단락 분리
        paragraphs = [
            p.strip() for p in content.split("\n\n")
            if p.strip()
        ]
        return paragraphs
```

#### 마크다운 파일 (.md)

| 항목 | 내용 |
|------|------|
| **라이브러리** | `markdown-it-py` 또는 `mistune` |
| **추출 대상** | 텍스트 블록, 코드 블록, 리스트, 헤더 |
| **난이도** | 중간 |
| **주의사항** | 코드 블록과 일반 텍스트 구분, 링크/이미지 참조 처리 |

```python
# 예시 구현 코드 (MarkdownLoader)
import re

class MarkdownLoader:
    def load(self, file_path: str) -> list[str]:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 코드 블록 제거 (선택)
        content = re.sub(r"```[\s\S]*?```", "", content)

        # 마크다운 문법 정제
        content = re.sub(r"#{1,6}\s+", "", content)  # 헤더
        content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)  # 링크
        content = re.sub(r"[*_]{1,2}([^*_]+)[*_]{1,2}", r"\1", content)  # 볼드/이탤릭

        paragraphs = [
            p.strip() for p in content.split("\n\n")
            if p.strip()
        ]
        return paragraphs
```

### 2.3 Scraper 대체 전략

```mermaid
flowchart LR
    subgraph ORIGINAL["원본 방식"]
        URL_LIST["URL 리스트\n(domain.json)"]
        SCRAPER["Scraper.scrape_html()"]
        HTML_PARSE["BeautifulSoup\nHTML 파싱"]
    end

    subgraph CUSTOM["커스텀 방식"]
        FILE_LIST["파일 경로 리스트\n(domain.json 수정)"]
        DOC_LOADER["DocumentLoader\n(통합 로더)"]
        FORMAT_DETECT["포맷 감지\n(.docx/.txt/.md)"]
    end

    subgraph COMMON["공통 파이프라인"]
        PARAGRAPHS["paragraphs[]"]
        MAKE_CHUNKS_C["make_chunks()"]
    end

    URL_LIST --> SCRAPER --> HTML_PARSE --> PARAGRAPHS
    FILE_LIST --> DOC_LOADER --> FORMAT_DETECT --> PARAGRAPHS
    PARAGRAPHS --> MAKE_CHUNKS_C

    style ORIGINAL fill:#e17055,stroke:#fab1a0,color:#fff
    style CUSTOM fill:#00b894,stroke:#55efc4,color:#fff
    style COMMON fill:#0984e3,stroke:#74b9ff,color:#fff
```

---

## 3. LLM 변경 검토: gemma3:27b

### 3.1 모델 비교

| 항목 | gemma3:12b (원본) | gemma3:27b (변경) |
|------|-------------------|-------------------|
| **파라미터 수** | 12B | 27B |
| **VRAM 요구량** | ~8GB (Q4) | ~16GB (Q4) |
| **추론 속도** | 빠름 | 중간 |
| **품질** | 양호 | 우수 |
| **다국어 지원** | 기본 | 향상 |
| **컨텍스트 윈도우** | 8K/128K | 8K/128K |

### 3.2 설정 변경 사항

```toml
# config.toml 변경
[rag]
# 변경 전
# llm_model = "gemma3:12b"

# 변경 후
llm_model = "gemma3:27b"
temperature = 0.0        # 결정적 응답 (유지)
max_tokens = 3000        # 최대 토큰 (필요시 증가)
```

### 3.3 gemma3:27b 적용 시 아키텍처

```mermaid
flowchart TD
    subgraph LLM_STACK["LLM 스택"]
        DSPY_MOD["DSPy Module\n(RAG Signature)"]
        OLLAMA_SRV["Ollama Server\n(localhost:11434)"]
        GEMMA["gemma3:27b\n(27B 파라미터)"]

        DSPY_MOD -->|"HTTP API"| OLLAMA_SRV
        OLLAMA_SRV -->|"추론"| GEMMA
    end

    subgraph REQUIREMENTS["시스템 요구사항"]
        GPU["GPU VRAM\n최소 16GB (Q4)\n최소 28GB (FP16)"]
        RAM["시스템 RAM\n최소 32GB 권장"]
        DISK["디스크\n~15GB 모델 파일"]
    end

    subgraph OPTIMIZATION["최적화 옵션"]
        QUANT["양자화 옵션"]
        Q4["Q4_K_M\n(16GB VRAM)"]
        Q8["Q8_0\n(28GB VRAM)"]
        FP16["FP16\n(54GB VRAM)"]
        QUANT --> Q4
        QUANT --> Q8
        QUANT --> FP16
    end

    GEMMA --> GPU
    GEMMA --> RAM
    GEMMA --> DISK

    style LLM_STACK fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style REQUIREMENTS fill:#e17055,stroke:#fab1a0,color:#fff
    style OPTIMIZATION fill:#00b894,stroke:#55efc4,color:#fff
```

### 3.4 Ollama 설정 명령어

```bash
# gemma3:27b 모델 다운로드
ollama pull gemma3:27b

# 모델 실행 확인
ollama run gemma3:27b "Hello, test"

# 서버 상태 확인
curl http://localhost:11434/api/tags
```

---

## 4. 임베딩 모델 변경 검토: bona/bge-m3:latest

### 4.1 모델 비교

| 항목 | 원본 (LanceDB 내장) | bona/bge-m3:latest |
|------|---------------------|-------------------|
| **차원 수** | 384 | 1024 |
| **다국어 지원** | 제한적 | **100+ 언어 지원** |
| **한국어 성능** | 보통 | **우수** |
| **최대 토큰** | 512 | 8192 |
| **모델 크기** | ~100MB | ~2.3GB |
| **Dense 검색** | 지원 | 지원 |
| **Sparse 검색** | 미지원 | **지원** |
| **Multi-vector** | 미지원 | **지원 (ColBERT)** |

### 4.2 변경 영향도 분석

```mermaid
flowchart TD
    CHANGE["임베딩 모델 변경\n384차원 → 1024차원"]

    subgraph HIGH_IMPACT["높은 영향도 (필수 변경)"]
        CTX_TC["ctx.py: TextChunk\n벡터 차원 384 → 1024"]
        LANCE_TBL_C["LanceDB 테이블\n스키마 변경"]
        EMBED_FUNC["임베딩 함수\n커스텀 구현 필요"]
    end

    subgraph MEDIUM_IMPACT["중간 영향도 (권장 변경)"]
        CHUNK_SIZE["chunk 크기 조정\n1024 → 2048 가능\n(BGE-M3 8K 지원)"]
        W2V_DIM["Word2Vec 차원\n23 → 조정 검토"]
        RAG_THRESHOLD["RAG 검색 threshold\n재조정 필요"]
    end

    subgraph LOW_IMPACT["낮은 영향도 (선택 변경)"]
        VIS_C["시각화 코드\n변경 불필요"]
        ERKG_C["KG 구조\n변경 불필요"]
        NLP_C["NLP 파이프라인\n변경 불필요"]
    end

    CHANGE --> HIGH_IMPACT
    CHANGE --> MEDIUM_IMPACT
    CHANGE --> LOW_IMPACT

    style HIGH_IMPACT fill:#e17055,stroke:#fab1a0,color:#fff
    style MEDIUM_IMPACT fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style LOW_IMPACT fill:#00b894,stroke:#55efc4,color:#fff
```

### 4.3 BGE-M3 통합 구현 방안

```mermaid
sequenceDiagram
    participant App as 애플리케이션
    participant Loader as DocumentLoader
    participant BGE as BGE-M3 모델<br/>(bona/bge-m3:latest)
    participant Lance as LanceDB
    participant DC as DomainContext

    Note over App,DC: 초기화 단계
    App->>BGE: 모델 로드 (Ollama 또는 직접)
    BGE-->>App: 모델 준비 완료

    Note over App,DC: 문서 처리 단계
    App->>Loader: 파일 로드 (.docx/.txt/.md)
    Loader-->>App: paragraphs[]
    App->>App: make_chunks(paragraphs)

    loop 각 chunk에 대해
        App->>BGE: embed(chunk_text)
        BGE-->>App: vector[1024]
        App->>Lance: add(TextChunk with vector)
        App->>DC: add_chunk()
    end

    Note over App,DC: 검색 단계
    App->>BGE: embed(question)
    BGE-->>App: query_vector[1024]
    App->>Lance: search(query_vector, limit=9)
    Lance-->>App: relevant_chunks[]
```

### 4.4 BGE-M3 Ollama 활용 설정

```bash
# BGE-M3 임베딩 모델 다운로드 (Ollama)
ollama pull bona/bge-m3:latest

# 임베딩 테스트
curl http://localhost:11434/api/embed \
  -d '{"model": "bona/bge-m3:latest", "input": "테스트 문장입니다."}'
```

```toml
# config.toml 변경 사항
[vect]
db_dir = "data/lancedb"
chunk_size = 2048          # 8K 토큰 지원으로 증가 가능
embed_model = "bona/bge-m3:latest"
embed_dim = 1024           # 384 → 1024
```

---

## 5. 코드 수정 필요 영역 상세 분석

### 5.1 수정 필요 파일 목록

```mermaid
graph TD
    subgraph MUST_CHANGE["필수 변경 파일"]
        F1["scrape.py 또는 신규 loader.py\n→ 문서 로더 추가"]
        F2["ctx.py\n→ TextChunk 벡터 차원 변경"]
        F3["work.py\n→ crawl_chunk_parse() 수정"]
        F4["config.toml\n→ LLM/임베딩 설정 변경"]
        F5["domain.json\n→ 입력 소스 정의 변경"]
    end

    subgraph SHOULD_CHANGE["권장 변경 파일"]
        F6["rag.py\n→ 검색 파라미터 재조정"]
        F7["ent.py\n→ Word2Vec 차원 검토"]
    end

    subgraph NO_CHANGE["변경 불필요 파일"]
        F8["elem.py - 데이터 모델"]
        F9["erkg.py - KG 구조"]
        F10["lex.py - Lexical Graph"]
        F11["nlp.py - NLP Parser"]
        F12["opt.py - 유틸리티"]
        F13["vis.py - 시각화"]
        F14["prof.py - 프로파일링"]
    end

    style MUST_CHANGE fill:#e17055,stroke:#fab1a0,color:#fff
    style SHOULD_CHANGE fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style NO_CHANGE fill:#00b894,stroke:#55efc4,color:#fff
```

### 5.2 핵심 코드 변경 가이드

#### (1) ctx.py - TextChunk 벡터 차원 변경

```python
# 변경 전 (384차원)
class TextChunk(LanceModel):
    uid: int
    url: str
    sent_id: int
    text: str
    vector: Vector(384)  # 원본

# 변경 후 (1024차원 - BGE-M3)
class TextChunk(LanceModel):
    uid: int
    url: str
    sent_id: int
    text: str
    vector: Vector(1024)  # BGE-M3 차원
```

#### (2) work.py - 파일 기반 파이프라인 추가

```python
# crawl_chunk_parse() 수정 또는 새 메서드 추가
def load_file_parse(self, file_paths: list[str]):
    """파일 기반 문서 로드 및 파싱"""
    loader = DocumentLoader()

    for file_path in file_paths:
        paragraphs = loader.load(file_path)
        chunks = self.make_chunks(paragraphs)

        for chunk_text in chunks:
            self.dc.add_chunk(chunk_text, file_path)
            self.parser.parse_para(chunk_text, ...)
```

#### (3) domain.json 구조 변경

```json
{
    "domain": "my_project",
    "description": "프로젝트 설명",
    "lang": "ko",
    "sources": [
        {
            "type": "file",
            "path": "data/documents/report.docx",
            "format": "docx"
        },
        {
            "type": "file",
            "path": "data/documents/notes.txt",
            "format": "txt"
        },
        {
            "type": "file",
            "path": "data/documents/spec.md",
            "format": "md"
        }
    ],
    "taxonomy": "data/taxonomy.ttl"
}
```

---

## 6. 구현 로드맵

### 6.1 단계별 구현 계획

```mermaid
gantt
    title Strwythura 커스텀 활용 구현 로드맵
    dateFormat  YYYY-MM-DD
    axisFormat  %m/%d

    section Phase 1: 환경 구축
    Ollama gemma3:27b 설치          :p1a, 2026-03-01, 1d
    BGE-M3 임베딩 모델 설치          :p1b, 2026-03-01, 1d
    Python 환경 및 의존성 설치        :p1c, 2026-03-01, 2d
    config.toml 설정 변경            :p1d, after p1c, 1d

    section Phase 2: 문서 로더 개발
    DocumentLoader 인터페이스 설계    :p2a, after p1d, 1d
    DocxLoader 구현                  :p2b, after p2a, 2d
    TextLoader 구현                  :p2c, after p2a, 1d
    MarkdownLoader 구현              :p2d, after p2a, 1d
    로더 통합 테스트                  :p2e, after p2b, 1d

    section Phase 3: 코어 수정
    TextChunk 벡터 차원 변경          :p3a, after p2e, 1d
    BGE-M3 임베딩 통합               :p3b, after p3a, 2d
    work.py 파이프라인 수정           :p3c, after p3b, 2d
    domain.json 스키마 변경           :p3d, after p3c, 1d

    section Phase 4: 통합 테스트
    파이프라인 End-to-End 테스트       :p4a, after p3d, 3d
    RAG 파라미터 튜닝                 :p4b, after p4a, 2d
    성능 벤치마크                     :p4c, after p4b, 2d

    section Phase 5: 배포
    문서화                           :p5a, after p4c, 2d
    최종 검증 및 배포                  :p5b, after p5a, 2d
```

### 6.2 구현 우선순위 매트릭스

```mermaid
quadrantChart
    title 구현 우선순위 매트릭스
    x-axis "낮은 난이도" --> "높은 난이도"
    y-axis "낮은 영향도" --> "높은 영향도"
    quadrant-1 "핵심 과제"
    quadrant-2 "우선 처리"
    quadrant-3 "후순위"
    quadrant-4 "선택적"
    "config.toml 수정": [0.2, 0.7]
    "LLM 모델 변경": [0.3, 0.6]
    "TextLoader": [0.15, 0.5]
    "DocxLoader": [0.5, 0.8]
    "MarkdownLoader": [0.4, 0.6]
    "BGE-M3 통합": [0.7, 0.9]
    "TextChunk 차원변경": [0.4, 0.85]
    "RAG 파라미터 튜닝": [0.6, 0.7]
    "Word2Vec 차원조정": [0.5, 0.3]
    "한국어 spaCy 모델": [0.65, 0.75]
```

---

## 7. 리스크 분석

### 7.1 기술적 리스크

```mermaid
flowchart TD
    subgraph RISK_HIGH["높은 리스크"]
        R1["BGE-M3 차원 변경에 따른\nLanceDB 호환성 이슈"]
        R1_MIT["완화: TextChunk 모델 수정\n+ 테이블 재생성"]

        R2["gemma3:27b VRAM 부족"]
        R2_MIT["완화: Q4 양자화 적용\n또는 CPU offload"]
    end

    subgraph RISK_MED["중간 리스크"]
        R3["한국어 NER 성능 저하\n(spaCy en_core_web_md)"]
        R3_MIT["완화: ko_core_news_lg 사용\n또는 GLiNER 한국어 모델"]

        R4["워드 파일 복잡한 서식\n(표, 이미지, 차트)"]
        R4_MIT["완화: 텍스트만 추출\n복잡 서식은 별도 처리"]
    end

    subgraph RISK_LOW["낮은 리스크"]
        R5["텍스트 인코딩 이슈"]
        R5_MIT["완화: chardet 라이브러리\n자동 감지"]

        R6["Taxonomy 재설계 필요"]
        R6_MIT["완화: 도메인별\n단계적 구축"]
    end

    R1 --> R1_MIT
    R2 --> R2_MIT
    R3 --> R3_MIT
    R4 --> R4_MIT
    R5 --> R5_MIT
    R6 --> R6_MIT

    style RISK_HIGH fill:#e17055,stroke:#fab1a0,color:#fff
    style RISK_MED fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style RISK_LOW fill:#00b894,stroke:#55efc4,color:#fff
```

### 7.2 리소스 요구사항

| 리소스 | 최소 사양 | 권장 사양 |
|--------|----------|----------|
| **GPU VRAM** | 16GB (Q4 양자화) | 24GB+ |
| **시스템 RAM** | 16GB | 32GB+ |
| **디스크** | 50GB | 100GB+ |
| **CPU** | 8코어 | 16코어+ |
| **네트워크** | Ollama 로컬 실행 | - |

---

## 8. 한국어 지원 검토

### 8.1 한국어 NLP 파이프라인 옵션

```mermaid
graph TD
    subgraph KO_NLP["한국어 NLP 옵션"]
        direction TB

        subgraph OPT1["옵션 1: spaCy 한국어"]
            SPACY_KO["ko_core_news_lg"]
            SPACY_KO_FEAT["형태소 분석\n개체명 인식\n의존 구문 분석"]
        end

        subgraph OPT2["옵션 2: 기존 영어 + GLiNER"]
            EN_SPACY["en_core_web_md\n(영어 기반)"]
            GLINER_ML["GLiNER\n(다국어 Zero-shot NER)"]
        end

        subgraph OPT3["옵션 3: 하이브리드"]
            MECAB["MeCab/Konlpy\n(한국어 형태소)"]
            GLINER_H["GLiNER\n(NER)"]
        end
    end

    subgraph RECOMMEND["권장 사항"]
        REC["BGE-M3와 조합 시\n옵션 2 권장:\n영어 spaCy + GLiNER\n(다국어 NER 지원)"]
    end

    KO_NLP --> RECOMMEND

    style OPT1 fill:#0984e3,stroke:#74b9ff,color:#fff
    style OPT2 fill:#00b894,stroke:#55efc4,color:#fff
    style OPT3 fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style RECOMMEND fill:#fdcb6e,stroke:#f39c12,color:#2d3436
```

### 8.2 BGE-M3의 한국어 성능 장점

- **다국어 임베딩:** 100개 이상 언어에서 통합 벡터 공간 지원
- **한국어 최적화:** MTEB 벤치마크에서 한국어 검색 성능 우수
- **Cross-lingual:** 한국어-영어 간 교차 언어 검색 가능
- **긴 문맥:** 최대 8192 토큰 지원으로 한국어 긴 문서 처리 가능

---

## 9. 최종 아키텍처 (커스텀)

```mermaid
graph TB
    subgraph INPUT_FINAL["입력 소스"]
        DOCX_F[".docx 파일"]
        TXT_F[".txt 파일"]
        MD_F[".md 파일"]
    end

    subgraph LOADER_FINAL["문서 로더 (신규)"]
        DOC_LOADER_F["DocumentLoader\n(포맷 자동 감지)"]
    end

    subgraph NLP_FINAL["NLP 파이프라인"]
        SPACY_F["spaCy\n(en_core_web_md)"]
        GLINER_F["GLiNER\n(다국어 NER)"]
    end

    subgraph EMBED_FINAL["임베딩"]
        BGE_F["bona/bge-m3:latest\n(1024차원, 다국어)"]
    end

    subgraph STORE_FINAL["저장소"]
        LANCE_F["LanceDB\n(1024차원 벡터)"]
        NX_F["NetworkX ERKG"]
        W2V_F["Word2Vec\n(엔티티 임베딩)"]
    end

    subgraph LLM_FINAL["LLM"]
        GEMMA_F["Ollama\ngemma3:27b"]
        DSPY_F["DSPy\nRAG Signature"]
    end

    subgraph OUTPUT_FINAL["출력"]
        QA_F["GraphRAG Q&A"]
        VIS_F["대화형 시각화"]
        DASH_F["Streamlit 대시보드"]
    end

    INPUT_FINAL --> LOADER_FINAL
    LOADER_FINAL --> NLP_FINAL
    LOADER_FINAL --> EMBED_FINAL
    EMBED_FINAL --> LANCE_F
    NLP_FINAL --> NX_F
    NLP_FINAL --> W2V_F
    LANCE_F --> QA_F
    NX_F --> QA_F
    W2V_F --> QA_F
    GEMMA_F --> DSPY_F
    DSPY_F --> QA_F
    NX_F --> VIS_F
    QA_F --> DASH_F
    VIS_F --> DASH_F

    style INPUT_FINAL fill:#e17055,stroke:#fab1a0,color:#fff
    style LOADER_FINAL fill:#fdcb6e,stroke:#f39c12,color:#2d3436
    style NLP_FINAL fill:#0984e3,stroke:#74b9ff,color:#fff
    style EMBED_FINAL fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style STORE_FINAL fill:#2d3436,stroke:#636e72,color:#dfe6e9
    style LLM_FINAL fill:#6c5ce7,stroke:#a29bfe,color:#fff
    style OUTPUT_FINAL fill:#00b894,stroke:#55efc4,color:#fff
```

---

## 10. 체크리스트

### 구현 전 확인 사항

- [ ] Ollama 설치 및 gemma3:27b 모델 다운로드
- [ ] Ollama에서 bona/bge-m3:latest 모델 다운로드
- [ ] GPU VRAM 16GB 이상 확인
- [ ] Python 3.11~3.13 환경 구성
- [ ] Strwythura 의존성 설치 (poetry install)

### 코드 변경 확인 사항

- [ ] config.toml: llm_model을 gemma3:27b로 변경
- [ ] config.toml: 임베딩 관련 설정 추가
- [ ] ctx.py: TextChunk 벡터 차원 384→1024 변경
- [ ] 문서 로더 모듈 구현 (loader.py)
- [ ] work.py: 파일 기반 파이프라인 메서드 추가
- [ ] domain.json: 파일 소스 구조로 변경

### 테스트 확인 사항

- [ ] 각 포맷별 문서 로더 단위 테스트
- [ ] BGE-M3 임베딩 벡터 생성 확인
- [ ] LanceDB 테이블 정상 생성 확인
- [ ] 전체 파이프라인 End-to-End 실행
- [ ] GraphRAG Q&A 품질 검증
- [ ] Streamlit 앱 정상 동작 확인

이 문서는 Strwythura를 커스텀 환경(워드/텍스트/마크다운 입력, gemma3:27b, BGE-M3)에서 활용하기 위한 종합적인 계획 검토 자료입니다.
