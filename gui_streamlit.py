import streamlit as st
import pandas as pd
from scraper import *
import os

# Competition mapping
comp_map = {
    "all competitions": "all",
    "domestic leagues": "dl",
    "domestic cups": "dc",
    "international cups": "ic",
    "national team": "nt"
    }

st.set_page_config(page_title="FBref Scraper", page_icon="⚽", layout="wide")

# Custom CSS for buttons in forms
st.markdown("""
<style>
/* Style global pour tous les boutons de formulaire */
div[data-testid="stForm"] button {
    border: 2px solid #FF7F50 !important;  /* contour orange */
    background-color: transparent !important; 
    color: inherit !important;              /* conserve la couleur du texte */
    transition: background-color 0.3s ease;
    cursor: pointer;
}

/* Fond orange foncé au survol */
div[data-testid="stForm"] button:hover {
    background-color: #FF4500 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("⚽ FBref Scraper — Player analysis")

tab_passport, tab_single_player_analysis, tab_compare = st.tabs(["Passport Player", "Single Player Analysis", "Compare Players"])

with tab_passport:
    st.header("🪪 Player Passport")

    # Form
    with st.form("passport_form"):
        name_passport = st.text_input("Player name", placeholder="Ex: Lamine Yamal")
        st.write("")
        col_left, col_button = st.columns([7, 1])
        with col_button:
            submitted_passport = st.form_submit_button("Generate Passport")
        
        if submitted_passport:
            if not name_passport.strip(): 
                st.warning("⚠️ Please enter a player name.")
                st.stop()
        
            # Player search
            with st.spinner(f"Search for player {name_passport} on FBref..."):
                try:
                    results = fbref_search(name_passport)
                except Exception as e:
                    st.error(f"Error during search : {e}")
                    st.stop()

            if not results.get("players"):
                st.error("⚠️ No player found on FBref")
                st.stop()

            # Player page found
            _, chosen = results["players"][0]
            st.success(f"✅ Player found : {name_passport}")
            
            with st.spinner("📄 Extracting player information..."):
                code, html = fetch_page(chosen)
                player_info = extract_player_info(html, chosen, name_passport)
                passport_html, passport_path = generate_player_passeport(player_info)

            st.components.v1.html(passport_html, height=600, scrolling=True)

with tab_single_player_analysis:
    st.header("📊 Single Player Analysis")
    with st.form("analysis_form"):
        name_single = st.text_input("Player name", placeholder="Ex: Lamine Yamal")
        season_single = st.text_input("Season", placeholder="(ex: YYYY-YYYY or YYYY or 'All' )")
        comp_single = st.selectbox(
            "Competition",
            ["Select a competition...","all competitions", "domestic leagues", "domestic cups",
             "international cups", "national team"],
            index=0
        )
        st.write("")
        col_left, col_button = st.columns([13.5, 1])
        with col_button:
            submitted_single = st.form_submit_button("Submit")

    if submitted_single:
        if not name_single.strip():
            st.warning("⚠️ Please enter a player name.")
            st.stop()
        if season_single.strip() == "":
            st.warning("⚠️ Please enter a season.")
            st.stop()
        if comp_single == "Sélectionnez une compétition...":
            st.warning("⚠️ Please select a competition.")
            st.stop()

        with st.spinner("📊 Data extraction..."):
            try:
                results = fbref_search(name_single)
                _, chosen = results["players"][0]
                comp_key = comp_map[comp_single]
                comp_url, table_id = get_competition_url_and_table_id(chosen, comp_key)
                code_comp, html_comp = fetch_page(comp_url)
                stats = extract_player_stats_by_competition(
                    html_comp,
                    table_id,
                    season=None if season_single.lower() == "all" else season_single
                )
            except Exception as e:
                st.error(f"Error extracting statistics : {e}")
                st.stop()

            # Save CSV
            csv_path = save_season_stats_to_csv(stats, player_name=name_single, season=season_single, comp=comp_single)

            st.subheader("📊 Data table")
            if not stats or "message" in stats:
                st.warning("No data available for this selection.")
            else:
                season_tables = []

                for season_key, categories in stats.items():
                    if not categories:
                        continue

                    rows = []
                    for category, subdict in categories.items():
                        for subheader, value in subdict.items():
                            rows.append((category or "General", subheader, value))

                    df = pd.DataFrame(rows, columns=["Category", "statistics", "Data"])
                    df.set_index(["Category", "statistics"], inplace=True)

                    st.markdown(f"### 🗓️ Season : **{season_key}**")
                    st.dataframe(df, use_container_width=True)

                    season_tables.append((season_key, df))

                if len(season_tables) > 1:
                    combined = pd.concat(
                        {s: d for s, d in season_tables},
                        names=["Season", "Category", "statistics"]
                    )
                    st.markdown("### 📊 Combined view — all seasons")
                    st.dataframe(combined, use_container_width=True)

            # Download CSV
            if csv_path is not None and os.path.exists(csv_path):
                with open(csv_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=f,
                        file_name=os.path.basename(csv_path),
                        mime="text/csv"
                    )
            
with tab_compare:
    st.header("🥊 Compare Players")
    with st.form("compare_form"):
        players_names = st.text_area("Player names", 
                                     placeholder="Ex: Lamine Yamal, Nico Williams", help="Enter two player names separated by commas.")
        season_compare = st.text_input("Season", placeholder="(ex: YYYY-YYYY or YYYY or 'All' )")
        comp_compare = st.selectbox(
            "Competition",
            ["Select a competition...", "all competitions", "domestic leagues", "domestic cups",
             "international cups", "national team"],
            index=0
        )
        st.write("")
        col_left, col_button = st.columns([13.5, 1])
        with col_button:
            compare_submitted = st.form_submit_button("Submit")
        
    if compare_submitted:
        player_list = [p.strip() for p in players_names.split(",") if p.strip()]
        if len(player_list) < 2:
            st.warning("⚠️ Please enter two player names separated by commas.")
            st.stop()
        if len(player_list) > 2:
            st.warning("⚠️ Please enter only two player names for comparison.")
            st.stop()
        if season_compare.strip() == "":
            st.warning("⚠️ Please enter a season.")
            st.stop()
        if comp_compare == "Select a competition...":
            st.warning("⚠️ Please select a competition.")
            st.stop()

        all_stats = []
        for name in player_list:
            with st.spinner(f"⚙️ Data Extraction..."):
                try:
                    results = fbref_search(name)
                    _, chosen = results["players"][0]
                    comp_key = comp_map[comp_compare]
                    comp_url, table_id = get_competition_url_and_table_id(chosen, comp_key)
                    code_comp, html_comp = fetch_page(comp_url)
                    stats = extract_player_stats_by_competition(
                        html_comp, table_id, season=season_compare
                    )
                    core_stats = extract_core_stats(stats, name)
                    all_stats.append(core_stats)
                except Exception as e:
                    st.error(f"Error processing {name}: {e}")
                    st.stop()
            
        # Affichage graphique
        if len(all_stats) >= 2:
            st.subheader("📊 Player Comparison")
            fig = compare_players_chart(all_stats, season_compare, comp_compare)
            st.plotly_chart(fig, use_container_width=True)