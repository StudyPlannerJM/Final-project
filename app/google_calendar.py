# ==============================================================================
# GOOGLE CALENDAR INTEGRATION MODULE
# ==============================================================================
# This file handles all interactions with Google Calendar API
# I use this for authentication, creating/updating/deleting events, and fetching events

import os
import json
from google.oauth2.credentials import Credentials  # Handles Google authentication credentials
from google_auth_oauthlib.flow import Flow  # Manages the OAuth2 login flow
from googleapiclient.discovery import build  # Creates the Google Calendar API service
from googleapiclient.errors import HttpError  # Catches errors from Google API
from datetime import datetime, timedelta  # For handling dates and times
from flask import url_for  # Generates URLs for my Flask app

# IMPORTANT: Allow OAuth2 to work over HTTP for local development
# In production with HTTPS, you can remove this line
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


# ==============================================================================
# CONFIGURATION
# ==============================================================================

# SCOPES: This tells Google what permissions I need
# 'calendar' scope allows me to read and write to the user's calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']

# This is the file I downloaded from Google Cloud Console
# Contains my app's credentials (must keep it secret!)
CLIENT_SECRET_FILE = 'client_secret.json'


# ==============================================================================
# AUTHENTICATION FUNCTIONS
# ==============================================================================

def get_google_auth_flow():
    """
    Creates the OAuth2 flow for Google authentication.
    
    What this does:
    1. Reads my app credentials from client_secret.json
    2. Sets up what permissions (scopes) I need
    3. Tells Google where to send the user after they login
    
    Returns:
        Flow object: Used to redirect user to Google login page
    """
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,  # My app's credentials
        scopes=SCOPES,  # What permissions I'm asking for
        redirect_uri=url_for('main.oauth2callback', _external=True)  # Where Google sends user back
    )
    return flow


def get_calendar_service(user):
    """
    Creates a connection to Google Calendar for a specific user.
    
    What this does:
    1. Checks if the user has connected their Google account
    2. Loads their saved authentication token from the database
    3. Creates a "service" object that can interact with Google Calendar
    
    I think of this as getting the "key" to access the user's Google Calendar.
    
    Args:
        user: The User object from my database (contains google_token)
    
    Returns:
        service: A Google Calendar API service object (the "key" to their calendar)
        None: If user hasn't connected Google Calendar yet
    """
    # Step 1: Check if user has connected their Google Calendar
    if not user.google_token:
        return None  # User never authorized, so I can't access their calendar
    
    try:
        # Step 2: Load the saved token from database
        # The token is stored as a JSON string, so I convert it back to a dictionary
        token_data = json.loads(user.google_token)
        
        # Step 3: Create credentials object from the saved token data
        # This is like reconstructing the "key" from saved pieces
        credentials = Credentials(
            token=token_data.get('token'),  # The actual access token
            refresh_token=token_data.get('refresh_token'),  # Used to get new token when old one expires
            token_uri=token_data.get('token_uri'),  # Where to get new tokens
            client_id=token_data.get('client_id'),  # My app's ID
            client_secret=token_data.get('client_secret'),  # My app's secret
            scopes=SCOPES  # What permissions I have
        )
        
        # Step 4: Build the service - this is the actual tool I use to interact with calendar
        # 'calendar' = the API I want, 'v3' = version 3 of the API
        service = build('calendar', 'v3', credentials=credentials)
        return service
    
    except Exception as e:
        # If anything goes wrong (bad token, network error, etc.), print error and return None
        print(f"Error creating calendar service: {e}")
        return None
    
# ==============================================================================
# CALENDAR EVENT MANAGEMENT FUNCTIONS
# ==============================================================================

def create_calendar_event(service, task):
    """
    Takes one of my tasks and creates it as an event in Google Calendar.
    
    How it works:
    1. Gets the task's due date (or uses tomorrow if none exists)
    2. Creates an event that lasts 1 hour
    3. Sends it to Google Calendar
    4. Returns the event ID so I can track it
    
    Args:
        service: The Google Calendar connection (from get_calendar_service)
        task: My Task object from the database (has title, description, due_date, etc.)
    
    Returns:
        event_id: A unique ID from Google for this event (I save this to sync later)
        None: If something went wrong
    """
    try:
        # STEP 1: Figure out when the event should start
        if task.due_date:
            # Use the task's due date if it has one
            start_time = task.due_date
        else:
            # No due date? I'll schedule it for tomorrow
            start_time = datetime.now() + timedelta(days=1)
        
        # STEP 2: Set event duration to 1 hour
        # (I can change this to any duration later if needed)
        end_time = start_time + timedelta(hours=1)
        
        # STEP 3: Create the event data structure
        # This is the format Google Calendar expects
        event = {
            'summary': task.title,  # Event title (what shows on calendar)
            'description': task.description or 'No description provided',  # Event details
            'start': {
                'dateTime': start_time.isoformat(),  # Start time in ISO format (e.g., 2024-01-15T14:00:00)
                'timeZone': 'UTC',  # Time zone
            },
            'end': {
                'dateTime': end_time.isoformat(),  # End time
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,  # Don't use calendar's default reminders
                'overrides': [
                    {'method': 'popup', 'minutes': 30},  # Popup reminder 30 minutes before
                ],
            },
        }
        
        # STEP 4: Send the event to Google Calendar
        # 'primary' means the user's main calendar
        created_event = service.events().insert(
            calendarId='primary',  # Which calendar to add to (primary = main calendar)
            body=event  # The event data we created above
        ).execute()  # Actually send the request to Google
        
        # STEP 5: Get the event ID from Google's response
        # I need this to update or delete the event later
        return created_event.get('id')
    
    except HttpError as error:
        # If Google returns an error (network issue, auth problem, etc.)
        print(f"An error occurred: {error}")
        return None  # Return None to indicate failure

def update_calendar_event(service, event_id, task):
    """
    Updates an existing event in Google Calendar when I edit a task.
    
    How it works:
    1. Finds the existing event in Google Calendar using its ID
    2. Updates it with the new information from my task
    3. Sends the updates back to Google Calendar
    
    Use case: When I edit a task's title, description, or due date,
    this function makes sure the calendar event matches.
    
    Args:
        service: The Google Calendar connection
        event_id: The unique ID of the event in Google Calendar
        task: My updated Task object with new information
    
    Returns:
        True: If update was successful
        False: If something went wrong
    """
    try:
        # STEP 1: Get the current event from Google Calendar
        # I need this to see what's already there
        event = service.events().get(
            calendarId='primary',  # User's main calendar
            eventId=event_id  # The specific event we want to update
        ).execute()
        
        # STEP 2: Figure out the new start time
        if task.due_date:
            # Use the task's new due date
            start_time = task.due_date
        else:
            # If task doesn't have a due date, keep the original event time
            # Try to get dateTime first, fall back to date if it's an all-day event
            start_time = datetime.fromisoformat(
                event['start'].get('dateTime', event['start'].get('date'))
            )
        
        # STEP 3: Calculate end time (1 hour after start)
        end_time = start_time + timedelta(hours=1)
        
        # STEP 4: Update the event with new information
        event['summary'] = task.title  # New title
        event['description'] = task.description or 'No description provided'  # New description
        event['start'] = {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC',
        }
        event['end'] = {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',
        }
        
        # STEP 5: Send the updated event back to Google Calendar
        updated_event = service.events().update(
            calendarId='primary',  # Which calendar
            eventId=event_id,  # Which event to update
            body=event  # The updated event data
        ).execute()
        
        return True  # Success!
    
    except HttpError as error:
        # If something goes wrong (network issue, event not found, etc.)
        print(f"An error occurred: {error}")
        return False  # Indicate failure
    
def delete_calendar_event(service, event_id):
    """
    Removes an event from Google Calendar.
    
    Simple and straightforward: This tells Google to delete a specific event.
    
    Use case: When I delete a task from my app, this removes
    the corresponding event from Google Calendar too.
    
    Args:
        service: The Google Calendar connection
        event_id: The unique ID of the event to delete
    
    Returns:
        True: If deletion was successful
        False: If something went wrong
    """
    try:
        # Tell Google Calendar to delete this event
        service.events().delete(
            calendarId='primary',  # From the user's main calendar
            eventId=event_id  # Which event to delete
        ).execute()  # Execute the deletion
        
        return True  # Success!
    
    except HttpError as error:
        # Error could mean: event already deleted, network issue, or permission problem
        print(f"An error occurred: {error}")
        return False
    
def get_upcoming_events(service, max_results=10):
    """
    Fetches upcoming events from Google Calendar to display in my app.
    
    How it works:
    1. Gets the current time
    2. Asks Google Calendar for events happening from now into the future
    3. Returns them sorted by start time (earliest first)
    
    Use case: Show what events are coming up in the user's Google Calendar,
    so they can see everything in one place (my app + their calendar).
    
    Args:
        service: The Google Calendar connection
        max_results: How many events to fetch (default is 10)
    
    Returns:
        list: A list of event dictionaries (each has title, time, description, etc.)
        Empty list: If no events found or error occurred
    """
    try:
        # STEP 1: Get current time in ISO format with 'Z' at the end
        # 'Z' means UTC time (Universal Coordinated Time)
        # Example: "2024-01-15T10:30:00Z"
        now = datetime.utcnow().isoformat() + 'Z'
        
        # STEP 2: Request events from Google Calendar
        events_result = service.events().list(
            calendarId='primary',  # User's main calendar
            timeMin=now,  # Only get events from now onwards (no past events)
            maxResults=max_results,  # Limit how many events to get
            singleEvents=True,  # Break recurring events into separate instances
            orderBy='startTime'  # Sort by start time (earliest first)
        ).execute()
        
        # STEP 3: Extract the events from the response
        # If no events found, this returns an empty list
        events = events_result.get('items', [])
        return events
    
    except HttpError as error:
        # If something goes wrong (network issue, auth problem, etc.)
        print(f"An error occurred: {error}")
        return []  # Return empty list instead of crashing


# ==============================================================================
# END OF FILE
# ==============================================================================
# Summary of what this file does:
# 1. get_google_auth_flow() - Starts the Google login process
# 2. get_calendar_service(user) - Gets access to a user's calendar
# 3. create_calendar_event(service, task) - Adds a task to Google Calendar
# 4. update_calendar_event(service, event_id, task) - Updates an existing event
# 5. delete_calendar_event(service, event_id) - Removes an event
# 6. get_upcoming_events(service, max_results) - Fetches upcoming events
# ==============================================================================