"""Configuration handling for the Bedrock Agent CLI."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model configuration."""
    model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    temperature: float = 0.7
    max_tokens: int = 4096


class AWSConfig(BaseModel):
    """AWS configuration."""
    region: str = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None


class AgentConfig(BaseModel):
    """Complete agent configuration."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    aws: AWSConfig = Field(default_factory=AWSConfig)
    system_prompt: str = "You are a helpful assistant."
    tools: list[str] = Field(default_factory=list)
    cache_enabled: bool = False
    cache_tokens: int = 10000


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """Load configuration from a YAML file or use defaults."""
    if config_path is None:
        # Look for default config
        default_paths = [
            Path("config/coding_agent.yaml"),
            Path(__file__).parent.parent.parent / "config" / "coding_agent.yaml",
        ]
        for path in default_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return AgentConfig(**data)

    return AgentConfig()


def get_default_config_path() -> Path:
    """Get the path to the default configuration file."""
    return Path(__file__).parent.parent.parent / "config" / "coding_agent.yaml"
