from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import os


class GoogleCalendar:
  __SCOPES = [
    "https://www.googleapis.com/auth/calendar"
  ]
  __FILE_PATH = "credentials.json"
  
  def __init__(self, calendar_id = None):
     # Get calendar ID from environment if not provided
    self.__calendar_id = calendar_id or os.getenv("GOOGLE_CALENDAR_ID")

    if not self.__calendar_id:
            raise ValueError("Calendar ID must be provided or set in GOOGLE_CALENDAR_ID")
    
    credentials = service_account.Credentials.from_service_account_file(filename=self.__FILE_PATH, scopes=self.__SCOPES)
    
    # Create service with cache disabled
    self.service = build(
        'calendar', 
        'v3', 
        credentials=credentials,
        cache_discovery=False,
        static_discovery=False
    )
  
  def create_booking(self, summary, start_iso, end_iso):
    body = {
        "summary": summary,
        "start": {"dateTime": start_iso, "timeZone": "UTC"},
        "end": {"dateTime": end_iso, "timeZone": "UTC"}
    }
    return self.service.events().insert(
        calendarId=self.__calendar_id, 
        body=body
    ).execute()
  
  def get_freebusy(self, start_iso, end_iso):
    body = {
        "timeMin": start_iso,
        "timeMax": end_iso,
        "items": [{"id": self.__calendar_id}],
        "timeZone": "UTC"
    }
    response = self.service.freebusy().query(body=body).execute()
    return response.get('calendars', {}).get(self.__calendar_id, {}).get('busy', []) 
  
  def list_events(self, start_iso, end_iso, max_results=10):
    return self.service.events().list(
        calendarId=self.__calendar_id,
        timeMin=start_iso,
        timeMax=end_iso,
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime"
    ).execute().get('items', [])



if __name__ == "__main__":
  calendar = GoogleCalendar()
  # Example data for the event
  summary = "Team Meeting"
  start_time = datetime.now() + timedelta(days=1)  # Tomorrow at the same time
  end_time = start_time + timedelta(hours=1)  # 1-hour meeting

  # Convert to ISO format (Google Calendar requires this format)
  start_iso = start_time.isoformat() + 'Z'  # Add 'Z' for UTC
  end_iso = end_time.isoformat() + 'Z'


  busy_slots = calendar.get_freebusy(start_iso, end_iso)

  if busy_slots:
    print("The calendar is busy during these times:")
    for slot in busy_slots:
        print(f"Start: {slot['start']}, End: {slot['end']}")
  else:
    # Call the function
    booking_link = calendar.create_booking(summary, start_iso, end_iso)

    print(f"Event created successfully. View it here: {booking_link}")

