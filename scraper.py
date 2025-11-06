import requests
import time
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import cloudscraper



DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://fbref.com/"
}

BASE = "https://fbref.com"

RATE_SEC = 1.5  # délai entre requêtes

# session réutilisables 
REQUESTS_SESSION = requests.Session()
REQUESTS_SESSION.headers.update(DEFAULT_HEADERS)

CLOUDSCRAPER_SESSION = cloudscraper.create_scraper()
CLOUDSCRAPER_SESSION.headers.update(DEFAULT_HEADERS)

def fetch_page(url, max_retries=3, timeout=15, use_cloudscraper_on_block=True):
    """
    Télécharge la page et renvoie (status_code, html or None).
    Essaie first requests, puis cloudscraper en fallback si bloqué.
    """
    last_status = None

    # 1) Tentative avec requests
    for attempt in range(max_retries):
        try:
            r = REQUESTS_SESSION.get(url, timeout=timeout, allow_redirects=True)
        except requests.RequestException as e:
            last_status = f"requests exception: {e}"
            time.sleep(2 ** attempt)
            continue

        last_status = r.status_code
        if r.status_code == 200:
            time.sleep(RATE_SEC)  # respecter délai global
            return r.status_code, r.text 

        # si bloqué / rate-limited -> backoff et retenter
        if r.status_code in (403, 429):
            time.sleep(2 ** attempt)
            continue

        # autres codes : on quitte en renvoyant le code + body (ou None)
        try:
            text = r.text if r.status_code < 500 else None
        except Exception:
            text = None
        return r.status_code, text
    
    # 2) Fallback cloudscraper si activé
    if use_cloudscraper_on_block:
        for attempt in range(max_retries):
            try:
                r = CLOUDSCRAPER_SESSION.get(url, timeout=timeout, allow_redirects=True)
            except Exception as e:
                last_status = f"cloudscraper exception: {e}"
                time.sleep(2 ** attempt)
                continue

            last_status = getattr(r, "status_code", None)
            if getattr(r, "status_code", None) == 200:
                time.sleep(RATE_SEC)
                return r.status_code, r.text

            time.sleep(2 ** attempt)

    # tout a échoué -> renvoyer code/erreur
    return (last_status or 0), None

def fbref_search(name):
    """
    Utilise la page de recherche FBref et renvoie les listes de résultats.
    Retour : dict { 'players': [(text, url), ...], 'teams': [...], 'comps': [...] }
    """
    q = quote_plus(name)
    url = f"{BASE}/search/search.fcgi?search={q}"
    print(f"[search] requête : {url}")
    status, html = fetch_page(url, max_retries=3, timeout=15, use_cloudscraper_on_block=True)
    if status != 200 or not html:
        # message utile pour debug
        raise RuntimeError(f"Erreur HTTP {status} lors de la recherche ou page vide.")
    # Respect du délai global
    time.sleep(RATE_SEC)
    soup = BeautifulSoup(html, "lxml")

    results = {"players": [], "teams": [], "comps": []}
    # FBref montre plusieurs blocs, on cherche les liens pertinents
    # on parcourt tous les <a> de la page de recherche et on catégorise selon l'URL
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not href or not text:
            continue
        if "/en/players/" in href:
            results["players"].append((text, BASE + href))
        elif "/en/squads/" in href or "/en/teams/" in href:
            results["teams"].append((text, BASE + href))
        elif "/en/comps/" in href:
            results["comps"].append((text, BASE + href))
    return results


