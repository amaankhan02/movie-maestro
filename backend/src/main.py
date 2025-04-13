from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .models import ChatRequest, ChatResponse, Message
from .services.chat_service import ChatService

app = FastAPI(title="AI Answer Engine API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chat service
chat_service = ChatService()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response, conversation_id = await chat_service.get_response(
            message=request.message, conversation_id=request.conversation_id
        )
        return ChatResponse(response=response, conversation_id=conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}", response_model=list[Message])
async def get_conversation(conversation_id: str):
    history = chat_service.get_conversation_history(conversation_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return history


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
