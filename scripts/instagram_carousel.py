#!/usr/bin/env python3
"""
Instagram Carousel Automation
Récupère les posts publiés hier sur Instagram et crée automatiquement un carousel récapitulatif.

Prérequis :
- Un compte Instagram Business ou Creator
- Une application Facebook avec l'API Instagram Graph activée
- Un token d'accès long-term (60 jours) ou un system user token (sans expiration)

Variables d'environnement requises :
- INSTAGRAM_ACCESS_TOKEN  : token d'accès Instagram Graph API
- INSTAGRAM_USER_ID       : ID numérique du compte Instagram (facultatif, déduit sinon)
- ANTHROPIC_API_KEY       : clé API Claude pour générer la légende du carousel (facultatif)
- CAROUSEL_LOOKBACK_DAYS  : nombre de jours à regarder en arrière (défaut : 1)
- CAROUSEL_MAX_ITEMS      : nombre max d'images dans le carousel (défaut : 10, max Instagram : 10)
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Optional

# ─────────────────────────── Configuration ────────────────────────────────────

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IG_USER_ID = os.environ.get("INSTAGRAM_USER_ID", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LOOKBACK_DAYS = int(os.environ.get("CAROUSEL_LOOKBACK_DAYS", "1"))
MAX_ITEMS = min(int(os.environ.get("CAROUSEL_MAX_ITEMS", "10")), 10)  # Instagram max = 10

GRAPH_BASE = "https://graph.instagram.com/v20.0"

# ─────────────────────────── API helpers ──────────────────────────────────────

def _get(path: str, params: dict) -> dict:
    """HTTP GET vers l'API Instagram Graph."""
    params["access_token"] = ACCESS_TOKEN
    url = f"{GRAPH_BASE}{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def _post(path: str, data: dict) -> dict:
    """HTTP POST vers l'API Instagram Graph."""
    data["access_token"] = ACCESS_TOKEN
    url = f"{GRAPH_BASE}{path}"
    payload = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_ig_user_id() -> str:
    """Récupère l'ID utilisateur Instagram depuis le token si non fourni."""
    if IG_USER_ID:
        return IG_USER_ID
    data = _get("/me", {"fields": "id,username"})
    print(f"Compte Instagram : @{data['username']} (id={data['id']})")
    return data["id"]


# ─────────────────────────── Récupération des posts ───────────────────────────

def fetch_recent_media(user_id: str, since: datetime) -> list[dict]:
    """
    Retourne les médias publiés après `since`.
    On récupère les 50 derniers posts et on filtre côté client.
    """
    fields = "id,caption,media_type,media_url,timestamp,thumbnail_url"
    data = _get(f"/{user_id}/media", {"fields": fields, "limit": 50})
    media = data.get("data", [])

    # Filtrer par date
    cutoff = since.astimezone(timezone.utc)
    recent = []
    for item in media:
        ts = datetime.fromisoformat(item["timestamp"].replace("Z", "+00:00"))
        if ts >= cutoff:
            recent.append(item)

    # Ne garder que les types supportés dans un carousel
    supported = {"IMAGE", "VIDEO"}
    recent = [m for m in recent if m.get("media_type") in supported]

    # Limiter au max Instagram (2-10 items)
    return recent[:MAX_ITEMS]


# ─────────────────────────── Génération de légende ────────────────────────────

def generate_caption(media_items: list[dict]) -> str:
    """Génère une légende pour le carousel via Claude, ou utilise une légende par défaut."""
    today = datetime.now().strftime("%d %B %Y")
    default_caption = f"Récap du {today} 📸\n\n" + "\n".join(
        f"• {m.get('caption', '').splitlines()[0]}" if m.get("caption") else ""
        for m in media_items
    ).strip()

    if not ANTHROPIC_API_KEY:
        return default_caption

    captions = [
        m.get("caption", "").strip()
        for m in media_items
        if m.get("caption", "").strip()
    ]
    if not captions:
        return default_caption

    prompt = (
        f"Voici les légendes de {len(media_items)} posts Instagram publiés aujourd'hui :\n\n"
        + "\n\n---\n\n".join(captions)
        + "\n\nRédige une courte légende percutante (max 220 caractères) pour un carousel "
        "récapitulatif Instagram. Inclus 3-5 emojis pertinents et 3-5 hashtags populaires "
        "en fitness/santé. Réponds uniquement avec la légende, sans guillemets."
    )

    body = json.dumps({
        "model": "claude-opus-4-6",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["content"][0]["text"].strip()


# ─────────────────────────── Création du carousel ─────────────────────────────

def create_carousel_item(user_id: str, media: dict) -> str:
    """Crée un item de carousel et retourne son container ID."""
    payload = {"is_carousel_item": "true"}

    if media["media_type"] == "VIDEO":
        payload["media_type"] = "REELS"
        payload["video_url"] = media["media_url"]
    else:
        payload["image_url"] = media["media_url"]

    result = _post(f"/{user_id}/media", payload)
    return result["id"]


def wait_for_container(user_id: str, container_id: str, max_wait: int = 60) -> None:
    """Attend que le container Instagram soit prêt (status=FINISHED)."""
    for _ in range(max_wait // 5):
        status = _get(f"/{container_id}", {"fields": "status_code"})
        code = status.get("status_code", "")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Erreur de traitement du container {container_id}")
        time.sleep(5)
    raise TimeoutError(f"Container {container_id} non prêt après {max_wait}s")


def create_carousel(user_id: str, item_ids: list[str], caption: str) -> str:
    """Crée le container carousel et retourne son ID."""
    payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(item_ids),
        "caption": caption,
    }
    result = _post(f"/{user_id}/media", payload)
    return result["id"]


def publish_carousel(user_id: str, carousel_id: str) -> str:
    """Publie le carousel et retourne l'ID du post final."""
    result = _post(f"/{user_id}/media_publish", {"creation_id": carousel_id})
    return result["id"]


# ─────────────────────────── Point d'entrée ───────────────────────────────────

def main():
    print("=== Instagram Carousel Automation ===")

    user_id = get_ig_user_id()

    # Fenêtre temporelle : hier 00:00 → aujourd'hui 00:00
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=LOOKBACK_DAYS)
    print(f"Recherche de posts depuis {since.strftime('%Y-%m-%d %H:%M UTC')}...")

    media_items = fetch_recent_media(user_id, since)
    print(f"Posts trouvés : {len(media_items)}")

    if len(media_items) < 2:
        print("Pas assez de posts pour créer un carousel (minimum 2). Arrêt.")
        return

    # Générer la légende
    print("Génération de la légende...")
    caption = generate_caption(media_items)
    print(f"Légende : {caption[:80]}...")

    # Créer les items du carousel
    print("Création des items du carousel...")
    item_ids = []
    for i, media in enumerate(media_items, 1):
        print(f"  Item {i}/{len(media_items)} (type={media['media_type']}, id={media['id']})")
        container_id = create_carousel_item(user_id, media)
        wait_for_container(user_id, container_id)
        item_ids.append(container_id)

    # Créer et publier le carousel
    print("Création du container carousel...")
    carousel_id = create_carousel(user_id, item_ids, caption)

    print("Publication du carousel...")
    post_id = publish_carousel(user_id, carousel_id)

    print(f"\n✓ Carousel publié avec succès ! Post ID : {post_id}")
    print(f"  URL : https://www.instagram.com/p/{post_id}/")


if __name__ == "__main__":
    main()
