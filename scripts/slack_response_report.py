#!/usr/bin/env python3
"""
Rapport hebdomadaire Slack — Temps de réponse moyen par utilisateur.

Chaque lundi matin, envoie dans un canal Slack le temps de réponse
moyen de chaque membre de l'équipe pour la semaine précédente.

Deux types de réponses sont mesurées :
 1. Réponses dans un fil de discussion (thread reply)
 2. Échanges consécutifs dans un canal (A poste → B répond dans les 4h)

Permissions Slack Bot requises :
  channels:history, groups:history, im:history, mpim:history,
  channels:read, groups:read, im:read, mpim:read, users:read
"""

import os
import time
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

TIMEZONE = pytz.timezone("America/Montreal")

# Fenêtre max pour considérer un message comme une réponse (évite les retours
# après une longue absence de ne pas fausser la moyenne)
MAX_RESPONSE_WINDOW_HOURS = 4


# ---------------------------------------------------------------------------
# Plage temporelle
# ---------------------------------------------------------------------------


def get_last_week_range():
    """Retourne (oldest_ts, latest_ts, week_start, week_end) pour la semaine passée (lun-dim)."""
    now = datetime.now(TIMEZONE)
    days_since_monday = now.weekday()
    week_start = (now - timedelta(days=days_since_monday + 7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return week_start.timestamp(), week_end.timestamp(), week_start, week_end


# ---------------------------------------------------------------------------
# Slack API helpers
# ---------------------------------------------------------------------------


def get_workspace_users(client):
    """Retourne {user_id: display_name} pour tous les membres actifs non-bot."""
    users = {}
    cursor = None
    while True:
        resp = client.users_list(cursor=cursor, limit=200)
        for m in resp["members"]:
            if m.get("is_bot") or m.get("deleted") or m["id"] == "USLACKBOT":
                continue
            profile = m.get("profile", {})
            name = (
                profile.get("real_name")
                or profile.get("display_name")
                or m.get("name", m["id"])
            )
            users[m["id"]] = name
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return users


def get_accessible_channels(client):
    """Liste les canaux publics, privés, DM de groupe et DM auxquels le bot a accès."""
    channels = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel,mpim,im",
            cursor=cursor,
            limit=200,
            exclude_archived=True,
        )
        channels.extend(resp["channels"])
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
    return channels


def fetch_channel_messages(client, channel_id, oldest, latest):
    """Récupère tous les messages de premier niveau d'un canal sur la période donnée."""
    messages = []
    cursor = None
    while True:
        try:
            resp = client.conversations_history(
                channel=channel_id,
                oldest=str(oldest),
                latest=str(latest),
                cursor=cursor,
                limit=200,
                inclusive=True,
            )
            messages.extend(resp["messages"])
            if not resp.get("has_more"):
                break
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            time.sleep(0.5)  # respect rate limits
        except SlackApiError as e:
            err = e.response.get("error", "")
            if err in ("not_in_channel", "channel_not_found", "missing_scope"):
                break  # Bot non invité dans ce canal — on passe
            raise
    return messages


def fetch_thread_replies(client, channel_id, thread_ts):
    """Récupère toutes les réponses d'un fil de discussion."""
    replies = []
    cursor = None
    while True:
        try:
            resp = client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                cursor=cursor,
                limit=200,
            )
            # Le premier élément est le message parent — on le retire
            replies.extend(resp["messages"][1:])
            if not resp.get("has_more"):
                break
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            time.sleep(0.3)
        except SlackApiError:
            break
    return replies


# ---------------------------------------------------------------------------
# Calcul des temps de réponse
# ---------------------------------------------------------------------------


def collect_response_times(client, channels, user_ids, oldest, latest):
    """
    Parcourt tous les canaux accessibles et collecte les temps de réponse
    (en secondes) par utilisateur.

    Retourne : {user_id: [delay_seconds, ...]}
    """
    response_times = defaultdict(list)
    max_window = MAX_RESPONSE_WINDOW_HOURS * 3600

    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel.get("name", channel_id)
        print(f"  Analyse de #{channel_name}…")

        messages = fetch_channel_messages(client, channel_id, oldest, latest)
        if not messages:
            continue

        # L'API renvoie les messages du plus récent au plus ancien — on inverse
        messages.sort(key=lambda m: float(m["ts"]))

        # --- Source 1 : fils de discussion (threads) ---
        for msg in messages:
            if msg.get("reply_count", 0) == 0:
                continue

            parent_user = msg.get("user")
            parent_ts = float(msg["ts"])
            if parent_user not in user_ids:
                continue

            replies = fetch_thread_replies(client, channel_id, msg["ts"])
            seen_responders = set()

            for reply in sorted(replies, key=lambda r: float(r["ts"])):
                reply_user = reply.get("user")
                reply_ts = float(reply["ts"])

                if (
                    reply_user
                    and reply_user in user_ids
                    and reply_user != parent_user
                    and reply_user not in seen_responders
                ):
                    delay = reply_ts - parent_ts
                    if 0 < delay <= max_window:
                        response_times[reply_user].append(delay)
                        seen_responders.add(reply_user)

        # --- Source 2 : échanges consécutifs dans le canal (non-threadés) ---
        prev_msg = None
        for msg in messages:
            # Ignorer les messages système (join, leave, bot_message…)
            if msg.get("subtype"):
                continue
            cur_user = msg.get("user")
            cur_ts = float(msg["ts"])
            # Exclure les réponses de thread (elles sont déjà comptées ci-dessus)
            is_thread_reply = msg.get("thread_ts") and msg["thread_ts"] != msg["ts"]

            if prev_msg and cur_user and cur_user in user_ids and not is_thread_reply:
                prev_user = prev_msg.get("user")
                prev_ts = float(prev_msg["ts"])
                delay = cur_ts - prev_ts

                if (
                    prev_user
                    and prev_user != cur_user
                    and prev_user in user_ids
                    and 0 < delay <= max_window
                ):
                    response_times[cur_user].append(delay)

            if not msg.get("subtype"):
                prev_msg = msg

        time.sleep(0.2)

    return response_times


# ---------------------------------------------------------------------------
# Formatage & envoi du rapport
# ---------------------------------------------------------------------------


def format_duration(seconds):
    """Convertit des secondes en texte lisible (ex: '19 min', '1h 05min')."""
    minutes = seconds / 60
    if minutes < 60:
        return f"{round(minutes)} min"
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h}h {m:02d}min" if m else f"{h}h"


def build_bar(value, max_value, width=10):
    """
    Barre ASCII : moins de temps de réponse = meilleur score = barre plus longue.
    La barre la plus courte correspond au temps le plus élevé.
    """
    if max_value == 0 or value == 0:
        return "░" * width
    ratio = 1 - (value / max_value)
    filled = max(0, min(width, round(ratio * width)))
    return "█" * filled + "░" * (width - filled)


def send_report(webhook_url, response_times, users, week_start, week_end):
    """Construit et envoie le rapport Block Kit dans Slack."""
    week_label = f"{week_start.strftime('%-d %b')} – {week_end.strftime('%-d %b %Y')}"

    # Calcul des moyennes par utilisateur
    user_stats = []
    for user_id, delays in response_times.items():
        if not delays or user_id not in users:
            continue
        avg = sum(delays) / len(delays)
        user_stats.append(
            {"name": users[user_id], "avg_seconds": avg, "sample": len(delays)}
        )

    # Tri : meilleur temps (le plus court) en premier
    user_stats.sort(key=lambda x: x["avg_seconds"])

    # Utilisateurs sans aucune donnée
    active_ids = set(response_times.keys())
    inactive_names = [
        name for uid, name in users.items() if uid not in active_ids
    ]

    if not user_stats:
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Temps de réponse Slack — {week_label}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_Aucune donnée disponible pour cette semaine._",
                },
            },
        ]
    else:
        max_seconds = max(s["avg_seconds"] for s in user_stats)

        lines = []
        for stat in user_stats:
            bar = build_bar(stat["avg_seconds"], max_seconds)
            duration = format_duration(stat["avg_seconds"])
            sample_label = f"{stat['sample']} échange{'s' if stat['sample'] > 1 else ''}"
            lines.append(
                f"`{bar}` *{stat['name']}* — {duration} en moyenne  _{sample_label}_"
            )

        if inactive_names:
            lines.append("")
            lines.append(f"_Aucune donnée : {', '.join(sorted(inactive_names))}_")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Temps de réponse Slack — {week_label}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Temps de réponse moyen à un message Slack*\n"
                        "_Moins c'est long, mieux c'est_ :white_check_mark:\n\n"
                        + "\n".join(lines)
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "_Mesuré sur les fils de discussion et les échanges consécutifs "
                            f"dans les canaux accessibles au bot (fenêtre max {MAX_RESPONSE_WINDOW_HOURS}h)._"
                        ),
                    }
                ],
            },
        ]

    resp = requests.post(webhook_url, json={"blocks": blocks}, timeout=10)
    resp.raise_for_status()
    print("Rapport envoyé avec succès.")


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------


def main():
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    client = WebClient(token=slack_token)
    oldest, latest, week_start, week_end = get_last_week_range()

    print(
        f"Période : {week_start.strftime('%Y-%m-%d')} → {week_end.strftime('%Y-%m-%d')}"
    )

    print("Récupération des utilisateurs…")
    users = get_workspace_users(client)
    print(f"  {len(users)} utilisateurs trouvés")

    print("Récupération des canaux accessibles…")
    channels = get_accessible_channels(client)
    print(f"  {len(channels)} canaux")

    print("Analyse des temps de réponse…")
    response_times = collect_response_times(
        client, channels, set(users.keys()), oldest, latest
    )

    print("Envoi du rapport…")
    send_report(webhook_url, response_times, users, week_start, week_end)


if __name__ == "__main__":
    main()
