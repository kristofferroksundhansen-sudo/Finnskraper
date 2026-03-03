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


def update_or_append_data(new_df):
    """
    Oppdaterer eksisterende rader med 'last_seen_date' og appender nye rader til historisk database.
    Returnerer tuple: (antall_nye_rader, antall_oppdaterte_rader)
    """
    if new_df.empty:
        return 0, 0

    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        # Hvis DB ikke eksisterer, skriv alt som nytt (og sett last_seen_date = first_seen_date hvis den mangler)
        if 'last_seen_date' not in new_df.columns:
            new_df['last_seen_date'] = new_df['first_seen_date']
        new_df.to_csv(db_path, index=False)
        return len(new_df), 0

    # Laster eksisterende database
    db_df = pd.read_csv(db_path, dtype={'finn_id': str})
    
    # Sørger for at 'last_seen_date' eksisterer i databasen
    if 'last_seen_date' not in db_df.columns:
        db_df['last_seen_date'] = db_df.get('first_seen_date', pd.Timestamp.now().strftime('%Y-%m-%d'))
        
    # Sørger for at status-kolonnen eksisterer
    if 'status' not in db_df.columns:
        db_df['status'] = 'Aktiv'

    new_ids = new_df['finn_id'].astype(str)
    existing_mask = db_df['finn_id'].astype(str).isin(new_ids)
    
    # 1. Oppdater last_seen_date og status for de annonsene som fortsatt finnes
    today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
    db_df.loc[existing_mask, 'last_seen_date'] = today_str
    
    # Standard antakelse er at de vi ser nå er Aktive
    db_df.loc[existing_mask, 'status'] = 'Aktiv'
    
    # Men hvis skraperen eksplisitt har merket dem som 'is_sold_flag' == 1, sett dem til Solgt
    if 'is_sold_flag' in new_df.columns:
        sold_in_new = new_df[new_df['is_sold_flag'] == 1]['finn_id'].astype(str)
        sold_mask = db_df['finn_id'].astype(str).isin(sold_in_new)
        db_df.loc[sold_mask, 'status'] = 'Solgt/Inaktiv'
        
    updated_count = existing_mask.sum()
    
    # Sett status til inaktiv for de vi ikke så i dag
    db_df.loc[~existing_mask, 'status'] = 'Solgt/Inaktiv'

    # 2. Finn nye rader som skal appenderes
    new_mask = ~new_ids.isin(db_df['finn_id'].astype(str))
    to_append = new_df[new_mask].copy()
    
    if not to_append.empty:
        if 'last_seen_date' not in to_append.columns:
            to_append['last_seen_date'] = today_str
            
        to_append['status'] = 'Aktiv'
        if 'is_sold_flag' in to_append.columns:
            to_append.loc[to_append['is_sold_flag'] == 1, 'status'] = 'Solgt/Inaktiv'
            # Vi trenger ikke lagre selve flagget i historisk DB, kun 'status'
            to_append = to_append.drop(columns=['is_sold_flag'])
            
        # Hvis new_df hadde is_sold_flag, men to_append ikke har det lenger, må vi fjerne det fra db_df hvis det snek seg inn
        if 'is_sold_flag' in db_df.columns:
             db_df = db_df.drop(columns=['is_sold_flag'])
        
        # Slett eventuelle kolonner som ikke hører hjemme hvis noe er usynkronisert
        db_df = pd.concat([db_df, to_append], ignore_index=True)

    # Skriv alt tilbake
    db_df.to_csv(db_path, index=False)
    
    return len(to_append), updated_count


def load_all_data():
    """Leser hele den historiske databasen. Returnerer en DataFrame."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return pd.DataFrame()
    return pd.read_csv(db_path)
