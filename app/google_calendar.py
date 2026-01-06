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
