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

# Type of statistics mapping
type_map = {
    "standard statistics": "standard", 
    "shooting statistics": "shooting",
    "passing statistics": "passing",
    "pass types statistics": "pass_types",
    "defense actions statistics": "da",
    "goal & shot creation statistics": "g&s"
}

st.set_page_config(page_title="FBref Scraper", page_icon="⚽", layout="wide")

# Custom CSS for buttons in forms
st.markdown("""
<style>
div[data-testid="stForm"] button {
    border: 2px solid #FF7F50 !important;  
    background-color: transparent !important; 
    color: inherit !important;            
    transition: background-color 0.3s ease;
    cursor: pointer;
}

div[data-testid="stForm"] button:hover {
    background-color: #FF4500 !important;
}
</style>
""", unsafe_allow_html=True)

st.title("⚽ Welcome on FBref Scraper !")
st.write("")

tab_passport, tab_single_player_analysis, tab_compare = st.tabs(["Passport Player", "Single Player Analysis", "Player Comparison"])

with tab_passport:
    st.header("Player Passport")

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
    st.header("Single Player Analysis")
    with st.form("analysis_form"):
        name_single = st.text_input("Player name", placeholder="Ex: Lamine Yamal")
        season_single = st.text_input("Season", placeholder="(ex: YYYY-YYYY or YYYY or 'All' )")
        comp_single = st.selectbox(
            "Competition",
            ["Select a competition...","all competitions", "domestic leagues", "domestic cups",
             "international cups", "national team"],
            index=0
        )
        stats_type_single = st.selectbox(
        "Type of Statistics",
        ["Select a type of statistics...", "standard statistics", "shooting statistics", "passing statistics",
         "pass types statistics", "defense actions statistics", "goal & shot creation statistics"],
        index=0,
        help="Select which type of statistics to extract"
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
        if comp_single == "Select a competition...":
            st.warning("⚠️ Please select a competition.")
            st.stop()
        if stats_type_single.strip() == "Select a type of statistics...":
            st.warning("⚠️ Please select a type of statistics.")
            st.stop()

        # Player search

        with st.spinner("📊 Data extraction..."):
            try:
                results = fbref_search(name_single)
                _, chosen = results["players"][0]
                comp_key = comp_map[comp_single]
                type_key = type_map[stats_type_single]

                table_id = get_table_id_for_type(type_key, comp_key)
                comp_url, _ = get_competition_url_and_table_id(chosen, comp_key)
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
            csv_path = save_season_stats_to_csv(stats, player_name=name_single, season=season_single, comp=comp_single, type=type_key)

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
    st.header("Player Comparison")

    with st.form("compare_form"):
        players_names = st.text_input("Player names", 
                                     placeholder="Ex: Lamine Yamal, Nico Williams", help="Enter two player names separated by commas.")
        season_compare = st.text_input("Season", placeholder="(ex: YYYY-YYYY or YYYY or 'All' )")
        comp_compare = st.selectbox(
            "Competition",
            ["Select a competition...", "all competitions", "domestic leagues", "domestic cups",
             "international cups", "national team"],
            index=0
        )
        stats_type_compare = st.selectbox(
        "Type of Statistics",
        [ "Select a type of statistics...", "standard statistics", "shooting statistics", "passing statistics",
         "pass types statistics", "defense actions statistics", "goal & shot creation statistics"],
        index=0,
        help="Select which type of statistics to extract"
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
        if stats_type_compare.strip() == "Select a type of statistics...":
            st.warning("⚠️ Please select a type of statistics.")
            st.stop()

        all_stats = []
        
        for name in player_list:
            with st.spinner(f"⚙️ Data Extraction..."):
                try:
                    results = fbref_search(name)
                    _, chosen = results["players"][0]
                    comp_key = comp_map[comp_compare]
                    type_key = type_map[stats_type_compare]
                    comp_url, _ = get_competition_url_and_table_id(chosen, comp_key)
                    code_comp, html_comp = fetch_page(comp_url)

                    table_id = get_table_id_for_type(type_key, comp_key)

                    stats = extract_player_stats_by_competition(
                        html_comp, table_id, season=season_compare
                    )
                    
                    core_stats = extract_core_stats(stats, name)
                    all_stats.append(core_stats)
                except Exception as e:
                    st.error(f"Error processing {name}: {e}")
                    st.stop()
                    
        st.session_state["compare_stats"] = all_stats
        st.session_state["compare_season"] = season_compare
        st.session_state["compare_comp"] = comp_key
        st.session_state["compare_type"] = type_key
                
            
    if "compare_stats" in st.session_state:

        st.subheader("📊 Player Comparison")

        chart_type = st.radio(
            "",
            ["Bar Chart", "Radar Chart"],
            horizontal=True
        )

        stats_list = st.session_state["compare_stats"]
        season_val = st.session_state["compare_season"]
        comp_val = st.session_state["compare_comp"]
        type_val = st.session_state["compare_type"]

        # Génération du graphique choisi
        if chart_type == "Bar Chart":
            fig = compare_players_chart(stats_list, season_val, comp_val, type_val)
        else:
            fig = compare_players_radar_chart(stats_list, season_val, comp_val, type_val)

        if fig is None:
            st.warning("⚠️ No common statistics to compare between the players.")
        else:
            st.plotly_chart(fig)

# Footer
st.markdown(
    """
    <style>
    .footer {
        bottom: 0;
        left: 0;
        width: 100%;
        color: gray;
        text-align: center;
        font-size: 12px;
        padding: 10px 0;
        z-index: 0;
    }
    </style>

    <div class="footer">
        © 2025 FBref Scraper. All rights reserved.
    </div>
    """,
    unsafe_allow_html=True
)