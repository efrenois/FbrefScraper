import sys
from scraper import fbref_search, fetch_page,extract_player_info, create_player_passport_image
import argparse 


def main():
    parser = argparse.ArgumentParser(description="Scraper FBref minimal")
    parser.add_argument("query", type=str, nargs="+", help="Nom du joueur (ou club si vous gérez) — on suppose ici joueur")
    parser.add_argument("--season", type=str, help="Saison à récupérer, ex: '2024-2025'")
    args = parser.parse_args()

    name = " ".join(args.query).strip()
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
        print("Infos du joueur extraites :", player_info)
        if not player_info:
            print("Impossible d'extraire les informations du joueur.")
            sys.exit(4)

        # Créer le fichier pour le fichier de sortie pour le passeport
        # safe_name = player_info.get("name", name).replace(" ", "_")
        # output_file = f"passeport_{safe_name}.png"

        # Générer l'image du passeport
        # create_player_passport_image(player_info, output_file)

        # print(f"\n✅ Passeport généré avec succès : {output_file}\n")

    else:
        print("Aucun résultat trouvé sur FBref.")
        sys.exit(0)


if __name__ == "__main__":
    main()

