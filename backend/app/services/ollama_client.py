"""Ollama LLM Client with retry and timeout safety."""
import httpx
import logging
import asyncio
import time
from typing import Optional, AsyncGenerator, List, Dict, Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class OllamaClient:
    """Wrapper for Ollama API with safety features."""
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model
        self.timeout = settings.bot_response_timeout
        self.max_retries = 3
        self.retry_delay = 1.0
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

    async def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create a persistent async httpx client."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client

    async def close(self) -> None:
        """Close the persistent httpx clients."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()
            self._async_client = None
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
            self._sync_client = None
        
    async def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            client = await self._get_async_client()
            response = await client.get(
                f"{self.base_url}/api/tags",
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context_messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> str:
        """Generate a response from Ollama (async)."""

        messages = self._build_messages(prompt, system_prompt, context_messages)

        for attempt in range(self.max_retries):
            try:
                client = await self._get_async_client()
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("message", {}).get("content", "")
                    return content.strip()
                logger.error(f"Ollama error: {response.status_code} - {response.text}")

            except asyncio.TimeoutError:
                logger.warning(f"Ollama timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Ollama error on attempt {attempt + 1}: {e}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        return self._get_fallback_response()

    async def generate_non_blocking(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context_messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> str:
        """Generate a response using a thread executor to avoid blocking the event loop."""
        return await asyncio.to_thread(
            self._generate_sync,
            prompt,
            system_prompt,
            context_messages,
            temperature,
            max_tokens
        )
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context_messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 300
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from Ollama."""
        
        messages = self._build_messages(prompt, system_prompt, context_messages)
        
        try:
            client = await self._get_async_client()
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                },
                timeout=self.timeout
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                                
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield self._get_fallback_response()
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when Ollama fails."""
        import random
        fallbacks = [
            "That's an interesting point. I'd like to hear more perspectives on this.",
            "I think we should consider multiple viewpoints on this topic.",
            "This is a complex issue that requires careful consideration.",
            "I agree that this topic has many dimensions to explore.",
            "Let's continue to build on these ideas together."
        ]
        return random.choice(fallbacks)

    def _build_messages(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context_messages: Optional[List[Dict[str, str]]]
    ) -> List[Dict[str, str]]:
        """Build Ollama chat messages payload."""
        messages: List[Dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if context_messages:
            for msg in context_messages:
                role = "user" if msg.get("speaker_id") == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": f"[{msg.get('speaker_name', 'Unknown')}]: {msg.get('content', '')}"
                })

        messages.append({"role": "user", "content": prompt})
        return messages

    def _get_sync_client(self) -> httpx.Client:
        """Get or create a persistent sync httpx client."""
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(timeout=self.timeout)
        return self._sync_client

    def _generate_sync(
        self,
        prompt: str,
        system_prompt: Optional[str],
        context_messages: Optional[List[Dict[str, str]]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Blocking Ollama call used inside a thread executor."""
        messages = self._build_messages(prompt, system_prompt, context_messages)
        client = self._get_sync_client()

        for attempt in range(self.max_retries):
            try:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data.get("message", {}).get("content", "")
                    return content.strip()
                logger.error(f"Ollama error: {response.status_code} - {response.text}")
            except httpx.TimeoutException:
                logger.warning(f"Ollama timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Ollama error on attempt {attempt + 1}: {e}")

            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        return self._get_fallback_response()
