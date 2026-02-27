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

import lancedb
import numpy as np
import pyarrow as pa

from .loaders import DocumentLoader
from .embeddings import OllamaEmbedding, OllamaLLM

logger = logging.getLogger(__name__)


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
        """Initialize LanceDB and prepare directories."""
        lancedb_uri = self.config["vect"]["lancedb_uri"]
        pathlib.Path(lancedb_uri).mkdir(parents=True, exist_ok=True)
        pathlib.Path("data/output").mkdir(parents=True, exist_ok=True)
        pathlib.Path(self.config["scraper"]["cache_path"]).mkdir(parents=True, exist_ok=True)

        self._lance_db = lancedb.connect(lancedb_uri)
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
        """Fallback NLP using standalone spaCy with Korean support."""
        try:
            import spacy
            nlp = self._load_spacy_model()
        except ImportError:
            logger.warning("spaCy not installed. Skipping NLP extraction.")
            return

        entities: dict[str, dict] = {}
        uid = 0

        for source, paragraphs in documents.items():
            chunks = self.make_chunks(paragraphs)
            for chunk_text in chunks:
                doc = nlp(chunk_text)

                # Extract named entities from spaCy NER
                for ent in doc.ents:
                    key = ent.text.strip()
                    if not key or len(key) <= 1:
                        continue
                    # For Korean, don't lowercase (no case distinction)
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

                # For Korean text, also extract noun phrases heuristically
                if self._detect_language(chunk_text) == "ko":
                    for token in doc:
                        if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 1:
                            key = token.text.strip()
                            if key and key not in entities:
                                entities[key] = {
                                    "uid": uid,
                                    "text": key,
                                    "label": "NOUN",
                                    "count": 0,
                                    "lemma_key": key,
                                }
                                uid += 1
                            if key in entities:
                                entities[key]["count"] += 1

        # Save entity store (ensure_ascii=False for Korean)
        store_path = pathlib.Path(self.config["ent"]["store_path"])
        store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(store_path, "w", encoding="utf-8") as f:
            for ent in entities.values():
                f.write(json.dumps(ent, ensure_ascii=False) + "\n")

        self._entities = list(entities.values())
        logger.info("Standalone NLP extracted %d entities", len(entities))

    # ── Phase 5: RAG Query ───────────────────────────────────────────

    def query(self, question: str, *, top_k: int = 0) -> dict:
        """
        GraphRAG query:
        1. Vector search for relevant chunks (BGE-M3)
        2. Entity context augmentation
        3. LLM answer generation (gemma3:27b)
        """
        if top_k <= 0:
            top_k = self.config["rag"].get("max_chunks", 9)

        # Vector search
        table = self._get_or_create_table()
        q_vec = self.embedder.embed_text(question)

        try:
            results = table.search(q_vec).limit(top_k).to_list()
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            results = []

        # Build context
        context_parts = []
        sources = set()
        for r in results:
            context_parts.append(r.get("text", ""))
            sources.add(r.get("source", "unknown"))
        context_text = "\n\n---\n\n".join(context_parts)

        # Augment with entity info
        entity_context = self._get_entity_context(question)
        if entity_context:
            context_text = f"{context_text}\n\n[Related Entities]\n{entity_context}"

        # Detect language and generate with LLM
        lang = self._detect_language(question)

        if lang == "ko":
            system_prompt = (
                "당신은 지식이 풍부한 도우미입니다. 제공된 컨텍스트를 기반으로 질문에 답변하세요. "
                "컨텍스트에 충분한 정보가 없으면 그렇다고 명확히 말하세요. "
                "상세하고 정확하게 한국어로 답변하세요."
            )
        else:
            system_prompt = (
                "You are a knowledgeable assistant. Answer the question based on the provided context. "
                "If the context does not contain enough information, say so. "
                "Be detailed and accurate. Respond in the same language as the question."
            )

        user_prompt = f"Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"

        t0 = time.time()
        answer = self.llm.generate(user_prompt, system=system_prompt)
        elapsed = time.time() - t0

        return {
            "question": question,
            "answer": answer,
            "sources": list(sources),
            "num_chunks": len(results),
            "elapsed_sec": round(elapsed, 2),
            "chunks": [r.get("text", "")[:200] for r in results],
        }

    def _get_entity_context(self, question: str) -> str:
        """Load entity info relevant to the question."""
        store_path = pathlib.Path(self.config["ent"]["store_path"])
        if not store_path.exists():
            return ""

        entities = []
        try:
            with open(store_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entities.append(json.loads(line))
        except Exception:
            return ""

        if not entities:
            return ""

        q_lower = question.lower()
        matched = [
            e for e in entities
            if e.get("lemma_key", "") in q_lower
            or any(w in q_lower for w in e.get("lemma_key", "").split("_") if len(w) > 3)
        ]
        matched.sort(key=lambda x: x.get("count", 0), reverse=True)

        parts = []
        for e in matched[:15]:
            parts.append(
                f"- {e.get('text', e.get('lemma_key', ''))} "
                f"[{e.get('label', '?')}] (mentions: {e.get('count', 0)})"
            )
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
        logger.info("=" * 60)

        return {
            "documents_loaded": len(documents),
            "total_paragraphs": sum(len(v) for v in documents.values()),
            "chunks_stored": num_chunks,
            "sources": list(documents.keys()),
        }

    # ── Interactive Session ──────────────────────────────────────────

    def interactive(self) -> None:
        """Run interactive Q&A session in the terminal."""
        lm = self.config["rag"]["lm_name"].replace("ollama_chat/", "")
        print(f"\n{'=' * 60}")
        print(f"  GraphRAG Interactive Q&A")
        print(f"  LLM: {lm}")
        print(f"  Embeddings: {self.config['embed']['model']}")
        print(f"  Chunks loaded: {len(self._chunks)}")
        print(f"{'=' * 60}")
        print("  Type 'quit' to exit.\n")

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

            result = self.query(question)
            print(f"\nA: {result['answer']}")
            print(f"   [{result['elapsed_sec']}s | {result['num_chunks']} chunks | "
                  f"sources: {', '.join(pathlib.Path(s).name for s in result['sources'])}]\n")
