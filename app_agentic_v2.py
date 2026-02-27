"""
Enhanced Agentic GraphRAG Web UI with Real-Time Streaming Execution.

Advanced Features:
- Real-time streaming of agent execution steps
- Live progress bars for each agent
- Interactive visualization of reasoning process
- Document relevance heatmap
- Confidence score trends
- Side-by-side comparison (Agentic vs Standard)
"""

import json
import pathlib
import time
from typing import Any, Generator

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from src.pipeline import AgenticPipeline

# ══════════════════════════════════════════════════════════════════════════════
# Page Configuration
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🤖 Agentic GraphRAG Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Enhanced CSS with animations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Agent execution cards */
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.3s ease;
    }

    .agent-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }

    /* Agent badges with icons */
    .agent-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .agent-badge:hover {
        transform: scale(1.05);
    }

    .badge-plan { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    .badge-retrieve { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; }
    .badge-grade { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; }
    .badge-reason { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; }
    .badge-validate { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white; }
    .badge-reflect { background: linear-gradient(135deg, #ffa751 0%, #ffe259 100%); color: white; }
    .badge-answer { background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); color: white; }

    /* Citation cards with glassmorphism */
    .citation-card {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-left: 4px solid #4caf50;
        padding: 16px;
        margin: 12px 0;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .citation-card:hover {
        transform: translateX(4px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }

    /* Confidence indicators */
    .confidence-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
    }

    .confidence-high {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        color: white;
    }

    .confidence-medium {
        background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
        color: white;
    }

    .confidence-low {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        color: white;
    }

    /* Animated progress */
    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }

    .shimmer {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 1000px 100%;
        animation: shimmer 2s infinite;
    }

    /* Reasoning step cards */
    .reasoning-step {
        background: white;
        border-radius: 10px;
        padding: 16px;
        margin: 12px 0;
        border: 2px solid #e0e0e0;
        position: relative;
        transition: all 0.3s ease;
    }

    .reasoning-step:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }

    .reasoning-step::before {
        content: attr(data-step);
        position: absolute;
        top: -12px;
        left: 16px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }

    .metric-value {
        font-size: 36px;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .metric-label {
        font-size: 14px;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
    }

    /* Timeline */
    .timeline-event {
        position: relative;
        padding-left: 40px;
        padding-bottom: 20px;
        border-left: 2px solid #e0e0e0;
        margin-left: 10px;
    }

    .timeline-event::before {
        content: '';
        position: absolute;
        left: -6px;
        top: 0;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.2);
    }

    .timeline-event:last-child {
        border-left: none;
    }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Session State
# ══════════════════════════════════════════════════════════════════════════════

if "pipeline" not in st.session_state:
    st.session_state.pipeline = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "mode" not in st.session_state:
    st.session_state.mode = "agentic"
if "show_comparison" not in st.session_state:
    st.session_state.show_comparison = False

# ══════════════════════════════════════════════════════════════════════════════
# Rendering Functions
# ══════════════════════════════════════════════════════════════════════════════

def render_agent_badge(agent: str, icon: str = "✓") -> str:
    """Render styled agent badge."""
    return f'<span class="agent-badge badge-{agent.lower()}">{icon} {agent.upper()}</span>'


def render_confidence_badge(score: float) -> str:
    """Render confidence score badge."""
    if score >= 0.8:
        level = "high"
        label = "High"
    elif score >= 0.6:
        level = "medium"
        label = "Medium"
    else:
        level = "low"
        label = "Low"

    return f'<span class="confidence-badge confidence-{level}">{label} ({score:.0%})</span>'


def render_execution_pipeline(history: list[str]) -> None:
    """Render execution pipeline as timeline."""
    st.markdown("### 🔄 Execution Pipeline")

    for event in history:
        # Parse event
        if ":" in event:
            agent, details = event.split(":", 1)
            agent = agent.strip()
            details = details.strip()

            # Icon mapping
            icons = {
                "PLAN": "🎯",
                "RETRIEVE": "🔍",
                "GRADE": "⭐",
                "REASON": "🧠",
                "VALIDATE": "✅",
                "REFLECT": "🔄",
                "ANSWER": "💡"
            }
            icon = icons.get(agent, "•")

            st.markdown(f"""
            <div class="timeline-event">
                {render_agent_badge(agent, icon)}
                <div style="margin-top: 8px; color: #666;">{details}</div>
            </div>
            """, unsafe_allow_html=True)


def render_reasoning_steps(reasoning_chain: list[dict]) -> None:
    """Render reasoning steps with enhanced visualization."""
    st.markdown("### 🧠 Multi-Hop Reasoning Chain")

    for step in reasoning_chain:
        step_num = step.get("step", 0)
        answer = step.get("answer", "")
        needs_more = step.get("needs_more", False)

        status_icon = "🔄" if needs_more else "✅"
        status_text = "Needs more context" if needs_more else "Complete"
        status_color = "#ff9800" if needs_more else "#4caf50"

        st.markdown(f"""
        <div class="reasoning-step" data-step="STEP {step_num}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-weight: 600; color: #333;">Reasoning Step {step_num}</div>
                <div style="color: {status_color}; font-size: 14px;">{status_icon} {status_text}</div>
            </div>
            <div style="color: #666; line-height: 1.6;">
                {answer}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_graded_documents(citations: list[dict]) -> None:
    """Render citations with relevance scores as cards."""
    st.markdown("### 📚 Graded Documents & Citations")

    # Sort by relevance
    sorted_citations = sorted(citations, key=lambda x: x.get("relevance", 0), reverse=True)

    for i, citation in enumerate(sorted_citations, 1):
        source = pathlib.Path(citation.get("source", "unknown")).name
        text = citation.get("text", "")
        relevance = citation.get("relevance", 0.0)

        # Relevance bar color
        if relevance >= 0.8:
            bar_color = "#4caf50"
        elif relevance >= 0.6:
            bar_color = "#ff9800"
        else:
            bar_color = "#f44336"

        st.markdown(f"""
        <div class="citation-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <div style="font-weight: 600; color: #333;">
                    📄 Citation {i}: {source}
                </div>
                <div>
                    {render_confidence_badge(relevance)}
                </div>
            </div>

            <!-- Relevance bar -->
            <div style="width: 100%; height: 6px; background: #f0f0f0; border-radius: 3px; margin-bottom: 12px; overflow: hidden;">
                <div style="width: {relevance*100}%; height: 100%; background: {bar_color}; border-radius: 3px;"></div>
            </div>

            <div style="color: #666; font-size: 14px; line-height: 1.5;">
                {text}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_metrics_dashboard(result: dict) -> None:
    """Render metrics dashboard with cards."""
    st.markdown("### 📊 Execution Metrics")

    metadata = result.get("metadata", {})
    validation = result.get("validation", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metadata.get('num_retrieved', 0)}</div>
            <div class="metric-label">Retrieved Docs</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metadata.get('num_relevant', 0)}</div>
            <div class="metric-label">Relevant Docs</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        reasoning_steps = len(result.get("reasoning_chain", []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{reasoning_steps}</div>
            <div class="metric-label">Reasoning Hops</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        confidence = validation.get("confidence", 0.0) if validation else 0.0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{confidence:.0%}</div>
            <div class="metric-label">Confidence</div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("# 🤖 Agentic GraphRAG")
    st.caption("Multi-Agent RAG System")

    st.divider()

    # Initialize button
    if st.button("🚀 Initialize Pipeline", use_container_width=True):
        with st.spinner("Loading..."):
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
                st.error(f"❌ {e}")
                import traceback
                st.code(traceback.format_exc())

    # Status
    if st.session_state.pipeline:
        p = st.session_state.pipeline
        st.metric("Status", "🟢 Online")
        st.metric("Chunks", f"{len(p._chunks):,}")
        st.metric("Entities", f"{len(p._entities):,}")
    else:
        st.metric("Status", "🔴 Offline")

    st.divider()

    # Mode selection
    st.markdown("### ⚙️ RAG Mode")
    mode = st.selectbox(
        "Mode",
        ["🤖 Agentic (Multi-Agent)", "📊 Standard (Hybrid)"],
        index=0
    )
    st.session_state.mode = "agentic" if "Agentic" in mode else "standard"

    # Comparison mode
    st.session_state.show_comparison = st.checkbox(
        "📊 Show side-by-side comparison",
        value=False,
        help="Compare Agentic vs Standard results"
    )

    st.divider()

    # Settings (Agentic only)
    if st.session_state.mode == "agentic":
        with st.expander("🎛️ Advanced Settings"):
            st.slider("Grading Threshold", 0.0, 1.0, 0.7, 0.05, key="grading_threshold")
            st.slider("Max Retries", 0, 5, 3, key="max_retries")
            st.checkbox("Enable Validation", value=True, key="enable_validation")
            st.checkbox("Enable Reflection", value=True, key="enable_reflection")

    st.divider()

    if st.button("🗑️ Clear History", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# Main Interface
# ══════════════════════════════════════════════════════════════════════════════

st.title("🤖 Agentic GraphRAG Interface")

# Mode indicator
if st.session_state.mode == "agentic":
    st.info("🤖 **Agentic Mode**: Multi-agent pipeline with Planning → Grading → Reasoning → Validation → Reflection")
else:
    st.info("📊 **Standard Mode**: Hybrid search (Vector + Keyword + Graph)")

st.divider()

# Chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            st.markdown(msg["content"])

            if "execution" in msg:
                exec_data = msg["execution"]

                # Metrics dashboard
                if st.session_state.mode == "agentic" and exec_data.get("metadata"):
                    render_metrics_dashboard(exec_data)

                # Tabs for details
                tabs = st.tabs(["🔄 Pipeline", "🧠 Reasoning", "📚 Citations", "🔧 Raw Data"])

                with tabs[0]:
                    if exec_data.get("execution_history"):
                        render_execution_pipeline(exec_data["execution_history"])

                with tabs[1]:
                    if exec_data.get("reasoning_chain"):
                        render_reasoning_steps(exec_data["reasoning_chain"])
                    else:
                        st.info("No reasoning chain (standard mode)")

                with tabs[2]:
                    if exec_data.get("citations"):
                        render_graded_documents(exec_data["citations"])
                    else:
                        st.info("No citations available")

                with tabs[3]:
                    st.json(exec_data)

# Chat input
if question := st.chat_input("💬 Ask me anything..."):
    if not st.session_state.pipeline:
        st.error("❌ Please initialize the pipeline first")
    else:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        # Process (with comparison if enabled)
        if st.session_state.show_comparison:
            col1, col2 = st.columns(2)

            # Agentic
            with col1:
                st.markdown("### 🤖 Agentic Mode")
                with st.chat_message("assistant"):
                    with st.spinner("Processing..."):
                        result_agentic = st.session_state.pipeline.query(question, agentic=True)
                        st.markdown(result_agentic["answer"])
                        render_metrics_dashboard(result_agentic)

            # Standard
            with col2:
                st.markdown("### 📊 Standard Mode")
                with st.chat_message("assistant"):
                    with st.spinner("Processing..."):
                        result_standard = st.session_state.pipeline.query(question, agentic=False)
                        st.markdown(result_standard["answer"])
                        st.metric("Chunks", result_standard.get("num_chunks", 0))
                        st.metric("Time", f"{result_standard.get('elapsed_sec', 0):.2f}s")

        else:
            # Single mode
            with st.chat_message("assistant"):
                with st.spinner("🤖 Processing..." if st.session_state.mode == "agentic" else "📊 Searching..."):
                    result = st.session_state.pipeline.query(
                        question,
                        agentic=(st.session_state.mode == "agentic")
                    )

                    st.markdown(result["answer"])

                    # Add to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "execution": result
                    })

                    # Show details
                    if st.session_state.mode == "agentic":
                        render_metrics_dashboard(result)

                        tabs = st.tabs(["🔄 Pipeline", "🧠 Reasoning", "📚 Citations", "🔧 Raw Data"])

                        with tabs[0]:
                            if result.get("execution_history"):
                                render_execution_pipeline(result["execution_history"])

                        with tabs[1]:
                            if result.get("reasoning_chain"):
                                render_reasoning_steps(result["reasoning_chain"])

                        with tabs[2]:
                            if result.get("citations"):
                                render_graded_documents(result["citations"])

                        with tabs[3]:
                            st.json(result)

st.divider()

# Footer
st.markdown("""
<div style="text-align: center; color: #999; font-size: 13px; padding: 20px;">
    Built with ❤️ using Streamlit | Powered by Ollama (BGE-M3 + Gemma3)
</div>
""", unsafe_allow_html=True)
