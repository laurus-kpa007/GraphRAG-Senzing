#!/bin/bash
# GraphRAG-Senzing 환경 설정 스크립트
# 실행: bash setup.sh

set -e

PYTHON=${PYTHON:-python3}

echo "============================================"
echo "  GraphRAG-Senzing 환경 설정"
echo "============================================"

# 1. Python 의존성 설치
echo ""
echo "[1/5] Python 의존성 설치 중..."
$PYTHON -m pip install python-docx chardet markdown-it-py httpx lancedb pyarrow \
    numpy streamlit spacy gensim networkx pydantic certifi \
    beautifulsoup4 requests requests-cache rdflib polars

# 2. SSL 인증서 설정 (spaCy 다운로드 SSL 에러 방지)
echo ""
echo "[2/5] SSL 인증서 확인 중..."
SSL_CERT=$($PYTHON -c "import certifi; print(certifi.where())" 2>/dev/null || echo "")
if [ -n "$SSL_CERT" ]; then
    export SSL_CERT_FILE="$SSL_CERT"
    export REQUESTS_CA_BUNDLE="$SSL_CERT"
    echo "  인증서 경로: $SSL_CERT"
fi

# spaCy 모델 설치 함수 (SSL 에러 시 pip 직접 설치로 폴백)
install_spacy_model() {
    local MODEL_NAME=$1
    local WHL_URL=$2

    echo "  $MODEL_NAME 설치 시도 중..."

    # 시도 1: spacy download
    if $PYTHON -m spacy download "$MODEL_NAME" 2>/dev/null; then
        echo "  ✓ $MODEL_NAME 설치 완료"
        return 0
    fi

    # 시도 2: pip로 whl 직접 설치
    echo "  spacy download 실패, pip 직접 설치 시도..."
    if $PYTHON -m pip install "$WHL_URL" 2>/dev/null; then
        echo "  ✓ $MODEL_NAME 설치 완료 (pip whl)"
        return 0
    fi

    # 시도 3: trusted-host 추가
    echo "  SSL 우회 설치 시도..."
    if $PYTHON -m pip install \
        --trusted-host github.com \
        --trusted-host objects.githubusercontent.com \
        "$WHL_URL" 2>/dev/null; then
        echo "  ✓ $MODEL_NAME 설치 완료 (SSL 우회)"
        return 0
    fi

    echo "  ✗ $MODEL_NAME 자동 설치 실패."
    echo "    수동 설치 방법:"
    echo "    1. 브라우저에서 다운로드: $WHL_URL"
    echo "    2. pip install ./<다운로드된 파일>.whl"
    echo "    또는 --skip-nlp 옵션으로 NLP 없이 실행 가능"
    return 1
}

# 3. spaCy 모델 다운로드
echo ""
echo "[3/5] spaCy 모델 다운로드 중..."

install_spacy_model "en_core_web_md" \
    "https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl" || true

echo ""
install_spacy_model "ko_core_news_lg" \
    "https://github.com/explosion/spacy-models/releases/download/ko_core_news_lg-3.8.0/ko_core_news_lg-3.8.0-py3-none-any.whl" || true
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
    echo "    ollama serve"
    echo "    ollama pull bona/bge-m3:latest"
    echo "    ollama pull gemma3:27b"
fi

# 5. 디렉토리 생성
echo ""
echo "[5/5] 디렉토리 생성 중..."
mkdir -p data/documents data/cache data/lancedb data/output data/uploads

# 설치 검증
echo ""
echo "============================================"
echo "  설치 검증"
echo "============================================"
echo ""

$PYTHON -c "
import sys
checks = []

# Python version
v = sys.version_info
checks.append(('Python >= 3.11', v >= (3, 11)))

# Core packages
for pkg in ['docx', 'chardet', 'httpx', 'lancedb', 'numpy', 'spacy', 'streamlit']:
    try:
        __import__(pkg)
        checks.append((pkg, True))
    except ImportError:
        checks.append((pkg, False))

# spaCy models
import spacy
for model in ['en_core_web_md', 'ko_core_news_lg']:
    try:
        spacy.load(model)
        checks.append((f'spaCy {model}', True))
    except OSError:
        checks.append((f'spaCy {model}', False))

for name, ok in checks:
    icon = '✓' if ok else '✗'
    print(f'  {icon} {name}')

failed = [n for n, ok in checks if not ok]
if failed:
    print(f'\n  경고: {len(failed)}개 항목 미설치 ({', '.join(failed)})')
    print('  --skip-nlp 옵션으로 NLP 없이도 실행 가능합니다.')
else:
    print('\n  모든 의존성 설치 완료!')
"

echo ""
echo "============================================"
echo "  설정 완료!"
echo "============================================"
echo ""
echo "다음 단계:"
echo "  1. Ollama 서버 시작:  ollama serve"
echo "  2. 상태 확인:         python run_pipeline.py --check"
echo "  3. 문서 추가:         cp *.docx *.txt *.md data/documents/"
echo "  4-A. CLI 실행:        python run_pipeline.py data/documents/"
echo "  4-B. 웹 UI 실행:     streamlit run app.py"
echo ""
