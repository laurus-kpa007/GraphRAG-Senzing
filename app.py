"""
Streamlit Web UI for GraphRAG-Senzing.
Provides document upload, pipeline execution, and interactive Q&A.
"""

import json
import logging
import pathlib
import time

import streamlit as st

from src.pipeline import AgenticPipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ── Page Config ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="GraphRAG-Senzing",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Session State Init ───────────────────────────────────────────────

if "pipeline" not in st.session_state:
    st.session_state.pipeline = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pipeline_summary" not in st.session_state:
    st.session_state.pipeline_summary = None


# ── Sidebar ──────────────────────────────────────────────────────────

with st.sidebar:
    st.title("GraphRAG-Senzing")
    st.caption("Agentic GraphRAG 파이프라인")

    st.divider()

    st.subheader("모델 설정")

    with open("config.toml", "rb") as f:
        import tomllib
        config = tomllib.load(f)

    lm_name = config["rag"]["lm_name"].replace("ollama_chat/", "")
    embed_name = config["embed"]["model"]

    st.markdown(f"**LLM:** `{lm_name}`")
    st.markdown(f"**Embeddings:** `{embed_name}`")
    st.markdown(f"**Vector dim:** `{config['embed']['dim']}`")
    st.markdown(f"**Chunk size:** `{config['vect']['chunk_size']}`")

    st.divider()

    st.subheader("파이프라인 상태")
    if st.session_state.pipeline_summary:
        s = st.session_state.pipeline_summary
        st.success("파이프라인 실행 중")
        st.metric("문서 수", s["documents_loaded"])
        st.metric("청크 수", s["chunks_stored"])
        st.metric("단락 수", s["total_paragraphs"])
    else:
        st.info("파이프라인이 실행되지 않았습니다. 문서를 업로드하세요.")


# ── Main Content ─────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs(["문서 업로드 & 파이프라인", "Q&A 채팅", "시스템 상태"])


# ── Tab 1: Document Upload ───────────────────────────────────────────

with tab1:
    st.header("문서 업로드 & 파이프라인 실행")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("문서 업로드")
        uploaded_files = st.file_uploader(
            ".docx, .txt, .md 파일을 업로드하세요 (한글 문서 지원)",
            type=["docx", "txt", "md", "markdown", "text"],
            accept_multiple_files=True,
        )

        doc_dir = st.text_input(
            "또는 디렉토리 경로 입력:",
            placeholder="data/documents",
        )

    with col2:
        st.subheader("파이프라인 옵션")
        skip_nlp = st.checkbox("NLP 추출 건너뛰기 (빠른 모드)", value=False)
        batch_size = st.slider("임베딩 배치 크기", 1, 32, 8)

    if st.button("파이프라인 실행", type="primary", use_container_width=True):
        input_paths = []

        # Save uploaded files to temp directory
        if uploaded_files:
            upload_dir = pathlib.Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)

            for uf in uploaded_files:
                save_path = upload_dir / uf.name
                save_path.write_bytes(uf.getvalue())
                input_paths.append(str(save_path))
                st.toast(f"Saved: {uf.name}")

        if doc_dir and pathlib.Path(doc_dir).exists():
            input_paths.append(doc_dir)

        if not input_paths:
            st.error("파일을 업로드하거나 디렉토리 경로를 입력하세요.")
        else:
            with st.status("Agentic 파이프라인 실행 중...", expanded=True) as status:
                try:
                    pipeline = AgenticPipeline()

                    st.write("사전 요구사항 확인 중...")
                    prereqs = pipeline.check_prerequisites()
                    for k, v in prereqs.items():
                        st.write(f"  {'✓' if v else '✗'} {k}")

                    if not prereqs["embed_model"]:
                        st.error(
                            f"임베딩 모델을 찾을 수 없습니다. "
                            f"실행: `ollama pull {config['embed']['model']}`"
                        )
                        st.stop()

                    st.write("파이프라인 초기화 중...")
                    pipeline.initialize()

                    st.write("문서 로딩 중...")
                    documents = pipeline.load_documents(input_paths)
                    st.write(f"  {len(documents)}개 문서 로드 완료")

                    st.write("임베딩 및 벡터 저장 중...")
                    num_chunks = pipeline.embed_and_store(documents, batch_size=batch_size)
                    st.write(f"  {num_chunks}개 청크 저장 완료")

                    if not skip_nlp:
                        st.write("NLP 엔티티 추출 중 (한글 지원)...")
                        pipeline.run_nlp_pipeline(documents)
                        st.write("  NLP 추출 완료")

                    summary = {
                        "documents_loaded": len(documents),
                        "total_paragraphs": sum(len(v) for v in documents.values()),
                        "chunks_stored": num_chunks,
                        "sources": list(documents.keys()),
                    }

                    st.session_state.pipeline = pipeline
                    st.session_state.pipeline_summary = summary
                    status.update(label="파이프라인 완료!", state="complete")

                except Exception as e:
                    status.update(label="파이프라인 실패", state="error")
                    st.error(f"오류: {e}")
                    logger.exception("Pipeline failed")


# ── Tab 2: Q&A Chat ─────────────────────────────────────────────────

with tab2:
    st.header("GraphRAG 질의응답")

    if st.session_state.pipeline is None:
        st.warning("먼저 파이프라인을 실행하세요 (첫 번째 탭).")
    else:
        # Display chat history
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "metadata" in msg:
                    meta = msg["metadata"]
                    st.caption(
                        f"⏱ {meta.get('elapsed_sec', '?')}s | "
                        f"📄 {meta.get('num_chunks', '?')} chunks | "
                        f"📁 {', '.join(pathlib.Path(s).name for s in meta.get('sources', []))}"
                    )

        # Chat input
        if question := st.chat_input("문서에 대해 질문하세요 (한국어/영어 모두 가능)..."):
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("답변 생성 중..."):
                    result = st.session_state.pipeline.query(
                        question,
                        conversation_history=st.session_state.messages,
                    )

                st.markdown(result["answer"])
                st.caption(
                    f"⏱ {result['elapsed_sec']}s | "
                    f"📄 {result['num_chunks']} chunks | "
                    f"📁 {', '.join(pathlib.Path(s).name for s in result['sources'])}"
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "metadata": result,
                })

            # Show retrieved chunks in expander
            with st.expander("검색된 청크 보기", expanded=False):
                for i, chunk in enumerate(result.get("chunks", [])):
                    st.text(f"[{i+1}] {chunk}...")

        # Clear chat
        if st.button("채팅 초기화"):
            st.session_state.messages = []
            st.rerun()


# ── Tab 3: System Status ────────────────────────────────────────────

with tab3:
    st.header("시스템 상태")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ollama 서비스")
        if st.button("상태 확인"):
            try:
                pipeline = AgenticPipeline()
                prereqs = pipeline.check_prerequisites()
                for key, val in prereqs.items():
                    if val:
                        st.success(f"{key}: 사용 가능")
                    else:
                        st.error(f"{key}: 사용 불가")
            except Exception as e:
                st.error(f"상태 확인 오류: {e}")

    with col2:
        st.subheader("엔티티 저장소")
        store_path = pathlib.Path(config["ent"]["store_path"])
        if store_path.exists():
            ent_count = sum(1 for _ in open(store_path, encoding="utf-8"))
            st.metric("엔티티 수", ent_count)
        else:
            st.info("아직 엔티티 저장소가 없습니다")

        st.subheader("벡터 저장소")
        lance_dir = pathlib.Path(config["vect"]["lancedb_uri"])
        if lance_dir.exists():
            st.success(f"LanceDB: {lance_dir}")
            try:
                db = lancedb.connect(str(lance_dir))
                tables = db.table_names()
                st.write(f"테이블: {tables}")
            except Exception:
                st.info("LanceDB 비어있음")
        else:
            st.info("아직 벡터 저장소가 없습니다")

    st.divider()

    st.subheader("설정 정보")
    st.json(config)
