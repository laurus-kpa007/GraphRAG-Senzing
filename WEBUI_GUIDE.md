# 🌐 Agentic GraphRAG Web UI Guide

## 🚀 Quick Start

### Windows
```bash
# 메뉴 기반 실행 (추천)
run_webui.bat

# 또는 직접 실행
streamlit run app_agentic_v2.py --server.port 8501
```

### Linux/Mac
```bash
# 메뉴 기반 실행
chmod +x run_webui.sh
./run_webui.sh

# 또는 직접 실행
streamlit run app_agentic_v2.py --server.port 8501
```

---

## 🎨 UI 선택 가이드

### 1. **app_agentic_v2.py** - Enhanced Modern UI ⭐ (추천)

**실행**:
```bash
streamlit run app_agentic_v2.py --server.port 8501
```

**특징**:
- 🎨 Modern glassmorphism design with gradients
- 📊 Real-time metrics dashboard (4 cards)
- 🔄 Timeline-based execution history
- 🎯 Agent badges with gradient backgrounds and icons
- 📚 Citation cards with progress bars
- ✨ Smooth animations and hover effects
- ⚖️ Side-by-side comparison mode
- 🧠 Expandable reasoning steps

**Best For**:
- 데모/발표
- 프로덕션 환경
- 비전문가 사용자

**Screenshot**:
```
┌─────────────────────────────────────────────┐
│ 🤖 Agentic GraphRAG Interface              │
├─────────────────────────────────────────────┤
│ 📊 Execution Metrics                        │
│ ┌─────┬─────┬─────┬─────┐                  │
│ │ 15  │  8  │  2  │ 92% │                  │
│ └─────┴─────┴─────┴─────┘                  │
│                                             │
│ 🔄 Pipeline │ 🧠 Reasoning │ 📚 Citations  │
│ ┌─────────────────────────────────────────┐ │
│ │ 🎯 PLAN → 🔍 RETRIEVE → ⭐ GRADE ...    │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

---

### 2. **app_agentic.py** - Simple Agentic UI

**실행**:
```bash
streamlit run app_agentic.py --server.port 8502
```

**특징**:
- 📋 Tab-based interface
- 🔍 Clean and functional design
- ✅ All essential features
- 📊 Overview, Reasoning, Citations, Details tabs

**Best For**:
- 빠른 테스트
- 기능 중심 사용
- 개발/디버깅

---

### 3. **app.py** - Original UI

**실행**:
```bash
streamlit run app.py --server.port 8503
```

**특징**:
- 📄 Basic document processing UI
- 🔍 Simple search interface
- ⚡ Lightweight

**Best For**:
- 기본 RAG 테스트
- 빠른 실행

---

## 🔧 포트 문제 해결

### Error: "Port 8501 is not available"

**해결 방법 1: 다른 포트 사용**
```bash
streamlit run app_agentic_v2.py --server.port 8510
```

**해결 방법 2: 기존 프로세스 종료 (Windows)**
```bash
# 8501 포트 사용 중인 프로세스 찾기
netstat -ano | findstr :8501

# PID로 프로세스 종료
taskkill /F /PID <PID>
```

**해결 방법 3: 기존 프로세스 종료 (Linux/Mac)**
```bash
# 8501 포트 사용 중인 프로세스 찾기
lsof -i :8501

# 프로세스 종료
kill -9 <PID>
```

**해결 방법 4: 자동으로 사용 가능한 포트 찾기**
```bash
streamlit run app_agentic_v2.py --server.port 0
# Streamlit이 자동으로 사용 가능한 포트를 찾습니다
```

---

## 📋 사용 전 체크리스트

### 1. 시스템 준비
```bash
# Python 버전 확인 (3.11+)
python --version

# Streamlit 설치 확인
pip show streamlit

# Streamlit 설치 (필요시)
pip install streamlit
```

### 2. Ollama 서버 확인
```bash
# Ollama 서버 상태 확인
curl http://192.168.68.68:11434/api/tags

# config.toml의 ollama_url 확인
cat config.toml | grep ollama_url
```

### 3. 데이터 준비
```bash
# 데이터 폴더 확인
ls data/lancedb/

# 데이터가 없으면 처리 실행
python run_pipeline.py data/documents/
```

### 4. Web UI 실행
```bash
# 추천 방법: 런처 스크립트 사용
run_webui.bat  # Windows
./run_webui.sh # Linux/Mac

# 또는 직접 실행
streamlit run app_agentic_v2.py --server.port 8501
```

---

## 💡 사용 팁

### Sidebar 설정 (app_agentic_v2.py)

1. **Pipeline 초기화**
   - "🚀 Initialize Pipeline" 버튼 클릭
   - Chunks와 Entities 로드 확인

2. **모드 선택**
   - 🤖 Agentic: Multi-agent pipeline (추천)
   - 📊 Standard: Hybrid search (빠름)

3. **비교 모드**
   - "📊 Show side-by-side comparison" 체크
   - Agentic vs Standard 동시 비교

4. **Advanced Settings** (Agentic 모드)
   - Grading Threshold: 0.7 (기본값)
   - Max Retries: 3 (기본값)
   - Enable Validation: ✓
   - Enable Reflection: ✓

### 질문 예시

**간단한 질문** (Standard mode):
```
Q: 재택근무 승인자는?
```

**복잡한 질문** (Agentic mode 추천):
```
Q: 누나가 결혼하면 경조금은 얼마이고, 백신 휴가는 며칠까지 가능한가요?
```

**비교 테스트**:
1. 비교 모드 활성화
2. 동일한 질문 입력
3. 양쪽 결과 비교

---

## 🎯 UI 기능 상세 설명

### 📊 Metrics Dashboard (app_agentic_v2.py)

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Retrieved    │ Relevant     │ Reasoning    │ Confidence   │
│    Docs      │    Docs      │    Hops      │    Score     │
├──────────────┼──────────────┼──────────────┼──────────────┤
│     15       │      8       │      2       │     92%      │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

- **Retrieved Docs**: 초기 검색된 문서 수
- **Relevant Docs**: Grader Agent가 선택한 관련 문서 수
- **Reasoning Hops**: 추론 단계 수 (Multi-hop)
- **Confidence Score**: Validation Agent의 신뢰도

### 🔄 Execution Pipeline Timeline

각 Agent의 실행 과정을 시간순으로 표시:

```
🎯 PLAN    → Query decomposition, strategy selection
🔍 RETRIEVE → Hybrid search (vector + keyword + graph)
⭐ GRADE    → Document relevance scoring
🧠 REASON   → Multi-hop reasoning
✅ VALIDATE → Fact checking, confidence scoring
💡 ANSWER   → Final answer with citations
```

실패 시:
```
🔄 REFLECT  → Analyze failure, create retry plan
```

### 🧠 Reasoning Chain

각 추론 단계를 카드로 표시:

```
┌─ STEP 1 ───────────────────────┐
│ ✅ Complete                     │
│ 재택근무 승인 절차를 찾았습니다    │
└─────────────────────────────────┘

┌─ STEP 2 ───────────────────────┐
│ 🔄 Needs more context           │
│ 승인자 정보가 필요합니다          │
└─────────────────────────────────┘
```

### 📚 Citation Cards

문서 출처와 Relevance score 표시:

```
┌─ 📄 Citation 1: 회사규정.docx ─────────────┐
│ Relevance: █████████░ 95% [HIGH]          │
│                                            │
│ 재택근무는 팀장의 사전 승인을 받아야...      │
└────────────────────────────────────────────┘
```

- **Progress Bar**: Relevance score 시각화
- **Badge**: HIGH/MEDIUM/LOW 표시
- **Hover Effect**: 마우스 오버 시 확대

---

## 🐛 문제 해결

### 1. "Pipeline not initialized"
```
해결: Sidebar에서 "🚀 Initialize Pipeline" 클릭
```

### 2. "No data found"
```
해결:
1. python run_pipeline.py data/documents/
2. Web UI에서 "🔄 Initialize Pipeline" 재클릭
```

### 3. "Connection refused to Ollama"
```
해결:
1. config.toml에서 ollama_url 확인
2. Ollama 서버 실행 상태 확인
3. 방화벽 설정 확인
```

### 4. "ModuleNotFoundError: streamlit"
```
해결: pip install streamlit
```

### 5. 화면이 깨짐/느림
```
해결:
1. 브라우저 캐시 삭제 (Ctrl+F5)
2. 다른 브라우저 시도 (Chrome 추천)
3. Streamlit 업데이트: pip install --upgrade streamlit
```

---

## 🔥 고급 사용법

### 1. 커스텀 포트 설정

**config 파일 생성**:
```bash
# .streamlit/config.toml 생성
mkdir .streamlit
cat > .streamlit/config.toml << EOF
[server]
port = 8510
headless = true

[browser]
gatherUsageStats = false
EOF
```

**실행**:
```bash
streamlit run app_agentic_v2.py
# 자동으로 8510 포트 사용
```

### 2. 외부 접속 허용

```bash
streamlit run app_agentic_v2.py \
  --server.port 8501 \
  --server.address 0.0.0.0
```

**보안 주의**: 프로덕션 환경에서는 인증 추가 필요

### 3. 백그라운드 실행

**Windows**:
```bash
start /B streamlit run app_agentic_v2.py --server.port 8501
```

**Linux/Mac**:
```bash
nohup streamlit run app_agentic_v2.py --server.port 8501 > webui.log 2>&1 &
```

### 4. Docker로 실행 (향후 추가 예정)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app_agentic_v2.py", "--server.port", "8501"]
```

---

## 📊 성능 최적화

### 1. Streamlit 캐싱 활용
코드에 이미 적용되어 있음:
```python
@st.cache_resource
def load_pipeline():
    # Pipeline은 한 번만 로드
    ...
```

### 2. 메모리 관리
- Chat history는 세션별로 관리
- "🗑️ Clear History" 버튼으로 초기화

### 3. 응답 속도 개선
- Standard mode: ~2-3초
- Agentic mode: ~5-10초 (validation + reflection)
- Grading threshold 조정으로 속도 향상 가능

---

## 📚 추가 리소스

- [Streamlit 공식 문서](https://docs.streamlit.io)
- [Agentic RAG 아키텍처](docs/agentic_graphrag_design.md)
- [Quick Start Guide](QUICKSTART.md)
- [GitHub Repository](https://github.com/laurus-kpa007/GraphRAG-Senzing)

---

**모든 준비 완료!** 🎉

```bash
# Let's go!
streamlit run app_agentic_v2.py --server.port 8501
```
