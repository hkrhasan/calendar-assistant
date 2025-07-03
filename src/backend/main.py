import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import atexit
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .agent.assistant import CalendarAssistant
from .agent.schemas import ChatRequest, ChatResponse


# Load environment variables from .env if exists
env_path = os.path.join(os.path.dirname(__file__), '../../.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
    logging.info("Loaded environment variables from .env file")
else:
    logging.info("No .env file found, using system environment variables")

# Session storage (in production, use a database)
sessions_db = {}

app = FastAPI(
  title="Calendar Assistant API",
  description="Backend for conversational calendar booking assistant",
  version="1.0.0"
)

# CORS configuration
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

def get_or_create_session(session_id: str):
  """Get or create session with error handling"""
  try:
    if session_id not in sessions_db:
      assistant = CalendarAssistant(session_id=session_id)
      sessions_db[session_id] = assistant.to_dict()
      logging.info(f"Created new session: {session_id}")
    else:
      assistant = CalendarAssistant.from_dict(sessions_db[session_id])
    return assistant
  except Exception as e:
    logging.error(f"Session creation failed: {str(e)}")
    raise HTTPException(status_code=500, detail="Session initialization error")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
  try:
    assistant = get_or_create_session(request.session_id)
    response = assistant.chat(request.message)
    sessions_db[request.session_id] = assistant.to_dict()
    return {"response": response, "session_id": request.session_id}
  except Exception as e:
    logging.error(f"Chat error: {str(e)}")
    raise HTTPException(
      status_code=500,
      detail="Internal server error" if os.getenv("IS_PRODUCTION") == "true" else str(e)
    )


@app.post("/reset/{session_id}")
async def reset_session(session_id: str):
  """Reset conversation history"""
  if session_id in sessions_db:
    assistant = CalendarAssistant.from_dict(sessions_db[session_id])
    assistant.clear_history()
    sessions_db[session_id] = assistant.to_dict()
    return {"status": "History cleared"}
  return {"status": "Session not found"}

@app.get("/sessions")
async def list_sessions():
  """List active sessions (for debugging)"""
  return {
    "count": len(sessions_db),
    "sessions": list(sessions_db.keys())
  }
    
@atexit.register
def save_sessions():
  with open("sessions_backup.json", "w") as f:
    json.dump(sessions_db, f)
  logging.info("Sessions saved to backup file")