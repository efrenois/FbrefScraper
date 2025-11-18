import sys
import argparse 
from scraper import *

def main():
    
    parser = argparse.ArgumentParser(description="Scraper FBref ")
    parser.add_argument("player_name", type=str, nargs="+", help="Name of the player whose information you want")
    parser.add_argument("--comp", type=str, default=None, choices=["all", "dl", "dc", "ic", "nt"], 
                        help="Competitions : all (all competitions), dl (domestic leagues), dc (domestic cups), ic (international cups), nt (national team)")
    parser.add_argument("--season", type=str, default=None, help="Player season to be analyzed (e.g., '2014-2015'). Use 'all' for all seasons.")
    parser.add_argument("--type", type=str, default=None, choices=["standard", "shooting", "passing", "pass_types", "da", "g&s"], help="Type of statistics to extract"
)
    args = parser.parse_args()
    

    names = args.player_name
    season_args = args.season
    comp_args = args.comp 
    types_args = args.type
    
    # Check of argument consistency
    if (season_args and not (comp_args and types_args)) or (comp_args and not (season_args and types_args)) or (types_args and not (season_args and comp_args)):
        print("⚠️ If you use the --season parameter, you must specify a value for the --comp and the --type parameters , and vice versa.")
        print("Example of a valid command: python3 main.py 'Lionel Messi' --season '2014-2015' --comp 'dl' --type 'standard'")
        sys.exit(1)

    print(f"🔍 Searching for : {names}")

    if len(names) == 1:
        try:
            name = " ".join(names).strip()
            results = fbref_search(name)
        except ValueError as ve:
            print("❌ Search declined :", ve)
            sys.exit(2)
        except Exception as e:
            print("❌ Error during search :", e)
            sys.exit(2)

        if results.get("players"):
            _, chosen = results["players"][0]
            print(f"✅ URL found : {chosen}")
            # Passport
            if not season_args and not comp_args:
                try:
                    _, html = fetch_page(chosen)
                except Exception as e:
                    print("❌ Error while downloading the page :", e)
                    sys.exit(3)

                player_info = extract_player_info(html, chosen, name)
                generate_player_passeport(player_info)
                sys.exit(0)

            # Stats by competition and season
            player_url = chosen
            try:
                # Generate the URL and ID of the HTML table according to the selected competition.
                comp_url, _ = get_competition_url_and_table_id(player_url, comp=comp_args)
                print(f"✅ URL found : {comp_url}")
                
                # Determine which table ID to extract (standard, shooting, passing, etc.)
                table_id = get_table_id_for_type(types_args, comp_args)
            

            except Exception as e:
                print("❌ Error generating URL  :", e)
                sys.exit(4)

            try:
                _, html_comp = fetch_page(comp_url)
            except Exception as e:
                print("❌ Error while downloading the competition page :", e)
                sys.exit(3)

            # Extract statistics by season
            season_param = season_args
            stats = extract_player_stats_by_competition(html_comp, table_id, season=season_param)

            # Save as CSV
            save_season_stats_to_csv(stats, player_name=name, season=season_args, comp=comp_args, type=types_args)
            sys.exit(0) 
            
    elif len(names) == 2:
        player_stats_list = []

        for name in names:
            name = name.strip()
            print(f"⚙️ Extraction for {name}...")
            try:
                results = fbref_search(name)
                if not results.get("players"):
                    print(f"⚠️ No results found for {name}")
                    continue
            except ValueError as ve:
                print(f"❌ Search declined for {name} :", ve)
                sys.exit(2)
            except Exception as e:
                print(f"❌ Error during search for {name} :", e)
                sys.exit(2)
            
            _, chosen = results["players"][0]
            comp_url, _ = get_competition_url_and_table_id(chosen, comp=comp_args)
            table_id = get_table_id_for_type(types_args, comp_args)
            _, html_comp = fetch_page(comp_url)
            season_param = season_args
            stats = extract_player_stats_by_competition(html_comp, table_id, season=season_param)

            core_stats = extract_core_stats(stats, name)
            player_stats_list.append(core_stats)

        if len(player_stats_list) < 2:
            print("⚠️ Cannot compare: only one valid player found.")
            sys.exit(0)

        print("\n📊 Generation of the comparative graph...")
        fig = compare_players_chart(player_stats_list, season_args, comp_args, types_args)   
        if fig is None:
            print("⚠️ Comparison could not be generated due to lack of common statistics.")
            sys.exit(0)  
        fig.show()
        
    elif len(names) > 2:
        print("⚠️ Comparison of more than two players is not supported.")
        sys.exit(0)
    else:
        print("⚠️ No results found on FBref.")
        sys.exit(0) 
        
if __name__ == "__main__":
    main()

