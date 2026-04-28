from fastapi import APIRouter
from schemas import ChatRequest, ChatResponse
from services.llm_service import chat

router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_with_copilot(req: ChatRequest):
    """
    Chat with Earth Intelligence Copilot.
    
    Supports multi-turn conversation with environmental context.
    Pass current analysis data in `context` for region-specific answers.
    
    Example questions:
    - "Is the forest loss in Jharkhand getting worse?"
    - "Northeast India mein kya ho raha hai?"
    - "Should I alert the forest department?"
    - "What's causing these fires?"
    """
    history_dicts = [{"role": m.role, "content": m.content} for m in req.history]
    
    reply = await chat(
        message=req.message,
        history=history_dicts,
        context=req.context or {}
    )
    
    return ChatResponse(
        reply=reply,
        sources=["NASA FIRMS VIIRS", "CV Analysis Engine"]
    )
