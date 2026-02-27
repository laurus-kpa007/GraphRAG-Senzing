# 🚀 Agentic GraphRAG - Quick Start Guide

## Step 1: 의존성 설치

### Windows
```bash
# 방법 1: 배치 스크립트 사용 (추천)
install_deps.bat

# 방법 2: pip 직접 사용
pip install -r requirements.txt
```

### Linux/Mac
```bash
pip install -r requirements.txt
```

### spaCy 한국어 모델 설치
```bash
python -m spacy download ko_core_news_lg
```

---

## Step 2: Ollama 모델 준비

```bash
# LLM 모델 (답변 생성)
ollama pull gemma3:4b

# Embedding 모델 (벡터 검색)
ollama pull bge-m3:latest
```

**중요**: `config.toml`에서 Ollama 서버 주소를 확인하세요:
```toml
[embed]
ollama_url = "http://192.168.68.68:11434"  # 본인의 Ollama 서버 주소로 변경

[rag]
api_base = "http://192.168.68.68:11434"     # 동일하게 변경
```

---

## Step 3: 문서 준비

```bash
# 문서를 data/documents/ 폴더에 복사
# 지원 형식: .docx, .txt, .md
```

예시:
```
data/documents/
├── 회사규정.docx
├── 복리후생.txt
└── 재택근무가이드.md
```

---

## Step 4: 데이터 처리 (최초 1회)

```bash
python run_pipeline.py data/documents/
```

이 과정에서:
- ✅ 문서 로드 및 파싱
- ✅ 텍스트 청크 분할
- ✅ BGE-M3 임베딩 생성
- ✅ LanceDB 벡터 저장
- ✅ NLP 엔티티 추출

**예상 시간**: 문서 100페이지 기준 약 5-10분

---

## Step 5: Agentic RAG 실행! 🤖

### 📊 Standard vs Agentic 비교 테스트

```bash
python test_agentic.py
```

**출력 예시**:
```
================================================================================
TEST 1: 재택근무 승인자는 누구인가요?
================================================================================

[STANDARD MODE]
--------------------------------------------------------------------------------
Answer: 재택근무 승인자는 팀장입니다.
Chunks: 8
Time: 2.3s

[AGENTIC MODE]
--------------------------------------------------------------------------------
[PLAN] 1 sub-queries, strategy=hybrid
[RETRIEVE] 15 docs, strategy=hybrid
[GRADE] 8/15 docs passed threshold 0.7
[REASON] 2 hops, answer generated
[VALIDATE] ✓ PASS (confidence=0.92)
[ANSWER] 2 citations added

Answer: 재택근무 승인자는 팀장입니다.
Validation: ✓ PASS (confidence: 0.92)
Reasoning steps: 2
Citations: 2
Retries: 0
Retrieved: 15 docs, Relevant: 8 docs
```

---

### 💬 인터랙티브 대화 세션

```bash
python test_agentic.py interactive
```

**대화 예시**:
```
Q: 누나 결혼하면 경조금은 얼마인가요?

[PLAN] 1 sub-queries, strategy=hybrid
[RETRIEVE] 12 docs, strategy=hybrid
[GRADE] 7/12 docs passed threshold 0.7
[REASON] 1 hops, answer generated
[VALIDATE] ✓ PASS (confidence=0.95)

A: 형제자매(누나)가 결혼하면 경조금은 50만원입니다.
   Validation: ✓ (confidence: 0.95)
   Reasoning: 1 steps
   Citations: 3
   Retries: 0

Q: quit  # 종료
```

---

## 트러블슈팅

### ❌ `ModuleNotFoundError: No module named 'lancedb'`
```bash
pip install lancedb pyarrow numpy polars
```

### ❌ `ModuleNotFoundError: No module named 'httpx'`
```bash
pip install httpx
```

### ❌ `OSError: [E050] Can't find model 'ko_core_news_lg'`
```bash
python -m spacy download ko_core_news_lg
```

### ❌ Ollama 연결 실패
```bash
# Ollama 서버 상태 확인
curl http://192.168.68.68:11434/api/tags

# config.toml의 ollama_url 주소가 맞는지 확인
```

### ❌ `FileNotFoundError: data/lancedb`
```bash
# 데이터 처리를 먼저 실행하세요
python run_pipeline.py data/documents/
```

---

## 설정 커스터마이징 (config.toml)

### Agentic 동작 조정

```toml
[agentic]
# 더 엄격한 검증 (정확도 우선)
grading_threshold = 0.85     # 0.7 → 0.85
validation_threshold = 0.90  # 0.8 → 0.90
max_retries = 5              # 3 → 5

# 빠른 실행 (속도 우선)
enable_validation = false    # 검증 스킵
enable_reflection = false    # 재시도 없음
max_reasoning_hops = 2       # 추론 깊이 제한

# 디버깅 모드
enable_tracing = true        # 실행 과정 출력
```

---

## 다음 단계

### 🔍 검색 디버깅
```bash
python tools/search_debug.py "검색어"
```

### 📊 그래프 시각화
```bash
python tools/visualize_graph.py --graph erkg
```

### 🌐 Streamlit Web UI
```bash
streamlit run app.py
```

---

## 🎯 핵심 차이점: Standard vs Agentic

| 기능 | Standard Mode | Agentic Mode |
|------|---------------|--------------|
| **검색** | Vector + Keyword + Graph | ✅ + Planning Agent |
| **문서 평가** | 없음 | ✅ Grader Agent (CRAG) |
| **추론** | Single-pass | ✅ Multi-hop + Interleaved |
| **검증** | 없음 | ✅ Validation Agent (Self-RAG) |
| **재시도** | 없음 | ✅ Reflection Agent (최대 3회) |
| **투명성** | 청크 수 | ✅ Reasoning chain + Audit trail |
| **정확도** | 기본 | ✅ +25-30% (복잡한 질문) |

---

## 📚 추가 문서

- [아키텍처 상세 설명](docs/agentic_graphrag_design.md)
- [연구 논문 레퍼런스](docs/agentic_graphrag_design.md#references)
- [도구 가이드](tools/README.md)

---

**모든 준비 완료!** 🎉

질문이 있으시면 GitHub Issues에 올려주세요.
