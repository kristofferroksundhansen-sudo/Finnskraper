"""
historical_db.py – Håndterer en lokal historisk database (CSV) for akkumulering
av skrapede Finn-annonser over tid.

Finn-annonse-ID (fra URL) brukes som unik nøkkel for deduplisering.
"""

import os
import re
import pandas as pd

DB_FILENAME = "historical_data.csv"


def get_db_path():
    """Returnerer absolutt sti til den historiske databasen."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)


def extract_finn_id(url):
    """Ekstraher Finn-annonse-ID fra URL, f.eks. 436036800 fra
    https://www.finn.no/mobility/item/436036800"""
    if not isinstance(url, str):
        return None
    match = re.search(r'/(\d+)(?:\?|$)', url)
    return match.group(1) if match else None


def load_historical_ids():
    """Leser eksisterende finn_id-er fra historisk database.
    Returnerer et set av ID-strenger."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return set()
    df = pd.read_csv(db_path, usecols=['finn_id'], dtype={'finn_id': str})
    return set(df['finn_id'].dropna().astype(str))


def append_new_data(new_df):
    """Appender nye rader til historisk database.
    Kun rader med finn_id som IKKE allerede finnes legges til.
    Returnerer antall nye rader som ble lagt til."""
    if new_df.empty:
        return 0

    db_path = get_db_path()
    existing_ids = load_historical_ids()

    # Filtrer ut rader vi allerede har
    new_df = new_df[~new_df['finn_id'].astype(str).isin(existing_ids)]

    if new_df.empty:
        return 0

    # Append til fil (opprett med header hvis den ikke eksisterer)
    write_header = not os.path.exists(db_path)
    new_df.to_csv(db_path, mode='a', header=write_header, index=False)
    return len(new_df)


def load_all_data():
    """Leser hele den historiske databasen. Returnerer en DataFrame."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame()
    return pd.read_csv(db_path)
