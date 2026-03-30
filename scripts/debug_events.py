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
    # Semaine courante : lundi au dimanche
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)

    print(f"Période : {monday.strftime('%Y-%m-%d')} → {sunday.strftime('%Y-%m-%d')}\n")

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=monday.isoformat(),
        timeMax=sunday.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = result.get("items", [])
    print(f"=== {len(events)} événements récupérés ===\n")

    # Résumé colorId
    from collections import Counter
    color_counts = Counter(e.get("colorId", "AUCUN") for e in events if "dateTime" in e.get("start", {}))
    print("=== Résumé colorId ===")
    for color_id, count in sorted(color_counts.items()):
        print(f"  colorId={color_id}: {count} événements")
    print()

    # Affiche les 3 premiers événements avec colorId
    labeled = [e for e in events if "colorId" in e]
    print(f"=== {len(labeled)} événements avec colorId ===")
    for event in labeled[:3]:
        print(f"\n--- {event.get('summary', 'Sans titre')} ---")
        print(json.dumps(event, indent=2, ensure_ascii=False))

    # Affiche aussi 2 événements sans colorId pour comparer
    unlabeled = [e for e in events if "colorId" not in e and "dateTime" in e.get("start", {})]
    print(f"\n=== Exemple sans colorId ===")
    for event in unlabeled[:2]:
        print(f"\n--- {event.get('summary', 'Sans titre')} ---")
        print(json.dumps(event, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
