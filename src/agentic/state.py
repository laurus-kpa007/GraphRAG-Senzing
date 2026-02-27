"""
State definitions for Agentic GraphRAG.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Plan:
    """Execution plan from Planning Agent."""

    original_query: str
    sub_queries: list[str]
    strategy: str  # "vector", "keyword", "graph", "hybrid"
    max_hops: int = 3
    validation_rules: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"Plan(query='{self.original_query[:50]}...', "
            f"sub_queries={len(self.sub_queries)}, strategy='{self.strategy}')"
        )


@dataclass
class GradedDocument:
    """Document with relevance score."""

    uid: str
    text: str
    source: str
    relevance_score: float  # 0.0 - 1.0
    metadata: dict = field(default_factory=dict)

    @property
    def is_relevant(self) -> bool:
        """Check if document passes relevance threshold."""
        return self.relevance_score >= 0.7


@dataclass
class ReasoningStep:
    """Single step in reasoning chain."""

    step_num: int
    question: str
    context_used: list[str]  # UIDs of chunks used
    partial_answer: str
    needs_more_info: bool


@dataclass
class ValidationResult:
    """Result from Validation Agent."""

    valid: bool
    confidence: float  # 0.0 - 1.0
    feedback: str = ""
    issues: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        status = "✓ VALID" if self.valid else "✗ INVALID"
        return f"ValidationResult({status}, confidence={self.confidence:.2f})"


@dataclass
class RetryPlan:
    """Retry strategy from Reflection Agent."""

    action: str  # "rephrase", "stricter_grading", "change_strategy", "fallback"
    new_query: Optional[str] = None
    new_strategy: Optional[str] = None
    new_threshold: Optional[float] = None
    message: str = ""


@dataclass
class AgenticRAGState:
    """
    State machine for Agentic GraphRAG.

    This state is passed between agents and tracks the full execution history.
    """

    # Input
    question: str

    # Planning
    plan: Optional[Plan] = None

    # Retrieval
    retrieved_docs: list[dict] = field(default_factory=list)
    graded_docs: list[GradedDocument] = field(default_factory=list)

    # Reasoning
    reasoning_chain: list[ReasoningStep] = field(default_factory=list)
    answer: Optional[str] = None

    # Validation
    validation: Optional[ValidationResult] = None

    # Reflection & Retry
    retry_count: int = 0
    retry_plan: Optional[RetryPlan] = None

    # Audit trail
    execution_history: list[str] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)

    def add_history(self, event: str) -> None:
        """Add event to execution history for audit trail."""
        self.execution_history.append(event)

    def get_relevant_docs(self) -> list[GradedDocument]:
        """Get only relevant documents."""
        return [doc for doc in self.graded_docs if doc.is_relevant]

    def __repr__(self) -> str:
        status = []
        if self.plan:
            status.append(f"planned({self.plan.strategy})")
        if self.retrieved_docs:
            status.append(f"retrieved({len(self.retrieved_docs)})")
        if self.graded_docs:
            relevant = len(self.get_relevant_docs())
            status.append(f"graded({relevant}/{len(self.graded_docs)})")
        if self.reasoning_chain:
            status.append(f"reasoned({len(self.reasoning_chain)} steps)")
        if self.validation:
            status.append(f"validated({self.validation.confidence:.2f})")
        if self.answer:
            status.append("answered")

        return f"AgenticRAGState({', '.join(status)})"


# Node name constants (prevent typos)
NODE_PLAN = "plan"
NODE_RETRIEVE = "retrieve"
NODE_GRADE = "grade"
NODE_REASON = "reason"
NODE_VALIDATE = "validate"
NODE_REFLECT = "reflect"
NODE_ANSWER = "answer"
