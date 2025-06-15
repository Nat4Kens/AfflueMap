### Fichier `obtenirTempsAttente.py` optimisé


import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from functools import lru_cache

# Pré‑ouvrir une session pour réutiliser la connexion HTTP
session = requests.Session()
# Pré‑compiler les regex
RE_CHART_SCRIPT = re.compile(r"var createChart = function")
RE_JSON = re.compile(r"\[\{\"name\":.*?\}\]", re.DOTALL)
# Utiliser des guillemets simples autour de la regex pour éviter les conflits
RE_MONTH_CHART = re.compile(r'\[\{"name":"Temps d\'attente moyen global","data":(.*?)}\]', re.DOTALL)

# URLs des attractions
URLS = {
    #'Blue Fire': 'https://queue-times.com/fr/parks/51/rides/5603',
    'Blue Fire': 'https://queue-times.com/fr/parks/51/rides/5603?given_date=2025-06-07#date',
    'Voltron Nevera': 'https://queue-times.com/fr/parks/51/rides/13349',
    'Wodan':        'https://queue-times.com/fr/parks/51/rides/5602',
    'Euro-Mir':     'https://queue-times.com/fr/parks/51/rides/5605',
    'Voletarium':   'https://queue-times.com/fr/parks/51/rides/5630',
    'Pirates in Batavia': 'https://queue-times.com/fr/parks/51/rides/5617',
    'Silver Star':  'https://queue-times.com/fr/parks/51/rides/5604',
    'Arthur':       'https://queue-times.com/fr/parks/51/rides/5618',
    'Matterhorn-Blitz': 'https://queue-times.com/fr/parks/51/rides/5607',
    'Eurosat':      'https://queue-times.com/fr/parks/51/rides/5737',
    'Poseidon':     'https://queue-times.com/fr/parks/51/rides/5611'
}

@lru_cache(maxsize=None)
def fetch_page(url):
    """
    Retourne le texte HTML d'une URL en utilisant une session partagée.
    """
    resp = session.get(url)
    resp.raise_for_status()
    return resp.text

@lru_cache(maxsize=None)
def dernierTemps(attraction: str) -> float:
    """
    Renvoie le dernier temps d'attente signalé pour une attraction.
    """
    url = URLS.get(attraction)
    if not url:
        return 0.0

    html = fetch_page(url)
    soup = BeautifulSoup(html, 'html.parser')

    # Trouver le script de données
    script = soup.find('script', string=RE_CHART_SCRIPT)
    if not script:
        return 0.0

    match = RE_JSON.search(script.string)
    if not match:
        return 0.0

    data = json.loads(match.group())
    # Extraire la dernière entrée
    for series in data:
        if series['name'] == 'Signalé par le parc':
            last = series['data'][-1]
            return float(last[1])
    return 0.0

@lru_cache(maxsize=None)
def moyen(attraction: str, heure: int, periode: str) -> float:
    """
    Renvoie le temps d'attente moyen ajusté pour une attraction, une heure, et une période.
    """
    url = URLS.get(attraction)
    if not url:
        return 0.0

    html = fetch_page(url)
    soup = BeautifulSoup(html, 'html.parser')

    # Extraire données globales par mois
    script3 = soup.find('script', string=lambda t: t and 'chart-3' in t)
    match3 = RE_MONTH_CHART.search(script3.string)
    global_data = json.loads(f'[{{"data":{match3.group(1)}}}]')[0]["data"]
    global_map = {m:d for m,d in global_data}

    # Extraire données horaires
    script5 = soup.find('script', string=lambda t: t and 'chart-5' in t)
    match5 = RE_MONTH_CHART.search(script5.string)
    hourly_data = json.loads(f'[{{"data":{match5.group(1)}}}]')[0]["data"]
    hours_map = {h:d for h,d in hourly_data}

    # Ajuster par coefficient
    values = list(hours_map.values())
    avg = sum(values) / len(values) if values else 1
    coef = global_map.get(periode, avg) / avg
    return hours_map.get(heure, avg) * coef
