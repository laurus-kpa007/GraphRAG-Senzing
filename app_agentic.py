"""
Modern Agentic GraphRAG Web UI with real-time execution visualization.

Features:
- Real-time agent execution tracking
- Step-by-step reasoning visualization
- Document grading and relevance scores
- Validation results and confidence metrics
- Full audit trail with citations
"""

import json
import pathlib
import time
from typing import Any

import streamlit as st

from src.pipeline import AgenticPipeline

# ══════════════════════════════════════════════════════════════════════════════
# Page Configuration
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🤖 Agentic GraphRAG",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Modern card styling */
    .stCard {
        border-radius: 10px;
        padding: 20px;
        background-color: #f8f9fa;
        border: 1px solid #e0e0e0;
        margin: 10px 0;
    }

    /* Agent step badges */
    .agent-badge {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: 600;
        margin: 5px 5px 5px 0;
    }

    .badge-plan { background-color: #e3f2fd; color: #1976d2; }
    .badge-retrieve { background-color: #f3e5f5; color: #7b1fa2; }
    .badge-grade { background-color: #fff3e0; color: #f57c00; }
    .badge-reason { background-color: #e8f5e9; color: #388e3c; }
    .badge-validate { background-color: #fce4ec; color: #c2185b; }
    .badge-reflect { background-color: #fff9c4; color: #f9a825; }

    /* Progress indicators */
    .step-active {
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
    }

    /* Citation cards */
    .citation-card {
        background-color: #ffffff;
        border-left: 4px solid #4caf50;
        padding: 12px;
        margin: 8px 0;
        border-radius: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Confidence score */
    .confidence-high { color: #4caf50; font-weight: bold; }
    .confidence-medium { color: #ff9800; font-weight: bold; }
    .confidence-low { color: #f44336; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Session State Initialization
# ══════════════════════════════════════════════════════════════════════════════

if "pipeline" not in st.session_state:
    st.session_state.pipeline = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_execution" not in st.session_state:
    st.session_state.current_execution = None
if "mode" not in st.session_state:
    st.session_state.mode = "agentic"  # "agentic" or "standard"

# ══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_confidence_class(confidence: float) -> str:
    """Get CSS class for confidence score."""
    if confidence >= 0.8:
        return "confidence-high"
    elif confidence >= 0.6:
        return "confidence-medium"
    else:
        return "confidence-low"


def format_agent_badge(agent_name: str, status: str = "completed") -> str:
    """Format agent execution badge."""
    badge_class = f"badge-{agent_name.lower()}"
    icon = "✓" if status == "completed" else "⟳"
    return f'<span class="agent-badge {badge_class}">{icon} {agent_name.upper()}</span>'


def render_reasoning_chain(reasoning_chain: list[dict]) -> None:
    """Render reasoning chain with expandable steps."""
    if not reasoning_chain:
        return

    st.markdown("### 🧠 Reasoning Chain")

    for step in reasoning_chain:
        step_num = step.get("step", 0)
        answer = step.get("answer", "")
        needs_more = step.get("needs_more", False)

        status_icon = "🔄" if needs_more else "✓"
        status_text = "Need more info" if needs_more else "Complete"

        with st.expander(f"{status_icon} Step {step_num}: {status_text}", expanded=(step_num == 1)):
            st.markdown(answer)


def render_citations(citations: list[dict]) -> None:
    """Render citation cards with relevance scores."""
    if not citations:
        return

    st.markdown("### 📚 Citations & Sources")

    for i, citation in enumerate(citations, 1):
        source = pathlib.Path(citation.get("source", "unknown")).name
        text = citation.get("text", "")
        relevance = citation.get("relevance", 0.0)

        confidence_class = get_confidence_class(relevance)

        st.markdown(f"""
        <div class="citation-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div><strong>📄 Citation {i}</strong>: {source}</div>
                <div class="{confidence_class}">Relevance: {relevance:.2%}</div>
            </div>
            <div style="margin-top: 8px; color: #666; font-size: 14px;">
                {text}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_execution_history(history: list[str]) -> None:
    """Render execution history timeline."""
    if not history:
        return

    st.markdown("### 📊 Execution Timeline")

    for event in history:
        # Parse event (format: "AGENT: details")
        if ":" in event:
            agent, details = event.split(":", 1)
            badge = format_agent_badge(agent.strip())
            st.markdown(f"{badge} {details.strip()}", unsafe_allow_html=True)
        else:
            st.markdown(f"• {event}")


def render_validation_result(validation: dict) -> None:
    """Render validation result with confidence score."""
    if not validation:
        return

    valid = validation.get("valid")
    confidence = validation.get("confidence", 0.0)

    if valid is None:
        return

    st.markdown("### ✅ Validation Result")

    col1, col2 = st.columns(2)

    with col1:
        if valid:
            st.success("✓ Answer validated successfully")
        else:
            st.error("✗ Validation failed")

    with col2:
        confidence_class = get_confidence_class(confidence)
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
            <div style="font-size: 14px; color: #666;">Confidence Score</div>
            <div class="{confidence_class}" style="font-size: 32px; margin-top: 5px;">
                {confidence:.0%}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_metadata(metadata: dict) -> None:
    """Render execution metadata."""
    if not metadata:
        return

    st.markdown("### 📈 Execution Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Strategy",
            metadata.get("strategy", "N/A").upper(),
            delta=None
        )

    with col2:
        st.metric(
            "Retrieved Docs",
            metadata.get("num_retrieved", 0),
            delta=None
        )

    with col3:
        relevant = metadata.get("num_relevant", 0)
        total = metadata.get("num_retrieved", 1)
        relevance_rate = (relevant / total * 100) if total > 0 else 0
        st.metric(
            "Relevant Docs",
            relevant,
            delta=f"{relevance_rate:.0f}% relevant"
        )

    with col4:
        sub_queries = metadata.get("sub_queries", [])
        st.metric(
            "Sub-queries",
            len(sub_queries),
            delta=None
        )


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🤖 Agentic GraphRAG")
    st.caption("Multi-Agent RAG with Planning, Reflection & Validation")

    st.divider()

    # Mode selection
    st.subheader("⚙️ Mode")
    mode = st.radio(
        "Select RAG mode:",
        ["🤖 Agentic (Multi-Agent)", "📊 Standard (Hybrid)"],
        index=0 if st.session_state.mode == "agentic" else 1,
        help="Agentic mode uses Planning, Grading, Reasoning, Validation, and Reflection agents"
    )
    st.session_state.mode = "agentic" if "Agentic" in mode else "standard"

    st.divider()

    # System status
    st.subheader("🔧 System Status")

    if st.button("🔄 Initialize Pipeline"):
        with st.spinner("Initializing pipeline..."):
            try:
                pipeline = AgenticPipeline()
                pipeline.initialize()

                # Load existing data
                result = pipeline.load_existing_data()

                st.session_state.pipeline = pipeline

                if result["success"]:
                    st.success(f"✓ {result['message']}")
                else:
                    st.warning(f"⚠️ {result['message']}")

            except Exception as e:
                st.error(f"❌ Initialization failed: {e}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

    if st.session_state.pipeline:
        st.success("✓ Pipeline ready")

        # Show stats
        pipeline = st.session_state.pipeline
        st.metric("Chunks", len(pipeline._chunks) if pipeline._chunks else 0)
        st.metric("Entities", len(pipeline._entities) if pipeline._entities else 0)
    else:
        st.warning("⚠️ Pipeline not initialized")

    st.divider()

    # Agentic settings (only in agentic mode)
    if st.session_state.mode == "agentic":
        st.subheader("🎛️ Agentic Settings")

        enable_validation = st.checkbox("Enable Validation", value=True)
        enable_reflection = st.checkbox("Enable Reflection", value=True)
        enable_tracing = st.checkbox("Show Execution Trace", value=True)

        max_retries = st.slider("Max Retries", 0, 5, 3)
        grading_threshold = st.slider("Grading Threshold", 0.0, 1.0, 0.7, 0.05)

    st.divider()

    # Clear history
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# Main Content
# ══════════════════════════════════════════════════════════════════════════════

st.title("🤖 Agentic GraphRAG Interface")

if st.session_state.mode == "agentic":
    st.markdown("""
    **Multi-Agent Pipeline**: Planning → Retrieval → Grading → Reasoning → Validation → (Reflection)

    Real-time visualization of each agent's execution with full transparency.
    """)
else:
    st.markdown("""
    **Standard Hybrid Search**: Vector (BGE-M3) + Keyword + Graph expansion

    Fast and efficient retrieval without agent orchestration.
    """)

st.divider()

# Chat interface
st.subheader("💬 Ask a Question")

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Show execution details for agentic responses
        if message["role"] == "assistant" and "execution" in message:
            execution = message["execution"]

            # Create tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 Overview",
                "🧠 Reasoning",
                "📚 Citations",
                "🔍 Details"
            ])

            with tab1:
                # Validation result
                if execution.get("validation"):
                    render_validation_result(execution["validation"])

                # Metadata
                if execution.get("metadata"):
                    render_metadata(execution["metadata"])

                # Retry count
                retry_count = execution.get("retry_count", 0)
                if retry_count > 0:
                    st.info(f"🔄 Retries: {retry_count}")

            with tab2:
                # Reasoning chain
                if execution.get("reasoning_chain"):
                    render_reasoning_chain(execution["reasoning_chain"])
                else:
                    st.info("No reasoning chain available (standard mode)")

            with tab3:
                # Citations
                if execution.get("citations"):
                    render_citations(execution["citations"])
                else:
                    st.info("No citations available")

            with tab4:
                # Execution history
                if execution.get("execution_history"):
                    render_execution_history(execution["execution_history"])

                # Full result (expandable)
                with st.expander("🔧 Raw Execution Data"):
                    st.json(execution)

# Chat input
if question := st.chat_input("Enter your question..."):
    if not st.session_state.pipeline:
        st.error("❌ Please initialize the pipeline first (use sidebar button)")
    else:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(question)

        # Generate response
        with st.chat_message("assistant"):
            # Create placeholder for streaming output
            status_placeholder = st.empty()
            answer_placeholder = st.empty()

            try:
                pipeline = st.session_state.pipeline

                # Show processing status
                if st.session_state.mode == "agentic":
                    status_placeholder.info("🤖 Agentic RAG processing...")
                else:
                    status_placeholder.info("📊 Standard search processing...")

                # Execute query
                start_time = time.time()
                result = pipeline.query(
                    question,
                    agentic=(st.session_state.mode == "agentic")
                )
                elapsed = time.time() - start_time

                # Clear status
                status_placeholder.empty()

                # Display answer
                answer = result.get("answer", "No answer generated.")
                answer_placeholder.markdown(answer)

                # Show elapsed time
                st.caption(f"⏱️ Response time: {elapsed:.2f}s")

                # Add assistant message to history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": answer,
                    "execution": result if st.session_state.mode == "agentic" else {
                        "elapsed": elapsed,
                        "num_chunks": result.get("num_chunks", 0),
                        "sources": result.get("sources", [])
                    }
                })

                # Show execution details (for current message)
                if st.session_state.mode == "agentic":
                    # Create tabs for different views
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📊 Overview",
                        "🧠 Reasoning",
                        "📚 Citations",
                        "🔍 Details"
                    ])

                    with tab1:
                        if result.get("validation"):
                            render_validation_result(result["validation"])

                        if result.get("metadata"):
                            render_metadata(result["metadata"])

                        retry_count = result.get("retry_count", 0)
                        if retry_count > 0:
                            st.info(f"🔄 Retries: {retry_count}")

                    with tab2:
                        if result.get("reasoning_chain"):
                            render_reasoning_chain(result["reasoning_chain"])

                    with tab3:
                        if result.get("citations"):
                            render_citations(result["citations"])

                    with tab4:
                        if result.get("execution_history"):
                            render_execution_history(result["execution_history"])

                        with st.expander("🔧 Raw Execution Data"):
                            st.json(result)
                else:
                    # Standard mode - show simpler info
                    st.info(f"📊 Retrieved {result.get('num_chunks', 0)} chunks in {elapsed:.2f}s")

                    if result.get("sources"):
                        with st.expander("📁 Sources"):
                            for source in result["sources"]:
                                st.markdown(f"- {pathlib.Path(source).name}")

            except Exception as e:
                status_placeholder.empty()
                st.error(f"❌ Error: {e}")
                import traceback
                with st.expander("🔧 Error Details"):
                    st.code(traceback.format_exc())

# ══════════════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════════════

st.divider()

st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    <p>
        🤖 <strong>Agentic GraphRAG</strong> - Multi-Agent RAG with Planning, Reflection & Validation<br>
        Built with <a href="https://streamlit.io">Streamlit</a> |
        Powered by <a href="https://ollama.ai">Ollama</a> (BGE-M3 + Gemma3)
    </p>
    <p>
        <a href="https://github.com/laurus-kpa007/GraphRAG-Senzing">GitHub</a> |
        <a href="docs/agentic_graphrag_design.md">Architecture Docs</a>
    </p>
</div>
""", unsafe_allow_html=True)
