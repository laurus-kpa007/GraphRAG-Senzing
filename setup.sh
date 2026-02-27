#!/bin/bash
# GraphRAG-Senzing 환경 설정 스크립트
# 실행: bash setup.sh

set -e

echo "============================================"
echo "  GraphRAG-Senzing 환경 설정"
echo "============================================"

# 1. Python 의존성 설치
echo ""
echo "[1/5] Python 의존성 설치 중..."
pip install python-docx chardet markdown-it-py httpx lancedb pyarrow \
    numpy streamlit spacy gensim networkx pydantic tomli \
    beautifulsoup4 requests requests-cache rdflib polars 2>/dev/null || \
pip3 install python-docx chardet markdown-it-py httpx lancedb pyarrow \
    numpy streamlit spacy gensim networkx pydantic tomli \
    beautifulsoup4 requests requests-cache rdflib polars

# 2. spaCy 영어 모델 다운로드
echo ""
echo "[2/5] spaCy 영어 모델 다운로드 중..."
python -m spacy download en_core_web_md 2>/dev/null || \
python3 -m spacy download en_core_web_md 2>/dev/null || \
echo "  경고: spaCy 영어 모델 설치 실패. 수동 설치: python -m spacy download en_core_web_md"

# 3. spaCy 한국어 모델 다운로드
echo ""
echo "[3/5] spaCy 한국어 모델 다운로드 중..."
python -m spacy download ko_core_news_lg 2>/dev/null || \
python3 -m spacy download ko_core_news_lg 2>/dev/null || \
echo "  경고: 한국어 모델 설치 실패. 수동 설치: python -m spacy download ko_core_news_lg"
echo "  (한국어 NLP가 필요하지 않으면 무시해도 됩니다)"

# 4. Ollama 모델 확인 및 안내
echo ""
echo "[4/5] Ollama 모델 확인 중..."
if command -v ollama &> /dev/null; then
    echo "  Ollama 발견. 모델 다운로드 중..."
    ollama pull bona/bge-m3:latest || echo "  경고: bge-m3 다운로드 실패. 수동 실행: ollama pull bona/bge-m3:latest"
    ollama pull gemma3:27b || echo "  경고: gemma3:27b 다운로드 실패. 수동 실행: ollama pull gemma3:27b"
else
    echo "  경고: Ollama를 찾을 수 없습니다. https://ollama.ai 에서 설치하세요."
    echo "  설치 후 실행:"
    echo "    ollama pull bona/bge-m3:latest"
    echo "    ollama pull gemma3:27b"
fi

# 5. 디렉토리 생성
echo ""
echo "[5/5] 디렉토리 생성 중..."
mkdir -p data/documents data/cache data/lancedb data/output data/uploads

echo ""
echo "============================================"
echo "  설정 완료!"
echo "============================================"
echo ""
echo "사용법:"
echo "  # data/documents/ 폴더에 문서를 넣으세요"
echo "  # (.docx, .txt, .md 파일 - 한글/영어 모두 지원)"
echo "  # 그 후 실행:"
echo "  python run_pipeline.py data/documents/"
echo ""
echo "  # 또는 Streamlit 웹 UI 사용:"
echo "  streamlit run app.py"
echo ""
echo "  # 시스템 상태 확인:"
echo "  python run_pipeline.py --check"
echo ""
