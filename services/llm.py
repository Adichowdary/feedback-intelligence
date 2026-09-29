from hindsight import HindsightServer
from hindsight_client import Hindsight as HindsightClient
from hindsight_litellm import wrap_openai
from openai import OpenAI
from config import settings, BANK_CONFIG
from typing import Optional
import os


# Global Hindsight server instance
_hindsight_server: Optional[HindsightServer] = None
_hindsight_client: Optional[HindsightClient] = None
_wrapped_client = None


def get_hindsight_server() -> HindsightServer:
    """Get or create the Hindsight embedded server"""
    global _hindsight_server
    
    if _hindsight_server is None:
        _hindsight_server = HindsightServer(
            llm_provider=settings.HINDSIGHT_LLM_PROVIDER,
            llm_model=settings.HINDSIGHT_LLM_MODEL,
            llm_api_key=settings.HINDSIGHT_LLM_API_KEY or os.environ.get("OPENAI_API_KEY")
        )
    
    return _hindsight_server


def get_hindsight_url() -> Optional[str]:
    """Resolve the Hindsight API URL: remote URL > embedded server > fallback"""
    if settings.HINDSIGHT_URL:
        return settings.HINDSIGHT_URL
    if _hindsight_server is not None:
        return getattr(_hindsight_server, "url", None)
    return None


def get_hindsight_client() -> HindsightClient:
    """Get or create the Hindsight client (remote Hindsight Cloud URL or embedded server)"""
    global _hindsight_client
    
    if _hindsight_client is None:
        url = settings.HINDSIGHT_URL
        if not url:
            server = get_hindsight_server()
            url = getattr(server, "url", None) or "http://127.0.0.1:8888"
        _hindsight_client = HindsightClient(base_url=url)
    
    return _hindsight_client


def get_llm_client() -> OpenAI:
    """Get the LLM client wrapped with Hindsight for automatic retain/recall"""
    global _wrapped_client
    
    if _wrapped_client is None:
        url = get_hindsight_url() or "http://127.0.0.1:8888"
        base_client = OpenAI(api_key=settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY"))
        
        _wrapped_client = wrap_openai(
            base_client,
            bank_id=BANK_CONFIG["bank_id"],
            hindsight_api_url=url,
        )
    
    return _wrapped_client