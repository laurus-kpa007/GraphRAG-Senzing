"""
Concrete agent implementations for Agentic GraphRAG.
"""

import json
from typing import Any

from .base_agent import BaseAgent
from .state import (
    AgenticRAGState,
    GradedDocument,
    Plan,
    ReasoningStep,
    RetryPlan,
    ValidationResult,
)


class PlanningAgent(BaseAgent):
    """
    Planning Agent: Query decomposition and strategy selection.

    Analyzes question complexity and creates execution plan.
    """

    def execute(self, state: AgenticRAGState) -> AgenticRAGState:
        """Create execution plan for the query."""
        self.log(f"Planning for question: {state.question[:100]}...")

        # Detect language
        lang = self._detect_language(state.question)

        # Analyze question complexity
        complexity = self._analyze_complexity(state.question, lang)

        # Decompose into sub-queries if needed
        sub_queries = self._decompose_query(state.question, lang, complexity)

        # Select retrieval strategy
        strategy = self._select_strategy(state.question, complexity)

        # Create plan
        plan = Plan(
            original_query=state.question,
            sub_queries=sub_queries,
            strategy=strategy,
            max_hops=min(complexity, 5),
            validation_rules={"min_confidence": 0.7},
        )

        state.plan = plan
        state.add_history(f"PLAN: {len(sub_queries)} sub-queries, strategy={strategy}")
        self.log(f"Plan created: {plan}")

        return state

    def _detect_language(self, text: str) -> str:
        """Detect if text is Korean or English."""
        korean_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
        return "ko" if korean_chars > len(text) * 0.3 else "en"

    def _analyze_complexity(self, question: str, lang: str) -> int:
        """
        Analyze question complexity (1-5 scale).

        1: Simple factoid (Who, What, When)
        2: Single-hop reasoning
        3: Multi-hop reasoning (2-3 hops)
        4: Complex reasoning (4-5 hops)
        5: Very complex (>5 hops)
        """
        if lang == "ko":
            system = "질문의 복잡도를 1-5로 평가하세요. 1=단순 사실, 5=매우 복잡한 추론"
            prompt = f"질문: {question}\n\n복잡도 (1-5):"
        else:
            system = "Rate question complexity 1-5. 1=simple fact, 5=very complex reasoning"
            prompt = f"Question: {question}\n\nComplexity (1-5):"

        response = self._call_llm(prompt, system=system)
        complexity = int(self._extract_score(response) * 5)
        return max(1, min(5, complexity))

    def _decompose_query(self, question: str, lang: str, complexity: int) -> list[str]:
        """Decompose question into sub-queries if complex."""
        if complexity <= 2:
            return [question]  # No decomposition needed

        if lang == "ko":
            system = "복잡한 질문을 단계별 하위 질문으로 분해하세요."
            prompt = f"""질문: {question}

이 질문에 답하기 위해 필요한 하위 질문들을 JSON 배열로 나열하세요.
예: ["하위 질문 1", "하위 질문 2"]

하위 질문:"""
        else:
            system = "Decompose complex questions into step-by-step sub-questions."
            prompt = f"""Question: {question}

List sub-questions needed to answer this as a JSON array.
Example: ["sub-question 1", "sub-question 2"]

Sub-questions:"""

        response = self._call_llm(prompt, system=system)

        # Extract JSON array
        try:
            sub_queries = json.loads(response)
            if isinstance(sub_queries, list) and len(sub_queries) > 0:
                return sub_queries
        except json.JSONDecodeError:
            pass

        # Fallback: return original question
        return [question]

    def _select_strategy(self, question: str, complexity: int) -> str:
        """
        Select retrieval strategy based on question type.

        Strategies:
        - vector: Semantic search (conceptual questions)
        - keyword: Exact term matching (specific terms, names)
        - graph: Entity traversal (relationship questions)
        - hybrid: All three (default for complex questions)
        """
        if complexity >= 3:
            return "hybrid"  # Complex questions need all strategies

        # Check for relationship indicators
        relation_keywords = [
            "관계", "연관", "관련", "영향", "원인",  # Korean
            "relation", "connect", "link", "affect", "cause",  # English
        ]
        if any(kw in question.lower() for kw in relation_keywords):
            return "graph"

        # Check for specific terms (names, IDs, exact phrases)
        if '"' in question or "'" in question:
            return "keyword"

        # Default to vector for conceptual questions
        return "vector"


class GraderAgent(BaseAgent):
    """
    Grader Agent: Document relevance assessment (CRAG pattern).

    Evaluates retrieved documents and filters irrelevant ones.
    """

    def execute(self, state: AgenticRAGState) -> AgenticRAGState:
        """Grade retrieved documents for relevance."""
        if not state.retrieved_docs:
            state.add_history("GRADE: No documents to grade")
            return state

        self.log(f"Grading {len(state.retrieved_docs)} documents...")

        graded = []
        threshold = self.config.get("grading_threshold", 0.7)

        for doc in state.retrieved_docs:
            score = self._grade_document(state.question, doc)
            graded_doc = GradedDocument(
                uid=doc.get("uid", ""),
                text=doc.get("text", ""),
                source=doc.get("source", ""),
                relevance_score=score,
                metadata=doc,
            )
            graded.append(graded_doc)

        # Sort by relevance (highest first)
        graded.sort(key=lambda d: d.relevance_score, reverse=True)

        state.graded_docs = graded
        relevant_count = len([d for d in graded if d.is_relevant])

        state.add_history(
            f"GRADE: {relevant_count}/{len(graded)} docs passed threshold {threshold}"
        )
        self.log(f"Graded: {relevant_count}/{len(graded)} relevant")

        return state

    def _grade_document(self, question: str, doc: dict) -> float:
        """
        Grade document relevance to question.

        Returns:
            Score 0.0-1.0 (higher = more relevant)
        """
        text = doc.get("text", "")[:500]  # First 500 chars

        # Detect language
        korean_chars = sum(1 for c in question if "\uac00" <= c <= "\ud7a3")
        lang = "ko" if korean_chars > len(question) * 0.3 else "en"

        if lang == "ko":
            system = "문서가 질문과 관련이 있는지 평가하세요. 0.0 (무관) ~ 1.0 (매우 관련)"
            prompt = f"""질문: {question}

문서: {text}

이 문서는 질문에 답하는 데 얼마나 관련이 있습니까?
점수만 답하세요 (0.0 ~ 1.0):"""
        else:
            system = "Evaluate document relevance to question. 0.0 (irrelevant) ~ 1.0 (very relevant)"
            prompt = f"""Question: {question}

Document: {text}

How relevant is this document to answering the question?
Score only (0.0 ~ 1.0):"""

        response = self._call_llm(prompt, system=system, temperature=0.0)
        score = self._extract_score(response)

        return score


class ReasoningAgent(BaseAgent):
    """
    Reasoning Agent: Multi-hop reasoning with interleaved retrieval.

    Generates answer through iterative reasoning and context integration.
    """

    def __init__(self, llm, config: dict[str, Any], verbose: bool = False) -> None:
        super().__init__(llm, config, verbose)
        # Reference to retriever for interleaved retrieval
        self._retriever = None

    def set_retriever(self, retriever) -> None:
        """Set retriever for interleaved retrieval."""
        self._retriever = retriever

    def execute(self, state: AgenticRAGState) -> AgenticRAGState:
        """Generate answer through multi-hop reasoning."""
        if not state.graded_docs:
            state.add_history("REASON: No graded docs available")
            state.answer = "I don't have enough information to answer this question."
            return state

        self.log("Starting reasoning process...")

        # Get relevant docs
        relevant_docs = state.get_relevant_docs()
        if not relevant_docs:
            state.add_history("REASON: No relevant docs found")
            state.answer = "No relevant information found."
            return state

        # Perform reasoning (with optional interleaved retrieval)
        max_hops = state.plan.max_hops if state.plan else 3
        reasoning_chain = []

        context_docs = relevant_docs[:10]  # Start with top 10
        for hop in range(max_hops):
            step = self._reasoning_step(
                state.question,
                context_docs,
                hop + 1,
                max_hops,
            )
            reasoning_chain.append(step)

            # Check if answer is sufficient
            if not step.needs_more_info:
                break

            # Interleaved retrieval: get more context if needed
            if self._retriever and hop < max_hops - 1:
                new_docs = self._retrieve_additional_context(step)
                if new_docs:
                    context_docs.extend(new_docs)

        # Synthesize final answer
        final_answer = self._synthesize_answer(state.question, reasoning_chain)

        state.reasoning_chain = reasoning_chain
        state.answer = final_answer
        state.add_history(f"REASON: {len(reasoning_chain)} hops, answer generated")
        self.log(f"Reasoning complete: {len(reasoning_chain)} steps")

        return state

    def _reasoning_step(
        self,
        question: str,
        docs: list[GradedDocument],
        step_num: int,
        max_steps: int,
    ) -> ReasoningStep:
        """Single reasoning step."""
        # Build context from docs
        context = "\n\n".join([f"[{i+1}] {d.text[:500]}" for i, d in enumerate(docs[:5])])

        # Detect language
        korean_chars = sum(1 for c in question if "\uac00" <= c <= "\ud7a3")
        lang = "ko" if korean_chars > len(question) * 0.3 else "en"

        if lang == "ko":
            system = f"제공된 컨텍스트를 기반으로 질문에 답하세요. (단계 {step_num}/{max_steps})"
            prompt = f"""질문: {question}

컨텍스트:
{context}

이 컨텍스트로 질문에 완전히 답할 수 있습니까?
- 예: 답변을 제공하세요
- 아니오: 부분 답변을 제공하고 더 필요한 정보를 명시하세요

답변:"""
        else:
            system = f"Answer the question based on provided context. (Step {step_num}/{max_steps})"
            prompt = f"""Question: {question}

Context:
{context}

Can you fully answer the question with this context?
- Yes: Provide the answer
- No: Provide partial answer and specify what info is missing

Answer:"""

        response = self._call_llm(prompt, system=system, temperature=0.1)

        # Check if more info needed
        needs_more = any(
            phrase in response.lower()
            for phrase in [
                "need more", "missing", "additional", "insufficient",
                "더 필요", "부족", "추가", "불충분"
            ]
        )

        return ReasoningStep(
            step_num=step_num,
            question=question,
            context_used=[d.uid for d in docs[:5]],
            partial_answer=response,
            needs_more_info=needs_more and step_num < max_steps,
        )

    def _retrieve_additional_context(self, step: ReasoningStep) -> list[GradedDocument]:
        """Retrieve additional context based on reasoning step (interleaved retrieval)."""
        # Extract entities/keywords from partial answer
        # Then use retriever to get more docs
        # For now, return empty (will implement when integrating with pipeline)
        return []

    def _synthesize_answer(
        self,
        question: str,
        reasoning_chain: list[ReasoningStep],
    ) -> str:
        """Synthesize final answer from reasoning chain."""
        if len(reasoning_chain) == 1:
            return reasoning_chain[0].partial_answer

        # Combine insights from multiple steps
        steps_text = "\n\n".join([
            f"Step {s.step_num}: {s.partial_answer}"
            for s in reasoning_chain
        ])

        korean_chars = sum(1 for c in question if "\uac00" <= c <= "\ud7a3")
        lang = "ko" if korean_chars > len(question) * 0.3 else "en"

        if lang == "ko":
            system = "여러 추론 단계를 종합하여 최종 답변을 작성하세요."
            prompt = f"""질문: {question}

추론 과정:
{steps_text}

위 추론 과정을 바탕으로 질문에 대한 명확하고 간결한 최종 답변을 작성하세요:"""
        else:
            system = "Synthesize reasoning steps into final answer."
            prompt = f"""Question: {question}

Reasoning steps:
{steps_text}

Based on the reasoning above, provide a clear and concise final answer:"""

        final_answer = self._call_llm(prompt, system=system, temperature=0.0)
        return final_answer


class ValidationAgent(BaseAgent):
    """
    Validation Agent: Fact-checking and consistency verification (Self-RAG).

    Validates answer against source documents.
    """

    def execute(self, state: AgenticRAGState) -> AgenticRAGState:
        """Validate answer against source documents."""
        if not state.answer:
            state.add_history("VALIDATE: No answer to validate")
            return state

        self.log("Validating answer...")

        # Get source documents
        sources = state.get_relevant_docs()
        if not sources:
            state.validation = ValidationResult(
                valid=False,
                confidence=0.0,
                feedback="No source documents to validate against",
            )
            return state

        # Perform validation checks
        validation = self._validate_answer(
            state.question,
            state.answer,
            sources,
        )

        state.validation = validation
        state.add_history(
            f"VALIDATE: {'PASS' if validation.valid else 'FAIL'} "
            f"(confidence={validation.confidence:.2f})"
        )
        self.log(f"Validation: {validation}")

        return state

    def _validate_answer(
        self,
        question: str,
        answer: str,
        sources: list[GradedDocument],
    ) -> ValidationResult:
        """
        Validate answer against sources.

        Checks:
        1. No contradictions with sources
        2. Completeness (addresses all parts of question)
        3. Citations (claims supported by sources)
        """
        # Build source context
        source_text = "\n\n".join([
            f"[Source {i+1}] {s.text[:300]}"
            for i, s in enumerate(sources[:5])
        ])

        # Detect language
        korean_chars = sum(1 for c in question if "\uac00" <= c <= "\ud7a3")
        lang = "ko" if korean_chars > len(question) * 0.3 else "en"

        if lang == "ko":
            system = "답변이 출처와 일치하는지 검증하세요."
            prompt = f"""질문: {question}

답변: {answer}

출처:
{source_text}

다음을 확인하세요:
1. 답변이 출처와 모순되지 않는가?
2. 답변이 질문의 모든 부분을 다루는가?
3. 답변의 모든 주장이 출처로 뒷받침되는가?

JSON 형식으로 답하세요:
{{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["문제점 1", "문제점 2"]
}}

검증 결과:"""
        else:
            system = "Validate answer against sources."
            prompt = f"""Question: {question}

Answer: {answer}

Sources:
{source_text}

Check:
1. Does answer contradict sources?
2. Does answer address all parts of question?
3. Are all claims supported by sources?

Respond in JSON:
{{
  "valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["issue 1", "issue 2"]
}}

Validation:"""

        response = self._call_llm(prompt, system=system, temperature=0.0)

        # Parse JSON response
        try:
            result = json.loads(response)
            return ValidationResult(
                valid=result.get("valid", False),
                confidence=result.get("confidence", 0.0),
                feedback=response,
                issues=result.get("issues", []),
            )
        except json.JSONDecodeError:
            # Fallback: simple yes/no parsing
            is_valid = self._extract_yes_no(response)
            confidence = self._extract_score(response) if is_valid else 0.5

            return ValidationResult(
                valid=is_valid,
                confidence=confidence,
                feedback=response,
            )


class ReflectionAgent(BaseAgent):
    """
    Reflection Agent: Analyze failures and generate retry strategies.

    Determines how to improve results when validation fails.
    """

    def execute(self, state: AgenticRAGState) -> AgenticRAGState:
        """Analyze validation failure and create retry plan."""
        if not state.validation:
            state.add_history("REFLECT: No validation result to reflect on")
            return state

        self.log("Reflecting on validation result...")

        # Create retry plan
        retry_plan = self._create_retry_plan(
            state.question,
            state.validation,
            state.retry_count,
        )

        state.retry_plan = retry_plan
        state.add_history(f"REFLECT: Action={retry_plan.action}")
        self.log(f"Retry plan: {retry_plan.action}")

        return state

    def _create_retry_plan(
        self,
        question: str,
        validation: ValidationResult,
        retry_count: int,
    ) -> RetryPlan:
        """
        Create retry plan based on validation failure.

        Strategies:
        - rephrase: Rephrase query to get better retrieval
        - stricter_grading: Increase relevance threshold
        - change_strategy: Try different retrieval strategy
        - fallback: Give up, return best-effort answer
        """
        max_retries = self.config.get("max_retries", 3)

        # Give up after max retries
        if retry_count >= max_retries:
            return RetryPlan(
                action="fallback",
                message=f"Max retries ({max_retries}) reached. Returning best-effort answer.",
            )

        # Analyze failure
        feedback_lower = validation.feedback.lower()

        # Low confidence → rephrase query
        if validation.confidence < 0.5:
            new_query = self._rephrase_query(question)
            return RetryPlan(
                action="rephrase",
                new_query=new_query,
                message="Low confidence - rephrasing query",
            )

        # Contradictions or unsupported claims → stricter grading
        if any(
            word in feedback_lower
            for word in ["contradict", "unsupported", "모순", "뒷받침"]
        ):
            return RetryPlan(
                action="stricter_grading",
                new_threshold=0.85,
                message="Found contradictions - using stricter grading",
            )

        # Missing info → change strategy
        if any(word in feedback_lower for word in ["missing", "incomplete", "부족"]):
            return RetryPlan(
                action="change_strategy",
                new_strategy="hybrid",
                message="Incomplete answer - switching to hybrid search",
            )

        # Default: try again with same settings
        return RetryPlan(
            action="retry",
            message="Retrying with current settings",
        )

    def _rephrase_query(self, question: str) -> str:
        """Rephrase query to improve retrieval."""
        korean_chars = sum(1 for c in question if "\uac00" <= c <= "\ud7a3")
        lang = "ko" if korean_chars > len(question) * 0.3 else "en"

        if lang == "ko":
            system = "질문을 다른 방식으로 표현하여 더 나은 검색 결과를 얻으세요."
            prompt = f"""원래 질문: {question}

이 질문을 다른 단어로 바꿔서 표현하세요 (의미는 유지):"""
        else:
            system = "Rephrase question to improve search results."
            prompt = f"""Original question: {question}

Rephrase this question using different words (keep same meaning):"""

        rephrased = self._call_llm(prompt, system=system, temperature=0.3)
        return rephrased.strip()
