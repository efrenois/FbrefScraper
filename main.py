import sys
from scraper import fbref_search, fetch_page


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 main.py "Nom du joueur ou de l\'équipe"')
        sys.exit(1)

    name = " ".join(sys.argv[1:]).strip()
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
            code, _ = fetch_page(chosen)
            print(f"Requête HTTP : {code}")
        except Exception as e:
            print("Erreur pendant le téléchargement de la page :", e)
            sys.exit(3)
    else:
        print("Aucun résultat trouvé sur FBref.")
        sys.exit(0)

if __name__ == "__main__":
    main()

