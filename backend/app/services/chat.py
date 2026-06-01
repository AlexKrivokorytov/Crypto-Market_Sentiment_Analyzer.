"""
Service layer for the AI market assistant chat feature.

Encapsulates all business logic for the /chat endpoint:
  - Early-return guard when LLM is not configured (avoids wasted DB I/O)
  - Async context builder (live prices + recent headlines)
  - LLM model fallback chain (reuses the shared httpx client)
  - Structured logging for every model attempt and failure
"""

import asyncio
import logging
from typing import List, Optional

import httpx

from backend.app.core.config import settings
from backend.app.core.database import articles_collection, assets_collection
from backend.app.core.http_client import get_shared_client
from backend.app.schemas.market import ChatRequest, ChatResponse

logger = logging.getLogger("app")

# ---------------------------------------------------------------------------
# System prompt (module-level constant — no magic strings inside methods)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a professional crypto market analyst assistant. "
    "Answer user questions concisely using the live context provided. "
    "Be direct and data-driven. 2-4 sentences max."
)

_LLM_NOT_CONFIGURED_REPLY = ChatResponse(
    reply=(
        "The AI assistant is not configured yet. "
        "Ask the site administrator to set LLM_API_URL and LLM_API_KEY."
    ),
    fallback=True,
)

_ALL_MODELS_FAILED_REPLY = ChatResponse(
    reply="Unable to reach the AI model right now. Please try again in a moment.",
    fallback=True,
)


class ChatService:
    """
    Orchestrates AI-powered market Q&A by combining live database context
    with an OpenRouter LLM call.

    Responsibilities:
      1. Guard early when LLM is not configured (avoids unnecessary DB queries).
      2. Build a rich context string from MongoDB (live prices + recent news).
      3. Route through the model fallback chain from settings.llm_fallback_models_list.
      4. Return a typed ChatResponse — never raises to the caller on partial failure.
    """

    # ── Public entry point ─────────────────────────────────────────────────

    async def answer(self, req: ChatRequest) -> ChatResponse:
        """
        Processes a user question and returns an AI-generated reply.

        Routing:
          - No LLM configured → return descriptive config-error message immediately.
          - LLM configured → build context from DB, then call OpenRouter.
          - On total LLM failure → return graceful fallback message.

        Args:
            req: Validated ChatRequest containing the user message and optional asset_id.

        Returns:
            ChatResponse with the AI reply and a fallback flag.
        """
        if not settings.LLM_API_URL or not settings.LLM_API_KEY:
            logger.warning("chat_llm_not_configured: returning config error reply")
            return _LLM_NOT_CONFIGURED_REPLY

        context = await self._build_context(req.asset_id)
        user_prompt = f"{context}\n\n=== USER QUESTION ===\n{req.message}"

        return await self._call_llm_with_fallback(user_prompt)

    # ── Private helpers ────────────────────────────────────────────────────

    async def _build_context(self, asset_id: str) -> str:
        """
        Queries MongoDB for live asset prices and recent news headlines
        and serialises them into a plain-text LLM context block.

        Args:
            asset_id: Optional asset filter (e.g. 'BTC'). Empty string = all assets.

        Returns:
            Multi-line context string prefixed with section headers.
        """
        article_filter = {"asset_id": asset_id} if asset_id else {}

        recent_articles, assets_raw = await asyncio.gather(
            articles_collection.find(article_filter, sort=[("timestamp_dt", -1)])
            .limit(8)
            .to_list(length=8),
            assets_collection.find({}).to_list(length=20),
        )

        lines: List[str] = ["=== LIVE MARKET CONTEXT ==="]
        for asset in assets_raw:
            lines.append(
                f"{asset.get('id', '?')} — ${asset.get('price', 0):.2f} | "
                f"Sentiment: {asset.get('sentimentLabel', '?')} "
                f"({asset.get('sentimentScore', 50)})"
            )

        if recent_articles:
            lines.append("\n=== RECENT NEWS ===")
            for art in recent_articles:
                reasoning_snippet = str(art.get("llmReasoning", ""))[:120]
                lines.append(
                    f"[{art.get('source', '?')}] {art.get('title', '')} — "
                    f"{art.get('sentimentLabel', '?')} | {reasoning_snippet}"
                )

        return "\n".join(lines)

    async def _call_llm_with_fallback(self, user_prompt: str) -> ChatResponse:
        """
        Iterates through the configured model fallback chain until one succeeds.

        On 429 (rate limit) for the first model only, waits 5 seconds and retries
        once before advancing to the next model. Background-logs every failure.

        Args:
            user_prompt: The fully assembled user prompt (context + question).

        Returns:
            ChatResponse with the LLM reply, or a graceful fallback message
            if every model in the chain fails.
        """
        api_url = str(settings.LLM_API_URL).rstrip("/")
        headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
        client = get_shared_client()
        models = settings.llm_fallback_models_list

        last_error: Optional[Exception] = None

        for idx, model in enumerate(models):
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            }

            try:
                resp = await client.post(
                    f"{api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )

                # Single retry on 429 for the first model only (user is waiting)
                if resp.status_code == 429 and idx == 0:
                    logger.warning("chat_429_retry: model=%s sleeping=5s", model)
                    await asyncio.sleep(5.0)
                    resp = await client.post(
                        f"{api_url}/chat/completions",
                        json=payload,
                        headers=headers,
                    )

                resp.raise_for_status()
                data = resp.json()

                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("Empty choices in LLM response")

                reply: str = str(choices[0]["message"]["content"]).strip()
                logger.info("chat_success: model=%s reply_len=%d", model, len(reply))
                return ChatResponse(reply=reply, fallback=False)

            except (httpx.HTTPStatusError, httpx.TimeoutException, ValueError) as exc:
                last_error = exc
                logger.warning("chat_model_failed: model=%s error=%s", model, str(exc))

        logger.warning("chat_all_models_failed: last_error=%s", str(last_error))
        return _ALL_MODELS_FAILED_REPLY


# Module-level singleton — imported directly by the endpoint
chat_service = ChatService()
