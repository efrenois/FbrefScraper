import time
import re
import pandas as pd
import cloudscraper
import unicodedata
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from io import BytesIO
import unicodedata
import os



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
CLOUDSCRAPER_SESSION = cloudscraper.create_scraper()
CLOUDSCRAPER_SESSION.headers.update(DEFAULT_HEADERS)


def normalize_text(s):
    """Supprime les accents et met en minuscules."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("utf-8")  # enlève les accents
    return s.lower().strip()

###############################################################################################################################################
# FONCTIONS PRINCIPALES
###############################################################################################################################################

def fetch_page(url, max_retries=3, timeout=15, use_cloudscraper_on_block=True):
    """
    Télécharge la page et renvoie (status_code, html or None).
    Essaie first requests, puis cloudscraper en fallback si bloqué.
    """
    last_status = None
    
    # Fallback cloudscraper si activé
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
    Recherche un joueur sur FBref par son nom.
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

    results = {"players": []}
    seen = set()

    search_norm = normalize_text(name)
    # Parcours avec boucle while + booléen : on s'arrête dès qu'on trouve le joueur 'name'
    anchors = soup.find_all("a", href=True)
    i = 0
    found = False

    while i < len(anchors) and not found:
        a = anchors[i]
        href = a["href"]
        text = a.get_text(strip=True)

        # ignorer les liens sans href
        if not href:
            i += 1
            continue

        # filtrer les liens de joueurs
        if re.match(r"^/en/players/[^/]+/.+", href):
            full = urljoin(BASE, href)
            name_text = text.strip()
            name_text_norm = normalize_text(name_text)
            
            if full not in seen:
                seen.add(full)
                results["players"].append((name_text, full))

            # Si le nom correspond (contenu, insensible à la casse), on s'arrête et on retourne
            if search_norm in name_text_norm:
                found = True
                return results

        i += 1

    # Si on a fini la boucle sans trouver de correspondance exacte pour 'name', on lève une erreur
    # (on considère que la requête ne vise pas un joueur)
    raise ValueError(f"Aucun joueur trouvé correspondant précisément à '{name}'.")

                     
def extract_player_info(html, base_url, name):
    """
    Extrait les informations de base du joueur depuis sa page FBref.
    Retourne un dict avec les champs principaux.
    """
    soup = BeautifulSoup(html, "lxml")
    info = {}

    # Nom principal 
    # Extraire le nom principal directement depuis la page FBref 
    h1 = soup.select_one("#meta h1") or soup.find("h1", {"itemprop": "name"})
    if h1:
        info["name"] = h1.get_text(strip=True)
    else:
        # fallback : utiliser le nom passé en paramètre si la page ne contient pas le h1 attendu
        info["name"] = name or ""
    # normalisé pour les comparaisons plus bas
    search_norm = normalize_text(info["name"])

    # Position, pied, nationalité, club
    p_tags = soup.select("#meta p")
    for p in p_tags:
        raw = p.get_text(" ", strip=True)
        # normaliser les espaces
        raw = re.sub(r"\s+", " ", raw)
        # split sur plusieurs séparateurs courants
        parts = re.split(r"\s*[▪•·|/]\s*", raw)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            part_norm = normalize_text(part)
            # Full name 
            if search_norm in part_norm and "position" not in part_norm and "born" not in part_norm:
                info["full_name"] = part.strip()
                continue
            
            # Position
            m = re.search(r"Position\s*: ?(.+)", part, flags=re.I)
            if m:
                info["position"] = m.group(1).strip()
                continue
            # Footed (pied)
            m = re.search(r"Footed\s*: ?(.+)", part, flags=re.I)
            if m:
                info["footed"] = m.group(1).strip()
                continue
            # Born
            m = re.search(r"Born\s*: ?(.+)", part, flags=re.I)
            if m:
                info["birth"] = m.group(1).strip()
                continue
            # National Team
            m = re.search(r"National Team\s*: ?(.+)", part, flags=re.I)
            if m:
                info["national_team"] = m.group(1).strip()
                continue
            # Club
            m = re.search(r"Club\s*: ?(.+)", part, flags=re.I)
            if m:
                info["club"] = m.group(1).strip()
                continue
            # Wages 
            m = re.search(r"Wages\s*: ?(.+)", part, flags=re.I)
            if m:
                val = m.group(1).strip()
                # garder uniquement la première phrase (jusqu'au premier point inclus)
                dot = val.find('.')
                if dot != -1:
                    val = val[:dot+1].strip()
                info["wages"] = val
                continue

    # --- Photo du joueur ---
    img_tag = soup.select_one("#meta img")
    if img_tag and img_tag.get("src"):
        img_src = img_tag["src"]
        if img_src.startswith("/"):
            img_src = base_url + img_src
        info["photo_url"] = img_src

    return info

