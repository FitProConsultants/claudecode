#!/usr/bin/env python3
"""
Rapport hebdomadaire CEO
Récupère tous les calendriers Google partagés, calcule les heures par catégorie,
génère un conseil CEO avec Claude et envoie le tout sur Slack.
"""

import os
import json
from datetime import datetime, timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests

# Timezone Québec
TIMEZONE = pytz.timezone("America/Montreal")

# Calendriers à exclure du rapport (insensible à la casse)
EXCLUDED_CALENDARS = {"personnel"}


def get_calendar_service():
    """Initialise le service Google Calendar."""
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    return build("calendar", "v3", credentials=credentials)


def get_last_week_range():
    """Retourne (lundi 00h00, dimanche 23h59) de la semaine passée."""
    now = datetime.now(TIMEZONE)
    last_monday = now - timedelta(days=now.weekday() + 7)
    last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return last_monday, last_sunday


def get_accessible_calendars(service):
    """Retourne la liste de tous les calendriers accessibles au compte de service."""
    calendars = []
    page_token = None
    while True:
        result = service.calendarList().list(pageToken=page_token).execute()
        calendars.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return calendars


def fetch_events_from_calendar(service, calendar_id, time_min, time_max):
    """Récupère tous les événements d'un calendrier dans la plage de temps."""
    all_events = []
    page_token = None
    while True:
        result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        ).execute()
        all_events.extend(result.get("items", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return all_events


def calculate_hours(events):
    """Calcule le total d'heures pour une liste d'événements (ignore journées entières)."""
    total = 0.0
    for event in events:
        start = event.get("start", {})
        end = event.get("end", {})
        if "dateTime" not in start:
            continue
        start_dt = datetime.fromisoformat(start["dateTime"])
        end_dt = datetime.fromisoformat(end["dateTime"])
        total += (end_dt - start_dt).total_seconds() / 3600
    return total


def get_ai_advice(category_hours, total_hours):
    """Génère un conseil CEO avec Claude via l'API Anthropic."""
    import urllib.request

    sorted_cats = sorted(category_hours.items(), key=lambda x: x[1], reverse=True)
    breakdown = "\n".join([f"  - {cat}: {h:.1f}h" for cat, h in sorted_cats])

    prompt = f"""Tu es un consultant senior spécialisé en croissance de PME.

Contexte : CEO d'une entreprise qui génère 1M$/an, 4 employés.
Objectif : scaler significativement cette année. Le CEO est encore impliqué dans presque tout.

Répartition du temps cette semaine (total: {total_hours:.1f}h) :
{breakdown}

Donne un conseil court et percutant (3 phrases max) basé sur cette répartition.
Identifie ce qui freine la croissance ou ce qu'il devrait déléguer/réduire.
Sois direct, concret et actionnable. Réponds en français."""

    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    return data["content"][0]["text"]


def build_slack_blocks(category_hours, total_hours, advice, week_start, week_end):
    """Construit les blocs Slack du message."""
    sorted_cats = sorted(category_hours.items(), key=lambda x: x[1], reverse=True)

    lines = []
    for cat, hours in sorted_cats:
        bar_len = int((hours / total_hours) * 12) if total_hours > 0 else 0
        bar = "█" * bar_len + "░" * (12 - bar_len)
        lines.append(f"`{bar}` *{cat}* — {hours:.1f}h")

    week_str = f"{week_start.strftime('%-d %b')} – {week_end.strftime('%-d %b %Y')}"

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"Rapport hebdo — {week_str}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Total : {total_hours:.1f}h travaillées*\n\n" + "\n".join(lines),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"Conseil :\n{advice}"},
        },
    ]


def send_slack(blocks):
    """Envoie le message sur Slack."""
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    response = requests.post(webhook_url, json={"blocks": blocks}, timeout=10)
    response.raise_for_status()


def main():
    week_start, week_end = get_last_week_range()
    print(f"Période analysée : {week_start.strftime('%Y-%m-%d')} → {week_end.strftime('%Y-%m-%d')}")

    service = get_calendar_service()

    # Récupère tous les calendriers accessibles
    calendars = get_accessible_calendars(service)
    print(f"{len(calendars)} calendrier(s) accessible(s) :")
    for cal in calendars:
        print(f"  - {cal['summary']} ({cal['id']})")

    # Calcule les heures par calendrier (= par catégorie)
    category_hours = {}
    for cal in calendars:
        name = cal["summary"]
        cal_id = cal["id"]

        if name.lower() in EXCLUDED_CALENDARS:
            print(f"  ⏭ Ignoré (exclu) : {name}")
            continue

        events = fetch_events_from_calendar(service, cal_id, week_start, week_end)
        hours = calculate_hours(events)

        if hours > 0:
            category_hours[name] = category_hours.get(name, 0) + hours
            print(f"  ✓ {name} : {hours:.1f}h ({len(events)} événements)")
        else:
            print(f"  - {name} : 0h")

    total_hours = sum(category_hours.values())
    print(f"\nTotal : {total_hours:.1f}h")

    if total_hours == 0:
        print("Aucune heure enregistrée cette semaine — rapport non envoyé.")
        return

    print("Génération du conseil IA...")
    advice = get_ai_advice(category_hours, total_hours)
    print(f"Conseil : {advice}")

    print("Envoi sur Slack...")
    blocks = build_slack_blocks(category_hours, total_hours, advice, week_start, week_end)
    send_slack(blocks)
    print("Message envoyé avec succès!")


if __name__ == "__main__":
    main()
