import pandas as pd
import joblib
import os
import json
import argparse
from datetime import datetime


def load_car_profile(profile_name):
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'config', 'cars', f'{profile_name}.json'
    )
    if not os.path.exists(config_path):
        return None
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Finn beste deals på Finn.no')
    parser.add_argument('--profile', default='nissan_leaf',
                        help='Bilprofil fra config/cars/ (uten .json). Standard: nissan_leaf')
    args = parser.parse_args()

    car_profile = load_car_profile(args.profile)
    if car_profile:
        car_make   = car_profile['make']
        car_model  = car_profile['model']
        model_path = f"model_{args.profile}.pkl"
        output_path = f"best_deals_{args.profile}.csv"
        print(f"--- Finding Best Deals: {car_make} {car_model} ---")
    else:
        car_make = car_model = None
        model_path  = "leaf_model.pkl"
        output_path = "best_deals.csv"
        print("--- Finding the Best Deals (alle biler) ---")

    data_path = "cleaned_data.csv"
    if not os.path.exists(data_path) or not os.path.exists(model_path):
        print(f"Error: Mangler {data_path} eller {model_path}. Kjør 01 og 02 først.")
        return

    df = pd.read_csv(data_path)

    # Filtrer på bilmodell
    if car_make and car_model and 'car_make' in df.columns:
        df = df[(df['car_make'] == car_make) & (df['car_model'] == car_model)]
        print(f"Filtrert til {len(df)} rader for {car_make} {car_model}.")

    # Kun aktive annonser
    if 'status' in df.columns:
        df = df[df['status'] == 'Aktiv']
        print(f"Kun aktive annonser: {len(df)} rader.")

    # Filtrer ut leasing og B2B-auksjon (priser < 50 000 kr er typisk ikke reelle forbrukerkjøp)
    MIN_PRICE = 50_000
    before_filter = len(df)
    df = df[df['price_cleaned'] >= MIN_PRICE]
    if before_filter - len(df) > 0:
        print(f"Filtrert ut {before_filter - len(df)} annonser under {MIN_PRICE:,} kr (leasing/auksjon).")

    saved = joblib.load(model_path)
    if not isinstance(saved, dict):
        print("Error: Utdatert modellformat. Kjør 02_train_model.py på nytt.")
        return

    model = saved['model']
    feature_cols = saved['feature_cols']

    # Calculate age and days_listed
    current_year = datetime.now().year
    df['age'] = current_year - df['year_cleaned']

    if 'first_seen_date' in df.columns:
        first_seen = pd.to_datetime(df['first_seen_date'], errors='coerce')
        if 'last_seen_date' in df.columns:
            last_seen = pd.to_datetime(df['last_seen_date'], errors='coerce').fillna(pd.Timestamp.now())
        else:
            last_seen = pd.Timestamp.now()
        df['days_listed'] = (last_seen - first_seen).dt.days.fillna(0).clip(lower=0)
    else:
        df['days_listed'] = 0

    # One-hot encode kategoriske variable
    if 'trim_level' in df.columns:
        df = pd.concat([df, pd.get_dummies(df['trim_level'], prefix='trim', dtype=int)], axis=1)
    if 'region' in df.columns:
        df = pd.concat([df, pd.get_dummies(df['region'], prefix='region', dtype=int)], axis=1)

    X = df.reindex(columns=feature_cols, fill_value=0)

    print("Predicting Market Value...")
    df['predicted_value'] = model.predict(X)
    df['value_difference'] = df['predicted_value'] - df['price_cleaned']

    df_sorted = df.sort_values(by='value_difference', ascending=False)
    df_sorted['predicted_value'] = df_sorted['predicted_value'].round(0).astype(int)
    df_sorted['value_difference'] = df_sorted['value_difference'].round(0).astype(int)

    columns_to_save = ['title', 'car_make', 'car_model', 'year_cleaned', 'mileage_cleaned',
                       'range_km_cleaned', 'months_to_eu_cleaned', 'owners_cleaned',
                       'has_condition_issue', 'has_warranty', 'trim_level', 'region',
                       'is_dealer', 'dealer_name', 'days_listed', 'status',
                       'price_cleaned', 'predicted_value', 'value_difference', 'url']
    columns_to_save = [c for c in columns_to_save if c in df_sorted.columns]
    df_sorted[columns_to_save].to_csv(output_path, index=False)

    print(f"Resultater lagret til {output_path}!\n")
    print(f"Top 5 Best Deals ({car_make or 'alle'} {car_model or ''}):")
    print("-" * 60)
    for index, row in df_sorted.head(5).iterrows():
        months_eu = int(row['months_to_eu_cleaned']) if pd.notnull(row.get('months_to_eu_cleaned')) else "?"
        trim = row.get('trim_level', '?')
        region = row.get('region', '?')
        seller_type = f"Forhandler ({row.get('dealer_name', '')})" if row.get('is_dealer', 0) == 1 else 'Privat'
        warn_str = " ⚠️FEIL!" if row.get('has_condition_issue', 0) == 1 else ""
        days = int(row.get('days_listed', 0))

        print(f"[{row['year_cleaned']}] {row['title']} ({trim}) - {row['mileage_cleaned']:,.0f} km{warn_str}")
        print(f"  {region} | {seller_type} | EU om {months_eu} mnd | {days} dager på Finn")
        print(f"  Prisforslag:  {row['price_cleaned']:,.0f} kr")
        print(f"  Markedsverdi: {row['predicted_value']:,} kr")
        print(f"  Rabatt:      +{row['value_difference']:,} kr")
        print(f"  Link: {row['url']}")
        print("-" * 60)


if __name__ == "__main__":
    main()
