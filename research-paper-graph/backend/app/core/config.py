import os
import yaml
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel

# Load .env as a safety net (main.py does this first, but importing config from
# tests/scripts would not go through main.py)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)
except ImportError:
    pass  # dotenv not installed yet during initial setup


class Neo4jConfig(BaseModel):
    uri: str  = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER",     "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "password")


class DatabaseConfig(BaseModel):
    backend: str = "neo4j"


class CrawlerConfig(BaseModel):
    download_dir: str = "./data/papers"
    max_concurrent_downloads: int = 3
    default_depth: int = 2
    default_max_papers: int = 20


class RateLimitsConfig(BaseModel):
    semantic_scholar: float = 1.2
    arxiv: float = 3.0
    google_scholar: float = 5.0


class LLMOllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434"
    model: str = "gemma3:latest"
    vision_model: str = "llava:latest"


class LLMGeminiConfig(BaseModel):
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = "gemini-2.0-flash"
    rate_limit_per_minute: int = 15


class LLMConfig(BaseModel):
    provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama: LLMOllamaConfig = LLMOllamaConfig()
    gemini: LLMGeminiConfig = LLMGeminiConfig()


class GoogleScholarConfig(BaseModel):
    enabled: bool = True
    use_proxy: bool = False
    proxy_url: str = ""


class APIConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000


class AppConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    neo4j: Neo4jConfig = Neo4jConfig()
    crawler: CrawlerConfig = CrawlerConfig()
    rate_limits: RateLimitsConfig = RateLimitsConfig()
    api: APIConfig = APIConfig()
    llm: LLMConfig = LLMConfig()
    google_scholar: GoogleScholarConfig = GoogleScholarConfig()


def load_config(config_path: str = "config.yaml") -> AppConfig:
    """Loads configuration from yaml file"""
    if not os.path.exists(config_path):
        # Check if it's in the parent directory or common locations
        possible_paths = [config_path, "backend/config.yaml", "../config.yaml"]
        for path in possible_paths:
            if os.path.exists(path):
                config_path = path
                break
        else:
            return AppConfig()  # use defaults

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    return AppConfig(**config_data)


# Singleton
try:
    settings = load_config()
except Exception as e:
    settings = AppConfig()
    print(f"Warning: Could not load config, using defaults: {e}")
