import sys
import argparse 
from scraper import *

def main():
    parser = argparse.ArgumentParser(description="Scraper FBref ")
    parser.add_argument("nom_joueur", type=str, nargs="+", help="Nom du joueur dont on veut les informations")
    parser.add_argument("--season", type=str, default= None, help="Saison du joueur à analyser (ex: '2023-2024') ")
    args = parser.parse_args()

    name = " ".join(args.nom_joueur).strip()
    season_args = args.season
    print(f"Recherche pour : {name}")

    try:
        results = fbref_search(name)
    except ValueError as ve:
        # fbref_search lève ValueError quand la requête ne correspond pas à un joueur
        print("Recherche refusée :", ve)
        sys.exit(2)
    except Exception as e:
        print("Erreur pendant la recherche :", e)
        sys.exit(2)

    # choisir le premier résultat de joueur
    if results.get("players"):
        _ , chosen = results["players"][0]
        # afficher l'URL trouvée et le nom du joueur
        print(f"URL trouvée : {chosen}")
        
        # Mode stats saison
        if season_args:
            player_url = chosen
            # Générer l'URL All Competitions
            all_comps_url = get_all_comps_url(player_url)
            # print(f"URL All Competitions : {all_comps_url}")
            try:
                code_all_comps, html_all_comps = fetch_page(all_comps_url)
                print(f"Requête HTTP : {code_all_comps}")
            except Exception as e:
                print("Erreur pendant le téléchargement de la page :", e)
                sys.exit(3)
            
            if season_args.lower() == "all":
                # Récupérer toutes les saisons
                season_stats = extract_player_season_stats_all_comps(html_all_comps, season=None)
            else:
                # Récupérer uniquement la saison spécifique
                season_stats = extract_player_season_stats_all_comps(html_all_comps, season=season_args)

            save_season_stats_to_csv(season_stats, player_name=name, season=season_args)
            sys.exit(0)
        
        # Mode passeport joueur (pas de saison spécifiée)
        try:
            code, html = fetch_page(chosen)
            print(f"Requête HTTP : {code}")
        except Exception as e:
            print("Erreur pendant le téléchargement de la page :", e)
            sys.exit(3)
        # Extraire les infos du joueur
        player_info = extract_player_info(html, chosen, name)
        # Générer le passeport du joueur en HTML
        generate_player_passeport(player_info)
        
    else:
        print("Aucun résultat trouvé sur FBref.")
        sys.exit(0)
        
if __name__ == "__main__":
    main()

