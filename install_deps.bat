@echo off
echo ============================================================
echo Installing GraphRAG-Senzing Dependencies
echo ============================================================
echo.

echo [1/4] Installing core dependencies...
pip install httpx pydantic certifi requests

echo.
echo [2/4] Installing vector database and data processing...
pip install lancedb pyarrow numpy polars

echo.
echo [3/4] Installing NLP and text processing...
pip install spacy gensim

echo.
echo [4/4] Installing graph, web UI, and optional tools...
pip install networkx rdflib pyvis streamlit python-docx chardet markdown-it-py beautifulsoup4 requests-cache pyinstrument

echo.
echo ============================================================
echo Installation complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Download spaCy Korean model:
echo      python -m spacy download ko_core_news_lg
echo.
echo   2. Process documents:
echo      python run_pipeline.py data/documents/
echo.
echo   3. Test Agentic RAG:
echo      python test_agentic.py
echo.
