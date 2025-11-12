import time
import re
import cloudscraper
import unicodedata
import unicodedata
import sys
import os 
import csv
from urllib.parse import urlparse
from difflib import SequenceMatcher
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from jinja2 import Template


################################################################################################################################################
# GLOBAL SETTINGS
################################################################################################################################################

DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://fbref.com/"
}

BASE = "https://fbref.com"

RATE_SEC = 1.5  # Delay between requests

# Reusable sessions 
CLOUDSCRAPER_SESSION = cloudscraper.create_scraper()
CLOUDSCRAPER_SESSION.headers.update(DEFAULT_HEADERS)

###############################################################################################################################################
# UTILITY FUNCTIONS
###############################################################################################################################################

def normalize_text(s):
    """Removes accents and converts to lowercase."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("utf-8")
    return s.lower().strip()

def save_season_stats_to_csv(season_stats, player_name, season, comp=None):
    """
    Saves statistics for one season or all seasons in a CSV file.
    - season_stats: dict (data returned by extract_player_season_stats_all_comps)
    - player_name: player name (string)
    - season: season (e.g., “2023-2024”) or “All” for all seasons
    - comp: competition (e.g., “dl,” “dc,” “ic,” “nt,” “all”), optional
    """
    if not season_stats or "message" in season_stats:
        print(f"⚠️ No data to record for {season}.")
        return None

    # Determine whether you want all seasons
    if str(season).lower() == "all" or season is None:
        data_to_save = season_stats
        safe_season_name = "All"
    else:
        data_to_save = {season: season_stats.get(season)}
        safe_season_name = season

    # Create the output folder
    output_dir = "output/datas_player"
    os.makedirs(output_dir, exist_ok=True)

    # Clean the player and competition names for the file name
    safe_player = player_name.replace(" ", "_").replace("/", "-")
    safe_season_name = safe_season_name.replace("/", "-").replace(" ", "")
    safe_comp = comp.replace("/", "-").replace(" ", "") if comp else "all"

    csv_filename = os.path.join(output_dir, f"stats_{safe_player}_{safe_comp}_{safe_season_name}.csv")

    # Prepare the data to be written
    fieldnames = ["Season", "Category", "Stat", "Value"]
    rows = []

    for season_key, categories in data_to_save.items():
        if not categories:
            continue
        for category, subdict in categories.items():
            for subheader, value in subdict.items():
                rows.append({
                    "Season": season_key,
                    "Category": category or "General",
                    "Stat": subheader,
                    "Value": value
                })

    if not rows:
        print(f"⚠️ No data available for the season '{season}'.")
        return None

    # Write to CSV file
    with open(csv_filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Data recorded in : {csv_filename}")
    return csv_filename

###############################################################################################################################################
# MAIN FUNCTIONS
###############################################################################################################################################

def fetch_page(url, max_retries=3, timeout=15, use_cloudscraper_on_block=True):
    """
    Download the page and return (status_code, html or None).
    """
    last_status = None
    
    # Cloudscraper attempt
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

    # Return code/error
    return (last_status or 0), None


def fbref_search(name):
    """
    Search for a player on FBref by name.
    """
    q = quote_plus(name)
    url = f"{BASE}/search/search.fcgi?search={q}"
    print(f"[search] requête : {url}")
    status, html = fetch_page(url, max_retries=3, timeout=15, use_cloudscraper_on_block=True)

    if status != 200 or not html:
        # Message for debugging
        raise RuntimeError(f"HTTP error {status} during search or empty page.")
    # Compliance with the overall deadline
    time.sleep(RATE_SEC)
    
    soup = BeautifulSoup(html, "lxml")

    results = {"players": []}
    seen = set()

    search_norm = normalize_text(name)
    
    # Loop : stop as soon as the player ‘name’ is found
    anchors = soup.find_all("a", href=True)
    i = 0
    # We keep the best match
    best_match = None
    best_score = 0.0
    while i < len(anchors):
        a = anchors[i]
        href = a["href"]
        text = a.get_text(strip=True)
        i += 1

        if not href:
            continue

        # Filter only FBref player links
        if re.match(r"^/en/players/[^/]+/.+", href):
            full = urljoin(BASE, href)
            name_text = text.strip()
            name_text_norm = normalize_text(name_text)

            if full in seen:
                continue
            seen.add(full)
            results["players"].append((name_text, full))

            # Text similarity calculation
            ratio = SequenceMatcher(None, search_norm, name_text_norm).ratio()
            if ratio > best_score:
                best_score = ratio
                best_match = (name_text, full)

    if not results["players"]:
        raise ValueError(f"⚠️ No players found matching exactly '{name}'.")

    # Display the best match found
    if best_match:
        return {"players": [best_match]}
    else:
        raise ValueError(f"❌ No players found matching '{name}'.")
    
                     
def extract_player_info(html, base_url, name):
    """
    Extracts basic player information from their FBref page.
    Returns a dictionary with the main fields.
    """
    soup = BeautifulSoup(html, "lxml")
    info = {}

    # Main name
    # Extract the main name directly from the FBref page 
    h1 = soup.select_one("#meta h1") or soup.find("h1", {"itemprop": "name"})
    if h1:
        info["name"] = h1.get_text(strip=True)
    else:
        # Use the name passed as a parameter if the page does not contain the expected h1
        info["name"] = "Nom inconnu"
    # Normalized for comparisons below
    search_norm = normalize_text(info["name"])

    p_tags = soup.select("#meta p")
    for p in p_tags:
        raw = p.get_text(" ", strip=True)
        # Standardize whitespaces
        raw = re.sub(r"\s+", " ", raw)
        # Split across multiple common separators
        parts = re.split(r"\s*[▪•·|/]\s*", raw)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            part_norm = normalize_text(part)
            
            # Initialize default values once
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

            # Detects full_name even if the form differs (e.g., “Cristiano Ronaldo” vs. “Cristiano Ronaldo dos Santos Aveiro”)
            if search_norm and not re.search(r"\b(position|born|footed|national team|club|wages)\b", part_norm):
                # Comparison by tokens: all tokens of the search name present in the candidate string
                search_tokens = set(search_norm.split())
                part_tokens = set(part_norm.split())
                token_match = any(tok in part_tokens for tok in search_tokens)

                # Overall similarity to tolerate different additions/order/punctuation
                ratio = SequenceMatcher(None, search_norm, part_norm).ratio()
                similar = ratio >= 0.70

                # Accept if one of the criteria is met
                if token_match or similar or part_norm.startswith(search_norm):
                    if info.get("full_name") in (None, "", "inconnu"):
                        info["full_name"] = part.strip()
                    continue

            # Position
            m = re.search(r"Position\s*: ?(.+)", part, flags=re.I)
            if m:
                info["position"] = m.group(1).strip()
                continue

            # Footed 
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
                # Keep only the first sentence (up to and including the first period)
                dot = val.find('.')
                if dot != -1:
                    val = val[:dot+1].strip()
                info["wages"] = val or "inconnu"
                continue

    # Photo of the player 
    img_tag = soup.select_one("#meta img")
    if img_tag and img_tag.get("src"):
        img_src = img_tag["src"]
        if img_src.startswith("/"):
            img_src = base_url + img_src
        info["photo_url"] = img_src
    
    if not info: 
        print("⚠️ Unable to retrieve player information.")
        sys.exit(4)

    return info

def generate_player_passeport(player_info):
    """Generates a passport image for the player with the extracted information."""
    
    # Generate the player's passport in HTML
    template_path = os.path.join("templates", "passport_template.html")
    output_html = os.path.join("output/passport_player", f"passport_{player_info.get("name").replace(" ", "")}.html")
        
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    template = Template(template_str)
    html_content = template.render(**player_info)
        
    os.makedirs("output/passport_player", exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ Generated HTML : {output_html}")
    return html_content, output_html


def get_competition_url_and_table_id(player_url, comp="all"):
    """
    Builds the complete URL and also returns the ID of the corresponding table,
    depending on the competition selected:
      - “all” → all competitions combined
      - “dl”  → domestic leagues
      - “dc”  → domestic cups
      - “ic”  → international cups
      - “nt”  → national team
    Example:
      https://fbref.com/en/players/82ec26c1/Lamine-Yamal
        -> “dl”  → https://fbref.com/en/players/82ec26c1/dom_lg/Lamine-Yamal-Domestic-League-Stats
    """
    comp = str(comp).lower()
    parsed = urlparse(player_url)
    parts = parsed.path.strip("/").split("/")

    if len(parts) < 3:
        raise ValueError(f"URL du joueur inattendue : {player_url}")

    player_id = parts[2]
    player_name = parts[3]

    # Competitions dictionary
    comp_map = {
        "all": ("all_comps", f"{player_name}-Stats---All-Competitions", "stats_standard_collapsed"),
        "dl":  ("dom_lg",  f"{player_name}-Domestic-League-Stats",       "stats_standard_dom_lg"),
        "dc":  ("dom_cup", f"{player_name}-Domestic-Cup-Stats",          "stats_standard_dom_cup"),
        "ic":  ("intl_cup", f"{player_name}-International-Cup-Stats",    "stats_standard_intl_cup"),
        "nt":  ("nat_tm",  f"{player_name}-National-Team-Stats",         "stats_standard_nat_tm"),
    }

    if comp not in comp_map:
        raise ValueError(f" ⚠️ Unknown type of competition : {comp}")

    folder, suffix, table_id = comp_map[comp]

    comp_path = f"/en/players/{player_id}/{folder}/{suffix}"
    full_url = f"{parsed.scheme}://{parsed.netloc}{comp_path}"

    return full_url, table_id
     
def extract_player_stats_by_competition(html, table_id, season):
    """
    Extracts statistics for the given season from the 'All Competitions' page.
    Returns a dictionary with statistics organized by category.
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Look for the table first
    table = soup.find("table", id=table_id)
    if not table:
        return {"message": "⚠️ Table not found in div #stats_standard_collapsed"}

    # Extract headers 
    thead = table.find("thead")
    categories = []
    subheaders = []

    headers_rows = thead.find_all("tr")
    category_row = headers_rows[0]
    subheader_row = headers_rows[1] 
    
    # Retrieve categories with correct colspan management
    for th in category_row.find_all("th"):
        cat_name = th.get_text(strip=True)
        colspan = int(th.get("colspan", 1))

        if not cat_name and colspan == 1:
            cat_name = ""
        for _ in range(colspan):
            categories.append(cat_name)

    # Retrieve subheaders
    for th in subheader_row.find_all("th"):
        subheaders.append(th.get_text(strip=True))

    # Correct the offset if it exists
    if len(categories) < len(subheaders):
        diff = len(subheaders) - len(categories)

        if categories and categories[-1] != "":
            categories += [categories[-1]] * diff
        else:
            categories = [""] * diff + categories
    elif len(categories) > len(subheaders):
        categories = categories[:len(subheaders)]

    for i in range(1, len(categories)):
        if categories[i] != "" and categories[i-1] == "":
            categories[i-1] = categories[i]
            break
    
    # Extract data rows
    tbody = table.find("tbody")
    if not tbody:
        return {"message": "⚠️ no data found in the table"}
    
    season_data = {}
    
    rows = tbody.find_all("tr")
    for row in rows:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        
        season_name = cells[0].get_text(strip=True)
        # Accept either YYYY-YYYY or YYYY
        if not re.match(r"^\d{4}(-\d{4})?$", season_name):
            continue
        
        # Create the structure for the season that is so lacking
        if season_name not in season_data:
            season_data[season_name] = {}
            
        # Associate each subheader with its category and value
        for idx, cell in enumerate(cells[1:], start=1):
            if idx >= len(subheaders):
                break
            cat = categories[idx]
            sub = subheaders[idx]
            val = cell.get_text(strip=True) or "N/A"

            if cat not in season_data[season_name]:
                season_data[season_name][cat] = {}

            season_data[season_name][cat][sub] = val
    
    if season is None or str(season).lower() == "all" :
        return season_data
    elif season in season_data:
        return {season: season_data[season]}
    else:
        return {"message": f"⚠️ Data unknown for the season {season}"}