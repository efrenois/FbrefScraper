import time
import re
import cloudscraper
import unicodedata
import unicodedata
import sys
import os 
import csv
import pandas as pd
from urllib.parse import urlparse
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from jinja2 import Template


################################################################################################################################################
# PARAMÈTRES GLOBAUX
################################################################################################################################################

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

###############################################################################################################################################
# FONCTIONS UTILITAIRES
###############################################################################################################################################

def normalize_text(s):
    """Supprime les accents et met en minuscules."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("utf-8")  # enlève les accents
    return s.lower().strip()

def save_season_stats_to_csv(season_stats, player_name, season):
    """
    Sauvegarde les statistiques d'une saison dans un fichier CSV.
    - season_stats : dict (les données retournées par extract_player_season_stats_all_comps)
    - player_name : nom du joueur (string)
    - season : saison (ex: "2023-2024")
    """
    if not season_stats or "message" in season_stats:
        print("⚠️ Aucune donnée à enregistrer.")
        return None

    # Récupérer les données de la saison
    data = season_stats.get(season)
    if not data:
        print(f"⚠️ Données inconnues pour la saison {season}.")
        return None

    # Créer le dossier de sortie
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Nettoyer le nom du joueur et de la saison pour le nom du fichier
    safe_player = player_name.replace(" ", "_").replace("/", "-")
    safe_season = season.replace("/", "-").replace(" ", "")

    csv_filename = os.path.join(output_dir, f"stats_{safe_player}_{safe_season}.csv")

    # Préparer les données à écrire
    fieldnames = ["Category", "Stat", "Value"]
    rows = []

    for category, subdict in data.items():
        for subheader, value in subdict.items():
            rows.append({
                "Category": category or "General",
                "Stat": subheader,
                "Value": value
            })

    # Écrire dans le fichier CSV
    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Données enregistrées dans : {csv_filename}")
    return csv_filename

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
    # on garde la meilleure correspondance
    best_match = None
    best_score = 0.0
    while i < len(anchors):
        a = anchors[i]
        href = a["href"]
        text = a.get_text(strip=True)
        i += 1

        if not href:
            continue

        # filtrer uniquement les liens joueurs FBref
        if re.match(r"^/en/players/[^/]+/.+", href):
            full = urljoin(BASE, href)
            name_text = text.strip()
            name_text_norm = normalize_text(name_text)

            if full in seen:
                continue
            seen.add(full)
            results["players"].append((name_text, full))

            # Calcul de similarité textuelle
            ratio = SequenceMatcher(None, search_norm, name_text_norm).ratio()
            if ratio > best_score:
                best_score = ratio
                best_match = (name_text, full)

    if not results["players"]:
        raise ValueError(f"Aucun joueur trouvé correspondant précisément à '{name}'.")

    # afficher la meilleure correspondance trouvée
    if best_match:
        return {"players": [best_match]}
    else:
        raise ValueError(f"Aucun joueur trouvé correspondant à '{name}'.")
    
                     
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
        info["name"] = "Nom inconnu"
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
            
            # initialiser les valeurs par défaut une seule fois
            if not info.get("_meta_inited"):
                defaults = {
                    "full_name": "inconnu",
                    "position": "inconnu",
                    "footed": "inconnu",
                    "birth": "inconnu",
                    "national_team": "inconnu",
                    "club": "inconnu",
                    "wages": "inconnu",
                }
                for k, v in defaults.items():
                    info.setdefault(k, v)
                info["_meta_inited"] = True

            # heuristique pour le nom complet : contient le terme de recherche et n'est pas une ligne de type "Position/Born/Footed/..."
            # Détecte full_name même si la forme diffère (ex: "Cristiano Ronaldo" vs "Cristiano Ronaldo dos Santos Aveiro")
            if search_norm and not re.search(r"\b(position|born|footed|national team|club|wages)\b", part_norm):
                # comparaison par tokens : tous les tokens du nom de recherche présents dans la chaîne candidate
                search_tokens = set(search_norm.split())
                part_tokens = set(part_norm.split())
                token_match = any(tok in part_tokens for tok in search_tokens)

                # similarité globale pour tolérer ajouts/ordre/ponctuation différents
                ratio = SequenceMatcher(None, search_norm, part_norm).ratio()
                similar = ratio >= 0.70

                # accepter si l'un des critères est rempli
                if token_match or similar or part_norm.startswith(search_norm):
                    if info.get("full_name") in (None, "", "inconnu"):
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
                info["wages"] = val or "inconnu"
                continue

    # --- Photo du joueur ---
    img_tag = soup.select_one("#meta img")
    if img_tag and img_tag.get("src"):
        img_src = img_tag["src"]
        if img_src.startswith("/"):
            img_src = base_url + img_src
        info["photo_url"] = img_src
    
    if not info: 
        print("Impossible d'extraire les informations du joueur.")
        sys.exit(4)

    return info

def generate_player_passeport(player_info):
    """Génère une image de passeport pour le joueur avec les informations extraites."""
    # Générer le passeport du joueur en HTML
    template_path = os.path.join("templates", "passeport_template.html")
    output_html = os.path.join("output", f"passeport_{player_info.get("name").replace(" ", "")}.html")
    css_path = os.path.abspath("templates/style.css")

        
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    template = Template(template_str)
    html_content = template.render(**player_info, css_path=css_path)
        
    os.makedirs("output", exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML généré : {output_html}")
    return html_content


def get_all_comps_url(player_url):
    """
    Transforme l'URL du joueur en URL 'All Competitions'.
    Ex: 
    https://fbref.com/en/players/82ec26c1/Lamine-Yamal
    ->
    https://fbref.com/en/players/82ec26c1/all_comps/Lamine-Yamal-Stats---All-Competitions
    """
    parsed = urlparse(player_url)
    parts = parsed.path.strip("/").split("/")
    
    if len(parts) < 3:
        raise ValueError("URL du joueur inattendue")

    player_id = parts[2]
    player_name = parts[3]

    all_comps_path = f"/en/players/{player_id}/all_comps/{player_name}-Stats---All-Competitions"
    return f"{parsed.scheme}://{parsed.netloc}{all_comps_path}"

        
def extract_player_season_stats_all_comps(html, season):
    """
    Extrait les statistiques de la saison donnée depuis la page 'All Competitions'.
    Retourne un dict avec les stats organisées par catégorie.
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Chercher d'abord la table
    table = soup.find("table", id="stats_standard_collapsed")
    if not table:
        return {"message": "table introuvable dans div #stats_standard_collapsed"}

    # Extraire les headers 
    thead = table.find("thead")
    categories = []
    subheaders = []

    headers_rows = thead.find_all("tr")
    category_row = headers_rows[0]
    subheader_row = headers_rows[1] 
    
    # Étape 1 : Récupérer les catégories avec gestion correcte du colspan
    for th in category_row.find_all("th"):
        cat_name = th.get_text(strip=True)
        colspan = int(th.get("colspan", 1))

        # Si le th est vide mais que c’est le dernier avant un vrai colspan,
        # on suppose qu’il "prépare" une catégorie
        if not cat_name and colspan == 1:
            cat_name = ""
        for _ in range(colspan):
            categories.append(cat_name)

    # Étape 2 : Récupérer les sous-headers
    for th in subheader_row.find_all("th"):
        subheaders.append(th.get_text(strip=True))

    # Étape 3 : Corriger le décalage s’il existe
    if len(categories) < len(subheaders):
        diff = len(subheaders) - len(categories)
        # Correction spécifique : si la dernière catégorie non vide est suivie de vides,
        # on prolonge cette dernière catégorie
        if categories and categories[-1] != "":
            categories += [categories[-1]] * diff
        else:
            categories = [""] * diff + categories
    elif len(categories) > len(subheaders):
        categories = categories[:len(subheaders)]

    # Correction spéciale FBref :
    # Si on a une série initiale de 5 vides mais que la 6e est "Playing Time",
    # on remplace le 5e vide par cette valeur
    for i in range(1, len(categories)):
        if categories[i] != "" and categories[i-1] == "":
            categories[i-1] = categories[i]
            break
    
    # Étape 4 : Extraire les lignes de données
    tbody = table.find("tbody")
    if not tbody:
        return {"message": "aucune donnée trouvée dans le tableau"}
    
    season_data = {}
    
    rows = tbody.find_all("tr")
    for row in rows:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        
        season_name = cells[0].get_text(strip=True)
        if not re.match(r"\d{4}-\d{4}", season_name):
            continue
        
        # Créer la structure pour la saison si absente
        if season_name not in season_data:
            season_data[season_name] = {}
            
        # Associer chaque sous-header à sa catégorie et valeur
        for idx, cell in enumerate(cells[1:], start=1):
            if idx >= len(subheaders):
                break
            cat = categories[idx]
            sub = subheaders[idx]
            val = cell.get_text(strip=True) or "N/A"

            if cat not in season_data[season_name]:
                season_data[season_name][cat] = {}

            season_data[season_name][cat][sub] = val

    # Retourner seulement la saison demandée si trouvée
    if season in season_data:
        return {season: season_data[season]}
    else:
        return {"message": f"Données inconnues pour la saison {season}"}
    




        



    
