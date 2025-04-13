from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.models import ChatRequest, ChatResponse, Message
from src.services.chat_service import ChatService

app = FastAPI(title="Movie Maestro API")

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
    """Process a chat message and return the AI's response.
    Creates a POST endpoint for the frontend to send messages to the backend.

    Args:
        request (ChatRequest): The chat request containing the message and optional conversation ID

    Returns:
        ChatResponse: The AI's response, conversation ID, and optional citations and images

    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        response, conversation_id, citations, images, related_queries = (
            await chat_service.get_response(
                message=request.message, conversation_id=request.conversation_id
            )
        )

        # send back a ChatResponse from the backend to the frontend
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            citations=citations,
            images=images,
            related_queries=related_queries,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{conversation_id}", response_model=list[Message])
async def get_conversation(conversation_id: str):
    """Retrieve the history of a specific conversation.
    Creates a GET endpoint for the frontend to retrieve the
    history of a specific conversation.

    Args:
        conversation_id (str): The ID of the conversation to retrieve

    Returns:
        list[Message]: List of messages in the conversation

    Raises:
        HTTPException: If the conversation is not found
    """
    history = chat_service.get_conversation_history(conversation_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return history


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True
    )
