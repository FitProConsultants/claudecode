#!/usr/bin/env python3
"""
Rapport hebdomadaire CEO
Analyse Google Agenda de la semaine passée et envoie un résumé + conseil sur Slack.
"""

import os
import json
from datetime import datetime, timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests
import anthropic

# Timezone Québec
TIMEZONE = pytz.timezone("America/Montreal")

# Mapping couleur Google Agenda → catégorie
# colorId: https://developers.google.com/calendar/api/v3/reference/colors
COLOR_TO_CATEGORY = {
    "1":  "Opérations",          # Lavande
    "2":  "Formation",            # Sauge
    "3":  "Rocks",                # Raisin (Grape)
    "4":  "Meeting",              # Flamant (Flamingo)
    "5":  "Personnel",            # Banane — EXCLU
    "6":  "Meeting",              # Mandarine
    "7":  "Opérations",           # Paon (Peacock)
    "8":  "Acquisition Clients",  # Myrtille (Blueberry)
    "9":  "Formation",            # Basilic (Basil)
    "10": "Meeting",              # Tomate
    "11": "Rencontre Clients",    # Graphite
}

# Catégories exclues du rapport
EXCLUDED_CATEGORIES = {"Personnel"}


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


def fetch_events(service, calendar_id, time_min, time_max):
    """Récupère tous les événements dans la plage de temps."""
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


def categorize_events(events):
    """
    Calcule les heures par catégorie.
    Retourne (dict catégorie→heures, liste événements sans couleur connue).
    """
    category_hours = {}
    unknown_events = []

    for event in events:
        start = event.get("start", {})
        end = event.get("end", {})

        # Ignorer les événements sans heure précise (journée entière)
        if "dateTime" not in start:
            continue

        color_id = event.get("colorId", "0")
        category = COLOR_TO_CATEGORY.get(color_id)

        if category is None:
            # Couleur inconnue → on note pour le log mais on classe en "Autre"
            unknown_events.append({
                "title": event.get("summary", "Sans titre"),
                "colorId": color_id,
            })
            category = "Autre"

        if category in EXCLUDED_CATEGORIES:
            continue

        start_dt = datetime.fromisoformat(start["dateTime"])
        end_dt = datetime.fromisoformat(end["dateTime"])
        duration = (end_dt - start_dt).total_seconds() / 3600

        category_hours[category] = category_hours.get(category, 0) + duration

    return category_hours, unknown_events


def get_ai_advice(category_hours, total_hours):
    """Génère un conseil CEO avec Claude."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

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

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


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
            "text": {
                "type": "plain_text",
                "text": f"📊 Rapport hebdo — {week_str}",
            },
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
            "text": {
                "type": "mrkdwn",
                "text": f"💡 *Conseil :*\n{advice}",
            },
        },
    ]


def send_slack(blocks):
    """Envoie le message sur Slack."""
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    response = requests.post(
        webhook_url,
        json={"blocks": blocks},
        timeout=10,
    )
    response.raise_for_status()


def main():
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]
    week_start, week_end = get_last_week_range()

    print(f"Période analysée : {week_start.strftime('%Y-%m-%d')} → {week_end.strftime('%Y-%m-%d')}")

    service = get_calendar_service()
    events = fetch_events(service, calendar_id, week_start, week_end)
    print(f"{len(events)} événements récupérés")

    category_hours, unknown = categorize_events(events)

    if unknown:
        print(f"⚠️  {len(unknown)} événements avec couleur inconnue :")
        for e in unknown:
            print(f"   - colorId={e['colorId']} : {e['title']}")
        print("   → Ajoutez ces colorId dans COLOR_TO_CATEGORY si nécessaire.")

    total_hours = sum(category_hours.values())
    print(f"Total heures : {total_hours:.1f}h")
    for cat, h in sorted(category_hours.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {h:.1f}h")

    if total_hours == 0:
        print("Aucune heure enregistrée cette semaine — rapport non envoyé.")
        return

    print("Génération du conseil IA...")
    advice = get_ai_advice(category_hours, total_hours)
    print(f"Conseil : {advice}")

    print("Envoi sur Slack...")
    blocks = build_slack_blocks(category_hours, total_hours, advice, week_start, week_end)
    send_slack(blocks)
    print("✅ Message envoyé avec succès!")


if __name__ == "__main__":
    main()
