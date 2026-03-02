import json
import os
import glob
import pandas as pd
import re
from datetime import datetime
from dotenv import load_dotenv
from historical_db import extract_finn_id, load_historical_ids, append_new_data, load_all_data

load_dotenv()

def parse_price(price_str):
    if not isinstance(price_str, str):
        return None
    # Remove all non-numeric characters (e.g. "199 900 kr" -> 199900)
    num = re.sub(r'[^\d]', '', price_str)
    return int(num) if num else None

def parse_mileage(mileage_str):
    if not isinstance(mileage_str, str):
        return None
    # Usually "146 800 km" or "146800km"
    num = re.sub(r'[^\d]', '', mileage_str)
    return int(num) if num else None

def parse_year(year_str):
    if not isinstance(year_str, str):
        return None
    num = re.sub(r'[^\d]', '', year_str)
    return int(num) if num else None

def parse_battery(battery_str):
    if not isinstance(battery_str, str):
        return None
    num = re.sub(r'[^\d]', '', battery_str)
    return int(num) if num else None

def parse_effect(effect_str):
    if not isinstance(effect_str, str):
        return None
    num = re.sub(r'[^\d]', '', effect_str)
    return int(num) if num else None

def parse_owners(owners_str):
    """Parse 'Eiere' field, e.g. '1' or '2'."""
    if not isinstance(owners_str, str):
        return None
    num = re.sub(r'[^\d]', '', owners_str)
    return int(num) if num else None

def parse_condition_flag(value_str):
    """Returns 1 if a known defect is reported (Ja), 0 if not (Nei), None if unknown."""
    if not isinstance(value_str, str):
        return None
    v = value_str.strip().lower()
    if v in ('ja', 'yes'):
        return 1
    elif v in ('nei', 'no'):
        return 0
    return None

def load_data_from_apify():
    import requests
    dataset_id = os.getenv('APIFY_DATASET_ID')
    api_token  = os.getenv('APIFY_API_TOKEN')
    if not dataset_id or not api_token:
        raise EnvironmentError(
            "Mangler APIFY_DATASET_ID eller APIFY_API_TOKEN i .env-filen."
        )
    url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={api_token}"
    print(f"Fetching data from Apify dataset '{dataset_id}'...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from API: {e}")
        return []

def clean_dataframe(df):
    """Rens en DataFrame med rå annonsedata og returner rensede rader."""
    # Apply parsers
    df['price_cleaned'] = df['price'].apply(parse_price)
    df['mileage_cleaned'] = df['mileage'].apply(parse_mileage)
    df['year_cleaned'] = df['year'].apply(parse_year)

    if 'spec_Batterikapasitet' in df.columns:
        df['battery_capacity_cleaned'] = df['spec_Batterikapasitet'].apply(parse_battery)
    else:
        df['battery_capacity_cleaned'] = pd.NA

    if 'spec_Effekt' in df.columns:
        df['effect_cleaned'] = df['spec_Effekt'].apply(parse_effect)
    else:
        df['effect_cleaned'] = pd.NA

    if 'spec_Neste frist for EU-kontroll' in df.columns:
        eu_dates = pd.to_datetime(df['spec_Neste frist for EU-kontroll'], format='%d.%m.%Y', errors='coerce')
        df['months_to_eu_cleaned'] = (eu_dates - pd.Timestamp.now()).dt.days / 30.0
    else:
        df['months_to_eu_cleaned'] = pd.NA

    # Antall eiere
    if 'spec_Eiere' in df.columns:
        df['owners_cleaned'] = df['spec_Eiere'].apply(parse_owners)
    else:
        df['owners_cleaned'] = pd.NA

    # Tilstandsflagg
    condition_cols = [c for c in df.columns if c.startswith('spec_condition_')]
    if condition_cols:
        flag_matrix = df[condition_cols].apply(lambda col: col.map(parse_condition_flag))
        df['has_condition_issue'] = (flag_matrix == 1).any(axis=1).astype(int)
    else:
        df['has_condition_issue'] = 0

    # Drop rows where essential info is missing
    df = df.dropna(subset=['price_cleaned', 'mileage_cleaned', 'year_cleaned'])

    # Impute missing values
    battery_median = df['battery_capacity_cleaned'].median()
    effect_median = df['effect_cleaned'].median()
    owners_median = df['owners_cleaned'].median()
    df['battery_capacity_cleaned'] = df['battery_capacity_cleaned'].fillna(battery_median if pd.notnull(battery_median) else 40)
    df['effect_cleaned'] = df['effect_cleaned'].fillna(effect_median if pd.notnull(effect_median) else 109)
    df['months_to_eu_cleaned'] = df['months_to_eu_cleaned'].fillna(12.0)
    df['owners_cleaned'] = df['owners_cleaned'].fillna(owners_median if pd.notnull(owners_median) else 2)

    # Filter outliers
    df = df[(df['year_cleaned'] >= 2010) & (df['price_cleaned'] > 10000)]

    return df


def main():
    print("--- Starting Data Cleaning ---")

    # Read newly formatted data directly from the API
    data = load_data_from_apify()

    if not data:
        print("No data found to clean!")
        return

    # Flatten the nested 'specifications' dictionary if it exists
    flattened_data = []
    for item in data:
        flat_item = item.copy()
        specs = flat_item.pop('specifications', {})
        if specs:
            for key, value in specs.items():
                flat_item[f"spec_{key}"] = value
        flattened_data.append(flat_item)

    df = pd.DataFrame(flattened_data)
    print(f"Loaded {len(df)} rows from Apify.")

    # Ekstraher finn_id fra URL
    if 'url' in df.columns:
        df['finn_id'] = df['url'].apply(extract_finn_id)
    else:
        print("ADVARSEL: Ingen 'url'-kolonne funnet – kan ikke deduplisere.")
        df['finn_id'] = None

    # Fjern duplikater innad i denne batchen
    initial_count = len(df)
    df = df.drop_duplicates(subset=['finn_id'], keep='last')
    batch_dupes = initial_count - len(df)
    if batch_dupes > 0:
        print(f"Fjernet {batch_dupes} duplikater innad i batchen.")

    # Sjekk mot historisk database – filtrer bort allerede kjente annonser
    known_ids = load_historical_ids()
    new_mask = ~df['finn_id'].astype(str).isin(known_ids)
    skipped_count = (~new_mask).sum()
    df_new = df[new_mask].copy()
    print(f"Historisk DB inneholder {len(known_ids)} annonser.")
    print(f"Nye annonser denne kjøringen: {len(df_new)} (hoppet over {skipped_count} kjente)")

    # Rens de nye annonsene
    if not df_new.empty:
        df_new = clean_dataframe(df_new)
        df_new['first_seen_date'] = datetime.now().strftime('%Y-%m-%d')

        # Velg kolonner for historisk lagring
        hist_cols = ['finn_id', 'title', 'url', 'price_cleaned', 'year_cleaned',
                     'mileage_cleaned', 'battery_capacity_cleaned', 'effect_cleaned',
                     'months_to_eu_cleaned', 'owners_cleaned', 'has_condition_issue',
                     'first_seen_date']
        hist_cols = [c for c in hist_cols if c in df_new.columns]
        added = append_new_data(df_new[hist_cols])
        print(f"La til {added} nye rader i historisk database.")
    else:
        print("Ingen nye annonser å legge til.")

    # Last HELE historisk database for modelltrening
    df_all = load_all_data()
    if df_all.empty:
        print("Historisk database er tom – ingen data for modelltrening.")
        return

    output_path = "cleaned_data.csv"
    df_all.to_csv(output_path, index=False)

    print(f"\nSkrev {len(df_all)} rader til {output_path} (hele historisk DB)")
    preview_cols = ['title', 'price_cleaned', 'year_cleaned', 'mileage_cleaned',
                    'battery_capacity_cleaned', 'effect_cleaned',
                    'months_to_eu_cleaned', 'owners_cleaned', 'has_condition_issue']
    preview_cols = [c for c in preview_cols if c in df_all.columns]
    print(df_all[preview_cols].head())

if __name__ == "__main__":
    main()
