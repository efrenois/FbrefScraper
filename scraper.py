import requests
import time
import re
import json
import pandas as pd
import cloudscraper
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from io import BytesIO

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

###############################################################################################################################################
# FONCTIONS PRINCIPALES
###############################################################################################################################################

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
    # FBref montre plusieurs blocs, on cherche uniquement les liens de joueurs
    # On parcourt tous les <a> de la page de recherche et on filtre strictement
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not href:
            continue
        # n'accepter que les URLs qui correspondent au pattern joueur
        # ex: /en/players/<id>/<player-slug>
        # on rejette la page index /en/players/ qui existe sur FBref
        if not re.match(r"^/en/players/[^/]+/.+", href):
            continue
        full = urljoin(BASE, href)
        if full in seen:
            continue
        seen.add(full)
        # si le texte du lien est générique (ex: 'Players'), inférer le nom depuis le slug
        name_text = text
        if not name_text or name_text.lower() in ("players", "player", "players »"):
            try:
                slug = href.rstrip("/").split("/")[-1]
                name_text = slug.replace("-", " ")
            except Exception:
                name_text = text or ""

        results["players"].append((name_text, full))

    # Si aucun joueur trouvé, on considère que la requête ne vise pas un joueur
    if not results["players"]:
        raise ValueError(f"Aucun joueur trouvé pour '{name}'. Il semble s'agir d'une équipe ou d'une autre entité.")

    return results

def extract_player_info(html, base_url, name):
    """
    Extrait les informations de base du joueur depuis sa page FBref.
    Retourne un dict avec les champs principaux.
    """
    soup = BeautifulSoup(html, "lxml")
    info = {}

    # Nom principal 
    info["name"] = name

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
            # Full name 
            m = re.search(name, part, flags=re.I)
            if m:
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

def create_player_passport_image(info, output_file):
    """
    Crée une image "passeport" du joueur avec ses informations de base.
    """
    # Télécharger la photo
    img_url = info.get("photo_url")
    if img_url:
        response = CLOUDSCRAPER_SESSION.get(img_url)
        photo = Image.open(BytesIO(response.content)).convert("RGBA")
        photo = photo.resize((200, 200))
    else:
        # placeholder gris
        photo = Image.new("RGBA", (200, 200), (180, 180, 180, 255))

    # Créer le fond (passeport)
    width, height = 800, 250
    background = Image.new("RGBA", (width, height), (245, 245, 245, 255))
    draw = ImageDraw.Draw(background)

    # Police (tu peux changer selon ton système)
    try:
        font_title = ImageFont.truetype("arialbd.ttf", 30)
        font_text = ImageFont.truetype("arial.ttf", 20)
    except:
        font_title = font_text = ImageFont.load_default()

    # Coller la photo
    background.paste(photo, (20, 25))

    # Texte du joueur
    x0 = 250
    y = 30
    draw.text((x0, y), info.get("name", "N/A"), fill=(0, 0, 0), font=font_title)
    y += 40
    draw.text((x0, y), f"Nom complet : {info.get('full_name', 'N/A')}", fill=(30, 30, 30), font=font_text)
    y += 30
    draw.text((x0, y), f"Position : {info.get('position', 'N/A')}", fill=(30, 30, 30), font=font_text)
    y += 30
    draw.text((x0, y), f"Pied : {info.get('footed', 'N/A')}", fill=(30, 30, 30), font=font_text)
    y += 30
    draw.text((x0, y), f"Naissance : {info.get('birth', 'N/A')}", fill=(30, 30, 30), font=font_text)
    y += 30
    draw.text((x0, y), f"Nationalité : {info.get('national_team', 'N/A')}", fill=(30, 30, 30), font=font_text)
    y += 30
    draw.text((x0, y), f"Club : {info.get('club', 'N/A')}", fill=(30, 30, 30), font=font_text)
    y += 30
    draw.text((x0, y), f"Salaire : {info.get('wages', 'N/A')}", fill=(30, 30, 30), font=font_text)

    # Sauvegarde
    background.save(output_file)
    print(f"✅ Passeport joueur enregistré sous {output_file}")




