#!/usr/bin/env python3
"""
Script one-time pour obtenir un refresh token OAuth Google.
À exécuter UNE SEULE FOIS sur ton ordinateur.

Usage:
  pip install google-auth-oauthlib
  python scripts/get_oauth_token.py
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# Colle ici le contenu de ton fichier client_secret JSON téléchargé
# (le fichier commence par {"installed": ...} ou {"web": ...})
CLIENT_CONFIG = {
    "installed": {
        "client_id": "COLLE_TON_CLIENT_ID_ICI",
        "client_secret": "COLLE_TON_CLIENT_SECRET_ICI",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

def main():
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n✅ Authentification réussie!\n")
    print("=== COPIE CES VALEURS DANS GITHUB SECRETS ===\n")
    print(f"GOOGLE_OAUTH_CLIENT_ID:\n  {CLIENT_CONFIG['installed']['client_id']}\n")
    print(f"GOOGLE_OAUTH_CLIENT_SECRET:\n  {CLIENT_CONFIG['installed']['client_secret']}\n")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN:\n  {creds.refresh_token}\n")
    print("=============================================")

if __name__ == "__main__":
    main()
