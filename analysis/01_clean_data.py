import json
import os
import glob
import pandas as pd
import re
from datetime import datetime
from dotenv import load_dotenv
from historical_db import extract_finn_id, load_historical_ids, append_new_data, load_all_data
from parsers import (
    parse_price, parse_mileage, parse_year, parse_battery, parse_effect,
    parse_owners, parse_condition_flag, parse_range_km, parse_warranty,
    parse_trim_level, parse_location
)

load_dotenv()


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
    total_before = len(df)

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

    # --- Fase 1.1: Parse utstyrsnivå (Trim) fra tittel, subtitle, og brødtekst ---
    df['trim_level'] = df.apply(
        lambda row: parse_trim_level(
            row.get('title', ''), 
            row.get('subtitle', ''), 
            row.get('description', '')
        ), 
        axis=1
    )

    # --- Fase 1.2: Mapper lokasjon til region + forhandler-deteksjon ---
    if 'location' in df.columns:
        loc_parsed = df['location'].apply(parse_location)
        df['city'] = loc_parsed.apply(lambda x: x[0])
        df['dealer_name'] = loc_parsed.apply(lambda x: x[1])
        df['is_dealer'] = loc_parsed.apply(lambda x: x[2])
        df['region'] = loc_parsed.apply(lambda x: x[3])
    else:
        df['city'] = ''
        df['dealer_name'] = ''
        df['is_dealer'] = 0
        df['region'] = 'Annet'

    # --- Fase 3.1: Rekkevidde (WLTP) ---
    range_col = [c for c in df.columns if 'Rekkevidde' in c and 'WLTP' in c]
    if range_col:
        df['range_km_cleaned'] = df[range_col[0]].apply(parse_range_km)
    elif 'spec_Rekkevidde' in df.columns:
        df['range_km_cleaned'] = df['spec_Rekkevidde'].apply(parse_range_km)
    else:
        df['range_km_cleaned'] = pd.NA

    # --- Fase 3.3: Garanti-info ---
    if 'spec_Garanti' in df.columns:
        df['has_warranty'] = df['spec_Garanti'].apply(parse_warranty)
    elif 'spec_Garantiens varighet' in df.columns:
        df['has_warranty'] = df['spec_Garantiens varighet'].apply(parse_warranty)
    else:
        df['has_warranty'] = pd.NA

    # --- Fase 1.4: Detaljert datatap-logging ---
    missing_price = df['price_cleaned'].isna().sum()
    missing_mileage = df['mileage_cleaned'].isna().sum()
    missing_year = df['year_cleaned'].isna().sum()

    # Drop rows where essential info is missing
    df = df.dropna(subset=['price_cleaned', 'mileage_cleaned', 'year_cleaned'])
    after_dropna = len(df)

    # Impute missing values dynamically via median
    for col in ['battery_capacity_cleaned', 'effect_cleaned', 'owners_cleaned', 'range_km_cleaned']:
        if col in df.columns:
            median_val = df[col].median()
            if pd.notnull(median_val):
                df[col] = df[col].fillna(median_val)
            else:
                # Fallback only if the entire column is NaN, though realistically this shouldn't happen with valid data
                df[col] = df[col].fillna(0)

    # Fast assumption for specific columns
    df['months_to_eu_cleaned'] = df['months_to_eu_cleaned'].fillna(12.0)
    df['has_warranty'] = df['has_warranty'].fillna(0)

    # Filter outliers
    before_outlier = len(df)
    df = df[(df['year_cleaned'] >= 2010) & (df['price_cleaned'] > 10000)]
    outlier_removed = before_outlier - len(df)

    # --- Logg datatap-sammendrag ---
    total_dropped = total_before - len(df)
    print(f"\n--- Datatap-analyse ({total_dropped}/{total_before} rader tapt, {total_dropped/total_before*100:.1f}%) ---")
    print(f"  Mangler pris:      {missing_price}")
    print(f"  Mangler km:        {missing_mileage}")
    print(f"  Mangler årsmodell: {missing_year}")
    print(f"  Dropna totalt:     {total_before - after_dropna}")
    print(f"  Outlier-filter:    {outlier_removed} (year<2010 eller price<=10000)")
    print(f"  Beholdt:           {len(df)} rader")

    # --- Trim-fordeling ---
    trim_counts = df['trim_level'].value_counts()
    print(f"\n--- Trim-fordeling ---")
    for trim, count in trim_counts.items():
        print(f"  {trim}: {count}")

    # --- Region-fordeling ---
    region_counts = df['region'].value_counts()
    print(f"\n--- Region-fordeling ---")
    for region, count in region_counts.items():
        print(f"  {region}: {count}")

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
        hist_cols = ['finn_id', 'title', 'url', 'location', 'city', 'dealer_name',
                     'is_dealer', 'region', 'price_cleaned', 'year_cleaned',
                     'mileage_cleaned', 'battery_capacity_cleaned', 'effect_cleaned',
                     'range_km_cleaned', 'months_to_eu_cleaned', 'owners_cleaned',
                     'has_condition_issue', 'has_warranty',
                     'trim_level', 'first_seen_date']
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
