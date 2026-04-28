"""
LLM Service for Earth Intelligence Copilot.
Supports: Groq (fast, free), OpenAI (GPT-4), Ollama (local).

Priority: Groq → OpenAI → Ollama (based on available keys).
"""

import httpx
import json
from typing import List, Dict, Optional
from config import settings

SYSTEM_PROMPT = """You are Earth Intelligence Copilot — an advanced AI assistant specialized in environmental monitoring using satellite data.

Your role:
- Analyze fire, deforestation, and flood data
- Provide clear, actionable environmental insights
- Explain scientific data in simple human language
- Highlight urgency and recommend actions
- Support both English and Hinglish responses based on user preference

Data context format you'll receive:
- Fire count, FRP (Fire Radiative Power in MW), forest loss %, CO2 estimate
- Region name, time period, alert level

Guidelines:
- Be concise but informative (2–4 paragraphs max)
- Mention specific numbers from the data
- Always suggest next actions (alert authorities, monitor closely, etc.)
- If alert level is Red/Orange, emphasize urgency
- Never make up data not provided in context"""


async def generate_insight(analysis_data: dict, query: Optional[str] = None) -> str:
    """Generate LLM insight from analysis data."""
    
    context = _build_context(analysis_data)
    user_msg = query or "Analyze this environmental data and provide key insights with recommendations."
    
    provider = _detect_provider()
    
    try:
        if provider == "groq":
            return await _call_groq(context, user_msg)
        elif provider == "openai":
            return await _call_openai(context, user_msg)
        else:
            return await _call_ollama(context, user_msg)
    except Exception as e:
        print(f"[LLM] {provider} failed: {e}. Using fallback.")
        return _fallback_insight(analysis_data)


async def chat(message: str, history: List[Dict], context: dict = {}) -> str:
    """Chat endpoint — handles ongoing conversation."""
    
    provider = _detect_provider()
    messages = _build_chat_messages(message, history, context)
    
    try:
        if provider == "groq":
            return await _chat_groq(messages)
        elif provider == "openai":
            return await _chat_openai(messages)
        else:
            return await _chat_ollama(messages)
    except Exception as e:
        print(f"[LLM Chat] {provider} failed: {e}")
        return "Sorry, LLM service is unavailable. Please check your API keys in .env file."


# ─── Provider Detection ────────────────────────────────────────────────────────

def _detect_provider() -> str:
    if settings.LLM_PROVIDER == "groq" and settings.GROQ_API_KEY:
        return "groq"
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return "openai"
    elif settings.GROQ_API_KEY:
        return "groq"
    elif settings.OPENAI_API_KEY:
        return "openai"
    else:
        return "ollama"


# ─── Groq ─────────────────────────────────────────────────────────────────────

async def _call_groq(context: str, user_msg: str) -> str:
    return await _chat_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n{user_msg}"}
    ])

async def _chat_groq(messages: List[Dict]) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "max_tokens": 600,
                "temperature": 0.7,
            }
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ─── OpenAI ───────────────────────────────────────────────────────────────────

async def _call_openai(context: str, user_msg: str) -> str:
    return await _chat_openai([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n{user_msg}"}
    ])

async def _chat_openai(messages: List[Dict]) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": 600,
            }
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ─── Ollama (Local) ───────────────────────────────────────────────────────────

async def _call_ollama(context: str, user_msg: str) -> str:
    return await _chat_ollama([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{context}\n\n{user_msg}"}
    ])

async def _chat_ollama(messages: List[Dict]) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"num_predict": 600, "temperature": 0.7}
            }
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_context(data: dict) -> str:
    return f"""
=== SATELLITE ENVIRONMENTAL DATA ===
Region:           {data.get('region', 'Unknown')}
Time Period:      Last {data.get('days', 7)} days
Alert Level:      {data.get('alert_level', 'Unknown')}

Fire Data:
  Active Fires:         {data.get('fire_count', 0)}
  High Confidence:      {data.get('high_confidence_fires', 0)}
  Total FRP:            {data.get('total_frp', 0):.1f} MW
  
Environmental Impact:
  Forest Loss:          {data.get('forest_loss_pct', 0):.1f}%
  CO2 Emitted:          {data.get('estimated_co2_tons', 0):.1f} tons
  Air Quality:          {data.get('air_quality_impact', 'Unknown')}
  Flood Risk:           {data.get('flood_risk', 'Unknown')}
=====================================
"""

def _build_chat_messages(message: str, history: List[Dict], context: dict) -> List[Dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if context:
        ctx_str = _build_context(context)
        messages.append({"role": "user", "content": f"Current monitoring context:\n{ctx_str}"})
        messages.append({"role": "assistant", "content": "Understood. I have the current satellite monitoring data. How can I help you?"})
    
    for h in history[-6:]:  # last 6 messages for context window
        messages.append({"role": h["role"], "content": h["content"]})
    
    messages.append({"role": "user", "content": message})
    return messages


def _fallback_insight(data: dict) -> str:
    """Fallback when all LLM providers fail."""
    fires = data.get("fire_count", 0)
    loss = data.get("forest_loss_pct", 0)
    alert = data.get("alert_level", "Green")
    region = data.get("region", "region")
    
    return (
        f"[Auto-Generated Alert — LLM Offline]\n\n"
        f"Alert Level: {alert}\n"
        f"Region: {region}\n"
        f"Active fires detected: {fires}\n"
        f"Estimated forest loss: {loss:.1f}%\n\n"
        f"Please configure GROQ_API_KEY or OLLAMA for detailed AI analysis."
    )
