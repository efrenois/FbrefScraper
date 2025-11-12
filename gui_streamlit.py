import streamlit as st
import pandas as pd
from scraper import (
    fbref_search,
    fetch_page,
    extract_player_info,
    generate_player_passeport,
    get_competition_url_and_table_id,
    extract_player_stats_by_competition,
    save_season_stats_to_csv
)
import os

st.set_page_config(page_title="FBref Scraper", page_icon="⚽", layout="wide")

st.title("⚽ FBref Scraper — Analyse des joueurs")

# --- Formulaire ---
with st.form("scraper_form"):
    name = st.text_input("Nom du joueur", placeholder="Ex: Lamine Yamal")
    comp = st.selectbox(
        "Compétition",
        ["all (all competitions)", "dl (domestic leagues)", "dc (domestic cups)", "ic (international cups)", "nt (national team)"],
        index=0,
        help="Choisis la compétition : all (toutes), dl (domestic leagues), dc (domestic cups), ic (international cups), nt (national team)"
    )
    season = st.text_input("Saison (ex: 2023-2024 ou 'All')", value="All")

    submitted = st.form_submit_button("🚀 Lancer le Scraper")

if submitted:
    if not name.strip():
        st.warning("⚠️ Veuillez entrer un nom de joueur.")
        st.stop()

    with st.spinner(f"Recherche du joueur {name} sur FBref..."):
        try:
            results = fbref_search(name)
        except Exception as e:
            st.error(f"Erreur lors de la recherche : {e}")
            st.stop()

    if results.get("players"):
        _, chosen = results["players"][0]
        st.success(f"✅ Joueur trouvé : {name}")

        # --- Extraction du passeport ---
        with st.spinner("📄 Extraction des informations du joueur..."):
            code, html = fetch_page(chosen)
            player_info = extract_player_info(html, chosen, name)
            passeport_html, passeport_path = generate_player_passeport(player_info)

        st.subheader("🪪 Passeport du joueur")

        # --- Affichage du passeport HTML directement dans Streamlit ---
        st.components.v1.html(passeport_html, height=600, scrolling=True)

        # --- Extraction des stats ---
        with st.spinner("📊 Extraction des statistiques..."):
            try:
                comp_key = comp.split(" ")[0].strip()  # récupère juste 'all', 'dl', 'dc', 'ic' ou 'nt'
                comp_url, table_id = get_competition_url_and_table_id(chosen, comp_key)
                code_comp, html_comp = fetch_page(comp_url)
                stats = extract_player_stats_by_competition(
                    html_comp, table_id, season=None if season.lower() == "all" else season
                )
            except Exception as e:
                st.error(f"Erreur lors de l'extraction des stats : {e}")
                st.stop()

        # --- Sauvegarde CSV ---
        csv_path = save_season_stats_to_csv(stats, player_name=name, season=season, comp=comp)
        st.success("✅ Statistiques extraites avec succès.")
        
        # --- Affichage du tableau hiérarchique ---
        from itertools import product

        st.subheader("📊 Tableau des statistiques structurées")

        if not stats or "message" in stats:
            st.warning("Aucune donnée disponible pour cette sélection.")
        else:
            # On crée un tableau multi-index : (Catégorie, Statistique) → Valeur
            season_tables = []

            for season_key, categories in stats.items():
                if not categories:
                    continue

                # Construction des tuples hiérarchiques (Catégorie, Sous-header)
                rows = []
                for category, subdict in categories.items():
                    for subheader, value in subdict.items():
                        rows.append((category or "General", subheader, value))

                df = pd.DataFrame(rows, columns=["Catégorie", "Sous-statistique", "Valeur"])
                df.set_index(["Catégorie", "Sous-statistique"], inplace=True)

                st.markdown(f"### 🗓️ Saison : **{season_key}**")
                st.dataframe(df, use_container_width=True)

                season_tables.append((season_key, df))

            # Si plusieurs saisons, possibilité de les concaténer
            if len(season_tables) > 1:
                combined = pd.concat(
                    {s: d for s, d in season_tables},
                    names=["Saison", "Catégorie", "Sous-statistique"]
                )
                st.markdown("### 📊 Vue combinée — toutes saisons")
                st.dataframe(combined, use_container_width=True)

        # --- Téléchargement CSV ---
        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                st.download_button(
                    label="⬇️ Télécharger le CSV",
                    data=f,
                    file_name=os.path.basename(csv_path),
                    mime="text/csv"
                )

        # --- Lien vers le passeport HTML ---
        html_path = f"output/passeport_player/passeport_{player_info['name'].replace(' ', '')}.html"
        if os.path.exists(html_path):
            st.markdown(f"[🌐 Ouvrir le passeport HTML]({html_path})", unsafe_allow_html=True)

    else:
        st.error("Aucun joueur trouvé sur FBref.")