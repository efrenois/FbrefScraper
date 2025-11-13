import streamlit as st
import pandas as pd
from scraper import *
import os

st.set_page_config(page_title="FBref Scraper", page_icon="⚽", layout="wide")

st.title("⚽ FBref Scraper — Player analysis")

tab1, tab2 = st.tabs(["Single Player Analysis", "Compare Players"])

with tab1:
    st.header("🔍 Single Player Analysis")
    # Form
    with st.form("scraper_form"):
        name = st.text_input("Player name", placeholder="Ex: Lamine Yamal")
        comp = st.selectbox(
            "Competition",
            ["all (all competitions)", "dl (domestic leagues)", "dc (domestic cups)", "ic (international cups)", "nt (national team)"],
            index=0,
            help="Choose the competition : all (all competitions), dl (domestic leagues), dc (domestic cups), ic (international cups), nt (national team)"
        )
        season = st.text_input("Season (ex: YYYY-YYYY or YYYY or 'All' )", value="All")

        submitted = st.form_submit_button("🚀 Launch the Scraper")

    if submitted:
        if not name.strip():
            st.warning("⚠️ Please enter a player name.")
            st.stop()

        with st.spinner(f"Search for player {name} on FBref..."):
            try:
                results = fbref_search(name)
            except Exception as e:
                st.error(f"Error during search : {e}")
                st.stop()

        if results.get("players"):
            _, chosen = results["players"][0]
            st.success(f"✅ Player found : {name}")

            # Passport extraction 
            with st.spinner("📄 Extracting player information..."):
                code, html = fetch_page(chosen)
                player_info = extract_player_info(html, chosen, name)
                passeport_html, passeport_path = generate_player_passeport(player_info)

            st.subheader("🪪 Player passport")

            st.components.v1.html(passeport_html, height=600, scrolling=True)

            # Stats exctraction 
            with st.spinner("📊 Data extraction..."):
                try:
                    comp_key = comp.split(" ")[0].strip()  
                    comp_url, table_id = get_competition_url_and_table_id(chosen, comp_key)
                    code_comp, html_comp = fetch_page(comp_url)
                    stats = extract_player_stats_by_competition(
                        html_comp, table_id, season=None if season.lower() == "all" else season
                    )
                except Exception as e:
                    st.error(f"Error extracting statistics : {e}")
                    st.stop()

            # Save CSV 
            csv_path = save_season_stats_to_csv(stats, player_name=name, season=season, comp=comp)
            st.success("✅ Data successfully extracted.")
            
            # Display stats

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
            if os.path.exists(csv_path):
                with open(csv_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=f,
                        file_name=os.path.basename(csv_path),
                        mime="text/csv"
                    )
        else:
            st.error("Aucun joueur trouvé sur FBref.")
            
with tab2:
    st.header("⚔️ Compare Players")
    with st.form("compare_form"):
        players_names = st.text_area("Player names (comma separated)", 
                                     placeholder="Ex: Lamine Yamal, Nico Williams")
        comp_compare = st.selectbox(
            "Competition",
            ["all (all competitions)", "dl (domestic leagues)", "dc (domestic cups)",
             "ic (international cups)", "nt (national team)"],
            index=0
        )
        season_compare = st.text_input("Season (ex: YYYY-YYYY or YYYY)", value="2023-2024")
        compare_submitted = st.form_submit_button("🚀 Compare Players")
        
    if compare_submitted:
        player_list = [p.strip() for p in players_names.split(",") if p.strip()]
        if len(player_list) < 2:
            st.warning("⚠️ Please enter at least two player names separated by commas.")
            st.stop()

        all_stats = []
        for name in player_list:
            with st.spinner(f"Data..."):
                try:
                    results = fbref_search(name)
                    _, chosen = results["players"][0]
                    comp_key = comp_compare.split(" ")[0].strip()
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