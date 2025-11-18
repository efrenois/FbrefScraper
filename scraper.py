import time
import re
import cloudscraper
import unicodedata
import sys
import os 
import csv
import pandas as pd
import plotly.graph_objects as go
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

def save_season_stats_to_csv(season_stats, player_name, season, comp=None, type=None):
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
    safe_type = type.replace("/", "-").replace(" ", "") if type else "standard"

    csv_filename = os.path.join(output_dir, f"stats_{safe_player}_{safe_comp}_{safe_season_name}_{safe_type}.csv")

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
        info["name"] = "Name not found"
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
                    "full_name": "Unknown",
                    "position": "Unknown",
                    "footed": "Unknown",
                    "birth": "Unknown",
                    "national_team": "Unknown",
                    "club": "Unknown",
                    "wages": "Unknown",
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
                    if info.get("full_name") in (None, "", "Unknown"):
                        info["full_name"] = part.strip()
                    continue
            
            # If full_name still not found, try detecting the first meaningful text block
            if info.get("full_name") in (None, "", "Unknown"):

                forbidden_keywords = {
                    "position", "born", "footed", "national team",
                    "club", "wages", "height", "weight"
                }

                football_positions = {
                    "defender", "midfielder", "forward", "goalkeeper",
                    "centre-back", "center-back", "winger", "striker",
                    "attacking", "defensive"
                }

                # Conditions for potential name
                is_potential_name = (
                    len(part.split()) >= 2
                    and not any(key in part_norm for key in forbidden_keywords)
                    and not any(pos in part_norm for pos in football_positions)
                    and not re.search(r"\d", part)
                    and ":" not in part
                )

                if is_potential_name:
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
                info["wages"] = val or "Unknown"
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
        
    season_data = {}
    
    if season is not None and str(season).lower() == "all":
        tfoot = table.find("tfoot")
        rows = [tfoot.find("tr")] if tfoot else []
        # Remove "Age" column if present in the footer
        if "Age" in subheaders:
            age_index = subheaders.index("Age")
            subheaders.pop(age_index)
            categories.pop(age_index)  
    else: 
        # Extract data rows
        tbody = table.find("tbody")
        if not tbody:
            return {"message": "⚠️ no data found in the table"}
        rows = tbody.find_all("tr")
        
    for row in rows:
        cells = row.find_all(["th", "td"])
        if not cells:
            continue
        
        season_name = cells[0].get_text(strip=True)
        if season is not None and str(season).lower() == "all":
            season_name = "All"
        # Accept either YYYY-YYYY or YYYY
        elif not re.match(r"^\d{4}(-\d{4})?$", season_name):
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
    
def extract_core_stats(stats_dict, player_name):
    """
    Extracts statistics for a player, keeping only selected categories:
    'Playing Time', 'Performance', and 'Expected'.
    Each category is retained to avoid collisions in metric names.
    """
    core_stats = {"Player": player_name}

    if not stats_dict:
        return core_stats

    for season, categories in stats_dict.items():
        if not isinstance(categories, dict):
            continue

        for category, substats in categories.items():
            if not isinstance(substats, dict):
                continue

            # Clean the category name
            clean_category = (
                category.replace(" ", "_")
                .replace("/", "_")
                .replace("-", "_")
                .lower()
            )

            for key, value in substats.items():
                clean_key = (
                    key.replace(" ", "_")
                    .replace("/", "_")
                    .replace("-", "_")
                    .lower()
                )

                metric_name = f"{clean_category}_{clean_key}"
                core_stats[metric_name] = value

    return core_stats

def get_table_id_for_type(stat_type, comp):
    """
    Returns the table ID associated with the selected statistics type.
    """
    stat_type = stat_type.lower()
    comp = comp.lower()  # all, dl, dc, ic, nt

    base_map = {
        "standard": "stats_standard",
        "shooting": "stats_shooting",
        "passing": "stats_passing",
        "pass_types": "stats_passing_types",
        "da": "stats_defense",
        "g&s": "stats_gca",
    }

    if stat_type not in base_map:
        raise ValueError(f"Unknown stat type: {stat_type}")

    base_id = base_map[stat_type]

    # For "all competitions", table IDs always end with "_collapsed"
    if comp == "all":
        return f"{base_id}_collapsed"

    # Otherwise: stats_xxx_dom_lg
    comp_suffix = {
        "dl": "dom_lg",
        "dc": "dom_cup",
        "ic": "intl_cup",
        "nt": "nat_tm",
    }[comp]

    return f"{base_id}_{comp_suffix}"

def compare_players_chart(stats_list, season, comp, type="standard"):
    """
    Compare two players with an interactive bar chart.
    Works with ANY stat type (standard, shooting, passing, pass types, defensive actions, goal&shot creation).
    """
    if not stats_list or len(stats_list) < 2:
        print("⚠️ At least two players are required to compare.")
        return

    # DataFrame creation 
    df = pd.DataFrame(stats_list)
    df.set_index("Player", inplace=True)
    
    # List of stats to remove depending on selected type
    excluded_stats = {
        "standard": ["_age", "_squad", "_country", "_comp", "_lgrank",
                    "playing_time_min", "playing_time_90s",
                    "per_90_minutes_gls", "per_90_minutes_ast", "per_90_minutes_g+a",
                    "per_90_minutes_g_pk", "per_90_minutes_g+a_pk",
                    "per_90_minutes_xg", "per_90_minutes_xag",
                    "per_90_minutes_xg+xag", "per_90_minutes_npxg",
                    "per_90_minutes_npxg+xag"
                    ],
        "shooting": ["_age", "_squad", "_country", "_comp", "_lgrank", "_matches",
                    "standard_90s", "standard_sh_90", "standard_sot_90",
                    "standard_g_sh", "standard_g_sot", "standard_dist",
                    "expected_npxg_sh", "expected_g_xg", "expected_np:g_xg"
                    ],
        "passing": ["_age", "_squad", "_country", "_comp", "_lgrank", "_ast", "_kp",
                    "_1_3", "_ppa", "_crspa", "_prgp", "_matches", "total_90s", "total_totdist", "total_prgdist",
                    "expected_xa", "expected_a_xag"
                    ],
        "pass_types": [ "_age", "_squad", "_country", "_comp", "_lgrank", "_90s", "_matches"],
        "da": ["_age", "_squad", "_country", "_comp", "_lgrank", "_matches", "_err"],
        "g&s": ["_age", "_squad", "_country", "_comp", "_lgrank", "_matches"],
    }

    # Stats meaning 
    stat_meaning = {
    "playing_time_mp": "Matches Played",
    "playing_time_starts": "Games started by player",
    "performance_gls": "Goals",
    "performance_ast": "Assists",
    "performance_g+a": "Goals + Assists",
    "performance_g-pk": "Non-penalty Goals",
    "performance_pk": "Penalty Kicks Made",
    "performance_pkatt": "Penalty Kicks Attempted",
    "performance_crdy": "Yellow Cards",
    "performance_crdr": "Red Cards",
    "expected_xg": "Expected Goals",
    "expected_npxg": "Non-penalty Expected Goals",
    "expected_xag": "Expected Assisted Goals",
    "expected_npxg+xag": "Non-penalty Expected Goals + Expected Assisted Goals",
    "standard_gls": "Goals",
    "standard_sh": "Shots Total",
    "standard_sot": "Shots on Target",
    "standard_sot%": "Shots on Target %",
    "standard_fk": "Shots from Free Kicks",
    "standard_pk": "Penalty Kicks Made",
    "standard_pkatt": "Penalty Kicks Attempted",
    "expected_xg": "Expected Goals",
    "expected_npxg": "Non-penalty Expected Goals",
    "_xag": "Expected Assisted Goals",
    "total_cmp": "Passes Completed",
    "total_att": "Passes Attempted",
    "total_cmp%": "Pass Completion %",
    "short_cmp": "Short Passes Completed",
    "short_att": "Short Passes Attempted",
    "short_cmp%": "Short Pass Completion %",
    "medium_cmp": "Medium Passes Completed",
    "medium_att": "Medium Passes Attempted",
    "medium_cmp%": "Medium Pass Completion %",
    "long_cmp": "Long Passes Completed",
    "long_att": "Long Passes Attempted",
    "long_cmp%": "Long Pass Completion %",
    "pass_types_att": "Passes Attempted",
    "pass_types_live": "Live Ball-Passes",
    "pass_types_dead": "Dead Ball-Passes",
    "pass_types_fk": "Passes from Free Kick Passes",
    "pass_types_tb": "Through Balls",
    "pass_types_sw": "Switches",
    "pass_types_crs": "Crosses",
    "pass_types_ti": "Throw Ins Taken",
    "pass_types_ck": "Corner Kicks",
    "corner_kicks_in": "Inswinging Corner Kicks",
    "corner_kicks_out": "Outswinging Corner Kicks",
    "corner_kicks_str": "Straight Corner Kicks",
    "outcomes_cmp": "Passes Completed",
    "outcomes_off": "Passes Offsides",
    "outcomes_blocks": "Passes Blocked",
    "_int": "Interceptions",
    '_tkl+int': "Tackles + Interceptions",
    '_clr': "Clearances",
    'tackles_90': "90s played",
    "tackles_tkl": "Tackles",
    "tackles_tklw": "Tackles Won",
    "tackles_def_3rd": "Defensive 3rd Tackles",
    "tackles_mid_3rd": "Middle 3rd Tackles",
    "tackles_att_3rd": "Attacking 3rd Tackles",
    "challenges_tkl": "Dribblers Tackled",
    "challenges_att": "dribbles Challenged",
    "challenges_tkl%":  "% of Dribblers Tackled",
    "challenges_lost": "Challenges Lost",
    "blocks_blocks": "Ball Blocked",
    "blocks_sh": "Shots Blocked",
    "blocks_pass": "Passes Blocked",
    "sca_90s": "90s played",
    "sca_sca": "Shot-Creating Actions",
    "sca_sca90": "Shot-Creating Actions per 90",
    "sca_types_passlive": "Shot-Creating Actions from Live Ball Passes",
    "sca_types_passdead": "Shot-Creating Actions from Dead Ball Passes",
    "sca_types_to": "SCA (Take Ons)",
    "sca_types_sh" : "SCA (Shots)",
    "sca_types_fld": "SCA (Fouled)",
    "sca_types_def": "SCA (Defensive Actions)",
    "gca_gca": "Goal-Creating Actions",
    "gca_gca90": "Goal-Creating Actions per 90",
    "gca_types_passlive": "Goal-Creating Actions from Live Ball Passes",
    "gca_types_passdead": "Goal-Creating Actions from Dead Ball Passes",
    "gca_types_to": "GCA (Take Ons)",
    "gca_types_sh": "GCA (Shots)",
    "gca_types_fld": "GCA (Fouled)",
    "gca_types_def": "GCA (Defensive Actions)",
    }
    
    # Identify stats to delete
    current_exclusions = excluded_stats.get(type, [])

    # Remove unwanted columns
    df = df.drop(columns=[col for col in current_exclusions if col in df.columns], errors="ignore")
    
    print(df.columns.tolist())
    
    # Replace commas (e.g. '1,234' -> '1234')
    df = df.replace({r",": ""}, regex=True)
    df = df.apply(pd.to_numeric, errors="coerce")

    # Remove empty columns
    df = df.dropna(axis=1, how="all")

    # Keep only columns where both players have values 
    common_stats = [col for col in df.columns if not df[col].isna().any()]
    if not common_stats:
        print("⚠️ No common statistics between players.")
        return None

    df_to_plot = df[common_stats]
    player1, player2 = df_to_plot.index.tolist()

    # Labels 
    display_labels = [stat_meaning.get(stat, stat) for stat in common_stats]
    
    # Plot building 
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=display_labels,
        x=-df_to_plot.loc[player1].values,   
        orientation='h',
        name=player1,
        marker_color="royalblue",

        customdata=[abs(v) for v in df_to_plot.loc[player1].values],
        hovertemplate="<br>%{customdata}<br><extra></extra>",

        hoverlabel=dict(
            align="left",
            bgcolor="lightblue",
            bordercolor="blue",
            font=dict(color="black")
        )
    ))

    # Player 2 (right side)
    fig.add_trace(go.Bar(
        y=display_labels,
        x=df_to_plot.loc[player2].values,
        orientation='h',
        name=player2,
        marker_color="crimson",
        hovertemplate="<br>%{x}<extra></extra>"
    ))

    # Title formatting 
    # Format season
    if str(season).lower() in ["all", "none", "", "null"]:
        season_label = "All Seasons"
    else:
        season_label = season

    # Format competition
    comp_map_full = {
        "all": "All Competitions",
        "dl": "Domestic Leagues",
        "dc": "Domestic Cups",
        "ic": "International Cups",
        "nt": "National Team",
        None: "Unknown Competition"
    }
    comp_label = comp_map_full.get(str(comp).lower(), comp)

    # Format stat type
    type_map_full = {
        "standard": "Standard Stats",
        "shooting": "Shooting Stats",
        "passing": "Passing Stats",
        "pass_types": "Pass Types Statistics",
        "da": "Defensive Actions",
        "g&s": "Goal & Shot Creation"
    }
    type_label = type_map_full.get(type, type)

    # Max scale
    max_val = max(abs(df_to_plot).max())

    # Layout 
    fig.update_layout(
        title=dict(
            text=f"{type_label} Comparison – {season_label}, {comp_label}",
            x=0.5,
            xanchor="center",
            font=dict(size=18)
        ),
        barmode="overlay",
        xaxis=dict(
            title="Value",
            tickvals=[-max_val, -max_val/2, 0, max_val/2, max_val],
            ticktext=[max_val, max_val/2, 0, max_val/2, max_val],
            zeroline=True
        ),
        yaxis=dict(title="", autorange="reversed"),
        template="plotly_white",
        bargap=0.45,
        height=900
    )

    return fig