"""LLM client abstraction — supports Gemini (free) and OpenAI-compatible (local/Qwen)."""

import os
import json
from abc import ABC, abstractmethod
from typing import Optional


class LLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class GeminiClient(LLMClient):
    """Google Gemini client (free tier) with rate limit handling."""

    def __init__(self, model: str = "gemini-2.5-flash", retry_delay: float = 12.0, rpm_limit: int = 10):
        try:
            from google import genai
        except ImportError:
            raise ImportError("Install: pip install google-genai")

        # Prefer GEMINI_API_KEY; fall back to GOOGLE_API_KEY
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Set GEMINI_API_KEY or GOOGLE_API_KEY env var")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self._name = f"gemini-{model}"
        self.retry_delay = retry_delay
        self.max_retries = 8
        # Proactive rate limiting
        self._min_interval = 60.0 / rpm_limit  # seconds between calls
        self._last_call_time = 0.0

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        import time
        from google.genai import types

        # Proactive throttle: wait if calling too fast
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self._min_interval:
            wait = self._min_interval - elapsed
            print(f"  [THROTTLE] Waiting {wait:.1f}s (rate limit pacing)...")
            time.sleep(wait)

        for attempt in range(self.max_retries):
            try:
                self._last_call_time = time.time()
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=4096,
                    )
                )
                return response.text
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = self.retry_delay * (attempt + 1)
                    print(f"  [RATE LIMIT] Waiting {wait:.0f}s before retry {attempt+2}/{self.max_retries}...")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError(f"Gemini rate limit exceeded after {self.max_retries} retries")

    @property
    def name(self) -> str:
        return self._name


class OpenAICompatibleClient(LLMClient):
    """OpenAI-compatible client — works with vLLM, Ollama, Together, etc."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "Qwen/Qwen2.5-Coder-32B-Instruct",
        api_key: str = "not-needed"
    ):
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install: pip install openai")

        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self._name = model.split("/")[-1] if "/" in model else model

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a formal verification expert specializing in Dafny."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=4096
        )
        return response.choices[0].message.content

    @property
    def name(self) -> str:
        return self._name


class OllamaClient(LLMClient):
    """Ollama client for local models."""

    def __init__(self, model: str = "qwen2.5-coder:32b"):
        self.model = model
        self._name = model
        self.base_url = "http://localhost:11434"

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        import urllib.request
        import json

        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 4096}
        }).encode()

        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")

    @property
    def name(self) -> str:
        return self._name


def create_client(provider: str = "gemini", **kwargs) -> LLMClient:
    """Factory for LLM clients."""
    if provider == "gemini":
        return GeminiClient(**kwargs)
    elif provider == "openai":
        return OpenAICompatibleClient(**kwargs)
    elif provider == "ollama":
        return OllamaClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use: gemini, openai, ollama")
