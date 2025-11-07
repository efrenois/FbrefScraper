import sys
import argparse 
import os
from scraper import fbref_search, fetch_page,extract_player_info
from jinja2 import Template

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
        print("Infos du joueur extraites :", player_info)
        if not player_info:
            print("Impossible d'extraire les informations du joueur.")
            sys.exit(4)
        
        # Générer le passeport du joueur en HTML
        template_path = os.path.join("templates", "passeport_template.html")
        output_html = os.path.join("output", f"passeport_{name}.html")
        
        with open(template_path, "r", encoding="utf-8") as f:
            template_str = f.read()

        template = Template(template_str)
        html_content = template.render(**player_info)
        
        os.makedirs("output", exist_ok=True)
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"✅ HTML généré : {output_html}")
        
    else:
        print("Aucun résultat trouvé sur FBref.")
        sys.exit(0)


if __name__ == "__main__":
    main()

