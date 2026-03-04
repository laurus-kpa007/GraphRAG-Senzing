"""
Agentic pipeline orchestrator.
Wraps strwythura's Workflow with custom document loaders and BGE-M3 embeddings.
Runs autonomously through all phases: load -> parse -> embed -> build KG -> serve RAG.
"""

import json
import logging
import pathlib
import time
import tomllib
from datetime import datetime
from typing import Optional

import lancedb
import networkx as nx
import numpy as np
import pyarrow as pa

from .loaders import DocumentLoader
from .embeddings import OllamaEmbedding, OllamaLLM

logger = logging.getLogger(__name__)

# Optional profiling support
try:
    from pyinstrument import Profiler
    PROFILING_AVAILABLE = True
except ImportError:
    PROFILING_AVAILABLE = False
    Profiler = None


class AgenticPipeline:
    """
    Self-orchestrating pipeline that:
    1. Loads documents from local files (.docx, .txt, .md)
    2. Chunks text and embeds with BGE-M3 via Ollama
    3. Builds a knowledge graph via strwythura NLP pipeline
    4. Provides GraphRAG Q&A with gemma3:27b via Ollama
    """

    def __init__(
        self,
        config_path: str = "config.toml",
        domain_path: str = "domain.json",
    ) -> None:
        self.config_path = pathlib.Path(config_path)
        self.domain_path = pathlib.Path(domain_path)

        with open(self.config_path, "rb") as f:
            self.config = tomllib.load(f)

        with open(self.domain_path, "r", encoding="utf-8") as f:
            self.domain = json.load(f)

        # Core components
        self.loader = DocumentLoader()
        self.embedder = OllamaEmbedding(
            model=self.config["embed"]["model"],
            base_url=self.config["embed"]["ollama_url"],
            dim=self.config["embed"]["dim"],
        )
        self.llm = OllamaLLM(
            model=self.config["rag"]["lm_name"].replace("ollama_chat/", ""),
            base_url=self.config["rag"]["api_base"],
            temperature=self.config["rag"]["temperature"],
            max_tokens=self.config["rag"]["max_tokens"],
        )

        # State
        self._strwythura_work = None
        self._lance_db = None
        self._lance_table = None
        self._chunks: list[dict] = []
        self._entities: list[dict] = []
        self._is_initialized = False

        # Knowledge Graph
        self._kg: nx.Graph = nx.Graph()
        self._entity_chunk_map: dict[str, set[int]] = {}  # entity_key -> {chunk_uids}

        # Profiling
        self._profiler: Optional[Profiler] = None
        self._use_profiling = self.config.get("prof", {}).get("use_pyinst", False)

    # ── Prerequisites ────────────────────────────────────────────────

    def check_prerequisites(self) -> dict[str, bool]:
        """Check all external services are available."""
        status = {
            "ollama_server": False,
            "llm_model": False,
            "embed_model": False,
        }

        status["embed_model"] = self.embedder.is_available()
        status["llm_model"] = self.llm.is_available()
        status["ollama_server"] = status["embed_model"] or status["llm_model"]

        return status

    def initialize(self) -> None:
        """Initialize LanceDB, load persisted graph, and prepare directories."""
        lancedb_uri = self.config["vect"]["lancedb_uri"]
        pathlib.Path(lancedb_uri).mkdir(parents=True, exist_ok=True)
        pathlib.Path("data/output").mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.config["scraper"]["cache_path"]).mkdir(parents=True, exist_ok=True)

        self._lance_db = lancedb.connect(lancedb_uri)

        # Load persisted knowledge graph if available
        self._load_graph()

        # Load persisted entities if available
        store_path = pathlib.Path(self.config["ent"]["store_path"])
        if store_path.exists() and not self._entities:
            try:
                with open(store_path, "r", encoding="utf-8") as f:
                    self._entities = [json.loads(line) for line in f if line.strip()]
                logger.info("Loaded %d entities from %s", len(self._entities), store_path)
            except Exception as e:
                logger.warning("Failed to load entities: %s", e)

        self._is_initialized = True
        logger.info("Pipeline initialized")

    def _get_or_create_table(self) -> lancedb.table.Table:
        """Get or create the chunks vector table in LanceDB."""
        if self._lance_table is not None:
            return self._lance_table

        dim = self.config["embed"]["dim"]
        table_name = self.config["vect"]["chunk_table"]

        try:
            self._lance_table = self._lance_db.open_table(table_name)
            logger.info("Opened existing table: %s", table_name)
        except Exception:
            schema = pa.schema([
                pa.field("uid", pa.int64()),
                pa.field("source", pa.utf8()),
                pa.field("text", pa.utf8()),
                pa.field("vector", pa.list_(pa.float32(), dim)),
            ])
            self._lance_table = self._lance_db.create_table(table_name, schema=schema)
            logger.info("Created new table: %s (dim=%d)", table_name, dim)

        return self._lance_table

    # ── Phase 1: Document Loading ────────────────────────────────────

    def load_documents(
        self,
        paths: list[str | pathlib.Path],
    ) -> dict[str, list[str]]:
        """Load documents from file paths or directories."""
        all_docs: dict[str, list[str]] = {}

        for p in paths:
            path = pathlib.Path(p)
            if path.is_dir():
                dir_docs = self.loader.load_directory(path)
                all_docs.update(dir_docs)
            elif path.is_file():
                paragraphs = self.loader.load(path)
                all_docs[str(path)] = paragraphs
            else:
                logger.warning("Path not found, skipping: %s", path)

        total_p = sum(len(v) for v in all_docs.values())
        logger.info("Loaded %d documents, %d total paragraphs", len(all_docs), total_p)
        return all_docs

    # ── Phase 2: Chunking ────────────────────────────────────────────

    def make_chunks(self, paragraphs: list[str], max_chunk_size: int = 0) -> list[str]:
        """Assemble paragraphs into chunks respecting max size."""
        if max_chunk_size <= 0:
            max_chunk_size = self.config["vect"].get("chunk_size", 1024)

        chunks: list[str] = []
        buf: list[str] = []
        buf_len = 0

        for para in paragraphs:
            plen = len(para)
            if buf and (buf_len + plen + 1) > max_chunk_size:
                chunks.append(" ".join(buf))
                buf = []
                buf_len = 0
            buf.append(para)
            buf_len += plen + 1

        if buf:
            chunks.append(" ".join(buf))

        return chunks

    # ── Phase 3: Embedding & Vector Store ────────────────────────────

    def embed_and_store(
        self,
        documents: dict[str, list[str]],
        *,
        batch_size: int = 8,
    ) -> int:
        """Chunk documents, embed with BGE-M3, store in LanceDB."""
        table = self._get_or_create_table()
        uid = len(self._chunks)
        total = 0

        for source, paragraphs in documents.items():
            chunks = self.make_chunks(paragraphs)
            logger.info("  %s: %d chunks", pathlib.Path(source).name, len(chunks))

            for i in range(0, len(chunks), batch_size):
                batch_texts = chunks[i:i + batch_size]
                batch_vectors = self.embedder.embed_batch(batch_texts)

                rows = []
                for text, vec in zip(batch_texts, batch_vectors):
                    rec = {"uid": uid, "source": source, "text": text, "vector": vec}
                    self._chunks.append(rec)
                    rows.append(rec)
                    uid += 1

                table.add(rows)
                total += len(rows)

        logger.info("Total chunks embedded: %d", total)
        return total

    # ── Phase 4: NLP Entity Extraction ───────────────────────────────

    def run_nlp_pipeline(self, documents: dict[str, list[str]]) -> None:
        """
        Run NLP entity extraction.
        Tries strwythura first, falls back to standalone spaCy.
        """
        # Try strwythura's full pipeline
        try:
            self._run_strwythura_nlp(documents)
            return
        except Exception as e:
            logger.info("strwythura pipeline not available (%s), using standalone NLP", e)

        # Fallback: standalone spaCy
        self._run_standalone_nlp(documents)

    def _run_strwythura_nlp(self, documents: dict[str, list[str]]) -> None:
        """Run strwythura's full NLP pipeline."""
        from strwythura import Workflow

        work = Workflow(config_path=self.config_path)
        work.load_parser()

        chunk_id = 0
        for source, paragraphs in documents.items():
            chunks = self.make_chunks(paragraphs)
            for chunk_text in chunks:
                work.parser.parse_para(chunk_id, chunk_text, debug=False)
                chunk_id += 1

        # Run TextRank on lexical graph
        work.ctx.lex.run_textrank()

        # Save outputs
        store_path = pathlib.Path(self.config["ent"]["store_path"])
        store_path.parent.mkdir(parents=True, exist_ok=True)
        work.ctx.ent_store.save_json(store_path)

        lex_path = pathlib.Path(self.config["nlp"]["lex_path"])
        lex_path.parent.mkdir(parents=True, exist_ok=True)
        work.ctx.lex.save_graph(lex_path)

        erkg_path = pathlib.Path(self.config["erkg"]["erkg_path"])
        erkg_path.parent.mkdir(parents=True, exist_ok=True)
        work.ctx.erkg.save_graph(erkg_path)

        self._strwythura_work = work
        logger.info("strwythura NLP pipeline complete")

    def _detect_language(self, text: str) -> str:
        """Detect if text is primarily Korean, English, or mixed."""
        korean_count = sum(1 for c in text if '\uAC00' <= c <= '\uD7A3' or '\u3131' <= c <= '\u318E')
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha == 0:
            return "en"
        ratio = korean_count / total_alpha
        if ratio > 0.3:
            return "ko"
        return "en"

    def _load_spacy_model(self):
        """Load appropriate spaCy model with Korean fallback."""
        import spacy

        # Try configured model first
        model_name = self.config["nlp"]["spacy_model"]
        try:
            return spacy.load(model_name)
        except OSError:
            pass

        # Try Korean model
        for ko_model in ["ko_core_news_lg", "ko_core_news_md", "ko_core_news_sm"]:
            try:
                return spacy.load(ko_model)
            except OSError:
                continue

        # Try English fallbacks
        for en_model in ["en_core_web_md", "en_core_web_sm"]:
            try:
                return spacy.load(en_model)
            except OSError:
                continue

        # Last resort: blank multilingual
        logger.warning("No trained spaCy model found. Using blank model with sentencizer.")
        nlp = spacy.blank("xx")  # multilingual blank
        nlp.add_pipe("sentencizer")
        return nlp

    def _run_standalone_nlp(self, documents: dict[str, list[str]]) -> None:
        """
        NLP pipeline that builds a real knowledge graph.

        For each chunk:
        1. Extract entities (NER + Korean nouns)
        2. Track entity ↔ chunk mapping
        3. Build co-occurrence edges from sentence-level proximity

        Result: NetworkX graph with entity nodes, co-occurrence edges,
        and entity-chunk mappings for graph-based retrieval.
        """
        try:
            import spacy
            nlp = self._load_spacy_model()
        except ImportError:
            logger.warning("spaCy not installed. Skipping NLP extraction.")
            return

        entities: dict[str, dict] = {}
        entity_chunk_map: dict[str, set[int]] = {}  # entity_key -> {chunk_uids}
        cooccurrence: dict[tuple[str, str], float] = {}  # (ent_a, ent_b) -> weight
        uid = 0
        chunk_uid = 0

        for source, paragraphs in documents.items():
            chunks = self.make_chunks(paragraphs)
            for chunk_text in chunks:
                doc = nlp(chunk_text)
                chunk_entities_all: list[str] = []  # all entity keys in this chunk

                # Process each sentence for fine-grained co-occurrence
                sents = list(doc.sents) if doc.has_annotation("SENT_START") else [doc]

                for sent in sents:
                    sent_entities: list[str] = []

                    # 1. Extract NER entities from this sentence
                    for ent in sent.ents:
                        key = ent.text.strip()
                        if not key or len(key) <= 1:
                            continue
                        norm_key = key if self._detect_language(key) == "ko" else key.lower()
                        if norm_key not in entities:
                            entities[norm_key] = {
                                "uid": uid,
                                "text": key,
                                "label": ent.label_,
                                "count": 0,
                                "lemma_key": norm_key,
                            }
                            uid += 1
                        entities[norm_key]["count"] += 1
                        sent_entities.append(norm_key)

                    # 2. Korean: also extract NOUN/PROPN tokens
                    if self._detect_language(sent.text) == "ko":
                        for token in sent:
                            if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 1:
                                key = token.text.strip()
                                if not key:
                                    continue
                                if key not in entities:
                                    entities[key] = {
                                        "uid": uid,
                                        "text": key,
                                        "label": "NOUN",
                                        "count": 0,
                                        "lemma_key": key,
                                    }
                                    uid += 1
                                entities[key]["count"] += 1
                                if key not in sent_entities:
                                    sent_entities.append(key)

                    # 3. Build co-occurrence edges: all pairs within a sentence
                    unique_sent = list(dict.fromkeys(sent_entities))  # dedupe, preserve order
                    for i in range(len(unique_sent)):
                        for j in range(i + 1, len(unique_sent)):
                            a, b = unique_sent[i], unique_sent[j]
                            pair = (min(a, b), max(a, b))  # canonical order
                            cooccurrence[pair] = cooccurrence.get(pair, 0) + 1.0

                    chunk_entities_all.extend(unique_sent)

                # 4. Track entity ↔ chunk mapping
                for ent_key in set(chunk_entities_all):
                    if ent_key not in entity_chunk_map:
                        entity_chunk_map[ent_key] = set()
                    entity_chunk_map[ent_key].add(chunk_uid)

                chunk_uid += 1

        # ── Build NetworkX knowledge graph ──
        kg = nx.Graph()

        # Add entity nodes
        for ent_key, ent_data in entities.items():
            kg.add_node(ent_key, **ent_data, kind="entity")

        # Add co-occurrence edges
        for (a, b), weight in cooccurrence.items():
            if a in kg and b in kg:
                kg.add_edge(a, b, weight=weight, rel="co_occurrence")

        # Run PageRank for entity importance
        if kg.number_of_nodes() > 0:
            try:
                alpha = self.config.get("tr", {}).get("tr_alpha", 0.85)
                pr = nx.pagerank(kg, alpha=alpha, weight="weight")
                for node, rank in pr.items():
                    kg.nodes[node]["rank"] = rank
            except Exception as e:
                logger.warning("PageRank failed: %s", e)

        self._kg = kg
        self._entity_chunk_map = entity_chunk_map

        # Save entity store
        store_path = pathlib.Path(self.config["ent"]["store_path"])
        store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(store_path, "w", encoding="utf-8") as f:
            for ent in entities.values():
                f.write(json.dumps(ent, ensure_ascii=False) + "\n")

        # Save graph
        self._save_graph()

        self._entities = list(entities.values())
        logger.info(
            "NLP extracted %d entities, %d edges, %d entity-chunk links",
            kg.number_of_nodes(), kg.number_of_edges(), sum(len(v) for v in entity_chunk_map.values()),
        )

    def _save_graph(self) -> None:
        """Persist knowledge graph and entity-chunk map to disk."""
        erkg_path = pathlib.Path(self.config["erkg"]["erkg_path"])
        erkg_path.parent.mkdir(parents=True, exist_ok=True)

        # Save graph as node_link JSON
        graph_data = nx.node_link_data(self._kg)
        with open(erkg_path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False)

        # Save entity-chunk map
        map_path = erkg_path.parent / "entity_chunk_map.json"
        serializable_map = {k: list(v) for k, v in self._entity_chunk_map.items()}
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(serializable_map, f, ensure_ascii=False)

        logger.info("Saved knowledge graph (%d nodes, %d edges) to %s",
                    self._kg.number_of_nodes(), self._kg.number_of_edges(), erkg_path)

    def _load_graph(self) -> bool:
        """Load persisted knowledge graph. Returns True if successful."""
        erkg_path = pathlib.Path(self.config["erkg"]["erkg_path"])
        map_path = erkg_path.parent / "entity_chunk_map.json"

        if not erkg_path.exists():
            return False

        try:
            with open(erkg_path, "r", encoding="utf-8") as f:
                graph_data = json.load(f)
            self._kg = nx.node_link_graph(graph_data)

            if map_path.exists():
                with open(map_path, "r", encoding="utf-8") as f:
                    raw_map = json.load(f)
                self._entity_chunk_map = {k: set(v) for k, v in raw_map.items()}

            logger.info("Loaded knowledge graph: %d nodes, %d edges",
                       self._kg.number_of_nodes(), self._kg.number_of_edges())
            return True
        except Exception as e:
            logger.warning("Failed to load graph: %s", e)
            return False

    # ── Phase 5: RAG Query ───────────────────────────────────────────

    def _keyword_search(self, question: str, top_k: int = 5) -> list[dict]:
        """Keyword-based search in chunks (fallback for exact term matching)."""
        results = []

        # Extract key terms from question (remove common words)
        stopwords = {"은", "는", "이", "가", "을", "를", "의", "에", "와", "과", "도", "로",
                     "은요", "는요", "뭐야", "뭔가요", "무엇", "어디", "언제", "누구", "왜"}

        # Split and clean question
        terms = [t.strip() for t in question.split() if len(t.strip()) > 1]
        key_terms = [t for t in terms if t not in stopwords]

        if not key_terms:
            return []

        # Search in stored chunks
        for chunk in self._chunks:
            text = chunk.get("text", "").lower()
            score = sum(1 for term in key_terms if term.lower() in text)

            if score > 0:
                results.append({
                    **chunk,
                    "keyword_score": score,
                })

        # Sort by keyword match score
        results.sort(key=lambda x: x.get("keyword_score", 0), reverse=True)
        return results[:top_k]

    def query(self, question: str, *, top_k: int = 0,
              conversation_history: list[dict] | None = None) -> dict:
        """
        Hybrid GraphRAG query:
        1. Vector search for semantic similarity (BGE-M3)
        2. Keyword search for exact term matching
        3. Entity context augmentation
        4. LLM answer generation (gemma3:27b)
        """
        if top_k <= 0:
            top_k = self.config["rag"].get("max_chunks", 9)

        # 1. Vector search
        table = self._get_or_create_table()
        q_vec = self.embedder.embed_text(question)

        try:
            vector_results = table.search(q_vec).limit(top_k).to_list()
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            vector_results = []

        # 2. Keyword search (for exact term matching)
        keyword_results = self._keyword_search(question, top_k=max(3, top_k // 2))

        # 3. Merge vector + keyword results (deduplicate by uid)
        seen_uids = set()
        initial_results = []

        # Prioritize vector results
        for r in vector_results:
            uid = r.get("uid")
            if uid not in seen_uids:
                initial_results.append(r)
                seen_uids.add(uid)

        # Add keyword results not in vector results
        for r in keyword_results:
            uid = r.get("uid")
            if uid not in seen_uids:
                initial_results.append(r)
                seen_uids.add(uid)

        # 4. Graph expansion (find related chunks through entity co-occurrence)
        graph_results = []
        if len(initial_results) > 0 and len(self._entities) > 0:
            graph_results = self._graph_search(question, initial_results[:5])

            # Add graph results
            for r in graph_results:
                uid = r.get("uid")
                if uid not in seen_uids:
                    initial_results.append(r)
                    seen_uids.add(uid)

        # Limit to top_k
        results = initial_results[:top_k]

        logger.info("GraphRAG search: %d vector + %d keyword + %d graph = %d total",
                   len(vector_results), len(keyword_results), len(graph_results), len(results))

        # Build context
        context_parts = []
        sources = set()
        for r in results:
            context_parts.append(r.get("text", ""))
            sources.add(r.get("source", "unknown"))
        context_text = "\n\n---\n\n".join(context_parts)

        # Augment with entity info (including co-occurring entities from chunks)
        entity_context = self._get_entity_context(question, chunks=results)
        if entity_context:
            context_text = f"{context_text}\n\n[Related Entities]\n{entity_context}"

        # Detect language and generate with LLM
        lang = self._detect_language(question)

        # Current date/time for temporal awareness
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S (%A)")

        if lang == "ko":
            system_prompt = (
                f"현재 날짜와 시간: {now_str}\n\n"
                "당신은 지식이 풍부한 도우미입니다. 제공된 컨텍스트를 기반으로 질문에 답변하세요.\n\n"
                "중요한 규칙:\n"
                "1. 테이블 정보가 있을 때, 질문과 정확히 일치하는 행(row)만 사용하세요.\n"
                "2. 예를 들어 '형제자매' 또는 '누나'에 대한 질문이면, '본인'이나 '부모'의 정보는 답변에 포함하지 마세요.\n"
                "3. 각 테이블 행은 독립적인 경우이므로, 관련 없는 행의 값을 나열하지 마세요.\n"
                "4. 컨텍스트에 충분한 정보가 없으면 그렇다고 명확히 말하세요.\n"
                "5. 상세하고 정확하게 한국어로 답변하세요.\n"
                "6. 날짜, 기간, 나이 등의 계산이 필요하면 현재 날짜를 기준으로 직접 계산하세요.\n\n"
                "추론 규칙:\n"
                "- 숫자 계산이 필요하면 단계별로 계산 과정을 보여주세요.\n"
                "- 여러 정보를 조합해야 하면 근거를 명시하며 논리적으로 추론하세요.\n"
                "- 비교, 순위, 합계, 평균 등을 요청받으면 컨텍스트에서 데이터를 추출해 직접 계산하세요."
            )
        else:
            system_prompt = (
                f"Current date and time: {now_str}\n\n"
                "You are a knowledgeable assistant. Answer the question based on the provided context.\n\n"
                "Important rules:\n"
                "1. When table data is provided, only use the row(s) that exactly match the question.\n"
                "2. For example, if asked about 'sibling' or 'sister', do NOT include information from 'self' or 'parent' rows.\n"
                "3. Each table row represents an independent case - do not list values from unrelated rows.\n"
                "4. If the context does not contain enough information, say so.\n"
                "5. Be detailed and accurate. Respond in the same language as the question.\n"
                "6. When calculations involving dates, durations, or ages are needed, compute them using the current date.\n\n"
                "Reasoning rules:\n"
                "- If numerical calculation is needed, show step-by-step computation.\n"
                "- If combining multiple pieces of information, state your evidence and reason logically.\n"
                "- For comparisons, rankings, totals, or averages, extract data from context and compute directly."
            )

        user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"

        # Build messages for chat API (supports conversation history)
        messages = [{"role": "system", "content": system_prompt}]

        # Append conversation history for multi-turn context
        if conversation_history:
            # Keep last N turns to avoid exceeding context window
            max_history_turns = self.config["rag"].get("max_history_turns", 5)
            recent_history = conversation_history[-(max_history_turns * 2):]
            for msg in recent_history:
                if msg["role"] in ("user", "assistant"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_prompt})

        t0 = time.time()
        answer = self.llm.chat(messages)
        elapsed = time.time() - t0

        return {
            "question": question,
            "answer": answer,
            "sources": list(sources),
            "num_chunks": len(results),
            "elapsed_sec": round(elapsed, 2),
            "chunks": [r.get("text", "")[:200] for r in results],
        }

    def _graph_search(self, question: str, initial_chunks: list[dict]) -> list[dict]:
        """
        Graph-based retrieval using the knowledge graph.

        1. Find anchor entities (entities mentioned in question or initial chunks)
        2. Traverse graph: 1-2 hop neighbors weighted by PageRank
        3. Collect chunks linked to discovered entities via entity-chunk map
        """
        if self._kg.number_of_nodes() == 0:
            return self._graph_search_fallback(initial_chunks)

        # Step 1: Find anchor entities from the question
        q_lower = question.lower()
        anchor_entities: set[str] = set()

        for node in self._kg.nodes:
            node_data = self._kg.nodes[node]
            text = node_data.get("text", "").lower()
            lemma = node_data.get("lemma_key", "").lower()
            if text and len(text) > 1 and (text in q_lower or q_lower in text):
                anchor_entities.add(node)
            elif lemma and len(lemma) > 1 and lemma in q_lower:
                anchor_entities.add(node)

        # Also find anchors from initial chunks
        initial_uids = {c.get("uid") for c in initial_chunks}
        for ent_key, chunk_uids in self._entity_chunk_map.items():
            if chunk_uids & initial_uids:  # entity appears in initial chunks
                anchor_entities.add(ent_key)

        if not anchor_entities:
            return self._graph_search_fallback(initial_chunks)

        # Step 2: Expand via graph traversal (1-2 hops)
        expanded_entities: dict[str, float] = {}
        for anchor in anchor_entities:
            if anchor not in self._kg:
                continue
            anchor_rank = self._kg.nodes[anchor].get("rank", 0.01)
            expanded_entities[anchor] = anchor_rank

            # 1-hop neighbors
            for neighbor in self._kg.neighbors(anchor):
                edge_weight = self._kg[anchor][neighbor].get("weight", 1.0)
                neighbor_rank = self._kg.nodes[neighbor].get("rank", 0.01)
                score = neighbor_rank * edge_weight
                expanded_entities[neighbor] = max(expanded_entities.get(neighbor, 0), score)

                # 2-hop neighbors (with decay)
                for hop2 in self._kg.neighbors(neighbor):
                    if hop2 in anchor_entities:
                        continue  # skip backtrack to anchors
                    edge2_weight = self._kg[neighbor][hop2].get("weight", 1.0)
                    hop2_rank = self._kg.nodes[hop2].get("rank", 0.01)
                    score2 = hop2_rank * min(edge_weight, edge2_weight) * 0.5  # decay
                    expanded_entities[hop2] = max(expanded_entities.get(hop2, 0), score2)

        # Step 3: Collect chunks linked to expanded entities
        candidate_chunks: dict[int, float] = {}  # chunk_uid -> aggregate score
        for ent_key, ent_score in expanded_entities.items():
            for chunk_uid in self._entity_chunk_map.get(ent_key, set()):
                if chunk_uid in initial_uids:
                    continue
                candidate_chunks[chunk_uid] = candidate_chunks.get(chunk_uid, 0) + ent_score

        # Rank and return top chunks
        sorted_uids = sorted(candidate_chunks.items(), key=lambda x: x[1], reverse=True)

        results = []
        for chunk_uid, score in sorted_uids[:7]:
            for chunk in self._chunks:
                if chunk.get("uid") == chunk_uid:
                    results.append({**chunk, "graph_score": round(score, 4)})
                    break

        logger.info(
            "Graph search: %d anchors → %d expanded entities → %d candidate chunks → %d results",
            len(anchor_entities), len(expanded_entities), len(candidate_chunks), len(results),
        )
        return results

    def _graph_search_fallback(self, initial_chunks: list[dict]) -> list[dict]:
        """Fallback: text-based co-occurrence when no graph is available."""
        if not initial_chunks or not self._entities:
            return []

        chunk_entities = set()
        for chunk in initial_chunks:
            text = chunk.get("text", "").lower()
            for ent in self._entities:
                ent_text = ent.get("text", "").lower()
                if ent_text and len(ent_text) > 2 and ent_text in text:
                    chunk_entities.add(ent_text)

        if not chunk_entities:
            return []

        initial_uids = {c.get("uid") for c in initial_chunks}
        expanded = []
        for chunk in self._chunks:
            uid = chunk.get("uid")
            if uid in initial_uids:
                continue
            text = chunk.get("text", "").lower()
            overlap = sum(1 for ent in chunk_entities if ent in text)
            if overlap >= 2:
                expanded.append({**chunk, "graph_score": overlap})

        expanded.sort(key=lambda x: x.get("graph_score", 0), reverse=True)
        return expanded[:5]

    def _get_entity_context(self, question: str, chunks: list[dict] = None) -> str:
        """
        Build entity context using the knowledge graph.

        Includes:
        - Matched entities with their labels and mention counts
        - Graph relationships (connected entities via edges)
        - PageRank importance scores
        """
        if not self._entities:
            return ""

        q_lower = question.lower()

        # Find entities matching the question
        matched_keys: list[str] = []
        for e in self._entities:
            entity_text = e.get("text", "").lower()
            lemma_key = e.get("lemma_key", "").lower()

            if entity_text in q_lower or lemma_key in q_lower:
                matched_keys.append(lemma_key)
                continue
            if len(entity_text) > 2 and (entity_text in q_lower or q_lower in entity_text):
                matched_keys.append(lemma_key)
                continue
            words = lemma_key.split("_")
            if any(w in q_lower for w in words if len(w) > 2):
                matched_keys.append(lemma_key)

        # Also match from chunk text
        if chunks:
            chunk_text = " ".join(c.get("text", "") for c in chunks).lower()
            for e in self._entities:
                ent_text = e.get("text", "").lower()
                if ent_text and len(ent_text) > 2 and ent_text in chunk_text:
                    key = e.get("lemma_key", "")
                    if key not in matched_keys:
                        matched_keys.append(key)

        if not matched_keys:
            return ""

        # Build context with graph relationships
        parts = []
        seen = set()

        for key in matched_keys[:15]:
            if key in seen:
                continue
            seen.add(key)

            node_data = self._kg.nodes.get(key, {}) if key in self._kg else {}
            text = node_data.get("text", key)
            label = node_data.get("label", "?")
            count = node_data.get("count", 0)
            rank = node_data.get("rank", 0)

            entry = f"- {text} [{label}] (mentions: {count}"
            if rank > 0:
                entry += f", importance: {rank:.4f}"
            entry += ")"

            # Add graph neighbors (related entities)
            if key in self._kg and self._kg.degree(key) > 0:
                neighbors = []
                for nbr in self._kg.neighbors(key):
                    edge_w = self._kg[key][nbr].get("weight", 1)
                    nbr_text = self._kg.nodes[nbr].get("text", nbr)
                    if edge_w >= 2:  # only show strong connections
                        neighbors.append(f"{nbr_text}(×{int(edge_w)})")
                if neighbors:
                    entry += f"\n  → related: {', '.join(neighbors[:8])}"

            parts.append(entry)

        return "\n".join(parts)

    # ── strwythura GraphRAG (full mode) ──────────────────────────────

    def run_strwythura_rag(self, question: str) -> dict:
        """
        Use strwythura's full GraphRAG pipeline if available.
        Falls back to simple vector RAG otherwise.
        """
        if self._strwythura_work is None:
            return self.query(question)

        try:
            from strwythura import GraphRAG

            rag = GraphRAG(
                self._strwythura_work,
                self.domain.get("name", "GraphRAG"),
                self.domain.get("description", ""),
                run_local=True,
                use_opik=False,
            )

            t0 = time.time()
            rag.run_errag(question, debug=False)
            chunks_text = rag.get_chunks_text()
            response = rag.rag.forward(question)
            elapsed = time.time() - t0

            return {
                "question": question,
                "answer": response.response if hasattr(response, "response") else str(response),
                "sources": ["strwythura_graphrag"],
                "num_chunks": len(chunks_text),
                "elapsed_sec": round(elapsed, 2),
                "mode": "strwythura_enhanced_graphrag",
            }
        except Exception as e:
            logger.warning("strwythura GraphRAG failed (%s), falling back to vector RAG", e)
            return self.query(question)

    # ── Full Agentic Run ─────────────────────────────────────────────

    def _start_profiling(self) -> None:
        """Start performance profiling if enabled."""
        if self._use_profiling and PROFILING_AVAILABLE:
            self._profiler = Profiler()
            self._profiler.start()
            logger.info("Performance profiling enabled")
        elif self._use_profiling and not PROFILING_AVAILABLE:
            logger.warning("Profiling requested but pyinstrument not installed. Run: pip install pyinstrument")

    def _stop_profiling(self) -> None:
        """Stop profiling and save report."""
        if self._profiler is not None:
            self._profiler.stop()
            output_dir = pathlib.Path("data/output")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save HTML report
            html_path = output_dir / "profile_report.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self._profiler.output_html())
            logger.info("Profiling report saved: %s", html_path)

            # Print text summary
            logger.info("Performance Profile:\n%s", self._profiler.output_text(unicode=True, color=False))

    def run(
        self,
        input_paths: list[str | pathlib.Path],
        *,
        skip_nlp: bool = False,
    ) -> dict:
        """
        Run the full agentic pipeline end-to-end.
        Returns a summary of what was processed.
        """
        # Start profiling if enabled
        self._start_profiling()

        try:
            logger.info("=" * 60)
            logger.info("  Agentic GraphRAG Pipeline Starting")
            logger.info("  LLM: %s", self.config["rag"]["lm_name"])
            logger.info("  Embeddings: %s", self.config["embed"]["model"])
            logger.info("=" * 60)

            # Check prerequisites
            status = self.check_prerequisites()
            logger.info("Prerequisites: %s", status)

            if not status["embed_model"]:
                raise RuntimeError(
                    f"Embedding model not available: {self.config['embed']['model']}. "
                    f"Run: ollama pull {self.config['embed']['model']}"
                )

            if not status["llm_model"]:
                lm = self.config["rag"]["lm_name"].replace("ollama_chat/", "")
                logger.warning("LLM not available: %s. Run: ollama pull %s", lm, lm)

            # Initialize
            self.initialize()

            # Load documents
            documents = self.load_documents(input_paths)
            if not documents:
                raise ValueError("No documents loaded. Check input paths.")

            # Embed & Store
            num_chunks = self.embed_and_store(documents)

            # NLP extraction
            if not skip_nlp:
                self.run_nlp_pipeline(documents)

            logger.info("=" * 60)
            logger.info("  Pipeline Ready - %d chunks from %d documents", num_chunks, len(documents))
            if self._kg.number_of_nodes() > 0:
                logger.info("  Knowledge Graph: %d nodes, %d edges",
                           self._kg.number_of_nodes(), self._kg.number_of_edges())
            logger.info("=" * 60)

            return {
                "documents_loaded": len(documents),
                "total_paragraphs": sum(len(v) for v in documents.values()),
                "chunks_stored": num_chunks,
                "sources": list(documents.keys()),
                "graph_nodes": self._kg.number_of_nodes(),
                "graph_edges": self._kg.number_of_edges(),
            }
        finally:
            # Stop profiling and save report
            self._stop_profiling()

    # ── Interactive Session ──────────────────────────────────────────

    def interactive(self) -> None:
        """Run interactive Q&A session in the terminal with conversation memory."""
        lm = self.config["rag"]["lm_name"].replace("ollama_chat/", "")
        print(f"\n{'=' * 60}")
        print(f"  GraphRAG Interactive Q&A")
        print(f"  LLM: {lm}")
        print(f"  Embeddings: {self.config['embed']['model']}")
        print(f"  Chunks loaded: {len(self._chunks)}")
        if self._kg.number_of_nodes() > 0:
            print(f"  Knowledge Graph: {self._kg.number_of_nodes()} nodes, {self._kg.number_of_edges()} edges")
        print(f"  Conversation memory: enabled")
        print(f"{'=' * 60}")
        print("  Type 'quit' to exit, 'clear' to reset conversation.\n")

        conversation_history: list[dict] = []

        while True:
            try:
                question = input("Q: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not question:
                continue
            if question.lower() in ("quit", "exit", "q"):
                break
            if question.lower() == "clear":
                conversation_history.clear()
                print("  [Conversation history cleared]\n")
                continue

            result = self.query(question, conversation_history=conversation_history)

            # Store Q&A in conversation history
            conversation_history.append({"role": "user", "content": question})
            conversation_history.append({"role": "assistant", "content": result["answer"]})

            print(f"\nA: {result['answer']}")
            print(f"   [{result['elapsed_sec']}s | {result['num_chunks']} chunks | "
                  f"sources: {', '.join(pathlib.Path(s).name for s in result['sources'])}]\n")
