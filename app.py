import os
import json
import re
import requests
import streamlit as st

# ─── Config ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Générateur de Carousel",
    page_icon="🎠",
    layout="wide",
)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

# ─── Style ───────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .slide-card {
        background: #1e1e2e;
        border: 1px solid #313244;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .slide-number {
        font-size: 12px;
        color: #6c7086;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 6px;
    }
    .slide-title {
        font-size: 20px;
        font-weight: 700;
        color: #cdd6f4;
        margin-bottom: 10px;
    }
    .slide-content {
        font-size: 15px;
        color: #bac2de;
        line-height: 1.6;
        margin-bottom: 12px;
    }
    .slide-visual {
        font-size: 13px;
        color: #6c7086;
        font-style: italic;
    }
    .hashtag-pill {
        display: inline-block;
        background: #313244;
        color: #89b4fa;
        border-radius: 20px;
        padding: 4px 12px;
        margin: 4px 4px 4px 0;
        font-size: 13px;
    }
    .section-header {
        font-size: 13px;
        font-weight: 600;
        color: #6c7086;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 24px 0 12px 0;
    }
    div[data-testid="stTextArea"] textarea {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ─── Génération Claude ────────────────────────────────────────────────────────

def generate_carousel(title: str, transcript: str, api_key: str) -> dict:
    prompt = f"""Tu es un expert en création de contenu viral pour LinkedIn et Instagram.

Voici la transcription d'une vidéo YouTube intitulée: "{title}"

TRANSCRIPTION:
{transcript[:8000]}

Ta mission: créer un carousel de 7 à 10 slides, engageant et percutant, basé sur le contenu réel de cette vidéo.

RÈGLES:
1. Slide 1 — Hook irrésistible qui donne envie de continuer
2. Slides 2 à N-1 — Les insights, conseils ou points clés les plus précieux
3. Dernière slide — Call-to-action clair (s'abonner, commenter, partager, etc.)
4. Chaque slide doit tenir en 3-5 lignes max (texte court, impactant)
5. Utilise des emojis pertinents mais sobrement
6. Extrais uniquement la vraie valeur de la vidéo, pas de rembourrage

RÉPONDS UNIQUEMENT avec un objet JSON valide (aucun texte avant ou après):
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

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
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

    if resp.status_code != 200:
        raise RuntimeError(f"Erreur API Anthropic ({resp.status_code}): {resp.text}")

    content = resp.json()["content"][0]["text"].strip()
    match = re.search(r"\{[\s\S]*\}", content)
    if not match:
        raise ValueError(f"Réponse inattendue de Claude:\n{content[:300]}")

    return json.loads(match.group())


def send_to_slack(carousel: dict, title: str, webhook_url: str):
    slides_text = ""
    for s in carousel["slides"]:
        slides_text += f"{s.get('emoji','▶️')} *Slide {s['numero']}: {s['titre']}*\n{s['contenu']}\n\n"

    hashtags = " ".join(carousel.get("hashtags", []))

    msg = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": "🎠 Nouveau Carousel Généré !", "emoji": True}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{carousel['titre_carousel']}*\n{carousel.get('description_post','')}"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": slides_text}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Hashtags:* {hashtags}"}},
        ]
    }

    r = requests.post(webhook_url, json=msg, timeout=30)
    return r.status_code == 200


# ─── Interface ───────────────────────────────────────────────────────────────

st.title("🎠 Générateur de Carousel YouTube")
st.caption("Collez votre transcript → obtenez un carousel LinkedIn/Instagram prêt à publier")

# Sidebar – paramètres
with st.sidebar:
    st.header("⚙️ Paramètres")

    api_key = st.text_input(
        "Clé API Anthropic",
        value=ANTHROPIC_API_KEY,
        type="password",
        help="Votre clé API Claude (commence par sk-ant-...)",
    )

    slack_url = st.text_input(
        "Slack Webhook URL (optionnel)",
        value=SLACK_WEBHOOK_URL,
        type="password",
        help="Pour envoyer le carousel directement sur Slack",
    )

    st.divider()
    st.markdown("**Comment obtenir le transcript YouTube:**")
    st.markdown("""
1. Ouvrez votre vidéo YouTube
2. Cliquez sur `···` sous la vidéo
3. Sélectionnez **Afficher la transcription**
4. Copiez tout le texte
5. Collez-le ci-contre
""")

# Formulaire principal
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.markdown('<div class="section-header">Votre contenu</div>', unsafe_allow_html=True)

    video_title = st.text_input(
        "Titre de la vidéo",
        placeholder="Ex: Comment doubler ses revenus en 6 mois",
    )

    transcript = st.text_area(
        "Transcript",
        placeholder="Collez ici la transcription de votre vidéo YouTube...",
        height=400,
    )

    generate_btn = st.button(
        "✨ Générer le Carousel",
        type="primary",
        use_container_width=True,
        disabled=not (video_title and transcript and api_key),
    )

    if not api_key:
        st.warning("Entrez votre clé API Anthropic dans la barre latérale.")
    elif not video_title or not transcript:
        st.info("Remplissez le titre et le transcript pour commencer.")

# Zone de résultat
with col2:
    st.markdown('<div class="section-header">Votre carousel</div>', unsafe_allow_html=True)

    if generate_btn:
        with st.spinner("Claude génère votre carousel..."):
            try:
                carousel = generate_carousel(video_title, transcript, api_key)
                st.session_state["carousel"] = carousel
                st.session_state["carousel_title"] = video_title
                st.success(f"✓ {len(carousel['slides'])} slides générées !")
            except Exception as e:
                st.error(f"Erreur: {e}")

    if "carousel" in st.session_state:
        carousel = st.session_state["carousel"]

        # Description du post
        st.markdown("**📝 Description du post**")
        desc = carousel.get("description_post", "")
        st.text_area("", value=desc, height=100, key="desc_copy", label_visibility="collapsed")

        # Hashtags
        hashtags_html = "".join(
            f'<span class="hashtag-pill">{h}</span>'
            for h in carousel.get("hashtags", [])
        )
        st.markdown(f'<div style="margin:8px 0 20px 0">{hashtags_html}</div>', unsafe_allow_html=True)

        st.divider()

        # Slides
        for slide in carousel["slides"]:
            emoji = slide.get("emoji", "▶️")
            st.markdown(f"""
<div class="slide-card">
  <div class="slide-number">Slide {slide['numero']}</div>
  <div class="slide-title">{emoji} {slide['titre']}</div>
  <div class="slide-content">{slide['contenu']}</div>
  <div class="slide-visual">🖼 {slide['visuel_suggere']}</div>
</div>
""", unsafe_allow_html=True)

        st.divider()

        # Actions
        action_col1, action_col2 = st.columns(2)

        with action_col1:
            json_bytes = json.dumps(carousel, ensure_ascii=False, indent=2).encode("utf-8")
            safe_name = re.sub(r"[^\w\-]", "_", st.session_state.get("carousel_title", "carousel"))
            st.download_button(
                "⬇️ Télécharger JSON",
                data=json_bytes,
                file_name=f"{safe_name}.json",
                mime="application/json",
                use_container_width=True,
            )

        with action_col2:
            if slack_url:
                if st.button("📤 Envoyer sur Slack", use_container_width=True):
                    with st.spinner("Envoi..."):
                        ok = send_to_slack(carousel, st.session_state.get("carousel_title", ""), slack_url)
                        if ok:
                            st.success("Envoyé sur Slack !")
                        else:
                            st.error("Échec de l'envoi Slack.")
            else:
                st.button("📤 Envoyer sur Slack", disabled=True, use_container_width=True, help="Configurez le Slack Webhook dans la barre latérale")
