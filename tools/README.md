# GraphRAG-Senzing Tools

유틸리티 도구 모음

## 📊 visualize_graph.py

Knowledge Graph를 인터랙티브 HTML로 시각화합니다.

### 사용법

```bash
# ERKG (Entity-Relation Knowledge Graph) 시각화
python tools/visualize_graph.py --graph erkg

# Lexical Graph (TextRank) 시각화
python tools/visualize_graph.py --graph lex

# 커스텀 출력 경로
python tools/visualize_graph.py --graph erkg --output my_graph.html

# 정적 PNG 이미지로 저장
python tools/visualize_graph.py --graph erkg --format png
```

### 옵션

- `--graph` : 시각화할 그래프 (`erkg` 또는 `lex`)
- `--config` : 설정 파일 경로 (기본값: `config.toml`)
- `--output` : 출력 파일 경로
- `--format` : 출력 형식 (`html` 또는 `png`)

### 출력 예시

- **ERKG (erkg.html)**: 엔티티와 관계를 노드-엣지 그래프로 표현
  - 노드 색상: 엔티티 타입별 (PERSON, ORG, GPE, LOC, etc.)
  - 노드 크기: 엔티티 언급 빈도
  - 엣지: 엔티티 간 관계

- **Lexical Graph (lex.html)**: TextRank 기반 단어 공기 그래프
  - 노드 크기: TextRank 점수
  - 엣지 굵기: 단어 간 연관성 가중치

### 요구사항

```bash
pip install pyvis  # HTML 인터랙티브 시각화
pip install matplotlib  # PNG 정적 시각화 (선택)
```

## 🔍 search_debug.py

검색이 제대로 작동하지 않을 때 디버깅 도구입니다.

### 사용법

```bash
# 특정 용어 검색 디버깅
python tools/search_debug.py "백신휴가"

# 재택근무 관련 검색
python tools/search_debug.py "재택근무"
```

### 출력 정보

1. **엔티티 검색**: `data/output/ent.json`에서 용어 찾기
2. **청크 검색**: `data/lancedb`의 벡터 저장소에서 용어 찾기
3. **진단 결과**: 용어가 왜 검색되지 않는지 분석

### 일반적인 문제

- **청크에 없음**: 문서가 로드되지 않았거나 용어가 원본에 없음
- **엔티티에 없음**: NLP가 용어를 엔티티로 추출하지 못함
- **검색 안 됨**: 임베딩 유사도 문제 (정확한 구문 사용 필요)

## 🔧 향후 추가 예정

- `export_graph.py` - GraphML, GEXF 등 다양한 형식으로 그래프 내보내기
- `analyze_graph.py` - 그래프 통계 및 중요 노드 분석
- `merge_graphs.py` - 여러 그래프 병합 및 비교
