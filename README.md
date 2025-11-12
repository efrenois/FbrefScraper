# FBref Scraper

Voici un scraper Python permettant de récupérer les informations et statistiques détaillées des joueurs depuis [FBref.com](https://fbref.com)￼.
Le projet permet de générer le passeport d’un joueur (téléchargeable en pdf) au format HTML ou d’extraire ses statistiques par saison et compétition au format CSV.

## Table des matières
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Options de ligne de commande](#options-de-ligne-de-commande)
- [Structure du projet](#structure-du-projet)
- [Limitation](#limitation)

## Fonctionnalités
- Récupération automatique des informations d’un joueur : nom, photo, position, pied fort, date de naissance, club, équipe nationale, salaire.
- Génération d’un passeport joueur avec toute ses informations au format HTML et passeport téléchargeable au format PDF.
- Extraction des statistiques détaillées du joueur par saison et compétition au format CSV.

## Prérequis
```bash
requirements.txt
```
## Installation
1. Cloner le dépôt GitHub :
```bash
git clone "repo_url"
```
2. Créer un environnement virtuel (optionnel mais recommandé) :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
```
3. Installer les dépendances :
```bash
pip install -r requirements.txt
```   

## Utilisation

1. Générer le passeport de Neymar Jr:
```bash
python main.py 'Neymar' 
```
Cette commande génère le passeport de Neymar Jr au format HTML et PDF dans le dossier `output/passport_player`.
Ouvrez le fichier HTML dans votre navigateur pour visualiser le passeport de Neymar Jr téléchargeable au format PDF.

Voici un exemple du HTML généré: 
<img width="1582" height="973" alt="ex_HTML_Neymar" src="https://github.com/user-attachments/assets/b2d84116-2830-467f-8866-847795a6543d" />

2. Extraire les statistiques de Neymar Jr sur la saison 2014-2015 en Ligue des champions:
```bash
python main.py 'Neymar' --season '2014-2015' --comp 'ic'
```
Cette commande extrait les statistiques de Neymar Jr pour la saison 2014-2015 en Ligue des champions et les enregistre au format CSV dans le dossier `output/datas_player`.

<img width="1116" height="691" alt="Capture d’écran 2025-11-12 à 14 51 05" src="https://github.com/user-attachments/assets/85007173-14c9-4e89-b110-b7790cd9bf57" />

## Options de ligne de commande

- `player_name` : Nom du joueur dont vous souhaitez récupérer les informations (obligatoire).
- `--season` : Saison du joueur à analyser (exemple : `2014-2015`). Utilisez `all` ou `All` pour toutes les saisons.
- `--comp` : Compétition à analyser. Options disponibles :
    - `all` : Toutes les compétitions.
    - `dl` : Ligues domestiques.
    - `dc` : Coupes domestiques.
    - `ic` : Coupes internationales.
    - `nt` : Équipe nationale.

## Structure du projet
```bash
FbrefScrapper/
├── main.py                         # Script principal pour exécuter le scraper
├── output                          # Dossier de sortie pour les passeports et données
├── README.md                       # Documentation du projet 
├── requirements.txt                # Fichier des dépendances Python
├── scraper.py                      # Module de scraping FBref
├── templates                       # Modèles HTML pour le passeport joueur    
│   └── passport_template.html
```
## Limitation
•	Dépend du format des pages FBref. Les changements sur le site peuvent casser le scraper.
