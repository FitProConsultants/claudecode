#!/usr/bin/env python3
"""
YouTube Carousel Creator
Génère automatiquement un carousel LinkedIn/Instagram à partir de la transcription d'une vidéo YouTube.

Usage:
  - Vérification auto des nouvelles vidéos: python youtube_carousel.py
  - Vidéo spécifique: python youtube_carousel.py VIDEO_ID "Titre de la vidéo"
"""

import os
import json
import sys
import re
import requests
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

LAST_VIDEO_FILE = "data/last_processed_video.txt"
CAROUSELS_DIR = "data/carousels"


# ─────────────────────────────────────────────
# YouTube helpers
# ─────────────────────────────────────────────

def get_latest_videos(channel_id, max_results=5):
    """Récupère les dernières vidéos d'une chaîne YouTube."""
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    channel_resp = youtube.channels().list(
        part="contentDetails",
        id=channel_id,
    ).execute()

    items = channel_resp.get("items", [])
    if not items:
        print(f"Aucune chaîne trouvée pour l'ID: {channel_id}")
        return []

    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    playlist_resp = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_id,
        maxResults=max_results,
    ).execute()

    videos = []
    for item in playlist_resp.get("items", []):
        snippet = item["snippet"]
        videos.append({
            "id": snippet["resourceId"]["videoId"],
            "title": snippet["title"],
            "published_at": snippet["publishedAt"],
        })

    return videos


def get_transcript(video_id):
    """Récupère la transcription d'une vidéo YouTube (FR puis EN)."""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Priorité : FR → EN → première dispo
        for lang_codes in (["fr", "fr-CA", "fr-FR"], ["en", "en-US"]):
            try:
                transcript = transcript_list.find_transcript(lang_codes)
                data = transcript.fetch()
                return " ".join(entry["text"] for entry in data)
            except NoTranscriptFound:
                continue

        # Transcription générée automatiquement
        generated = transcript_list.find_generated_transcript(["fr", "fr-CA", "en"])
        data = generated.fetch()
        return " ".join(entry["text"] for entry in data)

    except TranscriptsDisabled:
        print(f"Transcriptions désactivées pour la vidéo {video_id}")
        return None
    except Exception as exc:
        print(f"Erreur lors de la récupération de la transcription ({video_id}): {exc}")
        return None


# ─────────────────────────────────────────────
# Claude AI – génération du carousel
# ─────────────────────────────────────────────

def generate_carousel(video_title, transcript):
    """Utilise Claude pour transformer la transcription en carousel."""

    # On tronque à ~8 000 caractères pour rester dans les limites de tokens
    transcript_excerpt = transcript[:8000]

    prompt = f"""Tu es un expert en création de contenu viral pour LinkedIn et Instagram.

Voici la transcription d'une vidéo YouTube intitulée: "{video_title}"

TRANSCRIPTION:
{transcript_excerpt}

Ta mission: créer un carousel de 7 à 10 slides, engageant et percutant, basé sur le contenu réel de cette vidéo.

RÈGLES:
1. Slide 1 — Hook irrésistible qui donne envie de continuer
2. Slides 2 à N-1 — Les insights, conseils ou points clés les plus précieux
3. Dernière slide — Call-to-action clair (s'abonner, commenter, partager, etc.)
4. Chaque slide doit tenir en 3-5 lignes max (texte court, impactant)
5. Utilise des emojis pertinents mais sobrement
6. Extrais uniquement la vraie valeur de la vidéo, pas de rembourrage

RÉPONDS UNIQUEMENT avec un objet JSON valide (aucun texte avant ou après) de cette structure exacte:
{{
  "titre_carousel": "Titre accrocheur du carousel",
  "description_post": "Texte d'introduction pour accompagner le carousel sur LinkedIn/Instagram (2-3 phrases)",
  "slides": [
    {{
      "numero": 1,
      "titre": "Titre de la slide",
      "contenu": "Contenu percutant de la slide",
      "visuel_suggere": "Description courte du visuel recommandé",
      "emoji": "🎯"
    }}
  ],
  "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"]
}}"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-opus-4-6",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    if response.status_code != 200:
        print(f"Erreur API Anthropic: {response.status_code} — {response.text}")
        return None

    content = response.json()["content"][0]["text"].strip()

    # Extraction du JSON (au cas où Claude ajouterait du texte autour)
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        print(f"Impossible d'extraire le JSON de la réponse: {content[:200]}")
        return None

    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as exc:
        print(f"Erreur de parsing JSON: {exc}")
        return None


# ─────────────────────────────────────────────
# Formatage Slack
# ─────────────────────────────────────────────

def format_carousel_for_slack(video_title, video_id, carousel):
    """Formate le carousel pour un message Slack structuré."""

    slides_text = ""
    for slide in carousel["slides"]:
        emoji = slide.get("emoji", "▶️")
        slides_text += f"{emoji} *Slide {slide['numero']}: {slide['titre']}*\n"
        slides_text += f"{slide['contenu']}\n"
        slides_text += f"_Visuel suggéré: {slide['visuel_suggere']}_\n\n"

    hashtags = " ".join(carousel.get("hashtags", []))

    return {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🎠 Nouveau Carousel Généré !",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Vidéo YouTube:*\n<https://youtube.com/watch?v={video_id}|{video_title}>",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Titre du carousel:*\n{carousel['titre_carousel']}",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📝 Description du post:*\n{carousel.get('description_post', '')}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📊 Slides:*\n\n{slides_text}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*#️⃣ Hashtags:*\n{hashtags}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Fichier JSON complet: `data/carousels/{video_id}.json`",
                    }
                ],
            },
        ]
    }


def send_to_slack(message):
    """Envoie un message à Slack via webhook."""
    if not SLACK_WEBHOOK_URL:
        print("SLACK_WEBHOOK_URL non défini, affichage console uniquement.")
        return True

    resp = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=30)
    if resp.status_code == 200:
        print("Carousel envoyé sur Slack avec succès !")
        return True
    else:
        print(f"Erreur Slack: {resp.status_code} — {resp.text}")
        return False


# ─────────────────────────────────────────────
# Persistance – dernière vidéo traitée
# ─────────────────────────────────────────────

def load_last_processed_video():
    """Charge l'ID de la dernière vidéo traitée."""
    try:
        with open(LAST_VIDEO_FILE, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def save_last_processed_video(video_id):
    """Sauvegarde l'ID de la dernière vidéo traitée."""
    os.makedirs("data", exist_ok=True)
    with open(LAST_VIDEO_FILE, "w") as f:
        f.write(video_id)


# ─────────────────────────────────────────────
# Traitement d'une vidéo
# ─────────────────────────────────────────────

def process_video(video_id, video_title):
    """Pipeline complet : transcription → carousel → Slack + JSON."""
    print(f"\n{'='*60}")
    print(f"Traitement: {video_title} ({video_id})")
    print(f"{'='*60}")

    # 1. Transcription
    print("1/3 — Récupération de la transcription...")
    transcript = get_transcript(video_id)
    if not transcript:
        print("  ✗ Impossible d'obtenir la transcription.")
        return False
    print(f"  ✓ Transcription récupérée ({len(transcript):,} caractères)")

    # 2. Génération du carousel
    print("2/3 — Génération du carousel avec Claude...")
    carousel = generate_carousel(video_title, transcript)
    if not carousel:
        print("  ✗ Impossible de générer le carousel.")
        return False
    nb_slides = len(carousel.get("slides", []))
    print(f"  ✓ Carousel généré ({nb_slides} slides)")

    # 3. Sauvegarde JSON
    os.makedirs(CAROUSELS_DIR, exist_ok=True)
    output_path = f"{CAROUSELS_DIR}/{video_id}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"video_id": video_id, "video_title": video_title, "carousel": carousel},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"  ✓ Carousel sauvegardé → {output_path}")

    # 4. Envoi Slack
    print("3/3 — Envoi sur Slack...")
    slack_msg = format_carousel_for_slack(video_title, video_id, carousel)
    send_to_slack(slack_msg)

    return True


# ─────────────────────────────────────────────
# Point d'entrée
# ─────────────────────────────────────────────

def main():
    # Mode manuel: python youtube_carousel.py VIDEO_ID "Titre optionnel"
    if len(sys.argv) >= 2:
        video_id = sys.argv[1]
        video_title = sys.argv[2] if len(sys.argv) >= 3 else f"Vidéo {video_id}"
        process_video(video_id, video_title)
        return

    # Mode automatique: vérification des nouvelles vidéos
    if not YOUTUBE_CHANNEL_ID:
        print("YOUTUBE_CHANNEL_ID non défini. Spécifiez un VIDEO_ID en argument.")
        sys.exit(1)

    print("Vérification des nouvelles vidéos sur la chaîne...")
    videos = get_latest_videos(YOUTUBE_CHANNEL_ID)

    if not videos:
        print("Aucune vidéo trouvée.")
        return

    last_processed = load_last_processed_video()
    print(f"Dernière vidéo traitée : {last_processed or 'aucune'}")
    print(f"Vidéo la plus récente  : {videos[0]['id']} — {videos[0]['title']}")

    # Nouvelles vidéos = toutes celles avant de croiser la dernière traitée
    new_videos = []
    for video in videos:
        if video["id"] == last_processed:
            break
        new_videos.append(video)

    if not new_videos:
        print("Aucune nouvelle vidéo à traiter.")
        return

    print(f"\n{len(new_videos)} nouvelle(s) vidéo(s) à traiter.")

    for video in reversed(new_videos):  # Du plus ancien au plus récent
        success = process_video(video["id"], video["title"])
        if success:
            save_last_processed_video(video["id"])

    print("\nTraitement terminé.")


if __name__ == "__main__":
    main()
