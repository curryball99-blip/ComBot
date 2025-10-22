import asyncio
import os
import logging
from typing import AsyncGenerator, Optional, Tuple
from groq import AsyncGroq
import json
import time
from .prompt_templates import (
    system_prompt_chat,
    system_prompt_analysis,
    system_prompt_prioritized_troubleshoot,
)

logger = logging.getLogger(__name__)

class AsyncGroqClient:
    def __init__(self):
        self.api_key = os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        try:
            self.client = AsyncGroq(api_key=self.api_key)
        except TypeError:
            import httpx
            self.client = AsyncGroq(api_key=self.api_key, http_client=httpx.AsyncClient(timeout=30.0))
        self.model = os.getenv('LLM_MODEL', 'llama-3.3-70b-versatile')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.4'))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '2048'))
        self.top_p = float(os.getenv('LLM_TOP_P', '0.95'))
        # Diagnostics
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.total_failures: int = 0
        self.total_success: int = 0

    # ---------------- Internal helpers -----------------
    def _record_success(self):
        self.last_success_time = time.time()
        self.last_error = None
        self.total_success += 1

    def _record_error(self, err: Exception):
        self.last_error = str(err)
        self.last_error_time = time.time()
        self.total_failures += 1

    def _should_retry(self, msg: str, attempt: int) -> bool:
        transient_indicators = [
            'rate limit', 'Rate limit', '429', 'timeout', 'Timeout', 'temporarily unavailable',
            '502', '503', '504', 'connection reset', 'Connection reset'
        ]
        if attempt >= 3:
            return False
        return any(ind in msg for ind in transient_indicators)

    async def _retry_wrapper(self, coro_factory, op_name: str) -> Tuple[bool, Optional[any]]:
        attempt = 0
        last_exc: Optional[Exception] = None
        base_delay = 1.0
        while attempt < 4:  # up to 4 attempts (initial + 3 retries)
            try:
                result = await coro_factory()
                self._record_success()
                if attempt > 0:
                    logger.info(f"{op_name} succeeded after retry attempt {attempt}")
                return True, result
            except Exception as e:
                msg = str(e)
                self._record_error(e)
                last_exc = e
                if 'model `llama-3.1-70b-versatile` has been decommissioned' in msg and self.model != 'llama-3.3-70b-versatile':
                    logger.warning("Model decommissioned; falling back to llama-3.3-70b-versatile and retrying immediately")
                    self.model = 'llama-3.3-70b-versatile'
                    attempt += 1
                    continue
                if not self._should_retry(msg, attempt):
                    break
                delay = base_delay * (2 ** attempt) + (0.1 * attempt)
                logger.warning(f"{op_name} transient error (attempt {attempt+1}) -> {msg}. Retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
                attempt += 1
        logger.error(f"{op_name} failed after {attempt} attempts: {last_exc}")
        return False, last_exc

    async def generate_response_async(self, query: str, context: str = "", **ai_params) -> str:
        """Generic single-shot completion.

        ai_params may include:
          mode: Optional[str] in {"chat", "analyze", "assist"} to select a system prompt
          use_custom_prompt/custom_system_prompt: explicit override
        """
        if ai_params.get('use_custom_prompt') and ai_params.get('custom_system_prompt'):
            system_prompt = ai_params['custom_system_prompt']
        else:
            mode = ai_params.get('mode')
            if mode == 'chat':
                system_prompt = system_prompt_chat()
            elif mode == 'analyze':
                system_prompt = system_prompt_analysis()
            elif mode == 'assist':
                system_prompt = system_prompt_prioritized_troubleshoot()
            else:
                # fallback to chat style (close to original optimized system prompt)
                system_prompt = system_prompt_chat()
        user_prompt = self._build_generic_user_prompt(query, context)
        temperature = ai_params.get('temperature', self.temperature)
        max_tokens = ai_params.get('max_tokens', self.max_tokens)
        top_p = ai_params.get('top_p', self.top_p)
        model = ai_params.get('model', self.model)

        async def _do_call():
            return await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=False
            )

        ok, result = await self._retry_wrapper(_do_call, "Groq non-stream completion")
        if ok:
            try:
                response = result.choices[0].message.content
                logger.info(f"Generated Groq response len={len(response)}")
                return response
            except Exception as parse_e:
                logger.error(f"Failed to parse Groq response: {parse_e}")
                return "Model response parsing error. Please retry shortly."
        return "The language model is currently unavailable after retries. Please retry in a moment."

    async def generate_response_stream_async(self, query: str, context: str = "", **ai_params) -> AsyncGenerator[str, None]:
        if ai_params.get('use_custom_prompt') and ai_params.get('custom_system_prompt'):
            system_prompt = ai_params['custom_system_prompt']
        else:
            mode = ai_params.get('mode')
            if mode == 'chat':
                system_prompt = system_prompt_chat()
            elif mode == 'analyze':
                system_prompt = system_prompt_analysis()
            elif mode == 'assist':
                system_prompt = system_prompt_prioritized_troubleshoot()
            else:
                system_prompt = system_prompt_chat()
        user_prompt = self._build_generic_user_prompt(query, context)
        temperature = ai_params.get('temperature', self.temperature)
        max_tokens = ai_params.get('max_tokens', self.max_tokens)
        top_p = ai_params.get('top_p', self.top_p)
        model = ai_params.get('model', self.model)

        async def _do_stream_call():
            return await self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stream=True
            )

        ok, stream_or_exc = await self._retry_wrapper(_do_stream_call, "Groq streaming completion")
        if ok:
            try:
                async for chunk in stream_or_exc:
                    if hasattr(chunk, 'choices') and chunk.choices:
                        content = getattr(chunk.choices[0].delta, 'content', None)
                        if content:
                            yield content
                return
            except Exception as stream_parse_e:
                logger.error(f"Stream parsing error: {stream_parse_e}")
                yield "[Error: stream parsing failed]"
                return
        yield "[Error: model unavailable after retries]"

    # ---------------- Generic fallback user prompt -----------------
    def _build_generic_user_prompt(self, query: str, context: str) -> str:
        if not context.strip():
            return f"User Question: {query}\nProvide a precise, actionable response."
        return f"Context:\n{context}\n\nUser Question: {query}\nRespond using ONLY the factual information in context."

    async def is_healthy(self) -> bool:
        try:
            _ = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": "test"}],
                model=self.model,
                max_tokens=1,
                temperature=0
            )
            return True
        except Exception as e:
            logger.error(f"Groq health check failed: {e}")
            return False

    def get_model_info(self) -> dict:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "api_available": bool(self.api_key),
            "last_error": self.last_error,
            "last_error_time": self.last_error_time,
            "last_success_time": self.last_success_time,
            "total_failures": self.total_failures,
            "total_success": self.total_success,
        }
