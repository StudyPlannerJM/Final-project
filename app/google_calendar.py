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