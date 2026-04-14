"""LLM resource and configuration management."""

import os
from dataclasses import dataclass, field

PROVIDER_PATH_SUFFIXES = {
    "gpt": "/openai/v1/",
    "claude": "/anthropic",
}

DEFAULT_LLM_TEMPERATURE = 0.7
DEFAULT_LLM_MAX_TOKENS = 2048
MAX_RESOURCES = 5


@dataclass
class LLMResource:
    """An Azure Foundry resource hosting one or more model deployments."""

    base_url: str
    api_key: str
    provider: str  # "gpt" or "claude"
    deployments: list[str] = field(default_factory=list)

    @property
    def full_base_url(self) -> str:
        """Base URL with provider-specific path suffix appended."""
        suffix = PROVIDER_PATH_SUFFIXES.get(self.provider, "")
        return self.base_url.rstrip("/") + suffix


@dataclass
class LLMConfig:
    """Configuration for the LLM client."""

    resources: list[LLMResource]
    deployment: str = ""
    temperature: float = DEFAULT_LLM_TEMPERATURE
    max_tokens: int = DEFAULT_LLM_MAX_TOKENS

    def resolve_resource(self, deployment: str) -> LLMResource:
        """Find the resource that hosts the given deployment."""
        for resource in self.resources:
            if deployment in resource.deployments:
                return resource
        available = self.all_deployments()
        raise ValueError(
            f"Deployment '{deployment}' not found in any resource. "
            f"Available: {available}"
        )

    def all_deployments(self) -> list[str]:
        """Flat list of all deployment names across all resources."""
        result: list[str] = []
        for resource in self.resources:
            result.extend(resource.deployments)
        return result


def load_llm_config() -> LLMConfig:
    """Load LLM configuration from environment variables.

    Scans LLM_RESOURCE_1_* through LLM_RESOURCE_5_*.
    Skips resources with empty BASE_URL.
    """
    from dotenv import load_dotenv

    load_dotenv(override=True)

    resources: list[LLMResource] = []

    for i in range(1, MAX_RESOURCES + 1):
        prefix = f"LLM_RESOURCE_{i}_"
        base_url = os.getenv(f"{prefix}BASE_URL", "").strip()
        if not base_url:
            continue

        api_key = os.getenv(f"{prefix}API_KEY", "")
        provider = os.getenv(f"{prefix}PROVIDER", "gpt").lower()
        deployments_str = os.getenv(f"{prefix}DEPLOYMENTS", "")
        deployments = [d.strip() for d in deployments_str.split(",") if d.strip()]

        resources.append(
            LLMResource(
                base_url=base_url,
                api_key=api_key,
                provider=provider,
                deployments=deployments,
            )
        )

    # Default deployment: first deployment from first resource
    all_deps = []
    for r in resources:
        all_deps.extend(r.deployments)
    default_deployment = all_deps[0] if all_deps else ""

    return LLMConfig(
        resources=resources,
        deployment=os.getenv("LLM_DEPLOYMENT", default_deployment),
        temperature=float(os.getenv("LLM_TEMPERATURE", str(DEFAULT_LLM_TEMPERATURE))),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", str(DEFAULT_LLM_MAX_TOKENS))),
    )
