# Agentic GraphRAG Design Document

## Overview

이 문서는 GraphRAG-Senzing의 Agentic RAG 구현 설계를 설명합니다.
2025/2026년 최신 연구와 best practices를 기반으로 합니다.

## Research Foundation

### Key Papers & Resources
- [Agentic RAG Survey (arXiv 2501.09136)](https://arxiv.org/abs/2501.09136)
- [LangChain Agentic RAG Documentation](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
- [Self-Reflective RAG with LangGraph](https://blog.langchain.com/agentic-rag-with-langgraph/)
- [Multi-Agent RAG with Interleaved Retrieval and Reasoning](https://pathway.com/blog/multi-agent-rag-interleaved-retrieval-reasoning)
- [Agentic AI Design Patterns (2026 Edition)](https://medium.com/@dewasheesh.rana/agentic-ai-design-patterns-2026-ed-e3a5125162c5)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agentic GraphRAG Pipeline                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │  Planning Agent │ ◄── Query Decomposition
                     └────────┬────────┘     Multi-step Planning
                              │
                              ▼
                  ┌───────────────────────┐
                  │  Retrieval Orchestrator│
                  └───────────┬───────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    ┌─────────┐        ┌──────────┐        ┌──────────┐
    │ Vector  │        │ Keyword  │        │  Graph   │
    │ Search  │        │  Search  │        │ Traversal│
    └────┬────┘        └─────┬────┘        └────┬─────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Grader Agent    │ ◄── Document Relevance
                    │ (CRAG Pattern)  │     Quality Assessment
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌──────────────────┐         ┌──────────────────┐
    │ Relevant Docs    │         │ Low Quality Docs │
    └────────┬─────────┘         └────────┬─────────┘
             │                            │
             │                            ▼
             │                   ┌─────────────────┐
             │                   │ Web Search      │
             │                   │ (Fallback)      │
             │                   └────────┬────────┘
             │                            │
             └────────────────┬───────────┘
                              ▼
                    ┌──────────────────┐
                    │ Reasoning Agent  │ ◄── Multi-hop Reasoning
                    │ (Interleaved R&R)│     Context Integration
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Validation Agent │ ◄── Fact Checking
                    │ (Self-RAG)       │     Consistency Check
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
    ┌──────────────────┐         ┌──────────────────┐
    │ Valid Answer     │         │ Invalid Answer   │
    └────────┬─────────┘         └────────┬─────────┘
             │                            │
             │                            ▼
             │                   ┌─────────────────┐
             │                   │ Reflection Agent│
             │                   │ (Retry/Rephrase)│
             │                   └────────┬────────┘
             │                            │
             │                            ▼
             │                   (Loop back to Planning)
             │
             ▼
    ┌──────────────────┐
    │ Final Answer     │ ◄── Citations
    │ with Audit Trail │     Confidence Score
    └──────────────────┘
```

## Core Agents

### 1. Planning Agent
**책임**: Query decomposition, multi-step planning
**입력**: User question
**출력**: Execution plan (sub-queries, retrieval strategy)

**알고리즘**:
```python
def plan(question: str) -> Plan:
    # 1. Analyze question complexity
    # 2. Decompose into sub-questions (if multi-hop)
    # 3. Determine retrieval strategy:
    #    - Simple factoid → Vector search
    #    - Complex reasoning → Graph traversal
    #    - Ambiguous → Hybrid (Vector + Keyword + Graph)
    # 4. Set validation criteria
    return Plan(sub_queries, strategy, validation_rules)
```

### 2. Retrieval Orchestrator
**책임**: Execute retrieval strategy, coordinate multiple retrievers
**입력**: Plan
**출력**: Retrieved documents with metadata

**Features**:
- Parallel retrieval (vector + keyword + graph)
- Deduplication and ranking
- Metadata tracking (source, confidence)

### 3. Grader Agent (CRAG Pattern)
**책임**: Document relevance assessment
**입력**: Question + Retrieved documents
**출력**: Graded documents (relevant/irrelevant) + confidence scores

**Corrective RAG (CRAG) Logic**:
```python
def grade_documents(question: str, docs: list[dict]) -> GradedResult:
    relevant_docs = []
    needs_web_search = False

    for doc in docs:
        score = llm.evaluate_relevance(question, doc)

        if score > 0.7:  # High relevance
            relevant_docs.append(doc)
        elif score > 0.4:  # Ambiguous
            needs_web_search = True
        # else: Irrelevant (discard)

    if needs_web_search:
        web_docs = web_search(question)
        relevant_docs.extend(web_docs)

    return GradedResult(relevant_docs, needs_web_search)
```

### 4. Reasoning Agent (Interleaved Retrieval & Reasoning)
**책임**: Multi-hop reasoning, iterative retrieval
**입력**: Question + Graded documents
**출력**: Reasoning chain + answer draft

**Interleaved R&R Pattern**:
```python
def reason(question: str, docs: list[dict]) -> ReasoningResult:
    context = docs
    reasoning_chain = []

    for step in range(max_hops):
        # Generate intermediate answer
        partial_answer = llm.reason(question, context)
        reasoning_chain.append(partial_answer)

        # Check if more info needed
        if is_sufficient(partial_answer):
            break

        # Extract missing info from partial answer
        missing_entities = extract_entities(partial_answer)

        # Retrieve additional context (graph traversal)
        new_docs = graph_search(missing_entities)
        context.extend(new_docs)

    final_answer = synthesize(reasoning_chain)
    return ReasoningResult(final_answer, reasoning_chain, context)
```

### 5. Validation Agent (Self-RAG)
**책임**: Fact checking, consistency verification
**입력**: Answer draft + source documents
**출력**: Validation result (pass/fail) + feedback

**Self-RAG Validation**:
```python
def validate(answer: str, sources: list[dict]) -> ValidationResult:
    # 1. Fact-check: Does answer contradict sources?
    contradictions = check_contradictions(answer, sources)

    # 2. Completeness: Does answer address all parts of question?
    coverage = check_coverage(question, answer)

    # 3. Citation: Are all claims supported by sources?
    unsupported_claims = check_citations(answer, sources)

    if contradictions or coverage < 0.8 or unsupported_claims:
        return ValidationResult(
            valid=False,
            feedback=f"Issues: {contradictions}, {unsupported_claims}"
        )

    return ValidationResult(valid=True, confidence=coverage)
```

### 6. Reflection Agent
**책임**: Analyze failures, generate retry strategies
**입력**: Validation failure + execution history
**출력**: Retry plan (rephrase query, change strategy)

**Reflection Logic**:
```python
def reflect(failure: ValidationResult, history: ExecutionHistory) -> RetryPlan:
    # Analyze failure root cause
    if "no relevant docs found" in failure.feedback:
        # Try query rephrasing
        new_query = rephrase_query(original_query)
        return RetryPlan(action="rephrase", new_query=new_query)

    elif "contradictions" in failure.feedback:
        # Increase grading threshold
        return RetryPlan(action="stricter_grading", threshold=0.8)

    elif attempts > 3:
        # Give up, return best-effort answer with caveats
        return RetryPlan(action="fallback", message="Unable to validate fully")
```

## State Machine (LangGraph-style)

```python
class AgenticRAGState(TypedDict):
    question: str
    plan: Optional[Plan]
    retrieved_docs: list[dict]
    graded_docs: list[dict]
    reasoning_chain: list[str]
    answer: Optional[str]
    validation: Optional[ValidationResult]
    execution_history: list[str]
    retry_count: int

# Node definitions
PLAN = "plan"
RETRIEVE = "retrieve"
GRADE = "grade"
REASON = "reason"
VALIDATE = "validate"
REFLECT = "reflect"
ANSWER = "answer"

# Conditional edges
def should_retrieve_more(state: AgenticRAGState) -> str:
    if state["graded_docs"] or state["retry_count"] > 3:
        return REASON
    return REFLECT

def should_retry(state: AgenticRAGState) -> str:
    if state["validation"].valid:
        return ANSWER
    elif state["retry_count"] < 3:
        return REFLECT
    return ANSWER  # Fallback after 3 retries
```

## Implementation Plan

### Phase 1: Core Framework (Week 1)
- [ ] Implement `AgenticRAGState` state machine
- [ ] Create base `Agent` class with LLM interface
- [ ] Implement Planning Agent
- [ ] Implement Retrieval Orchestrator (reuse existing hybrid search)

### Phase 2: CRAG & Validation (Week 2)
- [ ] Implement Grader Agent (document relevance scoring)
- [ ] Add web search fallback (optional)
- [ ] Implement Validation Agent (fact-checking)
- [ ] Add citation tracking

### Phase 3: Reasoning & Reflection (Week 3)
- [ ] Implement Reasoning Agent (interleaved R&R)
- [ ] Implement Reflection Agent
- [ ] Add retry logic with exponential backoff
- [ ] Multi-hop reasoning support

### Phase 4: Integration & Testing (Week 4)
- [ ] Integrate with existing pipeline
- [ ] Add CLI interface for agentic mode
- [ ] Comprehensive testing (simple/multi-hop/adversarial queries)
- [ ] Performance benchmarking vs baseline

## Configuration

```toml
[agentic]
enabled = true
max_retries = 3
max_reasoning_hops = 5
grading_threshold = 0.7
validation_threshold = 0.8
enable_web_search = false  # Optional fallback
enable_reflection = true
enable_tracing = true  # Audit trail

[agentic.planning]
decompose_threshold = 3  # Decompose if >3 sub-questions detected
default_strategy = "hybrid"  # vector, keyword, graph, hybrid

[agentic.reasoning]
interleaved_retrieval = true
max_context_tokens = 4096
```

## Expected Benefits

### Accuracy Improvements
- **CRAG**: 5-10% improvement by filtering irrelevant docs
- **Self-RAG**: 15-20% improvement via validation & retry
- **Interleaved R&R**: 25-30% improvement on multi-hop queries

### Transparency
- Full audit trail (execution history)
- Reasoning chain visible to users
- Confidence scores for each step

### Robustness
- Automatic retry on validation failure
- Graceful degradation (fallback answers)
- Query rephrasing for failed searches

## References

1. **Agentic RAG Survey**: [arXiv:2501.09136](https://arxiv.org/abs/2501.09136)
2. **LangChain Agentic RAG**: [Official Docs](https://docs.langchain.com/oss/python/langgraph/agentic-rag)
3. **Self-Reflective RAG**: [LangChain Blog](https://blog.langchain.com/agentic-rag-with-langgraph/)
4. **Multi-Agent RAG**: [Pathway Blog](https://pathway.com/blog/multi-agent-rag-interleaved-retrieval-reasoning)
5. **Corrective RAG (CRAG)**: [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2024/07/building-agentic-rag-systems-with-langgraph/)
6. **2026 Design Patterns**: [Medium Article](https://medium.com/@dewasheesh.rana/agentic-ai-design-patterns-2026-ed-e3a5125162c5)
7. **RAG Blueprint 2025/2026**: [LangWatch](https://langwatch.ai/blog/the-ultimate-rag-blueprint-everything-you-need-to-know-about-rag-in-2025-2026)
8. **Agentic RAG Enterprise Guide**: [Data Nucleus](https://datanucleus.dev/rag-and-agentic-ai/agentic-rag-enterprise-guide-2026)
9. **Reasoning RAG Survey**: [arXiv:2506.10408](https://arxiv.org/html/2506.10408v1)
10. **What is Agentic RAG**: [Weaviate Blog](https://weaviate.io/blog/what-is-agentic-rag)
