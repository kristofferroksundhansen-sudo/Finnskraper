import json
import os
import glob
import pandas as pd
import re

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

def load_data_from_apify():
    import requests
    # Using the exact Dataset ID provided by the user
    url = "https://api.apify.com/v2/datasets/coaQqZ546k670rFMd/items?token=REDACTED"
    print("Fetching data directly from Apify dataset 'coaQqZ546k670rFMd'...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from API: {e}")
        return []

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
            # Map specifications back to the main dictionary
            for key, value in specs.items():
                flat_item[f"spec_{key}"] = value
                
        flattened_data.append(flat_item)
        
    df = pd.DataFrame(flattened_data)
    print(f"Loaded {len(df)} initial rows.")
    
    # Remove any duplicate listings (happens if the same car is scraped across multiple days)
    if 'url' in df.columns:
        initial_count = len(df)
        df = df.drop_duplicates(subset=['url'], keep='last')
        dropped = initial_count - len(df)
        if dropped > 0:
            print(f"Removed {dropped} duplicate ads from the historical database.")
    
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
        # Konverter dato fra format "30.04.2025"
        eu_dates = pd.to_datetime(df['spec_Neste frist for EU-kontroll'], format='%d.%m.%Y', errors='coerce')
        # Regn ut avstand fra dagens dato (forventer rundt i dag minus frist i antall dager / 30 for måneder)
        df['months_to_eu_cleaned'] = (eu_dates - pd.Timestamp.now()).dt.days / 30.0
    else:
        df['months_to_eu_cleaned'] = pd.NA
        
    # Drop rows where we couldn't parse essential ML info first
    df = df.dropna(subset=['price_cleaned', 'mileage_cleaned', 'year_cleaned'])
    
    # Impute missing values for battery and effect using median
    battery_median = df['battery_capacity_cleaned'].median()
    effect_median = df['effect_cleaned'].median()
    df['battery_capacity_cleaned'] = df['battery_capacity_cleaned'].fillna(battery_median if pd.notnull(battery_median) else 40)
    df['effect_cleaned'] = df['effect_cleaned'].fillna(effect_median if pd.notnull(effect_median) else 109)
    df['months_to_eu_cleaned'] = df['months_to_eu_cleaned'].fillna(12.0) # Assume average 12 months if unknown
    
    # Optional: Filter out obvious outliers (e.g., cars older than 2005 or price < 10000)
    df = df[(df['year_cleaned'] >= 2010) & (df['price_cleaned'] > 10000)]
    
    # Save the cleaned data
    output_path = "cleaned_data.csv"
    df.to_csv(output_path, index=False)
    
    print(f"Cleaning complete! Saved {len(df)} valid rows to {output_path}")
    print(df[['title', 'price_cleaned', 'year_cleaned', 'mileage_cleaned', 'battery_capacity_cleaned', 'effect_cleaned', 'months_to_eu_cleaned']].head())

if __name__ == "__main__":
    main()
