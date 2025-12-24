from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..schemas.ai import QARequest
from ..services.ai_service import DashscopeOpenAIClient, QwenClient, ArkResponsesClient

router = APIRouter(prefix="/ai_qa", tags=["AI QA"])

_dashscope_client = DashscopeOpenAIClient()
_qwen_client = QwenClient()
_ark_client = ArkResponsesClient()

@router.post("/qa/stream")
async def stream_qa(request: QARequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    model = (request.model or '').strip()
    if model == 'dashscope-openai' or model == 'qwen-plus':
        gen = _dashscope_client.call_stream_api(request.user_id, request.question, request.history_flag)
    elif model == 'tongyi':
        gen = _qwen_client.call_stream_api(request.user_id, request.question, request.history_flag)
    elif model == 'ark-deepseek':
        gen = _ark_client.call_stream_api(request.user_id, request.question, request.history_flag)
    else:
        gen = _dashscope_client.call_stream_api(request.user_id, request.question, request.history_flag)

    return StreamingResponse(gen, media_type="text/event-stream")
