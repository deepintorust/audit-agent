from __future__ import annotations

from functools import lru_cache

from src.llm_gateway.client import LLMGatewayClient
from src.llm_gateway.settings import load_gateway_config


@lru_cache
def llm_client() -> LLMGatewayClient:
    cfg = load_gateway_config()
    return LLMGatewayClient(cfg)

