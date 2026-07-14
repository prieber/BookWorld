# BookWorld

*[English version](README.md)*

Projet de pipeline de données pour BookWorld, une entreprise fictive de
vente de livres en ligne. Collecte les données de ventes depuis plusieurs
sources (CSV, SQLite, scraping web, API de taux de change), les nettoie
et les agrège en indicateurs de ventes par pays, stocke le résultat dans
une base SQLite finale, et l'expose via une API REST.

Ce projet est le projet de certification RNCP du programme DataBird DAPT.

## Démarrage rapide

Étapes à suivre dans l'ordre pour passer d'une installation vierge à l'API en fonctionnement. Le détail de chaque étape est repris dans les sections dédiées ci-dessous.

**0. Prérequis**
- [Python 3.10+](https://www.python.org/downloads/) installé et accessible via `python --version` dans un terminal
- [Git](https://git-scm.com/downloads) installé et accessible via `git --version`

**1. Cloner le repo**
```bash
git clone https://github.com/prieber/Bookworld.git
cd Bookworld
```
`data/sales_raw.csv` et `data/bookworld_reference.db` sont inclus dans le repo — rien à télécharger séparément.

**2. Créer et activer un environnement virtuel** *(recommandé, voir "Installer les dépendances" plus bas)*
```bash
python -m venv venv
```
```bash
# Windows (invite de commandes)
venv\Scripts\activate
```
```bash
# Windows (Git Bash) / Mac / Linux
source venv/bin/activate
```

**3. Installer les dépendances**
```bash
pip install -r requirements.txt
```

**4. Configurer le token de l'API**
```bash
# Windows (invite de commandes)
copy .env.example .env
```
```bash
# Windows (Git Bash) / Mac / Linux
cp .env.example .env
```
Ouvrir le fichier `.env` créé et remplacer la valeur de `BOOKWORLD_API_TOKEN` par le token souhaité.

**5. Lancer le pipeline** *(nécessite une connexion internet, voir "Exécuter le pipeline" plus bas)*
```bash
python pipeline.py
```

**6. Lancer l'API**
```bash
python api.py
```
L'API est alors accessible sur `http://127.0.0.1:5000`. Tester avec `http://127.0.0.1:5000/health` dans un navigateur : la réponse attendue est `{"status": "ok"}`.

## Structure du projet

| Fichier / dossier | Description |
|---|---|
| `pipeline.py` | Pipeline de données principal : `extract()`, `transform()`, `load()`, orchestrés par `main()` |
| `schema_final.sql` | Schéma de la base finale (7 tables, table `sales` conforme RGPD) |
| `api.py` | API REST exposant les données agrégées finales (`sales_by_country`) |
| `requirements.txt` | Dépendances Python |
| `.env.example` | Modèle de configuration du token API (à copier en `.env`) |
| `LICENSE` | Licence MIT du projet |
| `data/sales_raw.csv` | Ventes brutes (fichier source, fourni) |
| `data/bookworld_reference.db` | Base SQLite de référentiels : `countries`, `channels`, `category_rules` (fichier source, fourni) |
| `output_pipeline/queries.sql` | Généré automatiquement par `pipeline.py` : version finale et lisible des requêtes SQL utilisées pour extraire les données de `bookworld_reference.db` |
| `output_pipeline/bookworld_final.db` | Généré automatiquement par `pipeline.py` : la base finale, alimentée par `load()` |

## Dataset

### `data/sales_raw.csv`
Ventes brutes, une ligne = une commande. 240 lignes, aucune valeur manquante, pas de doublon sur `order_id`, période du 2025-01-03 au 2025-06-29.

| Colonne | Type | Description |
|---|---|---|
| `order_id` | texte | Identifiant unique de la commande (ex : `ORD000001`) |
| `order_date` | date | Date de la commande (`YYYY-MM-DD`) |
| `book_id` | texte | Identifiant du livre vendu (ex : `BOOK00007`) — 20 livres distincts |
| `country_code` | texte | Code pays ISO à 2 lettres du client |
| `channel_code` | texte | Code du canal de vente (`WEB`, `APP`, `MKT`) |
| `quantity` | entier | Nombre d'exemplaires vendus (1 à 8) |
| `discount_rate` | décimal | Taux de remise appliqué (0.0 à 0.4) |
| `customer_first_name` | texte | Prénom du client |
| `customer_last_name` | texte | Nom du client |
| `book_name` | texte | Titre du livre (relié au catalogue scrapé sur books.toscrape.com) |

### `data/bookworld_reference.db`
Base SQLite de référentiels, 3 tables :

**`countries`** (10 lignes)

| Colonne | Type | Description |
|---|---|---|
| `country_code` | texte (clé) | Code pays ISO à 2 lettres |
| `country_name` | texte | Nom du pays |
| `currency_code` | texte | Devise (`EUR`, `GBP`, `USD`, `CAD`) |
| `vat_rate` | décimal | Taux de TVA (%) |
| `region` | texte | Zone géographique (`Europe`, `North America`) |
| `is_active` | 0/1 | Pays actif — `PT` et `CA` sont inactifs |

**`channels`** (4 lignes)

| Colonne | Type | Description |
|---|---|---|
| `channel_code` | texte (clé) | Code du canal |
| `channel_name` | texte | Nom du canal |
| `acquisition_cost_gbp` | décimal | Coût d'acquisition par vente (£) |
| `channel_group` | texte | `Owned` ou `Partner` |
| `is_active` | 0/1 | Canal actif — `AFF` est inactif |

**`category_rules`** (10 lignes)

| Colonne | Type | Description |
|---|---|---|
| `category_name` | texte (clé) | Nom de la catégorie de livre |
| `margin_rate` | décimal | Taux de marge appliqué |
| `strategic_flag` | 0/1 | Catégorie jugée stratégique |
| `default_channel_code` | texte | Canal de vente par défaut associé |
| `is_active` | 0/1 | Catégorie active — `Horror` est inactive |

### Catalogue scrapé (books.toscrape.com)
Scraping de la 1ère page uniquement (~20 livres). Pour chaque livre, `extract()` visite la page catalogue puis la page détail, et en extrait :

| Champ | Type | Description |
|---|---|---|
| `book_name` | texte | Titre du livre — sert de clé de jointure avec `book_name` dans `sales_raw.csv` |
| `price_gbp` | décimal | Prix affiché (`price_color`), converti en nombre (symbole `£` retiré) |
| `book_url` | texte | URL absolue de la page détail du livre |
| `category` | texte | Catégorie du livre, lue dans le fil d'Ariane (breadcrumb) |
| `upc` | texte | Code produit unique (Universal Product Code), depuis le tableau détail |
| `price_excl_tax` | texte | Prix hors taxe, tel qu'affiché sur le site (avec symbole `£`) |
| `price_incl_tax` | texte | Prix TTC, tel qu'affiché sur le site |
| `tax` | texte | Montant de la taxe, tel qu'affiché sur le site |
| `number_of_reviews` | texte | Nombre d'avis, tel qu'affiché sur le site |
| `availability` | texte | Texte de disponibilité (ex : `"In stock (22 available)"`) |
| `rating` | entier | Note du livre de 1 à 5, décodée depuis la classe CSS `star-rating` (`One` à `Five`) |

Un livre est ignoré (avec avertissement en console) si une erreur survient pendant son scraping — le pipeline continue avec les autres.

### API de taux de change (Frankfurter)
Appel à `GET https://api.frankfurter.dev/v2/rate/GBP/EUR` pour convertir le revenu total de GBP en EUR. Réponse JSON à plat :

| Champ | Type | Description |
|---|---|---|
| `date` | date | Date du taux de change retourné |
| `base` | texte | Devise de base (`GBP`) |
| `quote` | texte | Devise cible (`EUR`) |
| `rate` | décimal | Taux de conversion GBP → EUR utilisé pour calculer `total_revenue_eur` |

Aucune clé API n'est requise pour cet endpoint.

## Installer les dépendances

Ce projet utilise **Python 3.10 ou supérieur** (vérifier la version avec `python --version` et l'adapter si besoin).

*(Recommandé)* Créer et activer un environnement virtuel avant d'installer les dépendances, pour isoler les paquets de ce projet du reste du système :

```bash
python -m venv venv
source venv/bin/activate  # Windows : venv\Scripts\activate
```

Installer ensuite les dépendances :

```bash
pip install -r requirements.txt
```

**Paquets nécessaires** (contenu de `requirements.txt`) :

| Paquet | Utilisé pour |
|---|---|
| `pandas` | Manipulation des données : lecture du CSV, jointures, agrégations |
| `requests` | Appels HTTP — scraping de books.toscrape.com et appel à l'API de taux de change Frankfurter |
| `beautifulsoup4` | Parsing du HTML des pages scrapées (catalogue de livres) |
| `flask` | Framework de l'API REST (`api.py`) |
| `python-dotenv` | Lecture du token API depuis le fichier `.env` |

`sqlite3`, `os`, `textwrap` et `functools` font partie de la bibliothèque standard de Python — pas d'installation nécessaire pour ceux-là.

## Exécuter le pipeline

**Prérequis réseau.** `extract()` a besoin d'une connexion internet : il scrape `books.toscrape.com` et interroge l'API de taux de change Frankfurter. Sans connexion, le pipeline échoue dès cette étape.

```bash
python pipeline.py
```

Ceci exécute le pipeline complet, dans l'ordre :
- **`extract()`** — collecte les données depuis les 4 sources (CSV,
  SQLite, scraping de `books.toscrape.com`, API de taux de change
  Frankfurter), et génère `output_pipeline/queries.sql`.
- **`transform()`** — nettoie les données, signale les problèmes de
  qualité (voir plus bas), relie les ventes au catalogue scrapé, calcule
  le revenu par vente, et agrège le tout dans `sales_by_country`.
- **`load()`** — crée `output_pipeline/bookworld_final.db` à partir de
  `schema_final.sql` et y charge les 7 tables finales.

**Pourquoi la base est supprimée et recréée à chaque exécution.** `load()`
écrit chaque table avec `to_sql(..., if_exists="append")` plutôt que
`"replace"` : `"replace"` supprimerait la table et laisserait pandas la
recréer avec son propre schéma déduit automatiquement, perdant les
contraintes `PRIMARY KEY`/`FOREIGN KEY` définies dans `schema_final.sql`.
`"append"` seul insérerait dans la table déjà existante, mais dupliquerait
les lignes si le pipeline est exécuté plusieurs fois sans vider la base au
préalable. Pour obtenir à la fois les contraintes de `schema_final.sql`
*et* l'absence de doublons entre exécutions, `load()` supprime
`output_pipeline/bookworld_final.db` (s'il existe) avant de recréer le
schéma depuis zéro — chaque exécution repart donc d'une base propre et
correctement contrainte.

La console affiche des avertissements pour chaque problème de qualité de
données détecté (valeurs manquantes, doublons, ventes faisant référence à
des données de référence inactives ou absentes) — voir la section "Notes
sur la qualité des données" ci-dessous.

## Notes sur la qualité des données

Plusieurs incohérences entre les données de référence et les ventes
réelles sont détectées pendant `transform()`, et volontairement
**conservées** (pas supprimées silencieusement) plutôt qu'exclues — un
avertissement est affiché pour chacune, pour que le problème reste
visible :

- **Données de référence inactives mais vendues** : certaines lignes du
  référentiel sont marquées `is_active = 0` (ex : le Portugal dans
  `countries`, "Horror" dans `category_rules`), mais des ventes existent
  bien pour elles dans `sales_raw.csv`.
- **Données de référence totalement absentes** : le pays `NL` (Pays-Bas) a
  des ventes mais aucune ligne du tout dans `countries` (ni même
  inactive). Son `country_name` est fixé à `"Unknown"` dans la table
  finale `sales_by_country`.
- **Catégories hors du référentiel** : le vrai catalogue de livres
  (scrapé depuis books.toscrape.com) inclut des catégories non couvertes
  par `category_rules` (ex : `Poetry`, `Fiction`, `History`), le
  référentiel ne définissant qu'un sous-ensemble de 10 catégories pour cet
  exercice.

À cause de cela, `schema_final.sql` ne déclare volontairement **pas** de
`FOREIGN KEY` sur `sales.country_code`, `sales_by_country.country_code`,
ni `book_catalog.category` — une contrainte stricte y rejetterait une
part significative de données réelles. Voir le rapport final pour la
justification complète de chaque choix.

## Lancer l'API

S'assurer d'abord que la base finale `bookworld_final.db` existe (exécuter le pipeline une fois,
voir ci-dessus).

```bash
python api.py
```

L'API démarre sur `http://127.0.0.1:5000`. Endpoints disponibles :

| Méthode | Route | Authentification requise | Description |
|---|---|---|---|
| GET | `/health` | Non | Renvoie `{"status": "ok"}` si l'API fonctionne |
| GET | `/sales-by-country` | Oui (token) | Renvoie les données agrégées de ventes par pays en JSON |

`/sales-by-country` renvoie `503` si la base finale n'a pas encore été
créée (pipeline non exécuté), et `500` si une table est manquante ou
illisible de façon inattendue.

**Note technique.** L'API est développée avec **Flask**. `python api.py`
lance le serveur de développement intégré (Werkzeug) avec `debug=True` —
pratique en développement (rechargement automatique du code,
messages d'erreur détaillés dans le navigateur), mais **à ne pas utiliser
en production** : ce serveur n'est pas conçu pour gérer de la charge, et
le mode debug expose la stack trace complète en cas d'erreur, ce qui est
une faille de sécurité. Pour un déploiement réel, il faudrait servir
l'application avec un serveur WSGI de production comme Gunicorn ou
Waitress, et désactiver `debug`.

## Authentification (token)

`/sales-by-country` est protégée par un token simple, vérifié par rapport
à la variable d'environnement `BOOKWORLD_API_TOKEN`.

**Configuration :**
1. Copier `.env.example` en `.env` :
   ```bash
   cp .env.example .env
   ```
2. Ouvrir `.env` et définir sa propre valeur de token, par exemple :
   ```
   BOOKWORLD_API_TOKEN=votre_token_secret
   ```
3. Lancer l'API (`python api.py`) — elle lit le token depuis `.env`
   automatiquement via `python-dotenv`.

Appeler la route protégée avec `curl` :
```bash
curl -H "Authorization: Bearer votre_token_secret" http://127.0.0.1:5000/sales-by-country
```

Sans token valide, l'API renvoie `401 Unauthorized` :
```bash
curl http://127.0.0.1:5000/sales-by-country
# -> {"error": "Missing or malformed Authorization header"}
```

**Pourquoi un en-tête plutôt qu'un paramètre d'URL.** L'en-tête
`Authorization` est la pratique standard pour une API REST en
production : le token n'apparaît jamais dans l'URL, donc pas dans
l'historique du navigateur ni les journaux d'accès serveur — contrairement
à un paramètre `?token=...`, envisagé mais volontairement écarté ici.

## Résultats

Après une exécution complète (`pipeline.py` puis `python api.py`), la table finale `sales_by_country` contient :

| Colonne | Type | Description |
|---|---|---|
| `country_code` | texte | Code pays |
| `country_name` | texte | Nom du pays (`"Unknown"` si absent du référentiel, voir "Notes sur la qualité des données") |
| `total_orders` | entier | Nombre de commandes |
| `total_quantity` | entier | Nombre total d'exemplaires vendus |
| `total_revenue_gbp` | décimal | Revenu total en GBP |
| `total_revenue_eur` | décimal | Revenu total en EUR (converti via l'API Frankfurter) |

**Aperçu** (calculé à partir de `sales_raw.csv` + du catalogue scrapé, taux GBP→EUR du 13/07/2026) :

| country_code | country_name | total_orders | total_revenue_gbp | total_revenue_eur |
|---|---|---|---|---|
| DE | Germany | 40 | 4 014.70 £ | 4 654.65 € |
| FR | France | 56 | 3 979.20 £ | 4 613.49 € |
| BE | Belgium | 30 | 2 682.30 £ | 3 109.86 € |
| ES | Spain | 28 | 1 992.23 £ | 2 309.79 € |
| PT | Portugal | 20 | 1 985.03 £ | 2 301.44 € |
| IE | Ireland | 19 | 1 854.43 £ | 2 150.03 € |
| IT | Italy | 28 | 1 781.22 £ | 2 065.14 € |
| NL | Unknown | 19 | 1 769.83 £ | 2 051.94 € |

**Quelques observations :**
- Revenu total : ~20 059 £ (~23 256 €) sur 240 commandes.
- L'**Allemagne** et la **France** génèrent à elles seules plus de 39 % du revenu total.
- Le canal **WEB** domine largement (12 680 £, ~63 % du revenu), loin devant `APP` (4 375 £) et `MKT` (3 004 £).
- Le **Portugal** (`PT`, marqué inactif dans le référentiel) et les **Pays-Bas** (`NL`, absents du référentiel) génèrent malgré tout un revenu non négligeable — cohérent avec les incohérences documentées dans "Notes sur la qualité des données" plus haut.

*Ces chiffres varient légèrement à chaque exécution réelle : le taux de change GBP→EUR est récupéré en direct auprès de l'API Frankfurter et change chaque jour.*

## Limites connues

- **Données personnelles dans le fichier source versionné** : `sales_raw.csv` (colonnes `customer_first_name`/`customer_last_name`, voir "Dataset" ci-dessus) contient des noms de clients en clair et reste commité tel quel sur Git. La minimisation RGPD protège la base finale, pas ce fichier source — à anonymiser ou sortir du contrôle de version pour un usage réel.
- Trois relations ne sont pas garanties par une contrainte SQL
  `FOREIGN KEY`, en raison d'un référentiel incomplet par rapport aux
  données réelles (voir "Notes sur la qualité des données" ci-dessus).
- Le scraping web est séquentiel (pas de parallélisation, pas de délai
  entre requêtes) — acceptable pour ce volume (20 livres), mais à revoir
  pour un catalogue plus large.
- **Authentification simple** : un token unique partagé, sans expiration ni gestion multi-utilisateurs — suffisant pour l'exercice, mais à renforcer (JWT, rotation de tokens) pour un usage réel.
- **API accessible uniquement en local par défaut** : `http://127.0.0.1:5000` n'est joignable que depuis la machine qui exécute le serveur. Pour une démonstration ou un test par un tiers sans déploiement complet, un outil comme [ngrok](https://ngrok.com/) (`ngrok http 5000`) peut créer un tunnel public temporaire — pratique ponctuellement, pas pour de la production (URL changeante, machine devant rester allumée).

## Licence

Ce projet est distribué sous licence MIT : n'importe qui peut réutiliser, modifier ou redistribuer ce code, y compris à des fins commerciales, à condition de conserver la mention de l'auteur original. Le code est fourni "tel quel", sans garantie.

## Auteur

Pierre Rieber — [GitHub](https://github.com/prieber)
