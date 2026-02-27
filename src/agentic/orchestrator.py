"""
Agentic RAG Orchestrator.

Coordinates all agents in the Agentic GraphRAG pipeline.
"""

from typing import Any, Callable, Optional

from ..embeddings import OllamaEmbedder
from .agents import (
    GraderAgent,
    PlanningAgent,
    ReasoningAgent,
    ReflectionAgent,
    ValidationAgent,
)
from .state import (
    NODE_ANSWER,
    NODE_GRADE,
    NODE_PLAN,
    NODE_REASON,
    NODE_REFLECT,
    NODE_RETRIEVE,
    NODE_VALIDATE,
    AgenticRAGState,
)


class AgenticOrchestrator:
    """
    Orchestrator for Agentic GraphRAG pipeline.

    Coordinates agents in a state machine pattern (LangGraph-style).
    """

    def __init__(
        self,
        llm: OllamaEmbedder,
        retriever: Callable[[str, str], list[dict]],  # (query, strategy) -> docs
        config: dict[str, Any],
        verbose: bool = False,
    ) -> None:
        """
        Initialize orchestrator.

        Args:
            llm: Language model for agents
            retriever: Retrieval function (hybrid search from pipeline)
            config: Configuration dict
            verbose: Enable verbose logging
        """
        self.llm = llm
        self.retriever = retriever
        self.config = config
        self.verbose = verbose

        # Initialize agents
        self.planning_agent = PlanningAgent(llm, config, verbose)
        self.grader_agent = GraderAgent(llm, config, verbose)
        self.reasoning_agent = ReasoningAgent(llm, config, verbose)
        self.validation_agent = ValidationAgent(llm, config, verbose)
        self.reflection_agent = ReflectionAgent(llm, config, verbose)

        # Set retriever for reasoning agent (interleaved retrieval)
        self.reasoning_agent.set_retriever(retriever)

    def query(
        self,
        question: str,
        *,
        enable_reflection: bool = True,
        enable_validation: bool = True,
    ) -> dict[str, Any]:
        """
        Execute Agentic RAG pipeline.

        Args:
            question: User question
            enable_reflection: Enable retry on validation failure
            enable_validation: Enable validation step

        Returns:
            Result dict with answer, reasoning chain, and audit trail
        """
        # Initialize state
        state = AgenticRAGState(question=question)

        if self.verbose:
            print("\n" + "=" * 60)
            print("🤖 AGENTIC GRAPHRAG PIPELINE")
            print("=" * 60)
            print(f"Question: {question}\n")

        # Execute pipeline
        state = self._run_pipeline(
            state,
            enable_reflection=enable_reflection,
            enable_validation=enable_validation,
        )

        # Build result
        result = self._build_result(state)

        if self.verbose:
            print("\n" + "=" * 60)
            print("✅ PIPELINE COMPLETE")
            print("=" * 60)
            self._print_summary(state)

        return result

    def _run_pipeline(
        self,
        state: AgenticRAGState,
        *,
        enable_reflection: bool,
        enable_validation: bool,
    ) -> AgenticRAGState:
        """
        Run the agentic pipeline (state machine).

        Flow:
        PLAN → RETRIEVE → GRADE → REASON → VALIDATE → ANSWER
                                              ↓ (fail)
                                           REFLECT → (retry from RETRIEVE)
        """
        max_retries = self.config.get("max_retries", 3)

        while state.retry_count <= max_retries:
            # Planning (only on first iteration)
            if state.plan is None:
                state = self._execute_node(NODE_PLAN, self.planning_agent, state)

            # Retrieval
            state = self._execute_retrieve(state)

            # Grading
            state = self._execute_node(NODE_GRADE, self.grader_agent, state)

            # Check if any relevant docs found
            if not state.get_relevant_docs():
                if enable_reflection and state.retry_count < max_retries:
                    state.retry_count += 1
                    state.add_history(f"No relevant docs - retry {state.retry_count}")
                    # Trigger reflection to rephrase
                    state.validation = type('obj', (object,), {
                        'valid': False,
                        'confidence': 0.0,
                        'feedback': 'No relevant documents found'
                    })()
                    state = self._execute_node(NODE_REFLECT, self.reflection_agent, state)
                    self._apply_retry_plan(state)
                    continue
                else:
                    state.answer = "관련 정보를 찾을 수 없습니다." if self._is_korean(state.question) else "No relevant information found."
                    break

            # Reasoning
            state = self._execute_node(NODE_REASON, self.reasoning_agent, state)

            # Validation
            if enable_validation:
                state = self._execute_node(NODE_VALIDATE, self.validation_agent, state)

                # Check validation result
                if state.validation and not state.validation.valid:
                    if enable_reflection and state.retry_count < max_retries:
                        state.retry_count += 1
                        state.add_history(f"Validation failed - retry {state.retry_count}")

                        # Reflection
                        state = self._execute_node(NODE_REFLECT, self.reflection_agent, state)

                        # Apply retry plan
                        if state.retry_plan:
                            self._apply_retry_plan(state)

                        # Retry or fallback?
                        if state.retry_plan.action == "fallback":
                            break  # Give up
                        continue  # Retry
                    else:
                        # Max retries reached or reflection disabled
                        break
                else:
                    # Validation passed
                    break
            else:
                # Validation disabled
                break

        # Final answer node (add citations)
        state = self._execute_answer(state)

        return state

    def _execute_node(
        self,
        node_name: str,
        agent,
        state: AgenticRAGState,
    ) -> AgenticRAGState:
        """Execute a single agent node."""
        if self.verbose:
            print(f"\n[{node_name.upper()}]")

        state = agent.execute(state)

        return state

    def _execute_retrieve(self, state: AgenticRAGState) -> AgenticRAGState:
        """Execute retrieval node."""
        if self.verbose:
            print(f"\n[{NODE_RETRIEVE.upper()}]")

        if not state.plan:
            raise RuntimeError("Cannot retrieve without a plan")

        # Determine query (original or rephrased)
        query = state.question
        if state.retry_plan and state.retry_plan.new_query:
            query = state.retry_plan.new_query

        # Retrieve using strategy from plan
        strategy = state.plan.strategy
        if state.retry_plan and state.retry_plan.new_strategy:
            strategy = state.retry_plan.new_strategy

        docs = self.retriever(query, strategy)

        state.retrieved_docs = docs
        state.add_history(f"RETRIEVE: {len(docs)} docs, strategy={strategy}")

        if self.verbose:
            print(f"Retrieved {len(docs)} documents using {strategy} strategy")

        return state

    def _execute_answer(self, state: AgenticRAGState) -> AgenticRAGState:
        """Execute final answer node (add citations)."""
        if self.verbose:
            print(f"\n[{NODE_ANSWER.upper()}]")

        # Build citations from relevant docs
        relevant_docs = state.get_relevant_docs()
        citations = [
            {
                "source": doc.source,
                "text": doc.text[:200] + "...",
                "relevance": doc.relevance_score,
            }
            for doc in relevant_docs[:5]  # Top 5 citations
        ]

        state.citations = citations
        state.add_history(f"ANSWER: {len(citations)} citations added")

        if self.verbose:
            print(f"Added {len(citations)} citations")

        return state

    def _apply_retry_plan(self, state: AgenticRAGState) -> None:
        """Apply retry plan to state (modifies state in-place)."""
        if not state.retry_plan:
            return

        plan = state.retry_plan

        if plan.action == "rephrase" and plan.new_query:
            # Query will be used in next retrieve
            if self.verbose:
                print(f"  → Rephrasing: '{state.question[:50]}' → '{plan.new_query[:50]}'")

        elif plan.action == "stricter_grading" and plan.new_threshold:
            # Update config for next grading
            self.config["grading_threshold"] = plan.new_threshold
            if self.verbose:
                print(f"  → Stricter grading: threshold={plan.new_threshold}")

        elif plan.action == "change_strategy" and plan.new_strategy:
            # Strategy will be used in next retrieve
            if self.verbose:
                print(f"  → Changing strategy: {state.plan.strategy} → {plan.new_strategy}")

        elif plan.action == "fallback":
            if self.verbose:
                print(f"  → Fallback: {plan.message}")

    def _build_result(self, state: AgenticRAGState) -> dict[str, Any]:
        """Build result dict from final state."""
        return {
            "answer": state.answer or "No answer generated.",
            "reasoning_chain": [
                {
                    "step": s.step_num,
                    "answer": s.partial_answer,
                    "needs_more": s.needs_more_info,
                }
                for s in state.reasoning_chain
            ],
            "citations": state.citations,
            "validation": {
                "valid": state.validation.valid if state.validation else None,
                "confidence": state.validation.confidence if state.validation else None,
            } if state.validation else None,
            "execution_history": state.execution_history,
            "retry_count": state.retry_count,
            "metadata": {
                "strategy": state.plan.strategy if state.plan else None,
                "sub_queries": state.plan.sub_queries if state.plan else [],
                "num_retrieved": len(state.retrieved_docs),
                "num_relevant": len(state.get_relevant_docs()),
            },
        }

    def _print_summary(self, state: AgenticRAGState) -> None:
        """Print execution summary."""
        print(f"\nAnswer: {state.answer}\n")

        if state.reasoning_chain:
            print(f"Reasoning Steps: {len(state.reasoning_chain)}")

        if state.validation:
            print(f"Validation: {'✓ PASS' if state.validation.valid else '✗ FAIL'} "
                  f"(confidence={state.validation.confidence:.2f})")

        print(f"Retries: {state.retry_count}")
        print(f"Citations: {len(state.citations)}")

        print(f"\nExecution History:")
        for event in state.execution_history:
            print(f"  • {event}")

    def _is_korean(self, text: str) -> bool:
        """Check if text is primarily Korean."""
        korean_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
        return korean_chars > len(text) * 0.3
