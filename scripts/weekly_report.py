#!/usr/bin/env python3
"""
Rapport hebdomadaire CEO
Récupère les événements Google Agenda, les classifie par catégorie via Claude,
calcule les heures par pôle et envoie un rapport + conseil sur Slack.
"""

import os
import json
import urllib.request
from datetime import datetime, timedelta
import pytz
from google.oauth2 import service_account
from googleapiclient.discovery import build
import requests

TIMEZONE = pytz.timezone("America/Montreal")

CATEGORIES = [
    "Acquisition Clients",
    "Opérations",
    "Rencontre Clients",
    "Meeting",
    "Rocks",
    "Formation",
    "Personnel",
]

EXCLUDED_CATEGORIES = {"Personnel"}


def get_calendar_service():
    service_account_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    return build("calendar", "v3", credentials=credentials)


def get_last_week_range():
    now = datetime.now(TIMEZONE)
    last_monday = now - timedelta(days=now.weekday() + 7)
    last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return last_monday, last_sunday


def fetch_events(service, calendar_id, time_min, time_max):
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


def classify_events_with_claude(events):
    """
    Envoie tous les titres d'événements à Claude pour classification par catégorie.
    Retourne un dict {titre: catégorie}.
    """
    # Extraire les titres uniques avec durée > 0
    timed_events = [
        e for e in events
        if "dateTime" in e.get("start", {}) and "dateTime" in e.get("end", {})
    ]

    if not timed_events:
        return {}

    titles = list({e.get("summary", "Sans titre") for e in timed_events})

    categories_str = "\n".join(f"- {c}" for c in CATEGORIES)
    titles_str = "\n".join(f"- {t}" for t in titles)

    prompt = f"""Tu es un assistant qui classifie des événements d'agenda pour un CEO.

Catégories disponibles :
{categories_str}

Voici les titres des événements de la semaine. Pour chaque titre, assigne la catégorie la plus appropriée.
Utilise exactement le nom de la catégorie tel qu'écrit ci-dessus.
Si un événement ne correspond clairement à aucune catégorie de travail, utilise "Personnel".

Titres à classifier :
{titles_str}

Réponds UNIQUEMENT avec un objet JSON valide, sans texte avant ou après.
Format : {{"titre de l'événement": "Catégorie", ...}}"""

    payload = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 1000,
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

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Anthropic API error {e.code}: {error_body}")
        raise

    raw = data["content"][0]["text"].strip()
    # Nettoyer si Claude ajoute des backticks
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def calculate_category_hours(events, classification):
    category_hours = {}

    for event in events:
        start = event.get("start", {})
        end = event.get("end", {})
        if "dateTime" not in start:
            continue

        title = event.get("summary", "Sans titre")
        category = classification.get(title, "Autre")

        if category in EXCLUDED_CATEGORIES:
            continue

        start_dt = datetime.fromisoformat(start["dateTime"])
        end_dt = datetime.fromisoformat(end["dateTime"])
        duration = (end_dt - start_dt).total_seconds() / 3600

        category_hours[category] = category_hours.get(category, 0) + duration

    return category_hours


def get_ai_advice(category_hours, total_hours):
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

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Anthropic API error {e.code}: {error_body}")
        raise

    return data["content"][0]["text"]


def build_slack_blocks(category_hours, total_hours, advice, week_start, week_end):
    sorted_cats = sorted(category_hours.items(), key=lambda x: x[1], reverse=True)

    lines = []
    for cat, hours in sorted_cats:
        bar_len = int((hours / total_hours) * 12) if total_hours > 0 else 0
        bar = "█" * bar_len + "░" * (12 - bar_len)
        pct = (hours / total_hours * 100) if total_hours > 0 else 0
        lines.append(f"`{bar}` *{cat}* — {hours:.1f}h ({pct:.0f}%)")

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
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    response = requests.post(webhook_url, json={"blocks": blocks}, timeout=10)
    response.raise_for_status()


def main():
    calendar_id = os.environ["GOOGLE_CALENDAR_ID"]
    week_start, week_end = get_last_week_range()

    print(f"Période : {week_start.strftime('%Y-%m-%d')} → {week_end.strftime('%Y-%m-%d')}")

    service = get_calendar_service()
    events = fetch_events(service, calendar_id, week_start, week_end)
    print(f"{len(events)} événements récupérés")

    print("Classification des événements avec Claude...")
    classification = classify_events_with_claude(events)
    print("Classification :")
    for title, cat in sorted(classification.items()):
        print(f"  {cat:25s} ← {title}")

    category_hours = calculate_category_hours(events, classification)
    total_hours = sum(category_hours.values())
    print(f"\nTotal : {total_hours:.1f}h")

    if total_hours == 0:
        print("Aucune heure enregistrée — rapport non envoyé.")
        return

    print("Génération du conseil...")
    advice = get_ai_advice(category_hours, total_hours)
    print(f"Conseil : {advice}")

    print("Envoi sur Slack...")
    blocks = build_slack_blocks(category_hours, total_hours, advice, week_start, week_end)
    send_slack(blocks)
    print("Message envoyé!")


if __name__ == "__main__":
    main()
