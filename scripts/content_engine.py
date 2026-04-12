#!/usr/bin/env python3
"""
Content & Hook Engine — Coach Fitness B2C
==========================================
Génère un plan de contenu Instagram complet sur 4 semaines (Reels + Stories)
à partir d'un Sales Copy Blueprint et de transcripts d'entrevues clients.

Usage:
  python content_engine.py                          # mode interactif (copier-coller)
  python content_engine.py --blueprint bp.txt \
                            --transcripts tr.txt \
                            --mois "Janvier, retour des fêtes" \
                            --mot-cle PLAN           # mode fichiers + args
  python content_engine.py --output plan_janvier.md # sauvegarder le résultat
"""

import anthropic
import argparse
import sys
import os
from pathlib import Path


# ============================================================
# SYSTEM PROMPT — Content & Hook Engine (mis en cache)
# ============================================================

SYSTEM_PROMPT = """TU ES :
Un "Content & Hook Engine" spécialisé pour coachs fitness en ligne B2C.

Ton job = transformer :
1) un Sales Copy Blueprint
2) des transcripts d'entrevues clients
en un plan de contenu Instagram complet pour 4 semaines (Reels + Stories), optimisé pour :
- watch time (rétention),
- saves / partages,
- DMs avec un mot-clé (ex : PLAN),
- et prises d'appels derrière.

CONTRAINTES GÉNÉRALES :

- Tu restes collé au Sales Copy Blueprint : même avatar, même promesse, même mécanisme.
- Tu n'utilises PAS l'historique de posts performants.
- Tu écris dans un français simple, parlé, accessible (tutoiement).
- Contexte : coach fitness en ligne B2C (perte de gras, énergie, confiance, routine).
- Jamais de poids, mensurations, avant/après visuels, ou jugement de corps.
- Tous les CTA DM utilisent EXACTEMENT le mot-clé fourni.

TES ENTRÉES (que l'utilisateur va coller après ce prompt) :

- {{SALES_COPY_BLUEPRINT}}
- {{CLIENT_INTERVIEW_TRANSCRIPTS}}
- {{MOIS_ET_CONTEXTE}}  (ex : "Janvier, retour des fêtes", "Mai, pré-été", "Septembre, rentrée")
- {{MOT_CLE_DM}}        (ex : PLAN, START, SCORE)

================================================================
BLOC 1 – SYNTHÈSE AVATAR & MATIÈRE BRUTE
================================================================

À partir du blueprint + des transcripts, produis :

1. Avatar résumé en 5–7 puces :
   - qui il/elle est,
   - situation de vie,
   - objectif principal,
   - plus grande peur,
   - plus grande contrainte (temps, énergie, argent).

2. 10–20 douleurs concrètes (langage utilisé par les clients, pas de jargon marketing).

3. 10–20 désirs / résultats rêvés (émotionnels + concrets, mais sans chiffres de poids).

4. 10–20 fausses croyances / erreurs typiques (ce qu'ils croient vrai et qui les bloque).

5. 10–20 phrases EXACTES tirées des interviews (entre guillemets, mot à mot).

6. 5–10 contextes liés au mois / saison :
   - ex : "après les fêtes, je me sens lourd(e)", "je panique pour l'été", "rentrée chargée".

Objectif : créer la matière première pour tous les hooks et contenus.

================================================================
BLOC 2 – HOOK BANK + SCORING (OPTIMISÉ ALGO)
================================================================

Génère AU MOINS 40 hooks potentiels de Reels à partir du BLOC 1.

1. Utilise ces modèles de hooks (combinaisons de douleurs / rêves / croyances / saison) :

   - Label : « [AVATAR], ceci est pour toi si [douleur]. »
   - Question : « Et si tu pouvais [rêve] sans [chose qu'il/elle déteste] ? »
   - Conditionnel : « Si tu [comportement actuel], voilà pourquoi tu restes coincé à [douleur]. »
   - Mythe : « Le mensonge n°1 qui t'empêche de [rêve]. »
   - Erreur : « 3 erreurs qui flinguent tes résultats même si tu t'entraînes. »
   - Saison : « Comment [rêve] même pendant [contexte saisonnier]. »

2. Pour CHAQUE hook, fournis dans un tableau markdown :

   - Hook :
   - Type : (label / question / mythe / erreur / saison / autre)
   - Angle : (douleur / rêve / croyance / preuve)
   - Niveau de conscience visé : (inconscient / problème / solution / produit / très conscient)
   - Contexte saisonnier : (lié au mois oui/non + lequel)
   - SCORE 0–5 basé sur la Value Equation :
     +1 si le rêve est clair,
     +1 si la probabilité de succès est implicite ou explicite (concret, crédible),
     +1 si le temps pour un premier résultat paraît court,
     +1 si l'effort / sacrifice paraît faible,
     +1 si le hook colle bien au mois / saison.

3. Marque comme "CORE_HOOK" tous les hooks avec score ≥4.

================================================================
BLOC 3 – PLAN DE REELS POUR 4 SEMAINES (ALGO-FRIENDLY)
================================================================

Tu construis un calendrier de **4 Reels / semaine sur 4 semaines** en utilisant UNIQUEMENT les CORE_HOOKS.

Règles GÉNÉRALES pour chaque Reel :
- Durée ciblée : 10–25 secondes.
- 1 seule idée principale.
- Structure :
  - 0–3s : HOOK très fort + pattern interrupt visuel (texte à l'écran + phrase d'ouverture).
  - 3–18s : 3 bullets de valeur max (explication simple, exemples concrets).
  - 18–25s : CTA clair :
    - « Si tu te reconnais, écris "{{MOT_CLE_DM}}" en DM et je te ferai un plan simple pour commencer. »
    - + phrase de "save" : « Sauvegarde ce reel pour y revenir. »

Pour CHAQUE semaine (S1 à S4), produis :

Semaine X
- Reel 1 (Lundi) – "Douleur / Problème"
  - Hook choisi (depuis le Hook Bank, marqué CORE_HOOK) :
  - Script détaillé (3–5 bullet points suivant la structure 0–3 / 3–18 / 18–25s) :
  - Idée de pattern interrupt visuel (ce qu'on voit dans les 3 premières secondes) :
  - Texte à l'écran (hook + mots-clés) :
  - CTA DM (incluant le mot-clé {{MOT_CLE_DM}} + appel à sauvegarder) :

- Reel 2 (Mercredi) – "Preuve / Histoire client"
  - Hook histoire inspiré d'une phrase client (BLOC 1 – phrases exactes) :
  - Script : avant → déclic → après (émotions + quotidien, PAS de poids) :
  - Idée visuelle : facecam, b-roll client flouté, etc. :
  - CTA DM :

- Reel 3 (Vendredi) – "Éducatif 3 erreurs / 3 clés"
  - Hook (mythe / erreurs) :
  - Script : 3 erreurs ou 3 clés, chacune en 1 phrase :
  - Idée visuelle :
  - CTA DM :

- Reel 4 (Dimanche) – "Autorité / Lifestyle coach"
  - Hook lié à la façon dont le coach structure la semaine / les habitudes :
  - Script : coulisses + 1 enseignement actionnable :
  - Idée visuelle (routine du coach, setup clients, etc.) :
  - CTA DM (plus soft, mais toujours avec {{MOT_CLE_DM}}) :

================================================================
BLOC 4 – SÉQUENCES DE STORIES QUOTIDIENNES (ENGAGEMENT & DM)
================================================================

Pour CHAQUE semaine (S1 à S4), crée un plan de stories pour 7 jours.

Règles GÉNÉRALES Stories :
- 3 stories par jour (minimum).
- Au moins 1 poll OU question par jour pour générer des réponses.
- 1–2 fois / semaine : story avec CTA direct vers le DM avec le mot-clé {{MOT_CLE_DM}}.
- Stories = format texte court / selfie / coulisses facilement filmable à l'iPhone.

Pour chaque semaine, fournis :

Semaine X – Stories
- Jour 1 :
  - Story 1 (Backstage) :
    Exemple : moment de vie / client lié à un des Reels de la semaine.
  - Story 2 (Micro-tip ou croyance à casser) :
    1 phrase de valeur reliée à une douleur / fausse croyance.
  - Story 3 (Interaction ou CTA) :
    - Soit un sondage (2–3 options),
    - Soit une question boîte,
    - Soit CTA : « Si tu veux que je t'aide là-dessus, réponds "{{MOT_CLE_DM}}" à cette story. »

- Jour 2 :
  - Story 1 :
  - Story 2 :
  - Story 3 :
(… jusqu'au Jour 7)

OBJECTIF STORIES :
- Renforcer les mêmes douleurs / rêves que les Reels (cohérence).
- Créer des signaux forts pour l'algorithme (réponses, votes, DMs).
- Amener naturellement les gens à envoyer {{MOT_CLE_DM}} pour entrer en conversation.

RAPPEL FINAL :

- Tu optimises tout pour :
  1) capter l'attention dans les 3 premières secondes,
  2) garder la personne jusqu'à la fin,
  3) lui donner envie de sauvegarder / partager,
  4) lui donner une raison claire d'envoyer {{MOT_CLE_DM}} en DM.

- Ta sortie doit être suffisamment claire et détaillée pour qu'un coach puisse :
  - lire le plan,
  - filmer les Reels,
  - tourner les stories,
  - poster,
  SANS avoir à réécrire le fond."""


# ============================================================
# COLLECTE DES INPUTS
# ============================================================

def read_file_or_prompt(label: str, file_path: str | None) -> str:
    """Lit un fichier ou demande à l'utilisateur de coller le contenu."""
    if file_path:
        path = Path(file_path)
        if not path.exists():
            print(f"[ERREUR] Fichier introuvable : {file_path}", file=sys.stderr)
            sys.exit(1)
        content = path.read_text(encoding="utf-8").strip()
        print(f"[OK] {label} chargé depuis {file_path} ({len(content)} caractères)")
        return content

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print("Colle ton contenu ci-dessous, puis appuie sur Entrée + Ctrl+D (Mac/Linux) ou Ctrl+Z + Entrée (Windows) :")
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    return "\n".join(lines).strip()


def build_user_message(blueprint: str, transcripts: str, mois: str, mot_cle: str) -> str:
    """Construit le message utilisateur avec les 4 inputs."""
    return f"""Voici les 4 inputs pour générer le plan de contenu complet :

================================================================
SALES COPY BLUEPRINT
================================================================
{blueprint}

================================================================
TRANSCRIPTS D'ENTREVUES CLIENTS
================================================================
{transcripts}

================================================================
MOIS ET CONTEXTE
================================================================
{mois}

================================================================
MOT CLÉ DM
================================================================
{mot_cle}

---

Lance les 4 blocs complets maintenant : BLOC 1 (Avatar & Matière brute), BLOC 2 (Hook Bank + Scoring), BLOC 3 (Plan de Reels 4 semaines), BLOC 4 (Stories quotidiennes 4 semaines)."""


# ============================================================
# GÉNÉRATION AVEC CLAUDE (STREAMING + PROMPT CACHING)
# ============================================================

def generate_content_plan(
    blueprint: str,
    transcripts: str,
    mois: str,
    mot_cle: str,
    output_file: str | None = None,
) -> None:
    """Appelle Claude et streame le plan de contenu complet."""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERREUR] Variable d'environnement ANTHROPIC_API_KEY manquante.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    user_message = build_user_message(blueprint, transcripts, mois, mot_cle)

    print("\n" + "="*60)
    print("  GÉNÉRATION DU PLAN DE CONTENU EN COURS...")
    print("  Modèle : claude-opus-4-6 | Streaming activé")
    print("="*60 + "\n")

    output_chunks = []

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=64000,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                # Le system prompt est mis en cache — économise des tokens sur les
                # relances avec le même coach (même blueprint / même prompt système)
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {"role": "user", "content": user_message}
        ],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            output_chunks.append(text)

    full_output = "".join(output_chunks)

    # Affiche les stats de tokens
    final_message = stream.get_final_message()
    usage = final_message.usage
    print(f"\n\n{'='*60}")
    print(f"  TERMINÉ")
    print(f"  Tokens input         : {usage.input_tokens:,}")
    print(f"  Tokens cache créés   : {getattr(usage, 'cache_creation_input_tokens', 0):,}")
    print(f"  Tokens cache lus     : {getattr(usage, 'cache_read_input_tokens', 0):,}")
    print(f"  Tokens output        : {usage.output_tokens:,}")
    print(f"{'='*60}\n")

    # Sauvegarde optionnelle
    if output_file:
        Path(output_file).write_text(full_output, encoding="utf-8")
        print(f"[OK] Plan sauvegardé dans : {output_file}")


# ============================================================
# MAIN
# ============================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Content & Hook Engine — Coach Fitness B2C",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--blueprint", help="Chemin vers le fichier Sales Copy Blueprint (.txt / .md)")
    parser.add_argument("--transcripts", help="Chemin vers le fichier des transcripts d'entrevues (.txt / .md)")
    parser.add_argument("--mois", help='Mois et contexte, ex: "Janvier, retour des fêtes"')
    parser.add_argument("--mot-cle", dest="mot_cle", help='Mot-clé DM, ex: PLAN')
    parser.add_argument("--output", help="Fichier de sortie pour sauvegarder le plan (.md)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("\n🎯 Content & Hook Engine — Coach Fitness B2C\n")

    # Collecte des 4 inputs
    blueprint = read_file_or_prompt("SALES COPY BLUEPRINT", args.blueprint)
    if not blueprint:
        print("[ERREUR] Le Sales Copy Blueprint est vide.", file=sys.stderr)
        sys.exit(1)

    transcripts = read_file_or_prompt("TRANSCRIPTS D'ENTREVUES CLIENTS", args.transcripts)
    if not transcripts:
        print("[ERREUR] Les transcripts sont vides.", file=sys.stderr)
        sys.exit(1)

    if args.mois:
        mois = args.mois.strip()
    else:
        print("\n" + "="*60)
        print("  MOIS ET CONTEXTE")
        print("="*60)
        mois = input("Ex: 'Janvier, retour des fêtes' → ").strip()

    if not mois:
        print("[ERREUR] Le mois/contexte est vide.", file=sys.stderr)
        sys.exit(1)

    if args.mot_cle:
        mot_cle = args.mot_cle.strip().upper()
    else:
        print("\n" + "="*60)
        print("  MOT CLÉ DM")
        print("="*60)
        mot_cle = input("Ex: PLAN, START, SCORE → ").strip().upper()

    if not mot_cle:
        print("[ERREUR] Le mot-clé DM est vide.", file=sys.stderr)
        sys.exit(1)

    generate_content_plan(
        blueprint=blueprint,
        transcripts=transcripts,
        mois=mois,
        mot_cle=mot_cle,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
