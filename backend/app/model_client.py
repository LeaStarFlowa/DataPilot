from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.error
import urllib.request
from typing import Any

from .config import Settings, settings


logger = logging.getLogger(__name__)


class ModelClient:
    """Chat、Embedding 和 Rerank 接口客户端。"""

    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        self._blocked_until: dict[str, float] = {}
        self.request_attempt_count = 0
        self.retry_count = 0
        self.timeout_event_count = 0
        self.connection_error_event_count = 0

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key)

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> str:
        payload = {
            "model": self.config.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.config.temperature if temperature is None else temperature,
            "stream": False,
            "enable_thinking": self.config.llm_enable_thinking,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        result = self._post(self.config.chat_url, payload)
        try:
            return str(result["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("大模型响应缺少 message.content") from exc

    def chat_json(self, system: str, user: str) -> dict[str, Any]:
        raw = self.chat(system, user, json_mode=True)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise RuntimeError("大模型未返回有效 JSON")
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as exc:
                raise RuntimeError("大模型未返回有效 JSON") from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 10):
            payload = {
                "model": self.config.embedding_model,
                "input": texts[start : start + 10],
                "dimensions": self.config.embedding_dimensions,
                "encoding_format": "float",
            }
            result = self._post(self.config.embeddings_url, payload)
            items = sorted(result.get("data", []), key=lambda item: item.get("index", 0))
            vectors.extend(self._normalize(item["embedding"]) for item in items)
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding 返回数量与输入不一致")
        return vectors

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        if not documents:
            return []
        payload = {
            "model": self.config.rerank_model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
            "instruct": "Rank database schema fields by relevance to the user's analytics query.",
        }
        result = self._post(self.config.rerank_url, payload)
        output = [
            (int(item["index"]), float(item.get("relevance_score", item.get("score", 0))))
            for item in result.get("results", [])
        ]
        return sorted(output, key=lambda item: item[1], reverse=True)

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.api_key:
            raise RuntimeError("LLM_API_KEY 尚未配置")
        if time.monotonic() < self._blocked_until.get(url, 0):
            raise RuntimeError("模型接口暂时处于30秒熔断窗口，请稍后重试")
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(self.config.max_retries + 1):
            self.request_attempt_count += 1
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                last_error = RuntimeError(f"模型接口返回 HTTP {exc.code}: {detail}")
                if exc.code < 500 and exc.code != 429:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                error_text = str(exc).lower()
                if any(token in error_text for token in ("timed out", "timeout", "超时")):
                    self.timeout_event_count += 1
                if any(token in error_text for token in ("winerror 10054", "connection reset", "连接")):
                    self.connection_error_event_count += 1
            if attempt < self.config.max_retries:
                self.retry_count += 1
                delay = 0.8 * (2**attempt)
                logger.warning(
                    "model_request_retry endpoint=%s attempt=%s/%s delay_seconds=%.1f error=%s",
                    url,
                    attempt + 1,
                    self.config.max_retries,
                    delay,
                    last_error,
                )
                time.sleep(delay)
        # 网络请求失败后对当前接口启用短时熔断。
        self._blocked_until[url] = time.monotonic() + 30
        raise RuntimeError(f"模型接口调用失败: {last_error}") from last_error

    def metrics(self) -> dict[str, int]:
        return {
            "model_request_attempt_count": self.request_attempt_count,
            "model_retry_count": self.retry_count,
            "model_timeout_event_count": self.timeout_event_count,
            "model_connection_error_event_count": self.connection_error_event_count,
        }

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [float(value) / norm for value in vector]
