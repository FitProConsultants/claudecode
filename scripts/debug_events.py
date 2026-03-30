#!/usr/bin/env python3
"""
Script de debug : affiche tous les champs des 5 premiers événements
pour identifier où sont stockés les libellés/catégories.
"""

import os
import json
from datetime import datetime, timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build

TIMEZONE = pytz.timezone("America/Montreal")


def get_calendar_service():
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    return build("calendar", "v3", credentials=credentials)


def main():
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]
    service = get_calendar_service()

    now = datetime.now(TIMEZONE)
    time_min = (now - timedelta(days=7)).isoformat()
    time_max = now.isoformat()

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        maxResults=5,
    ).execute()

    events = result.get("items", [])
    print(f"=== {len(events)} événements récupérés ===\n")

    for i, event in enumerate(events):
        print(f"--- Événement {i+1}: {event.get('summary', 'Sans titre')} ---")
        print(json.dumps(event, indent=2, ensure_ascii=False))
        print()


if __name__ == "__main__":
    main()
