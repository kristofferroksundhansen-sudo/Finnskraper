"""
export_json.py – Eksporterer CSV-data til JSON-format for web-frontenden.
Kjøres etter 03_find_deals.py for å oppdatere webapp/public/data/.
"""
import pandas as pd
import json
import os
import glob
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'webapp', 'public', 'data')


def clean_for_json(df):
    """Fjern NaN og konverter til JSON-kompatible typer."""
    import math
    # Konverter til dict og håndter NaN/inf manuelt
    records = df.to_dict(orient='records')
    cleaned = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            if v is None:
                clean_row[k] = None
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                clean_row[k] = None
            elif isinstance(v, float):
                clean_row[k] = round(v, 1)
            else:
                clean_row[k] = v
        cleaned.append(clean_row)
    return cleaned


def export_profile(profile_name, deals_path, label):
    """Eksporter deals-data for én bilprofil til JSON."""
    if not os.path.exists(deals_path):
        print(f"  Fant ikke {deals_path}, hopper over {label}.")
        return

    df = pd.read_csv(deals_path)

    # Filtrer ut leasing/auksjon, men behold ALLE aktive annonser (over og under markedsverdi)
    df = df[df['price_cleaned'] >= 50000].copy()

    deals = clean_for_json(df)

    output = {
        'profile': profile_name,
        'label': label,
        'generated_at': datetime.now().isoformat(),
        'count': len(deals),
        'deals': deals
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f'{profile_name}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Eksportert {len(deals)} deals for {label} → {out_path}")
    return len(deals)


def main():
    print("--- Eksporterer data til JSON for webapp ---")

    # Finn alle best_deals_*.csv i project root
    deals_files = glob.glob(os.path.join(PROJECT_ROOT, 'best_deals_*.csv'))

    if not deals_files:
        print("Ingen best_deals_*.csv filer funnet. Kjør 03_find_deals.py --profile <profil> først.")
        return

    total = 0
    profile_list = []
    for deals_path in deals_files:
        basename = os.path.basename(deals_path)
        profile_name = basename.replace('best_deals_', '').replace('.csv', '')

        # Lag et lesbart navn
        label = profile_name.replace('_', ' ').title()

        count = export_profile(profile_name, deals_path, label)
        if count:
            total += count
            profile_list.append({'profile': profile_name, 'label': label, 'count': count})

    # Eksporter en index-fil med alle tilgjengelige profiler
    index = {
        'generated_at': datetime.now().isoformat(),
        'profiles': profile_list
    }
    index_path = os.path.join(OUTPUT_DIR, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\nFerdig! Totalt {total} deals eksportert for {len(profile_list)} bilmodeller.")
    print(f"Data tilgjengelig i: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
