"""Módulo LLM - Gestión de modelos de lenguaje."""

from .lmstudio import LMStudioClient, get_client
from .prompts import get_system_prompt, SYSTEM_PROMPT_ES, SYSTEM_PROMPT_EN

__all__ = [
    'LMStudioClient',
    'get_client', 
    'get_system_prompt',
    'SYSTEM_PROMPT_ES',
    'SYSTEM_PROMPT_EN',
]
