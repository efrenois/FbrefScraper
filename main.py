import argparse
import sys
from scraper import *
from bs4 import BeautifulSoup



def main():
    if len(sys.argv) < 2:
        print("Usage: python3 main.py \"Nom du joueur ou de l'équipe\"")
        sys.exit(1)

    name = " ".join(sys.argv[1:]).strip()
    print(f"Recherche pour : {name}")

    try:
        results = fbref_search(name)
    except Exception as e:
        print("Erreur pendant la recherche :", e)
        sys.exit(2)

    # Priorité : joueur si trouvé, sinon équipe, sinon comps
    chosen = None
    if results["players"]:
        chosen = results["players"][0][1]
    elif results["teams"]:
        chosen = results["teams"][0][1]
    elif results["comps"]:
        chosen = results["comps"][0][1]
    else:
        print("Aucun résultat trouvé sur FBref.")
        sys.exit(0)

    try:
        code, _ = fetch_page(chosen)
    except Exception as e:
        print("Erreur pendant le téléchargement de la page :", e)
        sys.exit(3)

    print(f'Requête HTTP : {code}')


if __name__ == "__main__":
    main()

    