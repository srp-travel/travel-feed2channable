# travel-feed2channable

Génération automatique du feed JSON Channable depuis le flux XML Showroomprivé Voyage.

## Architecture

```
GitHub Actions (cron 3h UTC)
    → télécharge XML SRP (64 Mo)
    → parse avec iterparse (faible mémoire)
    → filtre ventes actives
    → génère feed.json
    → commit dans le repo
    → Channable lit l'URL raw GitHub
```

## URL pour Channable

```
https://raw.githubusercontent.com/salah-cherkaoui/travel-feed2channable/main/feed.json
```

## Configuration GitHub Secrets

| Secret | Description |
|---|---|
| `XML_AUTH_USER` | Login d'accès au flux XML SRP |
| `XML_AUTH_PASS` | Mot de passe du flux XML SRP |

Ajouter dans : `Settings → Secrets and variables → Actions → New secret`

## Lancer manuellement

`GitHub → Actions → Generate Channable Feed → Run workflow`

## Structure du feed.json

Chaque entrée correspond à une offre active :

```json
[
  {
    "id": "149365_515916",
    "sale_id": "149365",
    "sale_url": "https://voyage.showroomprive.com/sale?id=463507",
    "sale_begin_date": "2025-11-15T07:00:00",
    "sale_end_date": "2026-06-15T08:00:00",
    "offer_id": "515916",
    "offer_name": "Autotour l'Albanie du Nord au Sud",
    "offer_url": "https://voyage.showroomprive.com/offer?id=515916",
    "country_code": "AL",
    "country": "Albanie",
    "city": "Tirana",
    "price": "650",
    "price_currency": "EUR",
    ...
  }
]
```

## Développement local

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt

# Variables d'environnement
set XML_AUTH_USER=ton_login
set XML_AUTH_PASS=ton_mdp

python main.py
```