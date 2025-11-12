import sys
import argparse 
from scraper import *

def main():
    parser = argparse.ArgumentParser(description="Scraper FBref ")
    parser.add_argument("player_name", type=str, nargs="+", help="Name of the player whose information you want")
    parser.add_argument("--comp", type=str, default=None, choices=["all", "dl", "dc", "ic", "nt"],
                    help="Competitions : all (all competitions), dl (domestic leagues), dc (domestic cups), ic (international cups), nt (national team)")
    parser.add_argument("--season", type=str, default= None, help="Player season to be analyzed (e.g., '2014-2015'). Use 'all' for all seasons.")
    args = parser.parse_args()
    

    name = " ".join(args.player_name).strip()
    season_args = args.season
    comp_args = args.comp 
    
    # Check of argument consistency
    if (season_args and not comp_args) or (comp_args and not season_args):
        print("⚠️ If you use the --season parameter, you must specify a value for the --comp parameter, and vice versa.")
        print("Example of a valid command: python3 main.py 'Lionel Messi' --season '2014-2015' --comp 'dl'")
        sys.exit(1)

    print(f"⚙️ Searching for : {name}")

    try:
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
            comp_url, table_id = get_competition_url_and_table_id(player_url, comp=comp_args)
        except Exception as e:
            print("❌ Error generating URL  :", e)
            sys.exit(4)

        try:
            _, html_comp = fetch_page(comp_url)
        except Exception as e:
            print("❌ Error while downloading the competition page :", e)
            sys.exit(3)

        # Extract statistics by season
        season_param = None if (season_args is None or season_args.lower() == "all") else season_args
        stats = extract_player_stats_by_competition(html_comp, table_id, season=season_param)

        # Save as CSV
        save_season_stats_to_csv(stats, player_name=name, season=season_args, comp=comp_args)
        sys.exit(0)

    else:
        print("⚠️ No results found on FBref.")
        sys.exit(0)
        
if __name__ == "__main__":
    main()

