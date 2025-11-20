# FBref Scraper

Voici un scraper Python permettant de récupérer les informations et statistiques détaillées des joueurs depuis [FBref.com](https://fbref.com).  
Le projet permet de générer le passeport d’un joueur (téléchargeable en pdf) au format HTML ou d’extraire ses statistiques par saison et compétition au format CSV.  
De plus, il est possible de comparer les performances de deux joueurs sur une saison et une compétition données.  
Enfin, cet outil peut être utilisé en ligne de commande ou via une interface graphique Streamlit pour faciliter son utilisation.

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
- Comparaison des performances entre deux joueurs et visualisation via bar chart et radar chart.

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

Tout d'abord, cet outil peut être utilisé via une interface graphique Streamlit ou en ligne de commande.

### Ligne de commande
1. Générer le passeport de Neymar Jr:
```bash
python main.py 'Neymar' 
```
Cette commande génère le passeport de Neymar Jr au format HTML et PDF dans le dossier `output/passport_player`.
Ouvrez le fichier HTML dans votre navigateur pour visualiser le passeport de Neymar Jr téléchargeable au format PDF.

Voici un exemple du HTML généré: 
<img width="1582" height="973" alt="ex_HTML_Neymar" src="https://github.com/user-attachments/assets/b2d84116-2830-467f-8866-847795a6543d" />

2. Extraire les statistiques de tirs de Neymar Jr sur la saison 2017-2018 en Ligue des champions:
```bash
python main.py 'Neymar' --season '2017-2018' --comp 'ic' --type 'shooting'
```
Cette commande extrait les statistiques de Neymar Jr pour la saison 2017-2018 en Ligue des champions et les enregistre au format CSV dans le dossier `output/datas_player`.

<img width="1036" height="516" alt="Capture d’écran 2025-11-18 à 16 14 35" src="https://github.com/user-attachments/assets/61b8a0cc-d933-48cd-960c-eebf431f7fe2" />

3. Comparer les statistiques standards de Neymar Jr et Kylian Mbappé sur la saison 2022-2023 en Ligue 1:
```bash
python main.py 'Neymar' 'Kylian Mbappé' --season '2022-2023' --comp 'dl' --type 'standard'
```
Cette commande compare les performances de Neymar Jr et Kylian Mbappé pour la saison 2022-2023 en Ligue 1 et affiche un graphique comparatif.
<img width="1582" height="973" alt="Capture d’écran 2025-11-20 à 15 56 02" src="https://github.com/user-attachments/assets/8e1467d1-cd2a-44f5-a2a7-2140f2fc9881" />


### Options de la ligne de commande

- `player_name` : Nom du joueur dont vous souhaitez récupérer les informations (obligatoire).
- `--season` : Saison du joueur à analyser (exemple : `2014-2015`). Utilisez `all` ou `All` pour toutes les saisons.
- `--comp` : Compétition à analyser. Options disponibles :
    - `all` : Toutes les compétitions.
    - `dl` : Ligues domestiques.
    - `dc` : Coupes domestiques.
    - `ic` : Coupes internationales.
    - `nt` : Équipe nationale.
- `--type` : Type de statistiques à extraire. Options disponibles :
    - `standard` : Statistiques standard.
    - `shooting` : Statistiques de tir.
    - `passing` : Statistiques de passe.
    - `pass_types` : Types de passes.
    - `da` : Actions défensives.
    - `g&s` : Création de buts et tirs. 

### Interface graphique Streamlit
Lancez l'interface Streamlit avec la commande suivante :
```bash
streamlit run gui_streamlit.py
```
Cela ouvrira une interface web où vous pourrez jouer avec les fonctionnalités du scraper de manière interactive.
<img width="1582" height="973" alt="Capture d’écran 2025-11-14 à 16 06 28" src="https://github.com/user-attachments/assets/2ec6bbd1-17ac-49ef-a2f2-884093412aee" />

La seule différence avec la ligne de commande est que lorsque vous comparez deux joueurs, les statistiques comparées peuvent être visualisées sous forme de bar chart ou de radar chart alors qu'en ligne de commande, seul le bar chart est disponible.

https://github.com/user-attachments/assets/82091d62-dc13-4745-8c70-5abc3d6defcb

## Structure du projet
```bash
FbrefScrapper/
├── main.py                         # Script principal pour exécuter le scraper
├── output/                         # Dossier de sortie pour les passeports et données générées
├── README.md                       # Documentation du projet 
├── requirements.txt                # Fichier des dépendances Python
├── scraper.py                      # Module principal du scraper  
├── gui_streamlit.py                # Interface utilisateur Streamlit
├── templates/                      # Dossier des modèles HTML
│   └── passport_template.html      # Modèles HTML pour le passeport joueur 
```
## Limitation
•	Dépend du format des pages FBref. Les changements sur le site peuvent casser le scraper.
