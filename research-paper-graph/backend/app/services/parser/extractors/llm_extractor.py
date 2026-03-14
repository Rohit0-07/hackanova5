"""LLM abstraction layer — supports Ollama (local) and Gemini (online).

Usage:
    llm = get_llm_client()  # reads from config
    response = await llm.generate("Summarize this paper", system_prompt="You are a research analyst.")
    response = await llm.analyze_image(image_bytes, "Describe the key findings in this figure.")
"""

import base64
import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from loguru import logger


# ──────────────────────────────────────────────
# System Prompts
# ──────────────────────────────────────────────

PAPER_ANALYSIS_SYSTEM_PROMPT = """You are an expert research paper analyst. Your role is to extract structured information from academic papers.

When analyzing a research paper or PDF text, you must:
1. Identify and extract the key sections (Abstract, Introduction, Methodology, Results, Discussion, Conclusion)
2. Summarize the main contributions and findings
3. Extract key metrics, datasets used, and experimental setup
4. Identify limitations mentioned by the authors
5. Note the research methodology and approach used

Return your analysis in a structured, clear format. Be precise and cite specific passages when relevant.
Use academic language. Do not add information that is not present in the source material.
If a section is not found or unclear, explicitly state that with a confidence score."""

IMAGE_ANALYSIS_SYSTEM_PROMPT = """You are an expert at analyzing figures, charts, and diagrams from academic research papers.

When analyzing an image from a research paper, you must:
1. Describe what the figure/chart/diagram shows
2. Identify the type (bar chart, line graph, architecture diagram, flowchart, scatter plot, table, etc.)
3. Extract key data points, trends, or patterns visible in the figure
4. Note axis labels, legends, and any annotations
5. Explain the significance of the visualization in the context of research

Return your analysis as structured JSON with these keys:
- "figure_type": type of visualization
- "description": detailed description of what is shown
- "key_findings": list of main observations/data points
- "labels": any axis labels, legends, or annotations found
- "significance": why this figure matters for the research"""

FEATURE_EXTRACTION_SYSTEM_PROMPT = """You are an expert research feature extractor. Given the full text of a research paper, extract the following structured features:

1. **research_question**: The main question or hypothesis the paper addresses
2. **methodology**: The approach/method used (e.g., "transformer-based model", "randomized controlled trial")
3. **datasets**: List of datasets used with details
4. **key_results**: The main quantitative and qualitative results
5. **contributions**: Novel contributions claimed by the authors
6. **limitations**: Acknowledged limitations
7. **future_work**: Suggested future research directions
8. **keywords**: Key technical terms and concepts

Return your response as valid JSON with the keys listed above. Each value should be a string or list of strings.
Be precise. Only include information explicitly stated in the paper."""


# ──────────────────────────────────────────────
# Abstract LLM Client
# ──────────────────────────────────────────────


class LLMResponse(BaseModel):
    text: str
    model: str
    provider: str
    tokens_used: Optional[int] = None


class AbstractLLMClient(ABC):
    """Abstract interface for LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate text from a prompt."""
        pass

    @abstractmethod
    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str = "Analyze this figure from a research paper.",
        system_prompt: str = IMAGE_ANALYSIS_SYSTEM_PROMPT,
    ) -> LLMResponse:
        """Analyze an image and return a description/analysis."""
        pass


# ──────────────────────────────────────────────
# Ollama Client (Local — qwen3.5 or any model)
# ──────────────────────────────────────────────


class OllamaClient(AbstractLLMClient):
    """Local LLM via Ollama. Default model: qwen3.5:latest"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma3:latest",
        vision_model: str = "llava:latest",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vision_model = vision_model

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        logger.info(f"Ollama generate (chat): model={self.model}, prompt_len={len(prompt)}")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            text=data.get("message", {}).get("content", ""),
            model=self.model,
            provider=self.provider_name,
            tokens_used=data.get("eval_count"),
        )

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str = "Analyze this figure from a research paper.",
        system_prompt: str = IMAGE_ANALYSIS_SYSTEM_PROMPT,
    ) -> LLMResponse:
        logger.info(
            f"Ollama vision (chat): model={self.vision_model}, image_size={len(image_bytes)}"
        )
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {"role": "user", "content": prompt, "images": [b64_image]}
        )

        payload: Dict[str, Any] = {
            "model": self.vision_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.3, "num_predict": 2048},
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        return LLMResponse(
            text=data.get("message", {}).get("content", ""),
            model=self.vision_model,
            provider=self.provider_name,
            tokens_used=data.get("eval_count"),
        )


# ──────────────────────────────────────────────
# Gemini Client (Online — Google AI)
# ──────────────────────────────────────────────


class GeminiClient(AbstractLLMClient):
    """Google Gemini API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        logger.info(f"Gemini generate: model={self.model}, prompt_len={len(prompt)}")
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            contents.append(
                {
                    "role": "model",
                    "parts": [
                        {"text": "Understood. I will follow these instructions."}
                    ],
                }
            )
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        tokens = usage.get("totalTokenCount")

        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider_name,
            tokens_used=tokens,
        )

    async def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str = "Analyze this figure from a research paper.",
        system_prompt: str = IMAGE_ANALYSIS_SYSTEM_PROMPT,
    ) -> LLMResponse:
        logger.info(f"Gemini vision: model={self.model}, image_size={len(image_bytes)}")
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        contents = [
            {
                "role": "user",
                "parts": [
                    {"inline_data": {"mime_type": "image/png", "data": b64_image}},
                    {"text": full_prompt},
                ],
            }
        ]

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
        }

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.provider_name,
            tokens_used=data.get("usageMetadata", {}).get("totalTokenCount"),
        )


# ──────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────


def get_llm_client(
    provider: str = "ollama",
    ollama_base_url: str = "http://localhost:11434",
    ollama_model: str = "gemma3:latest",
    ollama_vision_model: str = "llava:latest",
    gemini_api_key: str = "",
    gemini_model: str = "gemini-2.0-flash",
) -> AbstractLLMClient:
    """Factory to create the appropriate LLM client.

    Providers:
        - "ollama": Local Ollama instance (default: qwen3.5:latest)
        - "gemini": Google Gemini API (requires api_key)
    """
    if provider == "ollama":
        return OllamaClient(
            base_url=ollama_base_url,
            model=ollama_model,
            vision_model=ollama_vision_model,
        )
    elif provider == "gemini":
        if not gemini_api_key:
            raise ValueError(
                "Gemini API key is required. Set llm.gemini_api_key in config.yaml"
            )
        return GeminiClient(api_key=gemini_api_key, model=gemini_model)
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. Supported: 'ollama', 'gemini'"
        )
