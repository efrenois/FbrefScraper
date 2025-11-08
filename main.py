import sys
import argparse 
from scraper import *

def main():
    parser = argparse.ArgumentParser(description="Scraper FBref ")
    parser.add_argument("nom_joueur", type=str, nargs="+", help="Nom du joueur dont on veut les informations")
    args = parser.parse_args()

    name = " ".join(args.nom_joueur).strip()
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
        try:
            code, html = fetch_page(chosen)
            print(f"Requête HTTP : {code}")
        except Exception as e:
            print("Erreur pendant le téléchargement de la page :", e)
            sys.exit(3)

        # Extraire les infos du joueur
        player_info = extract_player_info(html, chosen, name)

        # Générer le passeport du joueur en HTML
        output_html = generate_player_passeport(player_info)
        
    
    else:
        print("Aucun résultat trouvé sur FBref.")
        sys.exit(0)


if __name__ == "__main__":
    main()

