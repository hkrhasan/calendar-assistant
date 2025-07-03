import getpass, os, sys, logging, pytz, uuid, re
from datetime import datetime, timedelta, timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langchain import hub
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain_core.messages import AIMessage, HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential
import dateutil.parser
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from .calendar_client import GoogleCalendar  # Relative import
from .schemas import ListEventsSchema, CreateBookingSchema, CheckAvailabilitySchema

class CalendarAssistant:
  def __init__(self, session_id: str = None):
    load_dotenv()
    self.configure_logging()
    self.configure_api_keys()
    self.llm = self.create_llm()
    self.calendar = GoogleCalendar()
    self.tools = self.create_tools()
    self.agent_executor = self.create_agent_executor()
    # Initialize session and chat history
    self.session_id = session_id or str(uuid.uuid4())
    self.chat_history = []
    self.user_timezone = pytz.timezone("Asia/Kolkata")  # IST timezone
  
  def configure_logging(self):
    logging.basicConfig(level=logging.INFO)
    self.logger = logging.getLogger(__name__)
  
  def configure_api_keys(self):
    if not os.environ.get("GOOGLE_API_KEY"):
      os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter API key for Google Gemini: ")
    
    if not os.environ.get("GOOGLE_CALENDAR_ID"):
      os.environ["GOOGLE_CALENDAR_ID"] = getpass.getpass("Enter Calendar ID: ")
  
  @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
  def create_llm(self):
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0,
        timeout=60,
        max_retries=5,
    )
  
  def parse_time(self, time_str: str, reference: datetime = None) -> dict:
    """Parse natural language time expressions into start and end times"""
    if not reference:
      reference = datetime.now(self.user_timezone)
        
    time_str = time_str.lower().strip()
    
    # Handle relative times
    if time_str in ["now", "current time"]:
      start = reference
      end = start + timedelta(hours=1)
      return {"start": start, "end": end}
    
    if time_str == "today":
      start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
      end = start + timedelta(days=1)
      return {"start": start, "end": end}
    
    if time_str == "tomorrow":
      start = reference.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
      end = start + timedelta(days=1)
      return {"start": start, "end": end}
    
    # Handle time ranges
    try:
      # NEW: Pre-process to ensure future dates
      if re.match(r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", time_str):
          # If month is specified without year, assume future date
          if not re.search(r"\d{4}", time_str):
              # Add current year if missing
              time_str = f"{time_str} {reference.year}"
      
      # Try to parse as a time range
      if " to " in time_str or "-" in time_str:
        separator = " to " if " to " in time_str else "-"
        start_part, end_part = time_str.split(separator, 1)
        
        # Parse start time with exact hour handling
        start_dt = self._parse_with_future_preference(start_part.strip(), reference)
        
        # Parse end time with exact hour handling
        end_dt = self._parse_with_future_preference(end_part.strip(), start_dt)
        
        return {"start": start_dt, "end": end_dt}
      
      # Parse single time point with future preference
      dt = self._parse_with_future_preference(time_str, reference)
        
        # Default to 1 hour duration
      return {"start": dt, "end": dt + timedelta(hours=1)}
    
    except Exception as e:
      self.logger.error(f"Time parsing failed: {str(e)}")
      return {"error": f"Could not parse time: {time_str}"}   

  def _parse_with_future_preference(self, time_str: str, reference: datetime) -> datetime:
    """Parse time with preference for future dates and exact hour handling"""
    try:
      # First try to parse normally
      dt = dateutil.parser.parse(time_str, fuzzy=True, default=reference)
      
      # Extract time components from the string
      hour_match = re.search(r'(\d{1,2})(?::\d{1,2})?\s*(am|pm)?', time_str, re.IGNORECASE)
      if hour_match:
        hour = int(hour_match.group(1))
        period = hour_match.group(2).lower() if hour_match.group(2) else None
        
        # Convert to 24-hour format
        if period == 'pm' and hour < 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
            
        # Check if minutes were specified
        minute_match = re.search(r':(\d{1,2})', time_str)
        minutes = int(minute_match.group(1)) if minute_match else 0
        
        # Set exact time
        dt = dt.replace(hour=hour, minute=minutes, second=0, microsecond=0)
      
      # Handle timezone
      if not dt.tzinfo:
        dt = self.user_timezone.localize(dt)
      else:
        dt = dt.astimezone(self.user_timezone)
          
      return dt
    except:
        return reference
      
  def format_time(self, dt: datetime) -> str:
    """Format datetime for user display"""
    return dt.astimezone(self.user_timezone).strftime("%d %b %Y, %I:%M %p IST")

  def validate_iso_date(self, date_str: str) -> bool:
    """Validate ISO 8601 date format"""
    try:
        datetime.fromisoformat(date_str)
        return True
    except (ValueError, TypeError):
        return False
  
  def check_availability_tool(self, time_range: str) -> dict:
    """
    Check calendar availability in a given time range
    Returns: {available: bool, busy_slots: list, message: str, error: str}
    """
    try:
      parsed_time = self.parse_time(time_range)
      if "error" in parsed_time:
          return {"error": parsed_time["error"]}
      
      start_iso = parsed_time["start"].isoformat()
      end_iso = parsed_time["end"].isoformat()
      
      busy_slots = self.calendar.get_freebusy(start_iso, end_iso)
      
      formatted_start = self.format_time(parsed_time["start"])
      formatted_end = self.format_time(parsed_time["end"])
      logging.info("debugging >> ", busy_slots) 
      if busy_slots:
        return {
            "available": False,
            "busy_slots": busy_slots,
            "message": f"Busy between {formatted_start} and {formatted_end}",
            "suggestions": ["Try a different time", "Adjust the duration"]
        }
      return {
          "available": True,
          "busy_slots": [],
          "message": f"Available between {formatted_start} and {formatted_end}"
      }
    except Exception as e:
      self.logger.error(f"Availability check failed: {str(e)}")
      return {"error": f"Calendar error: {str(e)}"}
  
  def create_booking_tool(self, summary: str, time_range: str) -> dict:
    """
    Create calendar booking if time slot is available
    Returns: {success: bool, event_link: str, message: str, error: str}
    """
    try:
      if not summary.strip():
        return {"error": "Event summary is required"}
          
      parsed_time = self.parse_time(time_range)
      if "error" in parsed_time:
        return {"error": parsed_time["error"]}
     
      # Validate time is in future
      if parsed_time["start"] < datetime.now(self.user_timezone):
        return {
            "error": "Cannot create events in the past",
            "suggestion": "Please specify a future time"
        } 
      
      # Check availability first
      availability = self.check_availability_tool(time_range)
      if availability.get("error"):
        return availability
          
      if not availability["available"]:
        return {
            "error": "Time slot unavailable", 
            "busy_slots": availability.get("busy_slots", []),
            "suggestions": availability.get("suggestions", ["Please choose another time"])
        }
      
      start_iso = parsed_time["start"].isoformat()
      end_iso = parsed_time["end"].isoformat()
      
      # Create the booking
      event = self.calendar.create_booking(summary, start_iso, end_iso)
      
      formatted_start = self.format_time(parsed_time["start"])
      formatted_end = self.format_time(parsed_time["end"])
      
      return {
        "success": True,
        "event_link": event.get("htmlLink", "No link available"),
        "message": f"✅ Booking created: '{summary}' from {formatted_start} to {formatted_end}",
        "event_id": event.get("id", "")
      }
    except Exception as e:
      self.logger.error(f"Booking creation failed: {str(e)}")
      return {"error": f"Booking error: {str(e)}"}
  
  def list_events_tool(self, time_range: str, max_results: int = 5) -> dict:
      """
      List calendar events in a given time range
      Returns: {events: list, count: int, message: str, error: str}
      """
      try:
        parsed_time = self.parse_time(time_range)
        if "error" in parsed_time:
            return {"error": parsed_time["error"]}
        
        start_iso = parsed_time["start"].isoformat()
        end_iso = parsed_time["end"].isoformat()
        
        events = self.calendar.list_events(start_iso, end_iso, max_results)
        
        if not events:
            return {
                "count": 0,
                "events": [],
                "message": "No events found in this time range"
            }
        
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            formatted_events.append({
                "summary": event.get('summary', 'No title'),
                "start": start,
                "end": end,
                "status": event.get('status', 'confirmed')
            })
        
        formatted_start = self.format_time(parsed_time["start"])
        formatted_end = self.format_time(parsed_time["end"])
        
        return {
            "count": len(events),
            "events": formatted_events,
            "message": f"Found {len(events)} events between {formatted_start} and {formatted_end}"
        }
      except Exception as e:
        self.logger.error(f"List events failed: {str(e)}")
        return {"error": f"Error listing events: {str(e)}"}
  
  
  def create_tools(self):
      return [
        StructuredTool.from_function(
          name="GetCurrentTime",
          func=lambda: datetime.now(self.user_timezone).isoformat(),
          description="Returns the current time in ISO 8601 format"
        ),
        StructuredTool.from_function(
          name="CheckAvailability",
          func=self.check_availability_tool,
          description=(
            "Create a new calendar event. Requires event summary and time range. "
            "Always specify full date including year. "
            "Examples: "
            "'Team Meeting' and 'tomorrow 2-3pm', "
            "'Doctor Appointment' and 'July 5, 2024 10am to 11am', "
            "'Project Deadline' and '2025-07-10 17:00'"
          ),
          args_schema=CheckAvailabilitySchema
        ),
        StructuredTool.from_function(
          name="CreateBooking",
          func=self.create_booking_tool,
          description=(
              "Create a new calendar event. Requires event summary and time range. "
              "Examples: "
              "'Team Meeting' and 'tomorrow 2-3pm', "
              "'Doctor Appointment' and 'next friday 10am to 11am', "
              "'Project Deadline' and '2025-07-10 17:00'"
          ),
          args_schema=CreateBookingSchema
        ),
        StructuredTool.from_function(
          name="ListEvents",
          func=self.list_events_tool,
          description=(
            "List calendar events within a specific time range. "
            "Input should be a natural language time expression like: "
            "'today', 'this week', 'next month', or '2025-07-01 to 2025-07-10'. "
            "Optional max_results parameter limits the number of events returned."
          ),
          args_schema=ListEventsSchema
        )
      ]
  
  def create_agent_executor(self):
      prompt = hub.pull("hwchase17/structured-chat-agent")
      agent = create_structured_chat_agent(
        llm=self.llm,
        tools=self.tools,
        prompt=prompt
      )
      return AgentExecutor(
        agent=agent,
        tools=self.tools,
        verbose=True,
        handle_parsing_errors="Check your output and make sure it conforms to the required format!",
        max_iterations=5,
        return_intermediate_steps=True
      )
  
  def chat(self, user_input: str):
    try:
      response = self.agent_executor.invoke({
        "input": user_input,
        "chat_history": self.chat_history
      })
      
      # Add conversation to history
      self.chat_history.append(HumanMessage(content=user_input))
      self.chat_history.append(AIMessage(content=response["output"]))
      
      return response["output"]
    except Exception as e:
      error_msg = f"⚠️ Error: {str(e)}. Please try again or rephrase your request."
      self.logger.error(f"Agent error: {str(e)}")
      return error_msg
 
  def to_dict(self) -> dict:
    """Serialize state for session persistence"""
    return {
      "session_id": self.session_id,
      "chat_history": [
        {
          "type": "ai" if isinstance(msg, AIMessage) else "human",
          "content": msg.content
        }
        for msg in self.chat_history
      ]
    }
    
  @classmethod
  def from_dict(cls, data: dict):
    """Deserialize from session data"""
    assistant = cls(session_id=data["session_id"])
    assistant.chat_history = [
      AIMessage(content=msg["content"]) if msg["type"] == "ai" 
      else HumanMessage(content=msg["content"])
      for msg in data["chat_history"]
    ]
    return assistant
  
  
  def clear_history(self):
    self.chat_history = []

