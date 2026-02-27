"""
BGE-M3 embedding integration via Ollama API.
Provides OllamaEmbedding class compatible with LanceDB's embedding interface
and utility functions for direct embedding calls.
"""

import logging
from typing import Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)


class OllamaEmbedding:
    """
    Embedding client using Ollama's /api/embed endpoint.
    Configured for bona/bge-m3:latest (1024-dim) by default.
    """

    def __init__(
        self,
        model: str = "bona/bge-m3:latest",
        base_url: str = "http://localhost:11434",
        dim: int = 1024,
        timeout: float = 120.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.dim = dim
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string, return vector."""
        resp = self._client.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()

        embeddings = data.get("embeddings", [])
        if not embeddings:
            logger.warning("Empty embedding returned for text: %s...", text[:50])
            return [0.0] * self.dim

        return embeddings[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in one call."""
        if not texts:
            return []

        resp = self._client.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()

        embeddings = data.get("embeddings", [])

        # Pad missing embeddings with zeros
        while len(embeddings) < len(texts):
            embeddings.append([0.0] * self.dim)

        return embeddings

    def embed_numpy(self, text: str) -> np.ndarray:
        """Return embedding as numpy array."""
        vec = self.embed_text(text)
        return np.array(vec, dtype=np.float32)

    def embed_batch_numpy(self, texts: list[str]) -> np.ndarray:
        """Return batch embeddings as numpy array."""
        vecs = self.embed_batch(texts)
        return np.array(vecs, dtype=np.float32)

    def is_available(self) -> bool:
        """Check if the Ollama server and model are reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in models)
        except Exception:
            return False

    def close(self) -> None:
        self._client.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class OllamaLLM:
    """
    LLM client using Ollama's /api/generate endpoint.
    Configured for gemma3:27b by default.
    """

    def __init__(
        self,
        model: str = "gemma3:27b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
        max_tokens: int = 3000,
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = httpx.Client(timeout=timeout)

    def generate(self, prompt: str, *, system: Optional[str] = None, temperature: Optional[float] = None) -> str:
        """Generate a response from the LLM."""
        # Use provided temperature or fallback to instance default
        temp = temperature if temperature is not None else self.temperature

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_predict": self.max_tokens,
            },
        }
        if system:
            payload["system"] = system

        try:
            resp = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0,  # 2 minutes timeout
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            error_msg = f"LLM generation failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nOllama error: {error_detail}"
                except:
                    error_msg += f"\nResponse: {e.response.text[:500]}"
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def chat(
        self,
        messages: list[dict[str, str]],
    ) -> str:
        """Chat-style generation."""
        try:
            resp = self._client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
                timeout=120.0,  # 2 minutes timeout
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")
        except Exception as e:
            error_msg = f"LLM chat failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f"\nOllama error: {error_detail}"
                except:
                    error_msg += f"\nResponse: {e.response.text[:500]}"
            logger = logging.getLogger(__name__)
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def is_available(self) -> bool:
        """Check if the Ollama server and model are reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return any(m.get("name", "").startswith(self.model.split(":")[0]) for m in models)
        except Exception:
            return False

    def close(self) -> None:
        self._client.close()
