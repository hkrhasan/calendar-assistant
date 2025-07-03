from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str
    
class CheckAvailabilitySchema(BaseModel):
  time_range: str = Field(..., description="Time range in natural language (e.g., 'tomorrow 2-4pm', '2025-07-05 14:00 to 16:00')")

class CreateBookingSchema(BaseModel):
  summary: str = Field(..., description="Event title or description")
  time_range: str = Field(..., description="Time range in natural language (e.g., 'next monday 10am to 11am')")
  
class ListEventsSchema(BaseModel):
    time_range: str = Field(..., description="Time range to list events (e.g., 'today', 'this week', 'next monday')")
    max_results: int = Field(5, description="Maximum number of events to return (default: 5)")
    
    
class ConfirmBookingSchema(BaseModel):
    confirmation: bool = Field(..., description="User confirmation (True/False)")
    summary: str = Field(..., description="Event title")
    start_iso: str = Field(..., description="Start time in ISO format")
    end_iso: str = Field(..., description="End time in ISO format")