from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ..schemas.ai import QARequest
from ..services.ai_service import QwenClient

router = APIRouter(prefix="/ai_qa", tags=["AI QA"])

ai_client = QwenClient()

@router.post("/qa/stream")
async def stream_qa(request: QARequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    return StreamingResponse(
        ai_client.call_stream_api(request.user_id, request.question, request.history_flag),
        media_type="text/event-stream"
    )
