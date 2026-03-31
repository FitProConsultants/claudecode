#!/usr/bin/env python3
"""
YouTube Carousel Creator
Génère un carousel LinkedIn/Instagram à partir d'un fichier transcript.

Usage:
  python youtube_carousel.py transcripts/ma-video.txt
"""

import os
import json
import sys
import re
import requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")

CAROUSELS_DIR = "data/carousels"


def generate_carousel(video_title, transcript):
    """Utilise Claude pour transformer la transcription en carousel."""

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
        sys.exit(1)

    content = response.json()["content"][0]["text"].strip()

    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        print(f"Impossible d'extraire le JSON de la réponse:\n{content[:300]}")
        sys.exit(1)

    return json.loads(json_match.group())


def format_carousel_for_slack(transcript_file, carousel):
    """Formate le carousel pour Slack."""

    slides_text = ""
    for slide in carousel["slides"]:
        emoji = slide.get("emoji", "▶️")
        slides_text += f"{emoji} *Slide {slide['numero']}: {slide['titre']}*\n"
        slides_text += f"{slide['contenu']}\n"
        slides_text += f"_Visuel: {slide['visuel_suggere']}_\n\n"

    hashtags = " ".join(carousel.get("hashtags", []))

    return {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🎠 Nouveau Carousel Généré !", "emoji": True},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Fichier source:*\n`{transcript_file}`"},
                    {"type": "mrkdwn", "text": f"*Titre du carousel:*\n{carousel['titre_carousel']}"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*📝 Description du post:*\n{carousel.get('description_post', '')}"},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*📊 Slides:*\n\n{slides_text}"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*#️⃣ Hashtags:*\n{hashtags}"},
            },
        ]
    }


def send_to_slack(message):
    if not SLACK_WEBHOOK_URL:
        print("(SLACK_WEBHOOK_URL non défini — pas d'envoi Slack)")
        return
    resp = requests.post(SLACK_WEBHOOK_URL, json=message, timeout=30)
    if resp.status_code == 200:
        print("✓ Carousel envoyé sur Slack")
    else:
        print(f"Erreur Slack: {resp.status_code} — {resp.text}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python youtube_carousel.py <fichier_transcript.txt>")
        sys.exit(1)

    transcript_path = sys.argv[1]

    if not os.path.exists(transcript_path):
        print(f"Fichier introuvable: {transcript_path}")
        sys.exit(1)

    with open(transcript_path, "r", encoding="utf-8") as f:
        transcript = f.read().strip()

    if not transcript:
        print("Le fichier transcript est vide.")
        sys.exit(1)

    # Le nom de fichier (sans extension) devient le titre
    video_title = os.path.splitext(os.path.basename(transcript_path))[0].replace("-", " ").replace("_", " ").title()

    print(f"Fichier : {transcript_path}")
    print(f"Titre   : {video_title}")
    print(f"Taille  : {len(transcript):,} caractères")
    print("\nGénération du carousel avec Claude...")

    carousel = generate_carousel(video_title, transcript)
    nb_slides = len(carousel.get("slides", []))
    print(f"✓ Carousel généré ({nb_slides} slides)")

    # Sauvegarde JSON
    os.makedirs(CAROUSELS_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(transcript_path))[0]
    output_path = f"{CAROUSELS_DIR}/{base_name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"source": transcript_path, "titre": video_title, "carousel": carousel},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"✓ Carousel sauvegardé → {output_path}")

    # Envoi Slack
    slack_msg = format_carousel_for_slack(transcript_path, carousel)
    send_to_slack(slack_msg)


if __name__ == "__main__":
    main()
