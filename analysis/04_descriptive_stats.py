import pandas as pd
import os

def main():
    print("--- Descriptive Statistics ---")
    data_path = "cleaned_data.csv"
    
    if not os.path.exists(data_path):
        print("Error: Missing data. Run 01_clean_data.py first.")
        return
        
    df = pd.read_csv(data_path)
    
    print("\n1. Gjennomsnittspris og kilometer per årsmodell:")
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

    # --- Fase 1.1: Statistikk per utstyrsnivå ---
    if 'trim_level' in df.columns:
        print("\n4. Snittpris per utstyrsnivå (trim):")
        trim_stats = df.groupby('trim_level').agg(
            Antall=('price_cleaned', 'count'),
            Snittpris=('price_cleaned', 'mean'),
            Snitt_KM=('mileage_cleaned', 'mean')
        ).round(0).astype({'Snittpris': int, 'Snitt_KM': int}).sort_values('Snittpris', ascending=False)
        print(trim_stats.to_string())

    # --- Fase 1.2: Statistikk per region ---
    if 'region' in df.columns:
        print("\n5. Snittpris per region:")
        region_stats = df.groupby('region').agg(
            Antall=('price_cleaned', 'count'),
            Snittpris=('price_cleaned', 'mean'),
        ).round(0).astype({'Snittpris': int}).sort_values('Snittpris', ascending=False)
        print(region_stats.to_string())
    
    print("\n------------------------------")

if __name__ == "__main__":
    main()
