import pandas as pd
import os
import json
import argparse


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
    parser = argparse.ArgumentParser(description='Deskriptiv statistikk for Finn-data')
    parser.add_argument('--profile', default='nissan_leaf',
                        help='Bilprofil fra config/cars/ (uten .json). Standard: nissan_leaf')
    args = parser.parse_args()

    car_profile = load_car_profile(args.profile)
    if car_profile:
        car_make  = car_profile['make']
        car_model = car_profile['model']
        label = f"{car_make} {car_model}"
    else:
        car_make = car_model = None
        label = "alle biler"

    print(f"--- Descriptive Statistics: {label} ---")
    data_path = "cleaned_data.csv"

    if not os.path.exists(data_path):
        print("Error: Missing data. Run 01_clean_data.py first.")
        return

    df = pd.read_csv(data_path)

    # Filtrer på bilmodell
    if car_make and car_model and 'car_make' in df.columns:
        df = df[(df['car_make'] == car_make) & (df['car_model'] == car_model)]
        print(f"Filtrert til {len(df)} rader for {label}.\n")

    print("1. Gjennomsnittspris og kilometer per årsmodell:")
    stats = df.groupby('year_cleaned').agg(
        Antall=('price_cleaned', 'count'),
        Snittpris=('price_cleaned', 'mean'),
        Snitt_KM=('mileage_cleaned', 'mean')
    ).round(0).astype({'Snittpris': int, 'Snitt_KM': int})
    print(stats.to_string())

    print("\n2. Fordeling av batterikapasitet:")
    battery_dist = df['battery_capacity_cleaned'].value_counts().reset_index()
    battery_dist.columns = ['Batteri (kWh)', 'Antall Biler']
    print(battery_dist.to_string(index=False))

    print("\n3. Snittpris fordelt på batterikapasitet:")
    price_by_batt = df.groupby('battery_capacity_cleaned')['price_cleaned'].mean().round(0).astype(int).reset_index()
    price_by_batt.columns = ['Batteri (kWh)', 'Snittpris']
    print(price_by_batt.to_string(index=False))

    if 'trim_level' in df.columns:
        print("\n4. Snittpris per utstyrsnivå (trim):")
        trim_stats = df.groupby('trim_level').agg(
            Antall=('price_cleaned', 'count'),
            Snittpris=('price_cleaned', 'mean'),
            Snitt_KM=('mileage_cleaned', 'mean')
        ).round(0).astype({'Snittpris': int, 'Snitt_KM': int}).sort_values('Snittpris', ascending=False)
        print(trim_stats.to_string())

    if 'region' in df.columns:
        print("\n5. Snittpris per region:")
        region_stats = df.groupby('region').agg(
            Antall=('price_cleaned', 'count'),
            Snittpris=('price_cleaned', 'mean'),
        ).round(0).astype({'Snittpris': int}).sort_values('Snittpris', ascending=False)
        print(region_stats.to_string())

    # --- Bonus: Status-fordeling ---
    if 'status' in df.columns:
        print("\n6. Status (Aktiv / Solgt):")
        print(df['status'].value_counts().to_string())

    print("\n------------------------------")


if __name__ == "__main__":
    main()
