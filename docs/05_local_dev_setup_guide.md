# GraphRAG-Senzing 로컬 설치 및 개발자 모드 실행 가이드

> **대상:** macOS / Linux / Windows (WSL2)
> **Python:** 3.11 ~ 3.13
> **GPU:** 16GB+ VRAM 권장 (gemma3:27b Q4 기준)

---

## 1. 사전 요구사항 설치

### 1.1 Ollama 설치

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows (WSL2)
curl -fsSL https://ollama.ai/install.sh | sh
```

Ollama 서버 시작:

```bash
# 포그라운드 실행 (로그 확인용)
ollama serve

# 또는 백그라운드 실행
ollama serve &
```

### 1.2 Ollama 모델 다운로드

```bash
# 임베딩 모델 (BGE-M3, 약 1.2GB)
ollama pull bona/bge-m3:latest

# LLM 모델 (Gemma3 27B, 약 15GB)
ollama pull gemma3:27b
```

모델 다운로드 확인:

```bash
ollama list
# NAME                    SIZE
# bona/bge-m3:latest      1.2 GB
# gemma3:27b              15 GB
```

**GPU VRAM이 부족한 경우** 더 작은 모델 사용 가능:

```bash
# gemma3:12b (약 7GB, 8GB VRAM에서 동작)
ollama pull gemma3:12b
# → config.toml에서 lm_name = "ollama_chat/gemma3:12b" 로 변경
```

### 1.3 Python 환경 구성

```bash
# Python 3.11+ 확인
python3 --version

# venv 생성 (권장)
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
```

---

## 2. 프로젝트 설치

### 2.1 소스 클론

```bash
git clone https://github.com/laurus-kpa007/GraphRAG-Senzing.git
cd GraphRAG-Senzing
```

### 2.2 방법 A: setup.sh 자동 설치 (권장)

```bash
bash setup.sh
```

이 스크립트가 수행하는 작업:
1. Python 패키지 설치 (python-docx, lancedb, spacy, httpx 등)
2. spaCy 영어 모델 다운로드 (`en_core_web_md`)
3. spaCy 한국어 모델 다운로드 (`ko_core_news_lg`)
4. Ollama 모델 다운로드 확인
5. 데이터 디렉토리 생성

### 2.2 방법 B: 수동 설치

```bash
# 핵심 의존성
pip install python-docx chardet markdown-it-py httpx lancedb pyarrow \
    numpy streamlit spacy gensim networkx pydantic \
    beautifulsoup4 requests requests-cache rdflib polars

# spaCy 모델
python -m spacy download en_core_web_md

# 한국어 NLP가 필요한 경우
python -m spacy download ko_core_news_lg

# 디렉토리 생성
mkdir -p data/documents data/cache data/lancedb data/output data/uploads
```

### 2.3 설치 검증

```bash
python run_pipeline.py --check
```

정상 출력:
```
  [OK] ollama_server
  [OK] llm_model
  [OK] embed_model
```

MISSING이 있으면:
```
  [MISSING] embed_model    → ollama pull bona/bge-m3:latest
  [MISSING] llm_model      → ollama pull gemma3:27b
  [MISSING] ollama_server   → ollama serve
```

---

## 3. 개발자 모드 실행

### 3.1 문서 준비

`data/documents/` 폴더에 분석할 문서를 넣습니다:

```bash
# 예시: 기존 샘플 문서 확인
ls data/documents/
# sample.md  sample.txt  sample_ko.md  sample_ko.txt

# 자신의 문서 추가
cp ~/my_reports/*.docx data/documents/
cp ~/my_notes/*.md data/documents/
cp ~/my_data/*.txt data/documents/
```

지원 포맷: `.docx`, `.txt`, `.md`, `.markdown`, `.text`

### 3.2 CLI 모드 실행

```bash
# ── 기본 실행: 문서 처리 → 대화형 Q&A ──
python run_pipeline.py data/documents/

# ── 특정 파일만 처리 ──
python run_pipeline.py report.docx notes.txt spec.md

# ── NLP 건너뛰기 (빠른 모드, 벡터 검색만 사용) ──
python run_pipeline.py --skip-nlp data/documents/

# ── 단일 질문 후 종료 ──
python run_pipeline.py data/documents/ --query "GraphRAG란 무엇인가요?"

# ── 이미 처리된 데이터로 Q&A만 실행 ──
python run_pipeline.py --query-only

# ── 이미 처리된 데이터에 단일 질문 ──
python run_pipeline.py --query-only --query "Senzing은 어떤 역할을 하나요?"
```

실행 예시:
```
============================================================
  Agentic GraphRAG Pipeline Starting
  LLM: ollama_chat/gemma3:27b
  Embeddings: bona/bge-m3:latest
============================================================
09:15:01 [INFO] Prerequisites: {'ollama_server': True, 'llm_model': True, 'embed_model': True}
09:15:01 [INFO] Pipeline initialized
09:15:01 [INFO] Loaded 4 documents, 43 total paragraphs
09:15:01 [INFO]   sample.md: 2 chunks
09:15:02 [INFO]   sample.txt: 3 chunks
09:15:03 [INFO]   sample_ko.md: 2 chunks
09:15:03 [INFO]   sample_ko.txt: 1 chunks
09:15:03 [INFO] Total chunks embedded: 8
09:15:05 [INFO] Standalone NLP extracted 290 entities
============================================================
  Pipeline Ready - 8 chunks from 4 documents
============================================================

============================================================
  GraphRAG Interactive Q&A
  LLM: gemma3:27b
  Embeddings: bona/bge-m3:latest
  Chunks loaded: 8
============================================================
  Type 'quit' to exit.

Q: GraphRAG란 무엇인가요?

A: GraphRAG는 그래프 기반 검색 증강 생성 시스템으로...
   [3.42s | 9 chunks | sources: sample_ko.md, sample.md]

Q: quit
```

### 3.3 Streamlit 웹 UI 모드 실행

```bash
# 기본 실행
streamlit run app.py

# 포트 지정
streamlit run app.py --server.port 8501

# 외부 접근 허용
streamlit run app.py --server.address 0.0.0.0

# 개발 모드 (파일 변경 시 자동 리로드)
streamlit run app.py --server.runOnSave true
```

브라우저에서 `http://localhost:8501` 접속.

**웹 UI 사용 순서:**
1. **문서 업로드 & 파이프라인** 탭 → 파일 업로드 또는 디렉토리 경로 입력 → "파이프라인 실행"
2. **Q&A 채팅** 탭 → 질문 입력 (한국어/영어 모두 가능)
3. **시스템 상태** 탭 → Ollama 연결 상태, 엔티티/벡터 저장소 확인

---

## 4. 설정 커스터마이징

### 4.1 config.toml 주요 설정

```toml
# ── LLM 변경 ──
[rag]
lm_name = "ollama_chat/gemma3:27b"   # 다른 모델: gemma3:12b, llama3.1:8b 등
api_base = "http://localhost:11434"    # Ollama 서버 주소
temperature = 0.0                      # 0.0 = 결정적, 0.7 = 창의적
max_tokens = 3000                      # 최대 응답 길이
max_chunks = 11                        # 검색할 최대 청크 수

# ── 임베딩 모델 변경 ──
[embed]
model = "bona/bge-m3:latest"          # 다른 모델: nomic-embed-text 등
dim = 1024                             # 모델에 따라 변경 (bge-m3=1024)
ollama_url = "http://localhost:11434"

# ── NLP 설정 ──
[nlp]
spacy_model = "en_core_web_md"        # 한국어: "ko_core_news_lg"
gliner_model = "urchade/gliner_small-v2.1"

# ── 청킹 설정 ──
[vect]
chunk_size = 1024                     # 청크 최대 문자 수 (크면 컨텍스트 ↑, 정밀도 ↓)
```

### 4.2 한국어 전용 설정

한국어 문서만 사용하는 경우:

```toml
[nlp]
spacy_model = "ko_core_news_lg"      # 한국어 모델로 변경
```

```bash
# 한국어 모델 설치
python -m spacy download ko_core_news_lg
```

### 4.3 저사양 환경 설정

GPU VRAM이 8GB 이하인 경우:

```toml
[rag]
lm_name = "ollama_chat/gemma3:12b"    # 12B 모델 사용 (~7GB VRAM)
# 또는
lm_name = "ollama_chat/gemma3:4b"     # 4B 모델 사용 (~3GB VRAM)

[embed]
model = "nomic-embed-text:latest"      # 더 작은 임베딩 모델 (768-dim)
dim = 768
```

```bash
ollama pull gemma3:12b
ollama pull nomic-embed-text:latest
```

---

## 5. 개발 & 디버깅

### 5.1 디버그 로깅

```bash
# 상세 로그 출력
LOG_LEVEL=DEBUG python run_pipeline.py data/documents/
```

또는 코드에서:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 5.2 Python REPL에서 직접 사용

```python
from src.pipeline import AgenticPipeline

# 파이프라인 생성
pipeline = AgenticPipeline()

# 사전 확인
print(pipeline.check_prerequisites())

# 초기화
pipeline.initialize()

# 문서 로드
docs = pipeline.load_documents(["data/documents/"])
print(f"문서 {len(docs)}개 로드")

# 청킹 확인
for source, paras in docs.items():
    chunks = pipeline.make_chunks(paras)
    print(f"  {source}: {len(paras)} 단락 → {len(chunks)} 청크")

# 임베딩 & 저장
n = pipeline.embed_and_store(docs)
print(f"총 {n}개 청크 임베딩 완료")

# NLP 엔티티 추출
pipeline.run_nlp_pipeline(docs)

# 질문
result = pipeline.query("GraphRAG란?")
print(result["answer"])
```

### 5.3 개별 컴포넌트 테스트

```python
# 문서 로더만 테스트
from src.loaders import DocumentLoader
loader = DocumentLoader()
paras = loader.load("data/documents/sample_ko.md")
print(f"{len(paras)} paragraphs loaded")

# 임베딩만 테스트
from src.embeddings import OllamaEmbedding
embed = OllamaEmbedding()
vec = embed.embed_text("테스트 문장입니다")
print(f"Vector dim: {len(vec)}")  # 1024

# LLM만 테스트
from src.embeddings import OllamaLLM
llm = OllamaLLM()
answer = llm.generate("GraphRAG가 뭔가요?", system="한국어로 짧게 답변하세요.")
print(answer)
```

### 5.4 테스트 실행

```bash
# 전체 테스트 (25개)
python tests/test_integration.py

# 또는 pytest 사용 (설치 필요)
pip install pytest
pytest tests/ -v

# 특정 테스트만
python -m pytest tests/test_integration.py::TestDocumentLoader -v
python -m pytest tests/test_integration.py::TestPipeline -v
```

### 5.5 LanceDB 데이터 확인

```python
import lancedb

db = lancedb.connect("data/lancedb")
print(db.table_names())            # ['chunk']

table = db.open_table("chunk")
print(table.count_rows())          # 청크 수

# 저장된 데이터 확인
import polars as pl
df = pl.from_arrow(table.to_arrow())
print(df.select(["uid", "source", "text"]).head(5))
```

### 5.6 엔티티 저장소 확인

```python
import json

with open("data/output/ent.json", encoding="utf-8") as f:
    entities = [json.loads(line) for line in f if line.strip()]

print(f"총 엔티티: {len(entities)}")
# 상위 10개 (빈도순)
top = sorted(entities, key=lambda e: e["count"], reverse=True)[:10]
for e in top:
    print(f"  {e['text']} [{e['label']}] × {e['count']}")
```

---

## 6. 프로젝트 구조 상세

```
GraphRAG-Senzing/
│
├── src/                         ← 핵심 소스 코드
│   ├── __init__.py
│   ├── loaders.py               ← 문서 로더 (docx/txt/md, 한글 인코딩)
│   ├── embeddings.py            ← Ollama 임베딩 + LLM 클라이언트
│   └── pipeline.py              ← Agentic 파이프라인 오케스트레이터
│
├── tests/                       ← 통합 테스트 (25개)
│   ├── __init__.py
│   └── test_integration.py
│
├── data/
│   ├── documents/               ← 입력 문서 (여기에 파일 추가)
│   │   ├── sample.md
│   │   ├── sample.txt
│   │   ├── sample_ko.md
│   │   └── sample_ko.txt
│   ├── domain.ttl               ← 도메인 택소노미 (RDF)
│   ├── lancedb/                 ← 벡터 저장소 (자동 생성)
│   ├── output/                  ← 파이프라인 출력 (자동 생성)
│   │   ├── ent.json             ← 엔티티 저장소
│   │   ├── lex.json             ← Lexical Graph
│   │   └── erkg.json            ← Knowledge Graph
│   ├── cache/                   ← 스크래퍼 캐시 (자동 생성)
│   └── uploads/                 ← Streamlit 업로드 (자동 생성)
│
├── docs/                        ← 분석 문서 (Mermaid 다이어그램)
│
├── app.py                       ← Streamlit 웹 UI
├── run_pipeline.py              ← CLI 실행기
├── config.toml                  ← 전체 설정 파일
├── domain.json                  ← 도메인 메타데이터
├── pyproject.toml               ← 패키지 정의
├── setup.sh                     ← 환경 설정 스크립트
└── README.md
```

---

## 7. 데이터 초기화 & 재실행

```bash
# 벡터 저장소만 초기화 (문서 재임베딩 필요)
rm -rf data/lancedb/

# 전체 출력 초기화
rm -rf data/output/ data/lancedb/ data/cache/

# 디렉토리 재생성 후 파이프라인 재실행
mkdir -p data/output data/lancedb data/cache
python run_pipeline.py data/documents/
```

---

## 8. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `[MISSING] ollama_server` | Ollama 미실행 | `ollama serve` |
| `[MISSING] embed_model` | BGE-M3 미설치 | `ollama pull bona/bge-m3:latest` |
| `[MISSING] llm_model` | Gemma3 미설치 | `ollama pull gemma3:27b` |
| `ConnectError` | Ollama 서버 미실행 | `ollama serve` 후 재시도 |
| 한글 깨짐 | 인코딩 문제 | 파일을 UTF-8로 저장 |
| VRAM 부족 | 27B 모델 너무 큼 | `gemma3:12b` 또는 `gemma3:4b` 사용 |
| spaCy 모델 에러 | 모델 미설치 | 아래 [8.1 spaCy SSL 에러 해결] 참조 |
| LanceDB 에러 | 테이블 스키마 불일치 | `rm -rf data/lancedb/` 후 재실행 |
| 임베딩 차원 에러 | config.toml dim 불일치 | `[embed] dim`과 모델 출력 차원 맞추기 |
| Streamlit 접속 불가 | 포트 충돌 | `streamlit run app.py --server.port 8502` |

### 8.1 spaCy 모델 다운로드 SSL 에러 해결

`python -m spacy download` 실행 시 아래 에러가 발생하는 경우:

```
requests.exceptions.SSLError: HTTPSConnectionPool(host='raw.githubusercontent.com', port=443):
Max retries exceeded ... SSLCertVerificationError ... certificate verify failed:
unable to get local issuer certificate
```

**방법 1: pip로 직접 whl 설치 (가장 간단)**

```bash
# 영어 모델
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl

# 한국어 모델
pip install https://github.com/explosion/spacy-models/releases/download/ko_core_news_lg-3.8.0/ko_core_news_lg-3.8.0-py3-none-any.whl
```

위 명령도 SSL 에러가 나면 `--trusted-host` 추가:

```bash
pip install --trusted-host github.com --trusted-host objects.githubusercontent.com \
    https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
```

**방법 2: 인증서 갱신 (근본 해결)**

```bash
# certifi 설치/갱신
pip install --upgrade certifi

# SSL 인증서 경로 확인
python -c "import certifi; print(certifi.where())"

# 환경변수에 등록 (~/.bashrc 또는 ~/.zshrc에 추가)
export SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE

# macOS의 경우 추가로 실행
# /Applications/Python\ 3.XX/Install\ Certificates.command
```

등록 후 정상 설치:

```bash
python -m spacy download en_core_web_md
```

**방법 3: 브라우저에서 수동 다운로드**

1. 브라우저에서 접속:
   - 영어: https://github.com/explosion/spacy-models/releases/tag/en_core_web_md-3.8.0
   - 한국어: https://github.com/explosion/spacy-models/releases/tag/ko_core_news_lg-3.8.0
2. `.whl` 파일 다운로드
3. 로컬 설치:

```bash
pip install ./en_core_web_md-3.8.0-py3-none-any.whl
pip install ./ko_core_news_lg-3.8.0-py3-none-any.whl
```

**방법 4: spaCy 없이 실행**

spaCy 모델 설치가 어려운 환경에서는 NLP를 건너뛰고 벡터 검색만 사용:

```bash
python run_pipeline.py --skip-nlp data/documents/
```

이 모드에서도 BGE-M3 임베딩 기반 벡터 유사도 검색으로 Q&A가 동작합니다.
엔티티 추출 기반의 그래프 보강만 빠집니다.

---

## 9. 실행 흐름 요약

```
┌─────────────────────────────────────────────────────────┐
│  1. ollama serve                    ← Ollama 서버 시작  │
│  2. ollama pull bona/bge-m3:latest  ← 임베딩 모델       │
│  3. ollama pull gemma3:27b          ← LLM 모델          │
│  4. python run_pipeline.py --check  ← 상태 확인         │
│  5. 문서를 data/documents/ 에 복사                       │
│  6-A. python run_pipeline.py data/documents/   ← CLI    │
│  6-B. streamlit run app.py                     ← Web    │
└─────────────────────────────────────────────────────────┘
```
